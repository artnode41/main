from decimal import Decimal
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, Response, request
from flask_security import login_required, current_user
from . import bp
from ...models import Sale, SaleLineItem, Artwork, Contact, ArtworkConsignment, Gallery
from ...extensions import db
from .forms import SaleForm


def get_gallery():
    return Gallery.query.filter_by(id=current_user.tenant_id).first()


def calc_profit(line):
    """
    Calculate gallery profit for a sale line item.
    - Consignment: gallery_net already calculated from split
    - Owned: profit = sale price - acquisition cost
    Returns (gallery_profit, consignor_due, profit_label)
    """
    artwork = line.artwork
    if artwork.ownership_type == "consignment" or artwork.is_consignment:
        return line.gallery_net, line.consignor_net, "Gallery Commission"
    else:
        acq = artwork.acquisition_cost or Decimal("0")
        profit = line.price - acq
        return profit, Decimal("0"), "Gallery Profit (after acquisition cost)"


@bp.route("/")
@login_required
def index():
    sales = (
        Sale.query
        .filter_by(tenant_id=current_user.tenant_id)
        .order_by(Sale.created_at.desc())
        .all()
    )
    # Calculate totals
    total_revenue = Decimal("0")
    total_profit = Decimal("0")
    total_consignor = Decimal("0")
    for sale in sales:
        if sale.status not in ("cancelled", "draft") and sale.line_items:
            line = sale.line_items[0]
            total_revenue += line.price
            gp, cd, _ = calc_profit(line)
            total_profit += gp
            total_consignor += cd

    return render_template("sales/index.html", sales=sales,
                           total_revenue=total_revenue,
                           total_profit=total_profit,
                           total_consignor=total_consignor)


@bp.route("/new/<int:artwork_id>", methods=["GET", "POST"])
@login_required
def create(artwork_id):
    artwork = Artwork.query.filter_by(
        id=artwork_id, tenant_id=current_user.tenant_id
    ).first_or_404()

    form = SaleForm()
    contacts = Contact.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Contact.last_name).all()
    form.buyer_id.choices = [(0, "— Select buyer —")] + [
        (c.id, f"{c.last_name} {c.first_name}" if c.contact_type == "individual"
         else c.organisation or f"{c.last_name} {c.first_name}")
        for c in contacts
    ]

    if not form.price.data and artwork.price:
        form.price.data = artwork.price
    if not form.currency.data or form.currency.data == "CHF":
        form.currency.data = artwork.currency or "CHF"

    if form.validate_on_submit():
        price = Decimal(str(form.price.data))
        vat_rate = Decimal(str(form.vat_rate.data or 0))
        vat_amount = (price * vat_rate / 100).quantize(Decimal("0.01"))

        # Profit calculation depends on ownership type
        if artwork.ownership_type == "consignment" or artwork.is_consignment:
            consignment = ArtworkConsignment.query.filter_by(
                artwork_id=artwork.id, active=True
            ).first()
            if consignment:
                gallery_pct = Decimal(str(consignment.gallery_split_pct)) / 100
                gallery_net = (price * gallery_pct).quantize(Decimal("0.01"))
                consignor_net = (price - gallery_net).quantize(Decimal("0.01"))
            else:
                gallery_net = price
                consignor_net = Decimal("0.00")
        else:
            # Owned: gallery keeps full price, profit = price - acquisition_cost
            gallery_net = price
            consignor_net = Decimal("0.00")

        year = datetime.now(timezone.utc).year
        last_sale = Sale.query.filter(
            Sale.tenant_id == current_user.tenant_id,
            Sale.invoice_number.isnot(None)
        ).order_by(Sale.id.desc()).first()

        last_seq = 0
        if last_sale and last_sale.invoice_number:
            try:
                last_seq = int(last_sale.invoice_number.split("-")[-1])
            except (ValueError, IndexError):
                pass

        invoice_number = f"INV-{year}-{last_seq + 1:04d}"
        gallery = get_gallery()
        vat_scheme = (gallery.vat_scheme_default if gallery else None) or "standard"

        sale = Sale(
            tenant_id=current_user.tenant_id,
            status="confirmed",
            invoice_number=invoice_number,
            invoice_date=datetime.now(timezone.utc),
            vat_scheme=vat_scheme,
            notes=form.notes.data or None,
            created_by_id=current_user.id,
        )
        db.session.add(sale)
        db.session.flush()

        line_item = SaleLineItem(
            sale_id=sale.id,
            artwork_id=artwork.id,
            buyer_id=form.buyer_id.data if form.buyer_id.data != 0 else None,
            price=price,
            currency=form.currency.data,
            gallery_net=gallery_net,
            consignor_net=consignor_net,
            vat_rate=vat_rate,
            vat_amount=vat_amount,
        )
        db.session.add(line_item)
        artwork.status = "sold"
        db.session.commit()

        flash("Sale recorded successfully.", "success")
        return redirect(url_for("sales.detail", id=sale.id))

    return render_template("sales/form.html", form=form, artwork=artwork)


@bp.route("/<int:id>")
@login_required
def detail(id):
    sale = Sale.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    profit_data = None
    if sale.line_items:
        gp, cd, label = calc_profit(sale.line_items[0])
        profit_data = {"gallery_profit": gp, "consignor_due": cd, "label": label}
    return render_template("sales/detail.html", sale=sale, profit_data=profit_data)


@bp.route("/<int:id>/invoice")
@login_required
def invoice(id):
    from weasyprint import HTML
    sale = Sale.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    if not sale.line_items:
        flash("No line items found for this sale.", "error")
        return redirect(url_for("sales.detail", id=sale.id))
    line = sale.line_items[0]
    gallery = get_gallery()
    html_content = render_template("sales/invoice.html", sale=sale, line=line, gallery=gallery)
    pdf_bytes = HTML(string=html_content).write_pdf()
    filename = f"invoice_{sale.invoice_number or sale.id}.pdf"
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@bp.route("/<int:id>/payment-link", methods=["POST"])
@login_required
def payment_link(id):
    from flask import current_app
    from ...payments.payrexx import get_payment_provider
    sale = Sale.query.filter_by(id=id, tenant_id=current_user.tenant_id).first_or_404()
    if not sale.line_items:
        flash("No line items found.", "error")
        return redirect(url_for("sales.detail", id=sale.id))
    line = sale.line_items[0]
    provider = get_payment_provider(current_app)
    if not provider:
        flash("Payment provider not configured.", "error")
        return redirect(url_for("sales.detail", id=sale.id))
    try:
        total = line.price + (line.vat_amount or 0)
        buyer_email = line.buyer.email if line.buyer else None
        buyer_name = None
        if line.buyer:
            if line.buyer.contact_type == "individual":
                buyer_name = f"{line.buyer.first_name} {line.buyer.last_name}".strip()
            else:
                buyer_name = line.buyer.organisation
        result = provider.create_payment_link(
            amount=total, currency=line.currency,
            reference=sale.invoice_number or str(sale.id),
            description=line.artwork.title[:100],
            buyer_email=buyer_email, buyer_name=buyer_name,
        )
        sale.payment_link_url = result.payment_url
        sale.payment_provider_id = result.payment_id
        sale.status = "on_hold"
        db.session.commit()
        flash("Payment link created. Sale is now on hold.", "success")
    except Exception as e:
        flash(f"Payment link error: {str(e)}", "error")
    return redirect(url_for("sales.detail", id=sale.id))


@bp.route("/<int:id>/mark-paid", methods=["POST"])
@login_required
def mark_paid(id):
    sale = Sale.query.filter_by(id=id, tenant_id=current_user.tenant_id).first_or_404()
    sale.status = "paid"
    db.session.commit()
    flash("Sale marked as paid.", "success")
    return redirect(url_for("sales.detail", id=sale.id))


@bp.route("/<int:id>/cancel", methods=["POST"])
@login_required
def cancel(id):
    from flask import current_app
    from ...payments.payrexx import get_payment_provider
    sale = Sale.query.filter_by(id=id, tenant_id=current_user.tenant_id).first_or_404()
    if sale.payment_provider_id:
        try:
            provider = get_payment_provider(current_app)
            if provider:
                provider.delete_payment_link(sale.payment_provider_id)
        except Exception:
            pass
    for line in sale.line_items:
        line.artwork.status = "available"
    sale.status = "cancelled"
    db.session.commit()
    flash("Sale cancelled. Artwork status restored to available.", "success")
    return redirect(url_for("sales.index"))


@bp.route("/webhook/payrexx", methods=["POST"])
def webhook_payrexx():
    # Accept form, JSON, or raw body
    data = {}
    if request.content_type and "json" in request.content_type:
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception:
            pass
    if not data:
        data = request.form.to_dict() if request.form else {}
    if not data:
        try:
            import json
            data = json.loads(request.data.decode("utf-8")) or {}
        except Exception:
            pass
    reference_id = (
        data.get("transaction[referenceId]") or
        data.get("referenceId") or
        (data.get("transaction", {}) or {}).get("referenceId")
    )
    status = (
        data.get("transaction[status]") or
        data.get("status") or
        (data.get("transaction", {}) or {}).get("status")
    )
    if not reference_id:
        return {"status": "ignored"}, 200
    sale = Sale.query.filter_by(invoice_number=reference_id).first()
    if not sale:
        return {"status": "not_found"}, 200
    if status in ("confirmed", "authorized"):
        sale.status = "paid"
        db.session.commit()
    elif status in ("declined", "cancelled"):
        for line in sale.line_items:
            line.artwork.status = "available"
        sale.status = "cancelled"
        db.session.commit()
    return {"status": "ok"}, 200
