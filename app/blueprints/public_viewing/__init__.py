from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from ...models import ViewingRoom, Gallery
from datetime import datetime, timezone
import bcrypt

bp = Blueprint("public_viewing", __name__, url_prefix="/viewing-room")


def get_gallery():
    return Gallery.query.first()


@bp.route("/<int:id>", methods=["GET", "POST"])
def view(id):
    room = ViewingRoom.query.filter_by(id=id, is_active=True).first_or_404()
    gallery = get_gallery()
    now = datetime.now(timezone.utc)

    # Check if room is open
    if room.opens_at and now < room.opens_at:
        return render_template("viewing_rooms/public_closed.html",
                               gallery=gallery, room=room, reason="not_yet")
    if room.closes_at and now > room.closes_at:
        return render_template("viewing_rooms/public_closed.html",
                               gallery=gallery, room=room, reason="closed")

    # Check access code
    session_key = f"vr_access_{id}"
    if room.access_code_hash:
        if not session.get(session_key):
            if request.method == "POST":
                code = request.form.get("access_code", "")
                if bcrypt.checkpw(code.encode(), room.access_code_hash.encode()):
                    session[session_key] = True
                    return redirect(url_for("public_viewing.view", id=id))
                else:
                    flash("Incorrect access code.", "error")
            return render_template("viewing_rooms/public_gate.html",
                                   gallery=gallery, room=room)

    # Show the viewing room
    artworks = sorted(room.artworks, key=lambda vra: vra.sort_order)
    return render_template("viewing_rooms/public_view.html",
                           gallery=gallery, room=room, artworks=artworks)
