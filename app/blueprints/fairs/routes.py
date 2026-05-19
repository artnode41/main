from datetime import datetime, timezone
from decimal import Decimal
from flask import render_template, redirect, url_for, flash, request, Response
from flask_security import login_required, current_user
from . import bp
from ...models import ArtFair, Artwork, Sale, SaleLineItem, Contact, ArtworkConsignment, Gallery
from ...extensions import db
from .forms import ArtFairForm


def get_gallery():
    return Gallery.query.filter_by(id=current_user.tenant_id).first()


@bp.route("/")
@login_required
def index():
    fairs = (
        ArtFair.query
        .filter_by(tenant_id=current_user.tenant_id, active=True)
        .order_by(ArtFair.start_date.desc())
        .all()
    )
    return render_template("fairs/index.html", fairs=fairs)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ArtFairForm()
    if form.validate_on_submit():
        fair = ArtFair(
            tenant_id=current_user.tenant_id,
            name=form.name.data,
            location=form.location.data or None,
            start_date=datetime.combine(form.start_date.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.start_date.data else None,
            end_date=datetime.combine(form.end_date.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.end_date.data else None,
        )
        db.session.add(fair)
        db.session.commit()
        flash("Art fair created.", "success")
        return redirect(url_for("fairs.detail", id=fair.id))
    return render_template("fairs/form.html", form=form, fair=None)


@bp.route("/<int:id>")
@login_required
def detail(id):
    fair = ArtFair.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    # Available artworks not already in this fair
    fair_artwork_ids = {s.line_items[0].artwork_id for s in fair.sales if s.line_items}
    available = Artwork.query.filter_by(
        tenant_id=current_user.tenant_id,
        status="available",
        active=True
    ).order_by(Artwork.id.desc()).all()
    return render_template("fairs/detail.html", fair=fair, available=available, fair_artwork_ids=fair_artwork_ids)


@bp.route("/<int:id>/pos")
@login_required
def pos(id):
    fair = ArtFair.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    # Artworks assigned to this fair that are still available
    fair_artwork_ids = {s.line_items[0].artwork_id for s in fair.sales if s.line_items and s.status != "cancelled"}
    artworks = Artwork.query.filter(
        Artwork.tenant_id == current_user.tenant_id,
        Artwork.id.in_(fair_artwork_ids),
        Artwork.status == "available",
        Artwork.active == True
    ).all() if fair_artwork_ids else []
    contacts = Contact.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Contact.last_name).all()
    return render_template("fairs/pos.html", fair=fair, artworks=artworks, contacts=contacts)


@bp.route("/<int:id>/pos/sell/<int:artwork_id>", methods=["POST"])
@login_required
def pos_sell(id, artwork_id):
    fair = ArtFair.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    artwork = Artwork.query.filter_by(
        id=artwork_id,
        tenant_id=current_user.tenant_id,
        status="available"
    ).first_or_404()

    price = Decimal(str(request.form.get("price", artwork.price or 0)))
    currency = request.form.get("currency", "CHF")
    buyer_id = int(request.form.get("buyer_id", 0)) or None
    payment_method = request.form.get("payment_method", "cash")

    # Consignment split
    gallery_net = price
    consignor_net = Decimal("0.00")
    consignment = ArtworkConsignment.query.filter_by(artwork_id=artwork.id, active=True).first()
    if consignment and artwork.is_consignment:
        gallery_pct = Decimal(str(consignment.gallery_split_pct)) / 100
        gallery_net = (price * gallery_pct).quantize(Decimal("0.01"))
        consignor_net = (price - gallery_net).quantize(Decimal("0.01"))

    # Invoice number
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

    sale = Sale(
        tenant_id=current_user.tenant_id,
        art_fair_id=fair.id,
        status="confirmed",
        invoice_number=invoice_number,
        invoice_date=datetime.now(timezone.utc),
        vat_scheme="standard",
        notes=f"Art Fair POS — {fair.name} — {payment_method}",
        created_by_id=current_user.id,
    )
    db.session.add(sale)
    db.session.flush()

    line_item = SaleLineItem(
        sale_id=sale.id,
        artwork_id=artwork.id,
        buyer_id=buyer_id,
        price=price,
        currency=currency,
        gallery_net=gallery_net,
        consignor_net=consignor_net,
        vat_rate=Decimal("0"),
        vat_amount=Decimal("0"),
    )
    db.session.add(line_item)
    artwork.status = "sold"
    db.session.commit()

    flash(f"Sale recorded: {artwork.title} — {currency} {price:,.0f}", "success")
    return redirect(url_for("fairs.pos", id=fair.id))


@bp.route("/<int:id>/report")
@login_required
def report(id):
    from weasyprint import HTML
    fair = ArtFair.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    gallery = get_gallery()
    confirmed_sales = [s for s in fair.sales if s.status not in ("cancelled",)]
    total_revenue = sum(
        (s.line_items[0].price if s.line_items else 0)
        for s in confirmed_sales
    )
    html_content = render_template(
        "fairs/report.html",
        fair=fair,
        gallery=gallery,
        confirmed_sales=confirmed_sales,
        total_revenue=total_revenue,
    )
    pdf_bytes = HTML(string=html_content).write_pdf()
    filename = f"fair_report_{fair.name.replace(' ', '_')}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@bp.route("/<int:id>/assign/<int:artwork_id>", methods=["POST"])
@login_required
def assign_artwork(id, artwork_id):
    """Mark an artwork as brought to the fair (creates a placeholder sale record)."""
    fair = ArtFair.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    artwork = Artwork.query.filter_by(
        id=artwork_id,
        tenant_id=current_user.tenant_id
    ).first_or_404()

    # Check not already assigned
    already = any(
        l.artwork_id == artwork_id
        for s in fair.sales
        for l in s.line_items
        if s.status != "cancelled"
    )
    if already:
        flash("Artwork already assigned to this fair.", "error")
        return redirect(url_for("fairs.detail", id=fair.id))

    # Create a draft sale to track assignment
    sale = Sale(
        tenant_id=current_user.tenant_id,
        art_fair_id=fair.id,
        status="draft",
        notes=f"Assigned to fair: {fair.name}",
        created_by_id=current_user.id,
    )
    db.session.add(sale)
    db.session.flush()

    line_item = SaleLineItem(
        sale_id=sale.id,
        artwork_id=artwork.id,
        price=artwork.price or Decimal("0"),
        currency=artwork.currency or "CHF",
        gallery_net=artwork.price or Decimal("0"),
        consignor_net=Decimal("0"),
        vat_rate=Decimal("0"),
        vat_amount=Decimal("0"),
    )
    db.session.add(line_item)
    db.session.commit()

    flash(f"{artwork.title} assigned to {fair.name}.", "success")
    return redirect(url_for("fairs.detail", id=fair.id))
