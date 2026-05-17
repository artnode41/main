from flask import render_template, redirect, url_for, flash
from flask_security import login_required, current_user
from . import bp
from ...models import Artist, Artwork
from ...extensions import db
from .forms import ArtistForm
from sqlalchemy import func


@bp.route("/")
@login_required
def index():
    artists = (
        db.session.query(Artist, func.count(Artwork.id).label("artwork_count"))
        .outerjoin(Artwork, (Artwork.artist_id == Artist.id) & (Artwork.active == True))
        .filter(Artist.tenant_id == current_user.tenant_id)
        .filter(Artist.active == True)
        .group_by(Artist.id)
        .order_by(Artist.last_name)
        .all()
    )
    return render_template("artists/index.html", artists=artists)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ArtistForm()
    if form.validate_on_submit():
        artist = Artist(
            tenant_id=current_user.tenant_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            birth_year=form.birth_year.data,
            death_year=form.death_year.data,
            nationality=form.nationality.data or None,
            biography=form.biography.data or None,
            website=form.website.data or None,
        )
        db.session.add(artist)
        db.session.commit()
        flash("Artist added successfully.", "success")
        return redirect(url_for("artists.index"))
    return render_template("artists/form.html", form=form, artist=None)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    artist = Artist.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    form = ArtistForm(obj=artist)
    if form.validate_on_submit():
        artist.first_name = form.first_name.data
        artist.last_name = form.last_name.data
        artist.birth_year = form.birth_year.data
        artist.death_year = form.death_year.data
        artist.nationality = form.nationality.data or None
        artist.biography = form.biography.data or None
        artist.website = form.website.data or None
        db.session.commit()
        flash("Artist updated successfully.", "success")
        return redirect(url_for("artists.index"))
    return render_template("artists/form.html", form=form, artist=artist)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    artist = Artist.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    artist.active = False
    db.session.commit()
    flash("Artist removed.", "success")
    return redirect(url_for("artists.index"))
