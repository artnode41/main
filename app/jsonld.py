"""
ArtNode JSON-LD Serializer
schema.org + CIDOC CRM compatible properties.
Validation target: Rijksmuseum Linked Data Resolver (Linked Art profile).
Reference: https://linked.art/api/1.0/endpoint/physical_object/
"""


def build_artwork_jsonld(artwork, gallery):
    """
    Build a JSON-LD dict for a single artwork.
    Uses schema.org VisualArtwork as primary type,
    with Linked Art / CIDOC CRM compatible properties where possible.
    """
    artist = artwork.contact_artist
    images = artwork.images or []

    doc = {
        "@context": [
            "https://schema.org",
            {"crm": "http://www.cidoc-crm.org/cidoc-crm/"}
        ],
        "@type": "VisualArtwork",
        "@id": f"https://artnode.ch/api/v1/artworks/{artwork.id}",

        # Core identification
        "identifier": str(artwork.inventory_number or artwork.id),
        "name": artwork.title,

        # Date
        **({"dateCreated": str(artwork.year_from)} if artwork.year_from else {}),
        **({"dateModified": artwork.updated_at.isoformat() if artwork.updated_at else None}),

        # Medium / materials
        **({"artMedium": artwork.medium} if artwork.medium else {}),
        **({"material": artwork.materials} if artwork.materials else {}),

        # Dimensions
        **({"size": artwork.dimensions} if artwork.dimensions else {}),

        # Description
        **({"description": artwork.description} if artwork.description else {}),

        # Rights
        **({"license": artwork.rights} if artwork.rights else {}),
        **({"creditText": artwork.credit_line} if artwork.credit_line else {}),

        # Repository / holder
        "holdingOrganization": {
            "@type": "Organization",
            "name": gallery.public_name or gallery.name,
            **({"address": {
                "@type": "PostalAddress",
                "addressLocality": gallery.city or "",
                "addressCountry": gallery.country or "CH",
            }} if gallery.city else {}),
            **({"url": gallery.website} if gallery.website else {}),
        },

        # Source
        **({"url": artwork.source_url} if artwork.source_url else {}),
        **({"sameAs": artwork.source_url} if artwork.source_url else {}),
    }

    # Artist
    if artist:
        creator = {
            "@type": "Person",
            "name": f"{artist.first_name or ''} {artist.last_name or ''}".strip(),
        }
        if artist.birth_year:
            creator["birthDate"] = str(artist.birth_year)
        if artist.death_year:
            creator["deathDate"] = str(artist.death_year)
        if artist.nationality:
            creator["nationality"] = artist.nationality
        doc["creator"] = creator

    # Images
    if images:
        doc["image"] = [img.iiif_url for img in images if img.iiif_url]
        doc["thumbnailUrl"] = images[0].iiif_url if images[0].iiif_url else None

    # Provenance (CIDOC CRM P24i_changed_ownership_through)
    prov_events = artwork.provenance or []
    if prov_events:
        doc["crm:P24i_changed_ownership_through"] = [
            {
                "@type": "crm:E8_Acquisition",
                "crm:P2_has_type": prov.event_type,
                **({"crm:P4_has_time-span": {
                    "@type": "crm:E52_Time-Span",
                    "crm:P82a_begin_of_the_begin": prov.event_date.isoformat() if prov.event_date else None
                }} if prov.event_date else {}),
                **({"crm:P23_transferred_title_from": {
                    "@type": "crm:E39_Actor",
                    "name": prov.source_name
                }} if prov.source_name else {}),
                **({"description": prov.description} if prov.description else {}),
            }
            for prov in prov_events
        ]

    # Remove None values
    doc = _clean(doc)
    return doc


def _clean(obj):
    """Recursively remove None values from a dict."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_clean(i) for i in obj if i is not None]
    return obj
