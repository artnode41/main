from flask import render_template, redirect, url_for, flash
from flask_security import login_required, current_user
from . import bp
from ...models import Artwork, ArtworkImage, Artist, ArtworkProvenance
from ...extensions import db
from .forms import ArtworkForm
from .provenance_forms import ProvenanceForm
from datetime import datetime, timezone


@bp.route("/artworks")
@login_required
def index():
    artworks = (
        Artwork.query
        .filter_by(tenant_id=current_user.tenant_id, active=True)
        .order_by(Artwork.id.desc())
        .all()
    )
    return render_template("artworks/index.html", artworks=artworks)


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
    artists = Artist.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Artist.last_name).all()
    form.artist_id.choices = [(0, "— Select —")] + [
        (a.id, f"{a.last_name}, {a.first_name}") for a in artists
    ]

    if form.validate_on_submit():
        artwork = Artwork(
            tenant_id=current_user.tenant_id,
            title=form.title.data,
            artist_id=form.artist_id.data if form.artist_id.data != 0 else None,
            year_from=form.year_from.data,
            year_to=form.year_to.data,
            medium=form.medium.data,
            dimensions=form.dimensions.data,
            description=form.description.data,
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
        )
        db.session.add(artwork)
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
    artists = Artist.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Artist.last_name).all()
    form.artist_id.choices = [(0, "— Select —")] + [
        (a.id, f"{a.last_name}, {a.first_name}") for a in artists
    ]

    if form.validate_on_submit():
        artwork.title = form.title.data
        artwork.artist_id = form.artist_id.data if form.artist_id.data != 0 else None
        artwork.year_from = form.year_from.data
        artwork.year_to = form.year_to.data
        artwork.medium = form.medium.data
        artwork.dimensions = form.dimensions.data
        artwork.description = form.description.data
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
        db.session.commit()
        flash("Artwork updated successfully.", "success")
        return redirect(url_for("artworks.detail", id=artwork.id))

    return render_template("artworks/form.html", form=form, artwork=artwork)


@bp.route("/artworks/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
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
            recorded_by_id=current_user.id,
        )
        db.session.add(entry)
        db.session.commit()
        flash("Provenance record added.", "success")
        return redirect(url_for("artworks.detail", id=artwork.id))
    return render_template("artworks/provenance_form.html", form=form, artwork=artwork)
