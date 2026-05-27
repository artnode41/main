"""
ArtNode — Reset & Re-seed
Wipes all transactional data, resets logo, re-imports artworks + artists
from artnode_seed_contemporary.json.

Usage (from /home/debian/artnode):
    docker compose exec web python3 scripts/seed/reset_and_seed.py
"""

import json
import re
import sys
import os
from datetime import datetime, timezone
def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text

# ── Bootstrap Flask app ────────────────────────────────────────────────────────
sys.path.insert(0, "/app")
from app import create_app
from app.extensions import db
from app.models import (
    Gallery, Contact, Artwork, ArtworkImage,
)

app = create_app()

SEED_FILE = "/app/artnode_seed_contemporary.json"


# ── Artist name normalizer ─────────────────────────────────────────────────────

def parse_artist_name(raw: str) -> dict:
    """
    Handles two formats:
      "Andy Warhol"
      "Andy Warhol (American, 1928-1987)"
      "Mark Rothko (Marcus Rothkowitz)"   ← no dates, just alt name
    Returns dict with keys: display_name, first_name, last_name,
                             nationality, birth_year, death_year
    """
    result = {
        "display_name": raw,
        "first_name": "",
        "last_name": "",
        "nationality": None,
        "birth_year": None,
        "death_year": None,
    }

    # Strip parenthetical if present
    m = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", raw)
    if m:
        result["display_name"] = m.group(1).strip()
        paren = m.group(2).strip()

        # Try "Nationality, YYYY-YYYY" or "Nationality, born YYYY"
        nat_date = re.match(
            r"^([A-Za-z ]+),\s*(?:born\s*)?(\d{4})(?:\s*[-–]\s*(\d{4}))?$",
            paren
        )
        if nat_date:
            result["nationality"] = nat_date.group(1).strip()
            result["birth_year"] = int(nat_date.group(2))
            if nat_date.group(3):
                result["death_year"] = int(nat_date.group(3))
        # else: parenthetical is an alternate name — ignore it

    name = result["display_name"]
    parts = name.strip().split()
    if len(parts) >= 2:
        result["first_name"] = parts[0]
        result["last_name"] = " ".join(parts[1:])
    else:
        result["last_name"] = name

    return result


# ── Wipe ───────────────────────────────────────────────────────────────────────

def wipe(session):
    print("Wiping data...")

    tables = [
        "viewing_room_artwork",
        "viewing_room",
        "exhibition_artwork",
        "exhibition",
        "sale_line_item",
        "sale",
        "art_fair",
        "artwork_provenance",
        "artwork_consignment",
        "artwork_image",
        "artwork",
        "contact",
    ]

    for table in tables:
        result = session.execute(db.text(f"DELETE FROM {table}"))
        print(f"  {table}: {result.rowcount} rows deleted")

    # Reset logo
    session.execute(db.text("UPDATE gallery SET logo_url = NULL"))
    print("  gallery.logo_url: cleared")

    session.commit()
    print("Wipe complete.\n")


# ── Seed ───────────────────────────────────────────────────────────────────────

def seed(session):
    print(f"Loading seed file: {SEED_FILE}")
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  {len(data)} artworks found\n")

    gallery = session.execute(db.text("SELECT id FROM gallery LIMIT 1")).fetchone()
    if not gallery:
        print("ERROR: No gallery row found. Cannot seed.")
        sys.exit(1)
    tenant_id = gallery[0]
    print(f"Tenant gallery id: {tenant_id}\n")

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # ── Build unique artist list ───────────────────────────────────────────────
    # Normalize names first, deduplicate by display_name
    artist_map = {}  # display_name → Contact id
    unique_artists = {}  # display_name → parsed dict

    for item in data:
        parsed = parse_artist_name(item["artist"])
        dn = parsed["display_name"]
        if dn not in unique_artists:
            unique_artists[dn] = parsed

    print(f"Creating {len(unique_artists)} artist contacts...")
    for dn, p in sorted(unique_artists.items()):
        slug_base = slugify(dn)
        # Ensure slug uniqueness
        slug = slug_base
        suffix = 1
        while session.execute(
            db.text("SELECT 1 FROM contact WHERE slug = :s AND tenant_id = :t"),
            {"s": slug, "t": tenant_id}
        ).fetchone():
            slug = f"{slug_base}-{suffix}"
            suffix += 1

        contact = Contact(
            tenant_id=tenant_id,
            contact_type="individual",
            first_name=p["first_name"],
            last_name=p["last_name"],
            roles=["artist"],
            nationality=p["nationality"],
            birth_year=p["birth_year"],
            death_year=p["death_year"],
            sort_name=p["last_name"],
            slug=slug,
            is_active_representation=True,
            active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(contact)
        session.flush()  # get contact.id
        artist_map[dn] = contact.id
        print(f"  + {dn} (id={contact.id})")

    session.commit()
    print(f"\nArtist contacts created: {len(artist_map)}\n")

    # ── Create artworks ───────────────────────────────────────────────────────
    print("Creating artworks...")
    created = 0
    for item in data:
        parsed = parse_artist_name(item["artist"])
        dn = parsed["display_name"]
        contact_id = artist_map.get(dn)

        artwork = Artwork(
            tenant_id=tenant_id,
            title=item["title"],
            year_from=item.get("date_start"),
            year_to=item.get("date_end"),
            medium=item.get("medium"),
            dimensions=item.get("dimensions"),
            external_id=str(item["id"]),
            object_type=item["classifications"][0] if item.get("classifications") else None,
            status="available",
            is_public=True,
            is_featured=False,
            is_carousel=False,
            active=True,
            contact_artist_id=contact_id,
            created_at=now,
            updated_at=now,
        )
        session.add(artwork)
        session.flush()

        if item.get("image_url"):
            image = ArtworkImage(
                artwork_id=artwork.id,
                iiif_url=item["image_url"],
                is_primary=True,
                sort_order=0,
                created_at=now,
            )
            session.add(image)

        created += 1

    session.commit()
    print(f"Artworks created: {created}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    with app.app_context():
        session = db.session

        print("=" * 55)
        print("ArtNode — Reset & Re-seed")
        print("=" * 55 + "\n")

        wipe(session)
        seed(session)

        # Verify
        counts = session.execute(db.text("""
            SELECT 'artworks' as tbl, count(*) FROM artwork
            UNION ALL SELECT 'contacts', count(*) FROM contact
            UNION ALL SELECT 'exhibitions', count(*) FROM exhibition
            UNION ALL SELECT 'sales', count(*) FROM sale
        """)).fetchall()

        print("Verification:")
        for row in counts:
            print(f"  {row[0]}: {row[1]}")

        print("\nDone.")


if __name__ == "__main__":
    main()
