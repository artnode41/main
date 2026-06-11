from flask import Blueprint, render_template, abort, request, flash, redirect, url_for, current_app, session
from flask_babel import _
from ...models import Gallery, Artwork, ArtworkImage, Exhibition, ExhibitionArtwork, Contact
from ...extensions import db
from datetime import datetime, timezone
import re

bp = Blueprint("public", __name__, url_prefix="")

@bp.before_request
def check_maintenance():
    from flask import request as _req
    if _req.endpoint == "public.set_lang":
        return None
    gallery = get_gallery()
    if gallery and gallery.maintenance_mode:
        from flask import render_template
        return render_template("public/maintenance.html", gallery=gallery), 503


def get_gallery():
    return Gallery.query.first()


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


@bp.route("/lang/<lang>")
def set_lang(lang):
    from ...models import BlogPost
    supported = ["de", "fr", "it", "en"]
    if lang in supported:
        session["lang"] = lang
    # If coming from a blog post, redirect to same post in new language
    referrer = request.referrer or ""
    if "/blog/" in referrer:
        slug = referrer.rstrip("/").split("/blog/")[-1]
        post = BlogPost.query.filter_by(slug=slug, is_published=True).first()
        if post and post.translation_group_id:
            translation = BlogPost.query.filter_by(
                translation_group_id=post.translation_group_id,
                language=lang,
                is_published=True
            ).first()
            if translation:
                return redirect(url_for("public.blog_post", slug=translation.slug))
    return redirect(referrer or url_for("public.home"))


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
    forthcoming_exhibitions = Exhibition.query.filter(
        Exhibition.active == True,
        Exhibition.is_active_show == True,
        Exhibition.start_date > now,
    ).order_by(Exhibition.start_date.asc()).limit(3).all()

    # Carousel: active show exhibitions first, then is_carousel, then recent
    active_exhibitions = Exhibition.query.filter_by(
        active=True, is_active_show=True
    ).order_by(Exhibition.start_date.desc()).all()
    carousel_artworks = []
    if active_exhibitions:
        for ex in active_exhibitions:
            for ea in sorted(ex.artworks, key=lambda x: x.sort_order)[:4]:
                if ea.artwork.active and ea.artwork not in carousel_artworks:
                    carousel_artworks.append(ea.artwork)
                if len(carousel_artworks) >= 8:
                    break
            if len(carousel_artworks) >= 8:
                break
    if not forthcoming_exhibitions:
        if not carousel_artworks:
            carousel_artworks = Artwork.query.filter_by(
                is_carousel=True, active=True
            ).order_by(Artwork.id.desc()).all()
        if not carousel_artworks:
            carousel_artworks = Artwork.query.filter_by(
                status="available", active=True
            ).order_by(Artwork.id.desc()).limit(6).all()
    else:
        carousel_artworks = []
    # Featured: exclude exhibition artworks if active show
    exhibition_artwork_ids = {ea.artwork_id for ex in active_exhibitions for ea in ex.artworks} if active_exhibitions else set()
    featured_artworks = Artwork.query.filter_by(
        is_featured=True, active=True
    ).order_by(Artwork.id.desc()).all()
    if not featured_artworks:
        from sqlalchemy import not_
        query = Artwork.query.filter_by(status="available", active=True)
        if exhibition_artwork_ids:
            query = query.filter(~Artwork.id.in_(exhibition_artwork_ids))
        featured_artworks = query.order_by(Artwork.id.desc()).limit(12).all()

    return render_template("public/home.html",
                           gallery=gallery,
                           current_exhibitions=current_exhibitions,
                           carousel_artworks=carousel_artworks,
                           forthcoming_exhibitions=forthcoming_exhibitions,
                           featured_artworks=featured_artworks)


@bp.route("/artists")
def artists():
    gallery = get_gallery()
    from ...models import Contact, Artwork
    artists = Contact.query.filter(
        Contact.active == True,
        Contact.is_active_representation == True,
        Contact.roles.contains(["artist"])
    ).order_by(Contact.sort_name, Contact.last_name).all()
    # Attach thumbnail: photo_url first, then most recent public artwork image
    for a in artists:
        if not a.sort_name:
            a.sort_name = f"{a.last_name}, {a.first_name or ''}".strip(", ")
        a._thumbnail = None
        if a.photo_url:
            a._thumbnail = a.photo_url
        else:
            aw = Artwork.query.filter_by(
                contact_artist_id=a.id, is_public=True, active=True
            ).order_by(Artwork.id.desc()).first()
            if aw and aw.images:
                a._thumbnail = aw.images[0].iiif_url
    return render_template("public/artists.html", gallery=gallery, artists=artists)


@bp.route("/artists/<int:id>")
@bp.route("/artists/<int:id>/<slug>")
def artist_detail(id, slug=None):
    gallery = get_gallery()
    from ...models import Contact
    artist = Contact.query.filter_by(id=id, active=True).first_or_404()
    artworks = Artwork.query.filter_by(
        contact_artist_id=artist.id, active=True, is_public=True
    ).order_by(Artwork.id.desc()).all()
    exhibition_ids = db.session.query(ExhibitionArtwork.exhibition_id).join(
        Artwork, ExhibitionArtwork.artwork_id == Artwork.id
    ).filter(
        Artwork.contact_artist_id == artist.id
    ).subquery()
    exhibitions = Exhibition.query.filter(
        Exhibition.id.in_(exhibition_ids),
        Exhibition.active == True
    ).order_by(Exhibition.start_date.desc()).all()

    tab = request.args.get("tab", "artworks")
    return render_template("public/artist_detail.html",
                           gallery=gallery, artist=artist,
                           artworks=artworks, exhibitions=exhibitions,
                           tab=tab)



@bp.route("/artworks")
def artworks():
    from ...models import Artwork, Contact
    gallery = get_gallery()

    # Get filter params
    artist_id = request.args.get("artist", type=int)
    medium = request.args.get("medium", "").strip()
    price_min = request.args.get("price_min", type=float)
    price_max = request.args.get("price_max", type=float)

    q = Artwork.query.filter_by(tenant_id=gallery.id, is_public=True, active=True)

    if artist_id:
        q = q.filter_by(contact_artist_id=artist_id)
    if medium:
        q = q.filter(Artwork.medium.ilike(f"%{medium}%"))
    if price_min is not None:
        q = q.filter(Artwork.price >= price_min)
    if price_max is not None:
        q = q.filter(Artwork.price <= price_max)

    artworks = q.order_by(Artwork.id.desc()).all()

    # Get artists for filter dropdown
    from sqlalchemy import distinct
    artist_ids = [a[0] for a in Artwork.query.filter_by(
        tenant_id=gallery.id, is_public=True, active=True
    ).with_entities(distinct(Artwork.contact_artist_id)).all() if a[0]]
    artists = Contact.query.filter(Contact.id.in_(artist_ids)).order_by(Contact.sort_name).all()

    # Medium categories
    MEDIUM_CATEGORIES = {
        "Painting": ["acrylic", "oil", "gouache", "tempera", "encaustic", "fluorescent paint", "casein", "sumi ink"],
        "Works on Paper": ["graphite", "charcoal", "crayon", "pencil", "ink", "watercolor", "pastel", "collage", "brush", "wash", "conté", "pochoir"],
        "Print": ["etching", "lithograph", "screenprint", "engraving", "drypoint", "aquatint", "woodcut", "mezzotint"],
        "Sculpture": ["bronze", "aluminum", "iron", "epoxy", "polyester", "polyurethane", "cast", "fiberglass", "wood", "ceramic"],
        "Photography": ["photograph", "photo"],
    }

    def get_medium_category(medium):
        if not medium:
            return None
        m = medium.lower()
        for cat, keywords in MEDIUM_CATEGORIES.items():
            if any(k in m for k in keywords):
                return cat
        return "Other"

    # Filter by medium category
    medium_category = request.args.get("medium_category", "").strip()
    if medium_category:
        all_artworks = artworks
        artworks = [a for a in all_artworks if get_medium_category(a.medium) == medium_category]

    return render_template("public/artworks.html",
                           gallery=gallery,
                           artworks=artworks,
                           artists=artists,
                           medium_categories=list(MEDIUM_CATEGORIES.keys()) + ["Other"],
                           selected_artist=artist_id,
                           selected_medium_category=medium_category,
                           price_min=price_min,
                           price_max=price_max)

@bp.route("/artworks/<int:id>")
def artwork_detail(id):
    gallery = get_gallery()
    artwork = Artwork.query.filter_by(id=id, active=True, is_public=True).first_or_404()
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
        Artwork.active == True,
        Artwork.is_public == True
    ).order_by(ExhibitionArtwork.sort_order).all()
    return render_template("public/exhibition_detail.html",
                           gallery=gallery,
                           exhibition=exhibition,
                           artworks=artworks)



@bp.route("/blog")
def blog():
    from ...models import BlogPost
    gallery = get_gallery()
    lang = session.get("lang", "de")
    posts = BlogPost.query.filter_by(
        tenant_id=gallery.id, is_published=True, language=lang
    ).order_by(BlogPost.published_at.desc()).limit(10).all()
    # Fallback: if no posts in current language, show default language
    if not posts:
        posts = BlogPost.query.filter_by(
            tenant_id=gallery.id, is_published=True
        ).order_by(BlogPost.published_at.desc()).limit(10).all()
    return render_template("public/blog.html", gallery=gallery, posts=posts, lang=lang)


@bp.route("/blog/<slug>")
def blog_post(slug):
    from ...models import BlogPost
    gallery = get_gallery()
    post = BlogPost.query.filter_by(
        slug=slug, is_published=True
    ).first_or_404()
    # Get other language versions of this post
    translations = []
    if post.translation_group_id:
        translations = BlogPost.query.filter(
            BlogPost.translation_group_id == post.translation_group_id,
            BlogPost.id != post.id,
            BlogPost.is_published == True
        ).all()
    return render_template("public/blog_post.html", gallery=gallery, post=post, translations=translations)

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
