"""
ArtNode LIDO 1.1 Serializer
Maps artwork + provenance + exhibition data to LIDO XML.
Reference: https://lido-schema.org/schema/v1.1/lido-v1.1.html
"""
from lxml import etree
from datetime import datetime

LIDO_NS = "http://www.lido-schema.org"
SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
OWL_NS  = "http://www.w3.org/2002/07/owl#"
XSI_NS  = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = (
    "http://www.lido-schema.org "
    "http://www.lido-schema.org/schema/v1.1/lido-v1.1.xsd"
)

NSMAP = {
    "lido": LIDO_NS,
    "skos": SKOS_NS,
    "owl":  OWL_NS,
    "xsi":  XSI_NS,
}


def L(tag):
    """Shorthand for lido-namespaced tag."""
    return f"{{{LIDO_NS}}}{tag}"


def sub(parent, tag, text=None, **attrs):
    """Create a child element, optionally with text and lido: attributes."""
    lido_attrs = {L(k): v for k, v in attrs.items()}
    el = etree.SubElement(parent, L(tag), **lido_attrs)
    if text is not None:
        el.text = str(text)
    return el


def build_lido_record(artwork, gallery):
    """Build a single lido:lido element for one artwork."""
    lido = etree.Element(L("lido"), nsmap=NSMAP)
    lido.set(f"{{{XSI_NS}}}schemaLocation", SCHEMA_LOCATION)

    # --- lidoRecID ---
    rec_id = sub(lido, "lidoRecID",
                 f"ch.artnode.{gallery.id}.{artwork.id}",
                 type="http://terminology.lido-schema.org/lido00100",
                 source="ArtNode")

    # ================================================================
    # descriptiveMetadata
    # ================================================================
    dm = sub(lido, "descriptiveMetadata")
    dm.set(f"{{{LIDO_NS}}}lang", "en")

    # --- objectClassificationWrap ---
    ocw = sub(dm, "objectClassificationWrap")
    owtw = sub(ocw, "objectWorkTypeWrap")
    if artwork.object_type:
        owt = sub(owtw, "objectWorkType")
        sub(owt, "term", artwork.object_type)

    # --- objectIdentificationWrap ---
    oiw = sub(dm, "objectIdentificationWrap")

    # titleWrap
    tw = sub(oiw, "titleWrap")
    ts = sub(tw, "titleSet")
    sub(ts, "appellationValue", artwork.title)

    # inscriptionsWrap (not used for inventory — kept empty if no inscriptions)

    # repositoryWrap
    rw = sub(oiw, "repositoryWrap")
    rs = sub(rw, "repositorySet")
    sub(rs, "displayRepository", f"{gallery.name}, {gallery.city or ''}")
    repo_name = sub(rs, "repositoryName")
    lbn = sub(repo_name, "legalBodyName")
    sub(lbn, "appellationValue", gallery.public_name or gallery.name)
    if gallery.city or gallery.country:
        sub(repo_name, "legalBodyWeblink", gallery.website or "")
    # workID = inventory number
    if artwork.inventory_number:
        sub(rs, "workID", artwork.inventory_number,
            type="http://terminology.lido-schema.org/lido00318")

    # objectDescriptionWrap
    if artwork.description:
        odw = sub(oiw, "objectDescriptionWrap")
        ods = sub(odw, "objectDescriptionSet")
        sub(ods, "descriptiveNoteValue", artwork.description)

    # objectMeasurementsWrap
    if artwork.dimensions:
        omw = sub(oiw, "objectMeasurementsWrap")
        oms = sub(omw, "objectMeasurementsSet")
        sub(oms, "displayObjectMeasurements", artwork.dimensions)

    # --- objectMaterialsTechWrap ---
    if artwork.medium or artwork.materials or artwork.techniques:
        omtw = sub(dm, "objectMaterialsTechWrap")
        omts = sub(omtw, "objectMaterialsTechSet")
        if artwork.medium:
            sub(omts, "displayMaterialsTech", artwork.medium)
        for mat in (artwork.materials or []):
            mt = sub(omts, "materialsTech")
            tmt = sub(mt, "termMaterialsTech",
                      type="http://terminology.lido-schema.org/lido00132")
            sub(tmt, "term", mat)
        for tech in (artwork.techniques or []):
            mt = sub(omts, "materialsTech")
            tmt = sub(mt, "termMaterialsTech",
                      type="http://terminology.lido-schema.org/lido00131")
            sub(tmt, "term", tech)

    # --- eventWrap ---
    ew = sub(dm, "eventWrap")

    # Production event
    prod_es = sub(ew, "eventSet")
    prod_e  = sub(prod_es, "event")
    prod_et = sub(prod_e, "eventType")
    sub(prod_et, "term", "Production")

    # Creator
    artist = artwork.contact_artist
    if artist:
        ea = sub(prod_e, "eventActor")
        air = sub(ea, "actorInRole")
        act = sub(air, "actor")
        nas = sub(act, "nameActorSet")
        display_name = f"{artist.first_name or ''} {artist.last_name or ''}".strip()
        sub(nas, "appellationValue", display_name)
        if artist.birth_year or artist.death_year:
            vd = sub(act, "vitalDatesActor")
            bd = sub(vd, "date")
            if artist.birth_year:
                sub(bd, "earliestDate", str(artist.birth_year),
                    type="birthDate")
            if artist.death_year:
                sub(bd, "latestDate", str(artist.death_year),
                    type="deathDate")
        if artist.nationality:
            sub(act, "nationalityActor").append(
                _term_el("term", artist.nationality))
        role = sub(air, "roleActor")
        sub(role, "term", "creator")

    # Production date
    if artwork.year_from:
        ed = sub(prod_e, "eventDate")
        year_to = artwork.year_to or artwork.year_from
        sub(ed, "displayDate",
            str(artwork.year_from) if artwork.year_from == year_to
            else f"{artwork.year_from}–{year_to}")
        d = sub(ed, "date")
        sub(d, "earliestDate", str(artwork.year_from))
        sub(d, "latestDate", str(year_to))

    # Provenance events
    for prov in (artwork.provenance or []):
        pes = sub(ew, "eventSet")
        pe  = sub(pes, "event")
        pet = sub(pe, "eventType")
        sub(pet, "term", prov.event_type)

        if prov.event_date:
            ped = sub(pe, "eventDate")
            sub(ped, "displayDate", prov.event_date.strftime("%Y-%m-%d"))
            pd2 = sub(ped, "date")
            sub(pd2, "earliestDate", prov.event_date.strftime("%Y"))
            if prov.event_date_end:
                sub(pd2, "latestDate", prov.event_date_end.strftime("%Y"))

        if prov.source_name:
            pea = sub(pe, "eventActor")
            pair = sub(pea, "actorInRole")
            pact = sub(pair, "actor")
            pnas = sub(pact, "nameActorSet")
            sub(pnas, "appellationValue", prov.source_name)

        if prov.source_country:
            pep = sub(pe, "eventPlace")
            ppl = sub(pep, "place")
            pnps = sub(ppl, "namePlaceSet")
            sub(pnps, "appellationValue", prov.source_country)

        if prov.description:
            peds = sub(pe, "eventDescriptionSet")
            sub(peds, "descriptiveNoteValue", prov.description)

    # ================================================================
    # administrativeMetadata
    # ================================================================
    am = sub(lido, "administrativeMetadata")
    am.set(f"{{{LIDO_NS}}}lang", "en")

    # rightsWorkWrap
    if artwork.rights or artwork.credit_line:
        rww = sub(am, "rightsWorkWrap")
        rws = sub(rww, "rightsWorkSet")
        if artwork.rights:
            rt = sub(rws, "rightsType")
            sub(rt, "term", artwork.rights)
        if artwork.credit_line:
            sub(rws, "creditLine", artwork.credit_line)

    # recordWrap
    recw = sub(am, "recordWrap")
    sub(recw, "recordID", str(artwork.id),
        type="http://terminology.lido-schema.org/lido00100")
    rect = sub(recw, "recordType")
    sub(rect, "term", "item")
    recs = sub(recw, "recordSource")
    recn = sub(recs, "legalBodyName")
    sub(recn, "appellationValue", gallery.name)
    recinfo = sub(recw, "recordInfoSet")
    if artwork.source_url:
        sub(recinfo, "recordInfoLink", artwork.source_url)
    sub(recinfo, "recordMetadataDate",
        artwork.updated_at.strftime("%Y-%m-%dT%H:%M:%S") if artwork.updated_at else "")

    # resourceWrap
    images = artwork.images or []
    if images:
        resw = sub(am, "resourceWrap")
        for img in images:
            url = img.iiif_url
            if not url:
                continue
            ress = sub(resw, "resourceSet")
            resrep = sub(ress, "resourceRepresentation")
            lr = sub(resrep, "linkResource", url)
            lr.set(f"{{{LIDO_NS}}}formatResource", "image/jpeg")

    return lido


def _term_el(tag, text):
    el = etree.Element(L(tag))
    el.text = text
    return el


def build_lido_wrap(artworks, gallery):
    """Build a lidoWrap containing multiple lido records."""
    wrap = etree.Element(L("lidoWrap"), nsmap=NSMAP)
    wrap.set(f"{{{XSI_NS}}}schemaLocation", SCHEMA_LOCATION)
    for artwork in artworks:
        wrap.append(build_lido_record(artwork, gallery))
    return wrap


def serialize(root, pretty=True):
    """Serialize an lxml element to bytes."""
    return etree.tostring(
        root,
        pretty_print=pretty,
        xml_declaration=True,
        encoding="UTF-8",
    )
