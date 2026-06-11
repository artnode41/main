import uuid
from datetime import datetime, timezone
from flask_security import UserMixin, RoleMixin, SQLAlchemyUserDatastore
from sqlalchemy import (
    JSON,
    Boolean, Column, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from .extensions import db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_utc():
    return datetime.now(timezone.utc)

def new_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Flask-Security: roles + users (tenant-aware)
# ---------------------------------------------------------------------------

roles_users = db.Table(
    "roles_users",
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("role.id"), primary_key=True),
)


class Role(db.Model, RoleMixin):
    __tablename__ = "role"
    id          = Column(Integer, primary_key=True)
    name        = Column(String(80), unique=True, nullable=False)
    description = Column(String(255))


class User(db.Model, UserMixin):
    __tablename__ = "user"
    id                      = Column(Integer, primary_key=True)
    tenant_id               = Column(Integer, ForeignKey("gallery.id"), nullable=True)
    email                   = Column(String(255), unique=True, nullable=False)
    password                = Column(String(255), nullable=False)
    first_name              = Column(String(100))
    last_name               = Column(String(100))
    active                  = Column(Boolean, default=True)
    confirmed_at            = Column(DateTime)
    fs_uniquifier           = Column(String(64), unique=True, nullable=False,
                                     default=new_uuid)
    created_at              = Column(DateTime, default=now_utc)
    roles                   = relationship("Role", secondary=roles_users,
                                           backref="users")
    gallery                 = relationship("Gallery", back_populates="users")


# ---------------------------------------------------------------------------
# Gallery (tenant) — single row in practice (self-hosted model)
# ---------------------------------------------------------------------------

class Gallery(db.Model):
    __tablename__ = "gallery"
    id                    = Column(Integer, primary_key=True)
    name                  = Column(String(200), nullable=False)
    public_name           = Column(String(200))           # Display name on public site
    slug                  = Column(String(100), unique=True, nullable=False)
    tagline               = Column(String(300))           # Short line under logo
    about_text            = Column(Text)                  # About page body
    translations          = Column(JSON, default=dict)  # {"de": {"tagline": "...", "about_text": "..."}, "fr": {...}}
    address               = Column(Text)
    zip_code              = Column(String(20))
    city                  = Column(String(100))
    country               = Column(String(2), default="CH")
    phone                 = Column(String(50))
    email                 = Column(String(255))           # Internal/admin email
    contact_email         = Column(String(255))           # Public contact email
    website               = Column(String(255))
    website_custom_domain = Column(String(255))           # e.g. gallery.ch
    maintenance_mode      = Column(Boolean, default=False)
    instagram_url         = Column(String(255))
    logo_url              = Column(Text)  # Public site logo (PNG, stored in MinIO)
    vat_number            = Column(String(30))
    iban                  = Column(String(34))
    vat_scheme_default    = Column(String(20), default="standard")
    currency              = Column(String(3), default="CHF")
    locale                = Column(String(10), default="de")
    active                = Column(Boolean, default=True)
    created_at            = Column(DateTime, default=now_utc)
    updated_at            = Column(DateTime, default=now_utc, onupdate=now_utc)

    users                 = relationship("User", back_populates="gallery")
    artworks              = relationship("Artwork", back_populates="gallery")
    contacts              = relationship("Contact", back_populates="gallery")
    exhibitions           = relationship("Exhibition", back_populates="gallery")
    sales                 = relationship("Sale", back_populates="gallery")
    art_fairs             = relationship("ArtFair", back_populates="gallery")
    viewing_rooms         = relationship("ViewingRoom", back_populates="gallery")


# ---------------------------------------------------------------------------
# Artist
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Contact (collectors, institutions)
# ---------------------------------------------------------------------------

class Contact(db.Model):
    __tablename__ = "contact"
    id             = Column(Integer, primary_key=True)
    tenant_id      = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    contact_type   = Column(String(20), default="individual")
    first_name     = Column(String(100))
    last_name      = Column(String(100))
    organisation   = Column(String(200))
    email          = Column(String(255))
    phone          = Column(String(50))
    address        = Column(Text)
    city           = Column(String(100))
    country        = Column(String(2))
    zip_code       = Column(String(20))
    roles                    = Column(ARRAY(String), default=[])
    biography                = Column(Text)
    birth_year               = Column(Integer)
    death_year               = Column(Integer)
    nationality              = Column(String(100))
    sort_name                = Column(String(200))
    slug                     = Column(String(200))
    cv_json                  = Column(JSON)
    translations         = Column(JSON, default=dict)  # {"de": {"biography": "..."}, "fr": {...}}
    artist_website           = Column(String(255))
    is_active_representation = Column(Boolean, default=False)
    photo_url        = Column(Text)  # base64 data URL, square JPG/PNG
    legacy_artist_id         = Column(Integer)
    notes          = Column(Text)
    active         = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=now_utc)
    updated_at     = Column(DateTime, default=now_utc, onupdate=now_utc)

    gallery        = relationship("Gallery", back_populates="contacts")
    purchases      = relationship("SaleLineItem", back_populates="buyer")


# ---------------------------------------------------------------------------
# Artwork
# ---------------------------------------------------------------------------

class Artwork(db.Model):
    __tablename__ = "artwork"

    id               = Column(Integer, primary_key=True)
    tenant_id        = Column(Integer, ForeignKey("gallery.id"), nullable=False)

    title            = Column(String(500), nullable=False)
    year_from        = Column(Integer)
    year_to          = Column(Integer)
    medium           = Column(Text)
    dimensions       = Column(Text)
    description      = Column(Text)
    translations     = Column(JSON, default=dict)  # {"de": {"description": "..."}, "fr": {...}}

    external_id      = Column(String(100))
    source_url       = Column(Text)
    inventory_number = Column(String(100))
    object_type      = Column(String(100))
    materials        = Column(ARRAY(String))
    techniques       = Column(ARRAY(String))
    rights           = Column(String(200))
    credit_line      = Column(Text)
    source_updated_at = Column(DateTime(timezone=True))

    status           = Column(String(30), default="available", nullable=False)
    price            = Column(Numeric(12, 2))
    currency         = Column(String(3), default="CHF")
    contact_artist_id = Column(Integer, ForeignKey("contact.id"), nullable=True)
    contact_artist    = relationship("Contact", foreign_keys=[contact_artist_id], backref="artworks_as_artist")
    is_public         = Column(Boolean, default=True)   # Show on public website
    is_featured       = Column(Boolean, default=False)  # Show in Featured Works grid
    is_carousel       = Column(Boolean, default=False)  # Show in homepage hero carousel
    contact_artist_id = Column(Integer, ForeignKey("contact.id"), nullable=True)
    contact_artist    = relationship("Contact", foreign_keys=[contact_artist_id], backref="artworks_as_artist")
    is_featured       = Column(Boolean, default=False)  # Show in Featured Works grid
    is_carousel       = Column(Boolean, default=False)  # Show in homepage hero carousel
    is_consignment   = Column(Boolean, default=False)  # Legacy — use ownership_type
    ownership_type   = Column(String(20), default="owned")  # owned | consignment
    acquisition_cost = Column(Numeric(12, 2))               # What gallery paid
    acquisition_date = Column(DateTime(timezone=True))      # When acquired
    active           = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=now_utc)
    updated_at       = Column(DateTime, default=now_utc, onupdate=now_utc)

    __table_args__ = (
        UniqueConstraint("tenant_id", "inventory_number",
                         name="uq_artwork_inventory_per_tenant"),
    )

    gallery          = relationship("Gallery", back_populates="artworks")
    images           = relationship("ArtworkImage", back_populates="artwork",
                                    cascade="all, delete-orphan")
    provenance       = relationship("ArtworkProvenance", back_populates="artwork",
                                    cascade="all, delete-orphan")
    consignment      = relationship("ArtworkConsignment", back_populates="artwork",
                                    uselist=False)
    exhibition_links = relationship("ExhibitionArtwork", back_populates="artwork")
    sale_lines       = relationship("SaleLineItem", back_populates="artwork")
    viewing_room_links = relationship("ViewingRoomArtwork", back_populates="artwork")


# ---------------------------------------------------------------------------
# ArtworkImage
# ---------------------------------------------------------------------------

class ArtworkImage(db.Model):
    __tablename__ = "artwork_image"
    id           = Column(Integer, primary_key=True)
    artwork_id   = Column(Integer, ForeignKey("artwork.id"), nullable=False)
    minio_key    = Column(Text)
    iiif_url     = Column(Text)
    is_primary   = Column(Boolean, default=False)
    sort_order   = Column(Integer, default=0)
    created_at   = Column(DateTime, default=now_utc)

    artwork      = relationship("Artwork", back_populates="images")


# ---------------------------------------------------------------------------
# ArtworkProvenance (append-only, KGTG compliance)
# ---------------------------------------------------------------------------

class ArtworkProvenance(db.Model):
    __tablename__ = "artwork_provenance"
    id             = Column(Integer, primary_key=True)
    artwork_id     = Column(Integer, ForeignKey("artwork.id"), nullable=False)
    tenant_id      = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    event_type     = Column(String(50), nullable=False)
    event_date     = Column(DateTime(timezone=True))
    event_date_end = Column(DateTime(timezone=True))
    description    = Column(Text)
    source_name    = Column(String(200))
    source_country = Column(String(2))
    document_key   = Column(Text)
    document_hash  = Column(String(64))   # SHA-256 of PDF
    document_path  = Column(Text)         # MinIO path to PDF
    ots_file_path  = Column(Text)         # MinIO path to .ots proof
    gpg_sig_path   = Column(Text)         # MinIO path to .sig file
    ots_status     = Column(String(20), default="pending")  # pending|submitted|confirmed
    attached_files = Column(ARRAY(String), default=[])  # MinIO paths to attached documents
    # Art. 24a MWSTG acquisition fields
    purchase_invoice_number = Column(String(100))
    supplier_address    = Column(Text)
    supplier_vat_status = Column(String(20))  # private|non_vat|vat_registered
    purchase_price      = Column(Numeric(12, 2))
    right_of_disposal   = Column(Boolean, default=False)
    retention_30yr      = Column(Boolean, default=False)
    recorded_by_id = Column(Integer, ForeignKey("user.id"))
    recorded_at    = Column(DateTime, default=now_utc, nullable=False)

    artwork        = relationship("Artwork", back_populates="provenance")
    recorded_by    = relationship("User")


# ---------------------------------------------------------------------------
# ArtworkConsignment
# ---------------------------------------------------------------------------

class ArtworkConsignment(db.Model):
    __tablename__ = "artwork_consignment"
    id                 = Column(Integer, primary_key=True)
    artwork_id         = Column(Integer, ForeignKey("artwork.id"),
                                nullable=False, unique=True)
    tenant_id          = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    consignor_id       = Column(Integer, ForeignKey("contact.id"), nullable=True)
    gallery_split_pct  = Column(Numeric(5, 2), nullable=False)
    purchase_price     = Column(Numeric(12, 2), nullable=True)
    is_secondary_market = Column(Boolean, default=False)
    start_date         = Column(DateTime(timezone=True))
    end_date           = Column(DateTime(timezone=True))
    terms              = Column(Text)
    active             = Column(Boolean, default=True)
    created_at         = Column(DateTime, default=now_utc)
    updated_at         = Column(DateTime, default=now_utc, onupdate=now_utc)

    artwork            = relationship("Artwork", back_populates="consignment")
    consignor          = relationship("Contact")


# ---------------------------------------------------------------------------
# Exhibition
# ---------------------------------------------------------------------------

class Exhibition(db.Model):
    __tablename__ = "exhibition"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    title        = Column(String(300), nullable=False)
    description  = Column(Text)
    translations  = Column(JSON, default=dict)  # {"de": {"description": "..."}, "fr": {...}}
    start_date   = Column(DateTime(timezone=True))
    end_date     = Column(DateTime(timezone=True))
    venue        = Column(String(200))
    active       = Column(Boolean, default=True)
    is_active_show = Column(Boolean, default=False)  # Show is currently running
    created_at   = Column(DateTime, default=now_utc)
    updated_at   = Column(DateTime, default=now_utc, onupdate=now_utc)

    gallery      = relationship("Gallery", back_populates="exhibitions")
    artworks     = relationship("ExhibitionArtwork", back_populates="exhibition")


class ExhibitionArtwork(db.Model):
    __tablename__ = "exhibition_artwork"
    id            = Column(Integer, primary_key=True)
    exhibition_id = Column(Integer, ForeignKey("exhibition.id"), nullable=False)
    artwork_id    = Column(Integer, ForeignKey("artwork.id"), nullable=False)
    sort_order    = Column(Integer, default=0)
    notes         = Column(Text)

    __table_args__ = (
        UniqueConstraint("exhibition_id", "artwork_id",
                         name="uq_exhibition_artwork"),
    )

    exhibition    = relationship("Exhibition", back_populates="artworks")
    artwork       = relationship("Artwork", back_populates="exhibition_links")


# ---------------------------------------------------------------------------
# Sale + SaleLineItem
# ---------------------------------------------------------------------------

class Sale(db.Model):
    __tablename__ = "sale"
    id             = Column(Integer, primary_key=True)
    tenant_id      = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    art_fair_id    = Column(Integer, ForeignKey("art_fair.id"), nullable=True)
    invoice_number = Column(String(50))
    invoice_date   = Column(DateTime(timezone=True))
    delivery_date  = Column(DateTime(timezone=True))
    vat_scheme     = Column(String(20), default="standard")
    invoice_pdf_path = Column(Text)  # Garage path for archived invoice PDF (margin sales)
    payment_link_url = Column(Text)
    payment_provider_id = Column(String(100))
    sale_date      = Column(DateTime(timezone=True), default=now_utc)
    status         = Column(String(30), default="draft")
    notes          = Column(Text)
    created_by_id  = Column(Integer, ForeignKey("user.id"))
    created_at     = Column(DateTime, default=now_utc)
    updated_at     = Column(DateTime, default=now_utc, onupdate=now_utc)

    gallery        = relationship("Gallery", back_populates="sales")
    art_fair       = relationship("ArtFair", back_populates="sales")
    line_items     = relationship("SaleLineItem", back_populates="sale",
                                  cascade="all, delete-orphan")
    created_by     = relationship("User")


class SaleLineItem(db.Model):
    __tablename__ = "sale_line_item"
    id                  = Column(Integer, primary_key=True)
    sale_id             = Column(Integer, ForeignKey("sale.id"), nullable=False)
    artwork_id          = Column(Integer, ForeignKey("artwork.id"), nullable=False)
    buyer_id            = Column(Integer, ForeignKey("contact.id"), nullable=True)
    price               = Column(Numeric(12, 2), nullable=False)
    currency            = Column(String(3), default="CHF")
    gallery_net         = Column(Numeric(12, 2))
    consignor_net       = Column(Numeric(12, 2))
    vat_rate            = Column(Numeric(5, 2), default=0)
    vat_amount          = Column(Numeric(12, 2), default=0)
    tax_method          = Column(String(10), default="standard", nullable=False)
    purchase_price_at_sale = Column(Numeric(12, 2), nullable=True)

    sale                = relationship("Sale", back_populates="line_items")
    artwork             = relationship("Artwork", back_populates="sale_lines")
    buyer               = relationship("Contact", back_populates="purchases")


# ---------------------------------------------------------------------------
# ArtFair
# ---------------------------------------------------------------------------

class ArtFair(db.Model):
    __tablename__ = "art_fair"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    name         = Column(String(200), nullable=False)
    location     = Column(String(200))
    start_date   = Column(DateTime(timezone=True))
    end_date     = Column(DateTime(timezone=True))
    active       = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=now_utc)
    updated_at   = Column(DateTime, default=now_utc, onupdate=now_utc)

    gallery      = relationship("Gallery", back_populates="art_fairs")
    sales        = relationship("Sale", back_populates="art_fair")


# ---------------------------------------------------------------------------
# ViewingRoom (password-protected online exhibition)
# ---------------------------------------------------------------------------

class ViewingRoom(db.Model):
    __tablename__ = "viewing_room"
    id               = Column(Integer, primary_key=True)
    tenant_id        = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    title            = Column(String(300), nullable=False)
    description      = Column(Text)
    access_code_hash = Column(String(255))        # bcrypt hash of access code
    is_active        = Column(Boolean, default=False)
    opens_at         = Column(DateTime(timezone=True))
    closes_at        = Column(DateTime(timezone=True))
    created_at       = Column(DateTime, default=now_utc)
    updated_at       = Column(DateTime, default=now_utc, onupdate=now_utc)

    gallery          = relationship("Gallery", back_populates="viewing_rooms")
    artworks         = relationship("ViewingRoomArtwork", back_populates="viewing_room",
                                    cascade="all, delete-orphan")


class ViewingRoomArtwork(db.Model):
    __tablename__ = "viewing_room_artwork"
    id               = Column(Integer, primary_key=True)
    viewing_room_id  = Column(Integer, ForeignKey("viewing_room.id"), nullable=False)
    artwork_id       = Column(Integer, ForeignKey("artwork.id"), nullable=False)
    sort_order       = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("viewing_room_id", "artwork_id",
                         name="uq_viewing_room_artwork"),
    )

    viewing_room     = relationship("ViewingRoom", back_populates="artworks")
    artwork          = relationship("Artwork", back_populates="viewing_room_links")


# ---------------------------------------------------------------------------

class BlogPost(db.Model):
    __tablename__ = "blog_post"
    id                   = Column(Integer, primary_key=True)
    tenant_id            = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    title                = Column(String(300), nullable=False)
    slug                 = Column(String(320), nullable=False)
    body                 = Column(Text, nullable=False)
    language             = Column(String(2), default="de", nullable=False)
    translation_group_id = Column(Integer, nullable=True)
    is_published         = Column(Boolean, default=False)
    published_at         = Column(DateTime(timezone=True))
    created_at           = Column(DateTime, default=now_utc)
    updated_at           = Column(DateTime, default=now_utc, onupdate=now_utc)
    gallery              = relationship("Gallery", backref="blog_posts")
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_blog_post_slug"),
    )

# Flask-Security user datastore
# ---------------------------------------------------------------------------

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
