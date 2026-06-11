from flask import render_template, redirect, url_for, flash, request, Response
from flask_security import login_required, current_user
from flask import Blueprint
from ...models import Gallery
from ...extensions import db
from .forms import GallerySettingsForm

bp = Blueprint("settings", __name__, url_prefix="/admin/settings")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    gallery = Gallery.query.filter_by(id=current_user.tenant_id).first_or_404()
    form = GallerySettingsForm(obj=gallery)
    if request.method == "GET":
        form.maintenance_mode.data = gallery.maintenance_mode or False

    if form.validate_on_submit():
        gallery.name = form.name.data
        gallery.public_name = form.public_name.data or None
        gallery.tagline = form.tagline.data or None
        gallery.about_text = form.about_text.data or None
        gallery.address = form.address.data or None
        gallery.zip_code = form.zip_code.data or None
        gallery.city = form.city.data or None
        gallery.country = form.country.data or "CH"
        gallery.phone = form.phone.data or None
        gallery.email = form.email.data or None
        gallery.contact_email = form.contact_email.data or None
        gallery.website = form.website.data or None
        gallery.maintenance_mode = request.form.get("maintenance_mode") == "y"
        gallery.instagram_url = form.instagram_url.data or None
        gallery.currency = form.currency.data or "CHF"
        gallery.locale = form.locale.data or "de"
        gallery.vat_number = form.vat_number.data or None
        gallery.iban = form.iban.data or None
        gallery.vat_scheme_default = form.vat_scheme_default.data or "standard"
        # Save gallery translations
        from flask import request as _req
        trans = gallery.translations or {}
        for lang in ["de", "fr", "it", "en"]:
            if lang not in trans:
                trans[lang] = {}
            trans[lang]["tagline"] = _req.form.get(f"trans_tagline_{lang}", "").strip()
            trans[lang]["about_text"] = _req.form.get(f"trans_about_{lang}", "").strip()
        gallery.translations = trans
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(gallery, 'translations')
        db.session.commit()
        flash("Settings saved successfully.", "success")
        return redirect(url_for("settings.index"))

    return render_template("settings/index.html", form=form, gallery=gallery)


@bp.route("/logo", methods=["POST"])
@login_required
def upload_logo():
    from flask import request, current_app
    import io, os
    from minio import Minio
    from minio.error import S3Error

    if "logo" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("settings.index"))

    file = request.files["logo"]
    if not file.filename.lower().endswith(".png"):
        flash("Only PNG files are accepted.", "error")
        return redirect(url_for("settings.index"))

    data = file.read()
    if len(data) > 200 * 1024:
        flash("File too large. Maximum size is 200KB.", "error")
        return redirect(url_for("settings.index"))

    gallery = Gallery.query.filter_by(id=current_user.tenant_id).first_or_404()

    try:
        import base64
        data_b64 = base64.b64encode(data).decode('utf-8')
        gallery.logo_url = f"data:image/png;base64,{data_b64}"
        db.session.commit()
        flash("Logo uploaded successfully.", "success")
    except Exception as e:
        flash(f"Upload failed: {str(e)}", "error")

    return redirect(url_for("settings.index"))


@bp.route("/logo/delete", methods=["POST"])
@login_required
def delete_logo():
    gallery = Gallery.query.filter_by(id=current_user.tenant_id).first_or_404()
    gallery.logo_url = None
    db.session.commit()
    flash("Logo removed.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/export")
@login_required
def export():
    from flask import current_app, request
    from ...models import User
    user = User.query.filter_by(email=current_user.email).first()
    token = user.get_auth_token() if user else None
    base_url = request.host_url.rstrip("/")
    return render_template("settings/export.html",
                           token=token,
                           base_url=base_url)


@bp.route("/export/lido-download")
@login_required
def export_lido_download():
    from flask import Response
    from ...lido import build_lido_wrap, serialize
    from ...models import Artwork, Gallery
    artworks = Artwork.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).all()
    gallery = Gallery.query.filter_by(id=current_user.tenant_id).first()
    root = build_lido_wrap(artworks, gallery)
    xml_out = serialize(root)
    return Response(
        xml_out,
        mimetype="application/xml",
        headers={"Content-Disposition": "attachment; filename=collection-lido.xml"}
    )


@bp.route("/users")
@login_required
def users():
    from ...models import User, Role
    users = User.query.filter_by(tenant_id=current_user.tenant_id).order_by(User.created_at).all()
    roles = Role.query.all()
    return render_template("settings/users.html", users=users, roles=roles)


@bp.route("/users/invite", methods=["POST"])
@login_required
def invite_user():
    from flask import request
    from ...models import User, Role
    from ...extensions import db
    import uuid, secrets
    from ...models import user_datastore

    email = request.form.get("email", "").strip().lower()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    role_name = request.form.get("role", "staff")

    if not email:
        flash("Email is required.", "error")
        return redirect(url_for("settings.users"))

    if User.query.filter_by(email=email).first():
        flash("A user with this email already exists.", "error")
        return redirect(url_for("settings.users"))

    # Ensure role exists
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        role = Role(name=role_name, description=role_name.capitalize())
        db.session.add(role)
        db.session.commit()

    # Create user with random password
    from flask_security.utils import hash_password
    user = user_datastore.create_user(
        email=email,
        password=hash_password(secrets.token_urlsafe(32)),
        first_name=first_name,
        last_name=last_name,
        active=True,
    )
    user.tenant_id = current_user.tenant_id
    user_datastore.add_role_to_user(user, role)
    db.session.commit()

    # Send invitation email with password reset link
    try:
        from flask_security.recoverable import generate_reset_password_token
        from flask_mail import Message
        from flask import current_app, url_for
        token = generate_reset_password_token(user)
        reset_url = url_for("security.reset_password", token=token, _external=True)
        mail = current_app.extensions.get("mail")
        if mail:
            msg = Message(
                subject="You have been invited to ArtNode",
                recipients=[email],
                body=f"You have been invited to ArtNode.\n\nClick the link below to set your password and access the gallery admin:\n\n{reset_url}\n\nThis link expires in 24 hours."
            )
            mail.send(msg)
        flash(f"Invitation sent to {email}.", "success")
    except Exception as e:
        flash(f"User created but email failed: {str(e)}", "error")

    return redirect(url_for("settings.users"))


@bp.route("/users/<int:id>/delete", methods=["POST"])
@login_required
def delete_user(id):
    from ...models import User
    if id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("settings.users"))
    user = User.query.filter_by(id=id, tenant_id=current_user.tenant_id).first_or_404()
    db.session.delete(user)
    db.session.commit()
    flash(f"{user.email} deleted.", "success")
    return redirect(url_for("settings.users"))


@bp.route("/users/<int:id>/role", methods=["POST"])
@login_required
def set_user_role(id):
    from flask import request
    from ...models import User, Role
    from ...models import user_datastore
    user = User.query.filter_by(id=id, tenant_id=current_user.tenant_id).first_or_404()
    role_name = request.form.get("role", "staff")
    # Remove existing admin/staff roles
    for r in list(user.roles):
        if r.name in ("admin", "staff"):
            user_datastore.remove_role_from_user(user, r)
    # Add new role
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        role = Role(name=role_name, description=role_name.capitalize())
        db.session.add(role)
        db.session.commit()
    user_datastore.add_role_to_user(user, role)
    db.session.commit()
    flash(f"{user.email} role updated to {role_name}.", "success")
    return redirect(url_for("settings.users"))


@bp.route("/export/estv-csv")
@login_required
def export_estv_csv():
    import csv, io
    from flask import Response
    from ...models import Sale, SaleLineItem
    from decimal import Decimal

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = SaleLineItem.query.join(Sale).filter(
        Sale.tenant_id == current_user.tenant_id,
        SaleLineItem.tax_method == "margin"
    )
    if date_from:
        query = query.filter(Sale.invoice_date >= date_from)
    if date_to:
        query = query.filter(Sale.invoice_date <= date_to)
    lines = query.order_by(Sale.invoice_date).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Stock ID", "Artwork", "Artist",
        "Purchase Date", "Purchase Invoice No.",
        "Purchase Price (CHF)",
        "Invoice No.", "Invoice Date", "Sale Price (CHF)",
        "Margin (CHF)", "VAT Owed (CHF)"
    ])

    total_margin = Decimal("0")
    total_vat = Decimal("0")

    for line in lines:
        artwork = line.artwork
        sale = line.sale
        purchase_price = line.purchase_price_at_sale or Decimal("0")
        margin = max(Decimal("0"), line.price - purchase_price)
        vat = (margin - margin / Decimal("1.081")).quantize(Decimal("0.01")) if margin > 0 else Decimal("0")
        total_margin += margin
        total_vat += vat
        # Get purchase details from acquisition provenance event
        from ...models import ArtworkProvenance
        acq_prov = ArtworkProvenance.query.filter_by(
            artwork_id=artwork.id, event_type="acquisition"
        ).order_by(ArtworkProvenance.recorded_at.desc()).first()
        purchase_invoice_no = acq_prov.purchase_invoice_number if acq_prov else ""
        purchase_date = acq_prov.event_date.strftime("%d.%m.%Y") if acq_prov and acq_prov.event_date else (
            artwork.acquisition_date.strftime("%d.%m.%Y") if artwork.acquisition_date else ""
        )
        writer.writerow([
            artwork.inventory_number or f"ART-{artwork.id}",
            artwork.title,
            f"{artwork.contact_artist.last_name} {artwork.contact_artist.first_name}" if artwork.contact_artist else "",
            purchase_date,
            purchase_invoice_no,
            str(purchase_price),
            sale.invoice_number,
            sale.invoice_date.strftime("%d.%m.%Y") if sale.invoice_date else "",
            str(line.price),
            str(margin),
            str(vat),
        ])

    # Totals row
    writer.writerow([])
    writer.writerow(["", "", "", "", "", "", "TOTAL", "", str(total_margin), str(total_vat)])

    output.seek(0)
    filename = f"ESTV_Margensteuer_{date_from or 'all'}_{date_to or 'all'}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
