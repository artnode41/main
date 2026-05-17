import uuid
from datetime import datetime, timezone
from flask_security import UserMixin, RoleMixin, SQLAlchemyUserDatastore
from sqlalchemy import (
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
# Gallery (tenant)
# ---------------------------------------------------------------------------

class Gallery(db.Model):
    __tablename__ = "gallery"
    id           = Column(Integer, primary_key=True)
    name         = Column(String(200), nullable=False)
    slug         = Column(String(100), unique=True, nullable=False)
    address      = Column(Text)
    city         = Column(String(100))
    country      = Column(String(2), default="CH")   # ISO 3166-1 alpha-2
    phone        = Column(String(50))
    email        = Column(String(255))
    website      = Column(String(255))
    currency     = Column(String(3), default="CHF")
    locale       = Column(String(10), default="de")  # de, fr, it, en
    active       = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=now_utc)
    updated_at   = Column(DateTime, default=now_utc, onupdate=now_utc)

    users        = relationship("User", back_populates="gallery")
    artists      = relationship("Artist", back_populates="gallery")
    artworks     = relationship("Artwork", back_populates="gallery")
    contacts     = relationship("Contact", back_populates="gallery")
    exhibitions  = relationship("Exhibition", back_populates="gallery")
    sales        = relationship("Sale", back_populates="gallery")
    art_fairs    = relationship("ArtFair", back_populates="gallery")


# ---------------------------------------------------------------------------
# Artist
# ---------------------------------------------------------------------------

class Artist(db.Model):
    __tablename__ = "artist"
    id             = Column(Integer, primary_key=True)
    tenant_id      = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    first_name     = Column(String(100))
    last_name      = Column(String(100), nullable=False)
    birth_year     = Column(Integer)
    death_year     = Column(Integer)
    nationality    = Column(String(100))
    biography      = Column(Text)
    website        = Column(String(255))
    active         = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=now_utc)
    updated_at     = Column(DateTime, default=now_utc, onupdate=now_utc)

    gallery        = relationship("Gallery", back_populates="artists")
    artworks       = relationship("Artwork", back_populates="artist")


# ---------------------------------------------------------------------------
# Contact (collectors, institutions)
# ---------------------------------------------------------------------------

class Contact(db.Model):
    __tablename__ = "contact"
    id             = Column(Integer, primary_key=True)
    tenant_id      = Column(Integer, ForeignKey("gallery.id"), nullable=False)
    contact_type   = Column(String(20), default="individual")  # individual | institution
    first_name     = Column(String(100))
    last_name      = Column(String(100))
    organisation   = Column(String(200))
    email          = Column(String(255))
    phone          = Column(String(50))
    address        = Column(Text)
    city           = Column(String(100))
    country        = Column(String(2))
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
    artist_id        = Column(Integer, ForeignKey("artist.id"), nullable=True)

    # Core fields
    title            = Column(String(500), nullable=False)
    year_from        = Column(Integer)
    year_to          = Column(Integer)
    medium           = Column(Text)
    dimensions       = Column(Text)
    description      = Column(Text)

    # Seed / external source fields
    external_id      = Column(String(100))
    source_url       = Column(Text)
    inventory_number = Column(String(100))
    object_type      = Column(String(100))
    materials        = Column(ARRAY(String))
    techniques       = Column(ARRAY(String))
    rights           = Column(String(200))
    credit_line      = Column(Text)
    source_updated_at = Column(DateTime(timezone=True))

    # Status state machine: available | reserved | sold |
    #                        on_consignment | on_loan
    status           = Column(String(30), default="available", nullable=False)

    # Pricing
    price            = Column(Numeric(12, 2))
    currency         = Column(String(3), default="CHF")

    # Ownership
    is_consignment   = Column(Boolean, default=False)

    active           = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=now_utc)
    updated_at       = Column(DateTime, default=now_utc, onupdate=now_utc)

    __table_args__ = (
        UniqueConstraint("tenant_id", "inventory_number",
                         name="uq_artwork_inventory_per_tenant"),
    )

    gallery          = relationship("Gallery", back_populates="artworks")
    artist           = relationship("Artist", back_populates="artworks")
    images           = relationship("ArtworkImage", back_populates="artwork",
                                    cascade="all, delete-orphan")
    provenance       = relationship("ArtworkProvenance", back_populates="artwork",
                                    cascade="all, delete-orphan")
    consignment      = relationship("ArtworkConsignment", back_populates="artwork",
                                    uselist=False)
    exhibition_links = relationship("ExhibitionArtwork", back_populates="artwork")
    sale_lines       = relationship("SaleLineItem", back_populates="artwork")


# ---------------------------------------------------------------------------
# ArtworkImage
# ---------------------------------------------------------------------------

class ArtworkImage(db.Model):
    __tablename__ = "artwork_image"
    id           = Column(Integer, primary_key=True)
    artwork_id   = Column(Integer, ForeignKey("artwork.id"), nullable=False)
    minio_key    = Column(Text)           # MinIO object key (Phase 7+)
    iiif_url     = Column(Text)           # AIC IIIF URL (seed data, Phases 1-6)
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
    # acquisition | sale | loan | exhibition | restitution | import | export
    event_date     = Column(DateTime(timezone=True))
    event_date_end = Column(DateTime(timezone=True))
    description    = Column(Text)
    source_name    = Column(String(200))   # previous owner / institution
    source_country = Column(String(2))
    document_key   = Column(Text)          # MinIO key for scan upload
    recorded_by_id = Column(Integer, ForeignKey("user.id"))
    recorded_at    = Column(DateTime, default=now_utc, nullable=False)
    # No update — append-only

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
    gallery_split_pct  = Column(Numeric(5, 2), nullable=False)  # e.g. 50.00
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
    start_date   = Column(DateTime(timezone=True))
    end_date     = Column(DateTime(timezone=True))
    venue        = Column(String(200))
    active       = Column(Boolean, default=True)
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
    sale_date      = Column(DateTime(timezone=True), default=now_utc)
    status         = Column(String(30), default="draft")
    # draft | confirmed | invoiced | paid | cancelled
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
    gallery_net         = Column(Numeric(12, 2))   # after consignment split
    consignor_net       = Column(Numeric(12, 2))   # consignor payout
    vat_rate            = Column(Numeric(5, 2), default=0)
    vat_amount          = Column(Numeric(12, 2), default=0)

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
# Flask-Security user datastore
# ---------------------------------------------------------------------------

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
