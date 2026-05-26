from flask import Blueprint, render_template, abort, request, flash, redirect, url_for, current_app
from ...models import Gallery, Artist, Artwork, ArtworkImage, Exhibition, ExhibitionArtwork, Contact
from ...extensions import db
from datetime import datetime, timezone
import re

bp = Blueprint("public", __name__, url_prefix="")


def get_gallery():
    return Gallery.query.first()


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


@bp.route("/")
def home():
    gallery = get_gallery()
    # Hero: current exhibitions first, then featured available artworks
    now = datetime.now(timezone.utc)
    current_exhibitions = Exhibition.query.filter(
        Exhibition.active == True,
        Exhibition.start_date <= now,
        Exhibition.end_date >= now,
    ).order_by(Exhibition.start_date.desc()).limit(5).all()

    # Carousel: is_carousel=True first, fallback to recent available
    carousel_artworks = Artwork.query.filter_by(
        is_carousel=True, active=True
    ).order_by(Artwork.id.desc()).all()
    if not carousel_artworks:
        carousel_artworks = Artwork.query.filter_by(
            status="available", active=True
        ).order_by(Artwork.id.desc()).limit(6).all()

    # Featured: is_featured=True first, fallback to recent available
    featured_artworks = Artwork.query.filter_by(
        is_featured=True, active=True
    ).order_by(Artwork.id.desc()).all()
    if not featured_artworks:
        featured_artworks = Artwork.query.filter_by(
            status="available", active=True
        ).order_by(Artwork.id.desc()).limit(12).all()

    return render_template("public/home.html",
                           gallery=gallery,
                           current_exhibitions=current_exhibitions,
                           carousel_artworks=carousel_artworks,
                           featured_artworks=featured_artworks)


@bp.route("/artists")
def artists():
    gallery = get_gallery()
    from ...models import Contact
    artists = Contact.query.filter(
        Contact.active == True,
        Contact.is_active_representation == True,
        Contact.roles.contains(["artist"])
    ).order_by(Contact.sort_name, Contact.last_name).all()
    for a in artists:
        if not a.sort_name:
            a.sort_name = f"{a.last_name}, {a.first_name or ''}".strip(", ")
    return render_template("public/artists.html", gallery=gallery, artists=artists)


@bp.route("/artists/<int:id>")
@bp.route("/artists/<int:id>/<slug>")
def artist_detail(id, slug=None):
    gallery = get_gallery()
    from ...models import Contact
    artist = Contact.query.filter_by(id=id, active=True).first_or_404()
    artworks = Artwork.query.filter_by(
        contact_artist_id=artist.id, active=True
    ).order_by(Artwork.id.desc()).all()
    exhibitions = db.session.query(Exhibition).join(
        ExhibitionArtwork, ExhibitionArtwork.exhibition_id == Exhibition.id
    ).join(
        Artwork, ExhibitionArtwork.artwork_id == Artwork.id
    ).filter(
        Artwork.contact_artist_id == artist.id,
        Exhibition.active == True
    ).order_by(Exhibition.start_date.desc()).distinct().all()

    tab = request.args.get("tab", "artworks")
    return render_template("public/artist_detail.html",
                           gallery=gallery, artist=artist,
                           artworks=artworks, exhibitions=exhibitions,
                           tab=tab)


@bp.route("/artworks/<int:id>")
def artwork_detail(id):
    gallery = get_gallery()
    artwork = Artwork.query.filter_by(id=id, active=True).first_or_404()
    return render_template("public/artwork_detail.html",
                           gallery=gallery, artwork=artwork)


@bp.route("/exhibitions")
def exhibitions():
    gallery = get_gallery()
    now = datetime.now(timezone.utc)
    current = Exhibition.query.filter(
        Exhibition.active == True,
        Exhibition.start_date <= now,
        Exhibition.end_date >= now,
    ).order_by(Exhibition.start_date).all()
    forthcoming = Exhibition.query.filter(
        Exhibition.active == True,
        Exhibition.start_date > now,
    ).order_by(Exhibition.start_date).all()
    past = Exhibition.query.filter(
        Exhibition.active == True,
        Exhibition.end_date < now,
    ).order_by(Exhibition.end_date.desc()).limit(20).all()
    return render_template("public/exhibitions.html",
                           gallery=gallery,
                           current=current,
                           forthcoming=forthcoming,
                           past=past)


@bp.route("/exhibitions/<int:id>")
def exhibition_detail(id):
    gallery = get_gallery()
    exhibition = Exhibition.query.filter_by(id=id, active=True).first_or_404()
    artworks = db.session.query(Artwork).join(
        ExhibitionArtwork, ExhibitionArtwork.artwork_id == Artwork.id
    ).filter(
        ExhibitionArtwork.exhibition_id == id,
        Artwork.active == True
    ).order_by(ExhibitionArtwork.sort_order).all()
    return render_template("public/exhibition_detail.html",
                           gallery=gallery,
                           exhibition=exhibition,
                           artworks=artworks)


@bp.route("/about")
def about():
    gallery = get_gallery()
    from ...models import Contact
    artists = Contact.query.filter(
        Contact.active == True,
        Contact.is_active_representation == True,
        Contact.roles.contains(["artist"])
    ).order_by(Contact.sort_name, Contact.last_name).limit(8).all()
    return render_template("public/about.html", gallery=gallery, artists=artists)


@bp.route("/contact")
def contact():
    gallery = get_gallery()
    return render_template("public/contact.html", gallery=gallery)


@bp.route("/enquire", methods=["POST"])
def enquire():
    gallery = get_gallery()
    artwork_id = request.form.get("artwork_id")
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not email or not last_name:
        flash("Please fill in all required fields.", "error")
        return redirect(request.referrer or url_for("public.home"))

    # Upsert contact
    contact = Contact.query.filter_by(
        tenant_id=gallery.id, email=email
    ).first()
    if not contact:
        contact = Contact(
            tenant_id=gallery.id,
            contact_type="individual",
            first_name=first_name,
            last_name=last_name,
            email=email,
            active=True,
        )
        db.session.add(contact)

    # Log enquiry as a note on the contact
    note = f"Enquiry"
    if artwork_id:
        artwork = Artwork.query.get(artwork_id)
        if artwork:
            note += f" re: {artwork.title}"
    note += f"\n\n{message}"
    contact.notes = (contact.notes + "\n\n---\n" + note) if contact.notes else note
    db.session.commit()

    # Send email notification to gallery
    try:
        from flask_mail import Mail, Message
        mail = current_app.extensions.get("mail")
        if mail and current_app.config.get("MAIL_USERNAME"):
            gallery_email = gallery.contact_email or current_app.config.get("MAIL_DEFAULT_SENDER")
            if gallery_email:
                subject = f"New Enquiry"
                if artwork_id and artwork:
                    subject += f": {artwork.title}"
                body = "New enquiry received via the website.\n\n"
                body += f"From: {first_name} {last_name}\n"
                body += f"Email: {email}\n\n"
                body += f"Message:\n{message}\n"
                if artwork_id and artwork:
                    body += f"\nArtwork: {artwork.title}"
                    if artwork.contact_artist:
                        body += f"\nArtist: {artwork.contact_artist.first_name} {artwork.contact_artist.last_name}"

                msg = Message(
                    subject=subject,
                    recipients=[gallery_email],
                    body=body,
                    reply_to=email,
                )
                mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Mail send error: {e}")

    flash("Thank you for your enquiry. We will be in touch shortly.", "success")
    if artwork_id:
        return redirect(url_for("public.artwork_detail", id=artwork_id))
    return redirect(url_for("public.contact"))
