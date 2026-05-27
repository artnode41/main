"""
ArtNode Phase 8 — Cultural Heritage Export Routes
- /api/v1/artworks/<id>/lido  → single artwork LIDO XML
- /api/v1/lido                → bulk LIDO export (paginated, tenant-scoped)
- /api/v1/artworks/<id>       → single artwork JSON-LD
- /api/v1/collection          → bulk JSON-LD harvest
"""
from flask import Blueprint, Response, request, jsonify, abort
from flask_security import login_required, current_user, auth_token_required
from ...models import Artwork, Gallery, Exhibition, ExhibitionArtwork
from ...extensions import db

bp = Blueprint("export", __name__, url_prefix="/api/v1")


def _get_gallery(tenant_id):
    return Gallery.query.get(tenant_id)


# ============================================================
# LIDO XML
# ============================================================

@bp.route("/artworks/<int:id>/lido")
@auth_token_required
def artwork_lido(id):
    from ...lido import build_lido_record, serialize
    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id, active=True
    ).first_or_404()
    gallery = _get_gallery(current_user.tenant_id)
    root = build_lido_record(artwork, gallery)
    xml_bytes = serialize(root)
    return Response(
        xml_bytes,
        mimetype="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="lido_{artwork.id}.xml"'
        }
    )


@bp.route("/lido")
@auth_token_required
def bulk_lido():
    from ...lido import build_lido_wrap, serialize
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    artworks = Artwork.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Artwork.id).paginate(page=page, per_page=per_page, error_out=False)

    gallery = _get_gallery(current_user.tenant_id)
    root = build_lido_wrap(artworks.items, gallery)
    xml_bytes = serialize(root)
    resp = Response(xml_bytes, mimetype="application/xml")
    resp.headers["X-Total-Count"] = artworks.total
    resp.headers["X-Page"] = page
    resp.headers["X-Per-Page"] = per_page
    resp.headers["X-Total-Pages"] = artworks.pages
    return resp


# ============================================================
# JSON-LD
# ============================================================

@bp.route("/artworks/<int:id>")
@auth_token_required
def artwork_jsonld(id):
    from ...jsonld import build_artwork_jsonld
    artwork = Artwork.query.filter_by(
        id=id, tenant_id=current_user.tenant_id, active=True
    ).first_or_404()
    gallery = _get_gallery(current_user.tenant_id)
    data = build_artwork_jsonld(artwork, gallery)
    return jsonify(data)


@bp.route("/collection")
@auth_token_required
def collection_jsonld():
    from ...jsonld import build_artwork_jsonld
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    artworks = Artwork.query.filter_by(
        tenant_id=current_user.tenant_id, active=True
    ).order_by(Artwork.id).paginate(page=page, per_page=per_page, error_out=False)

    gallery = _get_gallery(current_user.tenant_id)
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"{gallery.public_name or gallery.name} — Collection",
        "numberOfItems": artworks.total,
        "hasPart": [build_artwork_jsonld(a, gallery) for a in artworks.items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": artworks.pages,
            "total_items": artworks.total,
        }
    }
    resp = jsonify(data)
    resp.headers["Link"] = f'<{request.base_url}?page={page+1}>; rel="next"' if artworks.has_next else ""
    return resp
