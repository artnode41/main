from flask import redirect, url_for
from flask_security import login_required
from . import bp


@bp.route("/")
@login_required
def index():
    return redirect(url_for("contacts.index") + "?role=artist")


@bp.route("/<int:id>")
@login_required
def detail(id):
    # Find contact by legacy_artist_id
    from ...models import Contact
    from flask_security import current_user
    contact = Contact.query.filter_by(
        legacy_artist_id=id,
        tenant_id=current_user.tenant_id
    ).first()
    if contact:
        return redirect(url_for("contacts.detail", id=contact.id))
    return redirect(url_for("contacts.index"))


@bp.route("/<int:id>/edit")
@login_required
def edit(id):
    from ...models import Contact
    from flask_security import current_user
    contact = Contact.query.filter_by(
        legacy_artist_id=id,
        tenant_id=current_user.tenant_id
    ).first()
    if contact:
        return redirect(url_for("contacts.edit", id=contact.id))
    return redirect(url_for("contacts.index"))
