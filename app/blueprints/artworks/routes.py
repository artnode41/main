from flask import render_template, redirect, url_for, flash, request
from flask_security import login_required, current_user
from . import bp
from ...models import Artwork, ArtworkImage, ArtworkProvenance, ArtworkConsignment, Contact, Gallery
from ...extensions import db
from .forms import ArtworkForm
from .provenance_forms import ProvenanceForm
from datetime import datetime, timezone
from decimal import Decimal


def _get_artist_choices(tenant_id):
    from ...models import Contact
    artists = Contact.query.filter(
        Contact.tenant_id == tenant_id,
        Contact.active == True,
        Contact.roles.contains(["artist"])
    ).order_by(Contact.last_name).all()
    return [(0, "— Select —")] + [(a.id, f"{a.last_name}, {a.first_name or ''}".strip(", ")) for a in artists]


def _get_contact_choices(tenant_id):
    contacts = Contact.query.filter_by(tenant_id=tenant_id, active=True).order_by(Contact.last_name).all()
    result = [(0, "— Select consignor —")]
    for c in contacts:
        name = f"{c.last_name} {c.first_name}" if c.contact_type == "individual" else (c.organisation or f"{c.last_name}")
        result.append((c.id, name))
    return result


def _save_consignment(artwork, form):
    """Create or update the ArtworkConsignment record."""
    consignment = artwork.consignment
    if not consignment:
        consignment = ArtworkConsignment(
            artwork_id=artwork.id,
            tenant_id=artwork.tenant_id,
        )
        db.session.add(consignment)

    consignment.consignor_id = form.consignor_id.data if form.consignor_id.data != 0 else None
    consignment.gallery_split_pct = form.gallery_split_pct.data or Decimal("50")
    consignment.start_date = datetime.combine(form.consignment_start.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.consignment_start.data else None
    consignment.end_date = datetime.combine(form.consignment_end.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.consignment_end.data else None
    consignment.terms = form.consignment_terms.data or None
    consignment.active = True


@bp.route("/artworks")
@login_required
def index():
    from flask import request
    q = request.args.get("q", "").strip().lower()
    query = Artwork.query.filter_by(tenant_id=current_user.tenant_id, active=True)
    artworks = query.order_by(Artwork.id.desc()).all()
    return render_template("artworks/index.html", artworks=artworks, search_query=q)


@bp.route("/artworks/<int:id>")
@login_required
def detail(id):
    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    return render_template("artworks/detail.html", artwork=artwork)


@bp.route("/artworks/new", methods=["GET", "POST"])
@login_required
def create():
    form = ArtworkForm()
    form.artist_id.choices = _get_artist_choices(current_user.tenant_id)
    form.consignor_id.choices = _get_contact_choices(current_user.tenant_id)

    if form.validate_on_submit():
        artwork = Artwork(
            tenant_id=current_user.tenant_id,
            title=form.title.data,
            contact_artist_id=form.artist_id.data if form.artist_id.data != 0 else None,
            year_from=form.year_from.data,
            year_to=form.year_to.data,
            medium=form.medium.data,
            dimensions=form.dimensions.data,
            description=form.description.data,
            translations={lang: {
                "description": request.form.get(f"trans_description_{lang}", "").strip(),
                "medium": request.form.get(f"trans_medium_{lang}", "").strip(),
            } for lang in ["de", "fr", "it", "en"]},
            object_type=form.object_type.data or None,
            status=form.status.data,
            price=form.price.data,
            currency=form.currency.data,
            ownership_type=form.ownership_type.data,
            is_consignment=(form.ownership_type.data == "consignment"),
            acquisition_cost=form.acquisition_cost.data if form.ownership_type.data == "owned" else None,
            acquisition_date=datetime.combine(form.acquisition_date.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.acquisition_date.data and form.ownership_type.data == "owned" else None,
            inventory_number=form.inventory_number.data or None,
            rights=form.rights.data or None,
            credit_line=form.credit_line.data or None,
            is_public=form.is_public.data,
            is_carousel=form.is_carousel.data,
            is_featured=form.is_featured.data,
        )
        db.session.add(artwork)
        db.session.flush()

        if form.ownership_type.data == "consignment":
            _save_consignment(artwork, form)

        db.session.commit()
        flash("Artwork added successfully.", "success")
        return redirect(url_for("artworks.detail", id=artwork.id))

    return render_template("artworks/form.html", form=form, artwork=None)


@bp.route("/artworks/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    form = ArtworkForm(obj=artwork)
    form.artist_id.choices = _get_artist_choices(current_user.tenant_id)
    form.consignor_id.choices = _get_contact_choices(current_user.tenant_id)
    if request_is_get():
        form.is_public.data = artwork.is_public if artwork.is_public is not None else True
        form.is_carousel.data = artwork.is_carousel or False
        form.is_featured.data = artwork.is_featured or False
        form.artist_id.data = artwork.contact_artist_id or 0

    # Pre-fill consignment fields from existing record
    if request_is_get() and artwork.consignment:
        c = artwork.consignment
        form.consignor_id.data = c.consignor_id or 0
        form.gallery_split_pct.data = c.gallery_split_pct
        form.consignment_start.data = c.start_date.date() if c.start_date else None
        form.consignment_end.data = c.end_date.date() if c.end_date else None
        form.consignment_terms.data = c.terms

    if form.validate_on_submit():
        artwork.title = form.title.data
        artwork.contact_artist_id = form.artist_id.data if form.artist_id.data != 0 else None
        artwork.year_from = form.year_from.data
        artwork.year_to = form.year_to.data
        artwork.medium = form.medium.data
        artwork.dimensions = form.dimensions.data
        artwork.description = form.description.data
        trans = artwork.translations or {}
        for lang in ["de", "fr", "it", "en"]:
            if lang not in trans:
                trans[lang] = {}
            trans[lang]["description"] = request.form.get(f"trans_description_{lang}", "").strip()
            trans[lang]["medium"] = request.form.get(f"trans_medium_{lang}", "").strip()
        artwork.translations = trans
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(artwork, 'translations')
        artwork.object_type = form.object_type.data or None
        artwork.status = form.status.data
        artwork.price = form.price.data
        artwork.currency = form.currency.data
        artwork.ownership_type = form.ownership_type.data
        artwork.is_consignment = (form.ownership_type.data == "consignment")
        artwork.acquisition_cost = form.acquisition_cost.data if form.ownership_type.data == "owned" else None
        artwork.acquisition_date = datetime.combine(form.acquisition_date.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.acquisition_date.data and form.ownership_type.data == "owned" else None
        artwork.inventory_number = form.inventory_number.data or None
        artwork.rights = form.rights.data or None
        artwork.credit_line = form.credit_line.data or None
        artwork.is_public = bool(form.is_public.data)
        artwork.is_carousel = bool(form.is_carousel.data)
        artwork.is_featured = bool(form.is_featured.data)

        if form.ownership_type.data == "consignment":
            _save_consignment(artwork, form)
        elif artwork.consignment:
            artwork.consignment.active = False

        db.session.commit()
        flash("Artwork updated successfully.", "success")
        return redirect(url_for("artworks.detail", id=artwork.id))

    return render_template("artworks/form.html", form=form, artwork=artwork)


def request_is_get():
    from flask import request
    return request.method == "GET"


@bp.route("/artworks/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    import os
    from minio import Minio
    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    # Delete images from MinIO
    minio_keys = [img.minio_key for img in artwork.images if img.minio_key]
    if minio_keys:
        try:
            client = Minio(
                os.environ.get("MINIO_ENDPOINT", "garage:3900"),
                access_key=os.environ.get("MINIO_ROOT_USER"),
                secret_key=os.environ.get("MINIO_ROOT_PASSWORD"),
                secure=False,
                region="garage"
            )
            bucket = os.environ.get("MINIO_BUCKET", "artnode-media")
            for key in minio_keys:
                client.remove_object(bucket, key)
        except Exception:
            pass
    artwork.active = False
    db.session.commit()
    flash("Artwork removed from collection.", "success")
    return redirect(url_for("artworks.index"))


@bp.route("/artworks/<int:id>/provenance/add", methods=["GET", "POST"])
@login_required
def provenance_add(id):
    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    form = ProvenanceForm()
    if form.validate_on_submit():
        entry = ArtworkProvenance(
            artwork_id=artwork.id,
            tenant_id=current_user.tenant_id,
            event_type=form.event_type.data,
            event_date=form.event_date.data,
            event_date_end=form.event_date_end.data,
            source_name=form.source_name.data or None,
            source_country=form.source_country.data.upper() if form.source_country.data else None,
            description=form.description.data or None,
            purchase_invoice_number=form.purchase_invoice_number.data or None,
            supplier_address=form.supplier_address.data or None,
            supplier_vat_status=form.supplier_vat_status.data or None,
            purchase_price=form.purchase_price.data or None,
            right_of_disposal=form.right_of_disposal.data,
            retention_30yr=form.retention_30yr.data,
            recorded_by_id=current_user.id,
            attached_files=[],
        )
        db.session.add(entry)
        db.session.flush()  # get entry.id before commit

        # Handle file uploads
        from flask import request
        import io, os
        files = request.files.getlist("attached_files")
        uploaded_paths = []
        allowed_ext = {".pdf", ".jpg", ".jpeg", ".xlsx", ".png"}
        for f in files:
            if not f or not f.filename:
                continue
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in allowed_ext:
                continue
            data = f.read()
            if len(data) > 10 * 1024 * 1024:  # 10MB limit
                flash(f"File {f.filename} too large (max 10MB), skipped.", "warning")
                continue
            try:
                from minio import Minio
                client = Minio(
                    os.environ.get("MINIO_ENDPOINT", "garage:3900"),
                    access_key=os.environ.get("MINIO_ROOT_USER", os.environ.get("MINIO_ROOT_USER")),
                    secret_key=os.environ.get("MINIO_ROOT_PASSWORD", ""),
                    secure=False,
                )
                bucket = os.environ.get("MINIO_BUCKET", "artnode-media")
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
                import uuid
                safe_name = f"{uuid.uuid4().hex}{ext}"
                object_name = f"provenance/{artwork.id}/{entry.id}/{safe_name}"
                content_types = {".pdf": "application/pdf", ".jpg": "image/jpeg",
                                  ".jpeg": "image/jpeg", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                  ".png": "image/png"}
                client.put_object(bucket, object_name, io.BytesIO(data), len(data),
                                  content_type=content_types.get(ext, "application/octet-stream"))
                uploaded_paths.append(f"{object_name}|{f.filename}")
            except Exception as e:
                flash(f"Upload failed for {f.filename}: {e}", "error")

        entry.attached_files = uploaded_paths
        db.session.commit()
        flash("Provenance record added.", "success")
        return redirect(url_for("artworks.detail", id=artwork.id))
    return render_template("artworks/provenance_form.html", form=form, artwork=artwork)


@bp.route("/<int:artwork_id>/provenance/<int:prov_id>/anchor", methods=["POST"])
@login_required
def anchor_provenance(artwork_id, prov_id):
    from flask import current_app
    artwork = Artwork.query.filter_by(
        id=artwork_id, tenant_id=current_user.tenant_id
    ).first_or_404()
    prov = ArtworkProvenance.query.filter_by(
        id=prov_id, artwork_id=artwork_id
    ).first_or_404()
    gallery = Gallery.query.get(current_user.tenant_id)
    from ...kgtg import anchor_provenance as do_anchor
    gpg_key_id = current_app.config.get("GPG_KEY_ID")
    result = do_anchor(prov, artwork, gallery, gpg_key_id=gpg_key_id)
    if result["status"] == "ok":
        flash(f"Provenance anchored. SHA-256: {result['hash'][:16]}… Steps: {', '.join(result['steps'])}", "success")
    else:
        flash(f"Anchoring failed: {result.get('error', 'unknown error')}", "error")
    return redirect(url_for("artworks.detail", id=artwork_id))


@bp.route("/<int:artwork_id>/provenance/<int:prov_id>/download-pdf")
@login_required
def download_provenance_pdf(artwork_id, prov_id):
    from flask import Response
    artwork = Artwork.query.filter_by(
        id=artwork_id, tenant_id=current_user.tenant_id
    ).first_or_404()
    prov = ArtworkProvenance.query.filter_by(
        id=prov_id, artwork_id=artwork_id
    ).first_or_404()
    gallery = Gallery.query.get(current_user.tenant_id)
    from ...kgtg import generate_provenance_pdf
    pdf_bytes = generate_provenance_pdf(prov, artwork, gallery)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="provenance_{prov_id}.pdf"'}
    )


@bp.route("/<int:artwork_id>/provenance/<int:prov_id>/file/<int:file_idx>")
@login_required
def download_provenance_file(artwork_id, prov_id, file_idx):
    from flask import Response
    import io, os
    prov = ArtworkProvenance.query.filter_by(
        id=prov_id, artwork_id=artwork_id
    ).first_or_404()
    files = prov.attached_files or []
    if file_idx >= len(files):
        abort(404)
    entry = files[file_idx]
    parts = entry.split("|", 1)
    object_name = parts[0]
    filename = parts[1] if len(parts) > 1 else object_name.split("/")[-1]
    try:
        from minio import Minio
        client = Minio(
            os.environ.get("MINIO_ENDPOINT", "garage:3900"),
            access_key=os.environ.get("MINIO_ROOT_USER", os.environ.get("MINIO_ROOT_USER")),
            secret_key=os.environ.get("MINIO_ROOT_PASSWORD", ""),
            secure=False,
        )
        bucket = os.environ.get("MINIO_BUCKET", "artnode-media")
        response = client.get_object(bucket, object_name)
        data = response.read()
        ext = os.path.splitext(filename)[1].lower()
        content_types = {".pdf": "application/pdf", ".jpg": "image/jpeg",
                         ".jpeg": "image/jpeg", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         ".png": "image/png"}
        ct = content_types.get(ext, "application/octet-stream")
        return Response(data, mimetype=ct,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except Exception as e:
        flash(f"Download failed: {e}", "error")
        return redirect(url_for("artworks.detail", id=artwork_id))




@bp.route("/<int:id>/images/upload", methods=["POST"])
@login_required
def upload_image(id):
    from flask import current_app
    from ...models import ArtworkImage
    from ...extensions import db
    import uuid

    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()

    if "image" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("artworks.detail", id=id))

    file = request.files["image"]
    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        flash("Only JPG and PNG files are accepted.", "error")
        return redirect(url_for("artworks.detail", id=id))

    data = file.read()
    if len(data) > 10 * 1024 * 1024:
        flash("File too large. Maximum size is 10MB.", "error")
        return redirect(url_for("artworks.detail", id=id))

    ext = "jpg" if file.filename.lower().endswith((".jpg", ".jpeg")) else "png"
    content_type = "image/jpeg" if ext == "jpg" else "image/png"
    object_name = f"images/{current_user.tenant_id}/{id}/{uuid.uuid4().hex}.{ext}"

    try:
        url = current_app.upload_to_minio(data, object_name, content_type)
        sort_order = len(artwork.images)
        img = ArtworkImage(
            artwork_id=id,
            minio_key=object_name,
            iiif_url=url,
            sort_order=sort_order,
        )
        db.session.add(img)
        db.session.commit()
        flash("Image uploaded.", "success")
    except Exception as e:
        flash(f"Upload failed: {str(e)}", "error")

    return redirect(url_for("artworks.detail", id=id))


@bp.route("/<int:id>/images/<int:image_id>/delete", methods=["POST"])
@login_required
def delete_image(id, image_id):
    from flask import current_app
    from ...models import ArtworkImage
    from ...extensions import db
    import os
    from minio import Minio

    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    img = ArtworkImage.query.filter_by(id=image_id, artwork_id=id).first_or_404()

    # Delete from MinIO if it has a minio_key
    if img.minio_key:
        try:
            client = Minio(
                os.environ.get("MINIO_ENDPOINT", "garage:3900"),
                access_key=os.environ.get("MINIO_ROOT_USER"),
                secret_key=os.environ.get("MINIO_ROOT_PASSWORD"),
                secure=False,
                region="garage"
            )
            bucket = os.environ.get("MINIO_BUCKET", "artnode-media")
            client.remove_object(bucket, img.minio_key)
        except Exception:
            pass

    db.session.delete(img)
    db.session.commit()
    flash("Image deleted.", "success")
    return redirect(url_for("artworks.detail", id=id))
