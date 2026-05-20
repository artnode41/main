from flask import render_template, redirect, url_for, flash
from flask_security import login_required, current_user
from . import bp
from ...models import Contact
from ...extensions import db
from .forms import ContactForm


@bp.route("/")
@login_required
def index():
    contacts = (
        Contact.query
        .filter_by(tenant_id=current_user.tenant_id, active=True)
        .order_by(Contact.last_name)
        .all()
    )
    return render_template("contacts/index.html", contacts=contacts)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ContactForm()
    if form.validate_on_submit():
        contact = Contact(
            tenant_id=current_user.tenant_id,
            contact_type=form.contact_type.data,
            first_name=form.first_name.data or None,
            last_name=form.last_name.data or None,
            organisation=form.organisation.data or None,
            email=form.email.data or None,
            phone=form.phone.data or None,
            address=form.address.data or None,
            city=form.city.data or None,
            country=form.country.data.upper() if form.country.data else None,
            notes=form.notes.data or None,
        )
        db.session.add(contact)
        db.session.commit()
        flash("Contact added successfully.", "success")
        return redirect(url_for("contacts.index"))
    return render_template("contacts/form.html", form=form, contact=None)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    contact = Contact.query.filter_by(
        id=id, tenant_id=current_user.tenant_id
    ).first_or_404()
    form = ContactForm(obj=contact)
    if form.validate_on_submit():
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
        db.session.commit()
        flash("Contact updated successfully.", "success")
        return redirect(url_for("contacts.index"))
    return render_template("contacts/form.html", form=form, contact=contact)


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
