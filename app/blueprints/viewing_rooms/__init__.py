from flask import render_template, redirect, url_for, flash, request, session
from flask_security import login_required, current_user
from flask import Blueprint
from ...models import ViewingRoom, ViewingRoomArtwork, Artwork
from ...extensions import db
from .forms import ViewingRoomForm
from datetime import datetime, timezone
import bcrypt

bp = Blueprint("viewing_rooms", __name__, url_prefix="/admin/viewing-rooms")


@bp.route("/")
@login_required
def index():
    rooms = ViewingRoom.query.filter_by(
        tenant_id=current_user.tenant_id
    ).order_by(ViewingRoom.created_at.desc()).all()
    return render_template("viewing_rooms/index.html", rooms=rooms)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ViewingRoomForm()
    if form.validate_on_submit():
        access_code_hash = None
        if form.access_code.data:
            access_code_hash = bcrypt.hashpw(
                form.access_code.data.encode(), bcrypt.gensalt()
            ).decode()

        room = ViewingRoom(
            tenant_id=current_user.tenant_id,
            title=form.title.data,
            description=form.description.data or None,
            access_code_hash=access_code_hash,
            is_active=form.is_active.data,
            opens_at=datetime.combine(form.opens_at.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.opens_at.data else None,
            closes_at=datetime.combine(form.closes_at.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.closes_at.data else None,
        )
        db.session.add(room)
        db.session.commit()
        flash("Viewing room created.", "success")
        return redirect(url_for("viewing_rooms.detail", id=room.id))
    return render_template("viewing_rooms/form.html", form=form, room=None)


@bp.route("/<int:id>")
@login_required
def detail(id):
    room = ViewingRoom.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    assigned_ids = {vra.artwork_id for vra in room.artworks}
    available = Artwork.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Artwork.id.desc()).all()
    public_url = url_for("public_viewing.view", id=room.id, _external=True)
    return render_template("viewing_rooms/detail.html",
                           room=room, available=available,
                           assigned_ids=assigned_ids,
                           public_url=public_url)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    room = ViewingRoom.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    form = ViewingRoomForm(obj=room)
    if form.validate_on_submit():
        room.title = form.title.data
        room.description = form.description.data or None
        room.is_active = form.is_active.data
        room.opens_at = datetime.combine(form.opens_at.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.opens_at.data else None
        room.closes_at = datetime.combine(form.closes_at.data, datetime.min.time()).replace(tzinfo=timezone.utc) if form.closes_at.data else None
        if form.access_code.data:
            room.access_code_hash = bcrypt.hashpw(
                form.access_code.data.encode(), bcrypt.gensalt()
            ).decode()
        db.session.commit()
        flash("Viewing room updated.", "success")
        return redirect(url_for("viewing_rooms.detail", id=room.id))
    return render_template("viewing_rooms/form.html", form=form, room=room)


@bp.route("/<int:id>/assign/<int:artwork_id>", methods=["POST"])
@login_required
def assign(id, artwork_id):
    room = ViewingRoom.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    existing = ViewingRoomArtwork.query.filter_by(
        viewing_room_id=id, artwork_id=artwork_id
    ).first()
    if not existing:
        vra = ViewingRoomArtwork(
            viewing_room_id=id,
            artwork_id=artwork_id,
            sort_order=len(room.artworks),
        )
        db.session.add(vra)
        db.session.commit()
        flash("Artwork added to viewing room.", "success")
    return redirect(url_for("viewing_rooms.detail", id=id))


@bp.route("/<int:id>/remove/<int:artwork_id>", methods=["POST"])
@login_required
def remove(id, artwork_id):
    vra = ViewingRoomArtwork.query.filter_by(
        viewing_room_id=id, artwork_id=artwork_id
    ).first_or_404()
    db.session.delete(vra)
    db.session.commit()
    flash("Artwork removed from viewing room.", "success")
    return redirect(url_for("viewing_rooms.detail", id=id))


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    room = ViewingRoom.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    db.session.delete(room)
    db.session.commit()
    flash("Viewing room deleted.", "success")
    return redirect(url_for("viewing_rooms.index"))
