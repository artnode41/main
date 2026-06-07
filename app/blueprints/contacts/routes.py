from flask import render_template, redirect, url_for, flash, request
from flask_security import login_required, current_user
from . import bp
from ...models import Contact, Artwork
from ...extensions import db
from .forms import ContactForm, ROLE_CATEGORIES


def _save_contact_from_form(contact, form):
    from flask import request
    # Collect roles from checkboxes (not a WTForms field)
    selected_roles = request.form.getlist("roles")
    # Always handle artist role separately via is_artist checkbox
    # but include other selected roles
    existing_roles = list(contact.roles or [])
    artist_in_roles = "artist" in existing_roles
    # Rebuild roles: keep artist flag from is_artist checkbox, add others
    new_roles = [r for r in selected_roles if r != "artist"]
    contact.roles = new_roles
    contact.contact_type = form.contact_type.data
    contact.first_name = form.first_name.data or None
    contact.last_name = form.last_name.data or None
    contact.organisation = form.organisation.data or None
    contact.email = form.email.data or None
    contact.phone = form.phone.data or None
    contact.address = form.address.data or None
    contact.zip_code = form.zip_code.data or None
    contact.city = form.city.data or None
    contact.country = form.country.data.upper() if form.country.data else None
    contact.notes = form.notes.data or None

    # Handle artist role
    roles = list(contact.roles or [])
    if form.is_artist.data:
        if 'artist' not in roles:
            roles.append('artist')
        # Merge with non-artist roles already set
        for r in (contact.roles or []):
            if r != 'artist' and r not in roles:
                roles.append(r)
        contact.biography = form.biography.data or None
        # Save biography translations
        from flask import request as _req
        trans = contact.translations or {}
        for lang in ["de", "fr", "it", "en"]:
            val = _req.form.get(f"trans_biography_{lang}", "").strip()
            if lang not in trans:
                trans[lang] = {}
            trans[lang]["biography"] = val
        contact.translations = trans
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(contact, 'translations')
        contact.birth_year = form.birth_year.data
        contact.death_year = form.death_year.data
        contact.nationality = form.nationality.data or None
        contact.artist_website = form.artist_website.data or None
        contact.is_active_representation = form.is_active_representation.data
        # Auto-generate sort_name
        if contact.last_name:
            contact.sort_name = f"{contact.last_name}, {contact.first_name or ''}".strip(", ")
    else:
        if 'artist' in roles:
            roles.remove('artist')
        contact.is_active_representation = False

    contact.roles = roles


@bp.route("/")
@login_required
def index():
    role_filter = request.args.get("role")
    query = Contact.query.filter_by(tenant_id=current_user.tenant_id, active=True)
    if role_filter:
        query = query.filter(Contact.roles.contains([role_filter]))
    contacts = query.order_by(Contact.last_name).all()
    return render_template("contacts/index.html", contacts=contacts, role_filter=role_filter)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ContactForm()
    # Pre-check artist if coming from ?role=artist
    if request.method == "GET" and request.args.get("role") == "artist":
        form.is_artist.data = True

    if form.validate_on_submit():
        contact = Contact(tenant_id=current_user.tenant_id, active=True, roles=[])
        _save_contact_from_form(contact, form)
        db.session.add(contact)
        db.session.commit()
        flash("Contact added successfully.", "success")
        return redirect(url_for("contacts.detail", id=contact.id))
    return render_template("contacts/form.html", form=form, contact=None, role_categories=ROLE_CATEGORIES)


@bp.route("/<int:id>")
@login_required
def detail(id):
    contact = Contact.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    artworks = []
    if 'artist' in (contact.roles or []):
        artworks = Artwork.query.filter_by(
            contact_artist_id=contact.id, active=True
        ).order_by(Artwork.id.desc()).all()
    return render_template("contacts/detail.html", contact=contact, artworks=artworks)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    contact = Contact.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    form = ContactForm(obj=contact)

    if request.method == "GET":
        form.is_artist.data = 'artist' in (contact.roles or [])
        form.is_active_representation.data = contact.is_active_representation or False

    if form.validate_on_submit():
        _save_contact_from_form(contact, form)
        db.session.commit()
        flash("Contact updated successfully.", "success")
        return redirect(url_for("contacts.detail", id=contact.id))
    return render_template("contacts/form.html", form=form, contact=contact, role_categories=ROLE_CATEGORIES)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    contact = Contact.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    contact.active = False
    db.session.commit()
    flash("Contact removed.", "success")
    return redirect(url_for("contacts.index"))


@bp.route("/<int:id>/photo", methods=["POST"])
@login_required
def upload_photo(id):
    from flask import request, current_app
    from PIL import Image
    import io, base64

    contact = Contact.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()

    if "photo" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("contacts.edit", id=id))

    file = request.files["photo"]
    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        flash("Only JPG and PNG files are accepted.", "error")
        return redirect(url_for("contacts.edit", id=id))

    data = file.read()
    if len(data) > 500 * 1024:
        flash("File too large. Maximum size is 500KB.", "error")
        return redirect(url_for("contacts.edit", id=id))

    # Check square dimensions
    try:
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        if w != h:
            flash(f"Image must be square. Yours is {w}×{h}px.", "error")
            return redirect(url_for("contacts.edit", id=id))
    except Exception:
        flash("Could not read image file.", "error")
        return redirect(url_for("contacts.edit", id=id))

    ext = "jpeg" if file.filename.lower().endswith((".jpg", ".jpeg")) else "png"
    b64 = base64.b64encode(data).decode("utf-8")
    contact.photo_url = f"data:image/{ext};base64,{b64}"
    db.session.commit()
    flash("Photo uploaded.", "success")
    return redirect(url_for("contacts.edit", id=id))


@bp.route("/<int:id>/photo/delete", methods=["POST"])
@login_required
def delete_photo(id):
    contact = Contact.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    contact.photo_url = None
    db.session.commit()
    flash("Photo removed.", "success")
    return redirect(url_for("contacts.edit", id=id))
