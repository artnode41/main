from flask import render_template, redirect, url_for, flash
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
        gallery.website_custom_domain = form.website_custom_domain.data or None
        gallery.instagram_url = form.instagram_url.data or None
        gallery.logo_url = form.logo_url.data or None
        gallery.currency = form.currency.data or "CHF"
        gallery.locale = form.locale.data or "de"
        gallery.vat_number = form.vat_number.data or None
        gallery.iban = form.iban.data or None
        gallery.vat_scheme_default = form.vat_scheme_default.data or "standard"
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
