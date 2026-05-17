import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")

from app import create_app
from app.extensions import db
from app.models import Gallery, Artist, Artwork, ArtworkImage

SEED_FILE = Path("/app/artnode_seed_contemporary.json")


def parse_artist_name(name):
    name = name.split("(")[0].strip()
    parts = name.split()
    if len(parts) == 1:
        return "", parts[0]
    return " ".join(parts[:-1]), parts[-1]


def infer_object_type(classifications):
    for c in classifications:
        c = c.lower()
        if "painting" in c or "oil on canvas" in c or "oil on panel" in c:
            return "painting"
        if "sculpture" in c:
            return "sculpture"
        if "print" in c or "etching" in c or "lithograph" in c or "screenprint" in c or "drypoint" in c:
            return "print"
        if "drawing" in c or "watercolor" in c or "gouache" in c or "graphite" in c or "charcoal" in c or "pastel" in c:
            return "drawing"
        if "photograph" in c:
            return "photograph"
    return "other"


def run():
    app = create_app()
    with app.app_context():
        gallery = Gallery.query.filter_by(slug="demo-gallery").first()
        if not gallery:
            gallery = Gallery(
                name="ArtNode Demo Gallery",
                slug="demo-gallery",
                city="Zurich",
                country="CH",
                currency="CHF",
                locale="en",
            )
            db.session.add(gallery)
            db.session.flush()
            print(f"Created gallery: {gallery.name} (id={gallery.id})")
        else:
            print(f"Using existing gallery: {gallery.name} (id={gallery.id})")

        with open(SEED_FILE, encoding="utf-8") as f:
            records = json.load(f)

        artists_cache = {}
        imported = 0
        skipped = 0

        for rec in records:
            existing = Artwork.query.filter_by(
                tenant_id=gallery.id,
                external_id=str(rec["id"])
            ).first()
            if existing:
                skipped += 1
                continue

            artist_name = rec.get("artist", "Unknown")
            if artist_name not in artists_cache:
                first, last = parse_artist_name(artist_name)
                artist = Artist.query.filter_by(
                    tenant_id=gallery.id,
                    first_name=first,
                    last_name=last
                ).first()
                if not artist:
                    artist = Artist(
                        tenant_id=gallery.id,
                        first_name=first,
                        last_name=last,
                    )
                    db.session.add(artist)
                    db.session.flush()
                artists_cache[artist_name] = artist
            else:
                artist = artists_cache[artist_name]

            artwork = Artwork(
                tenant_id=gallery.id,
                artist_id=artist.id,
                title=rec["title"],
                year_from=rec.get("date_start"),
                year_to=rec.get("date_end"),
                medium=rec.get("medium"),
                dimensions=rec.get("dimensions"),
                external_id=str(rec["id"]),
                source_url=f"https://www.artic.edu/artworks/{rec['id']}",
                object_type=infer_object_type(rec.get("classifications", [])),
                rights="Public Domain",
                status="available",
            )
            db.session.add(artwork)
            db.session.flush()

            if rec.get("image_url"):
                image = ArtworkImage(
                    artwork_id=artwork.id,
                    iiif_url=rec["image_url"],
                    is_primary=True,
                    sort_order=0,
                )
                db.session.add(image)

            imported += 1

        db.session.commit()
        print(f"Done. Imported: {imported}, Skipped: {skipped}, Artists: {len(artists_cache)}")


if __name__ == "__main__":
    run()
