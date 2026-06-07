from flask import render_template, redirect, url_for, flash, request
from flask_security import login_required, current_user
from flask import Blueprint
from ...models import Exhibition, ExhibitionArtwork, Artwork
from ...extensions import db
from .forms import ExhibitionForm
from datetime import datetime, timezone

bp = Blueprint("exhibitions", __name__, url_prefix="/admin/exhibitions")


@bp.route("/")
@login_required
def index():
    exhibitions = Exhibition.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Exhibition.start_date.desc()).all()
    return render_template("exhibitions/index.html", exhibitions=exhibitions)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ExhibitionForm()
    if form.validate_on_submit():
        exhibition = Exhibition(
            tenant_id=current_user.tenant_id,
            title=form.title.data,
            description=form.description.data or None,
            translations={lang: {"description": request.form.get(f"trans_description_{lang}", "").strip()}
                         for lang in ["de", "fr", "it", "en"]},
            venue=form.venue.data or None,
            start_date=datetime.combine(form.start_date.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.start_date.data else None,
            end_date=datetime.combine(form.end_date.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.end_date.data else None,
            is_active_show=form.is_active_show.data,
        )
        db.session.add(exhibition)
        db.session.commit()
        flash("Exhibition created.", "success")
        return redirect(url_for("exhibitions.detail", id=exhibition.id))
    return render_template("exhibitions/form.html", form=form, exhibition=None)


@bp.route("/<int:id>")
@login_required
def detail(id):
    exhibition = Exhibition.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    assigned_ids = {ea.artwork_id for ea in exhibition.artworks}
    available = Artwork.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Artwork.id.desc()).all()
    return render_template("exhibitions/detail.html",
                           exhibition=exhibition,
                           available=available,
                           assigned_ids=assigned_ids)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    exhibition = Exhibition.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    form = ExhibitionForm(obj=exhibition)
    if request.method == "GET":
        form.start_date.data = exhibition.start_date.date() if exhibition.start_date else None
        form.end_date.data = exhibition.end_date.date() if exhibition.end_date else None
        form.is_active_show.data = exhibition.is_active_show or False
        form.is_active_show.data = exhibition.is_active_show or False
    if request.method == "POST":
        from flask import current_app
        current_app.logger.warning(f"POST data keys: {list(request.form.keys())}")
        current_app.logger.warning(f"trans_de: {request.form.get('trans_description_de', 'NOT FOUND')[:50]}")
        current_app.logger.warning(f"form valid: {form.validate()}, errors: {form.errors}")
    if form.validate_on_submit():
        exhibition.title = form.title.data
        exhibition.description = form.description.data or None
        trans = exhibition.translations or {}
        for lang in ["de", "fr", "it", "en"]:
            val = request.form.get(f"trans_description_{lang}", "").strip()
            if lang not in trans:
                trans[lang] = {}
            trans[lang]["description"] = val
        from sqlalchemy.orm.attributes import flag_modified
        exhibition.translations = trans
        flag_modified(exhibition, "translations")
        exhibition.venue = form.venue.data or None
        exhibition.start_date = datetime.combine(form.start_date.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.start_date.data else None
        exhibition.end_date = datetime.combine(form.end_date.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.end_date.data else None
        exhibition.is_active_show = form.is_active_show.data
        db.session.commit()
        flash("Exhibition updated.", "success")
        return redirect(url_for("exhibitions.detail", id=exhibition.id))
    return render_template("exhibitions/form.html", form=form, exhibition=exhibition)


@bp.route("/<int:id>/assign/<int:artwork_id>", methods=["POST"])
@login_required
def assign(id, artwork_id):
    exhibition = Exhibition.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    existing = ExhibitionArtwork.query.filter_by(
        exhibition_id=id, artwork_id=artwork_id
    ).first()
    if not existing:
        ea = ExhibitionArtwork(
            exhibition_id=id,
            artwork_id=artwork_id,
            sort_order=len(exhibition.artworks),
        )
        db.session.add(ea)
        db.session.commit()
        flash("Artwork added to exhibition.", "success")
    return redirect(url_for("exhibitions.detail", id=id))


@bp.route("/<int:id>/remove/<int:artwork_id>", methods=["POST"])
@login_required
def remove(id, artwork_id):
    ea = ExhibitionArtwork.query.filter_by(
        exhibition_id=id, artwork_id=artwork_id
    ).first_or_404()
    db.session.delete(ea)
    db.session.commit()
    flash("Artwork removed from exhibition.", "success")
    return redirect(url_for("exhibitions.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    exhibition = Exhibition.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    exhibition.active = False
    db.session.commit()
    flash("Exhibition deleted.", "success")
    return redirect(url_for("exhibitions.index"))
