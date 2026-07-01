# ArtNode — Project Briefing for New Session

## What is ArtNode
Open-source gallery management platform for small Swiss contemporary art galleries. Practical replacement for Excel-based workflows and expensive SaaS tools like Artlogic. MIT licensed. Self-hostable with Docker. Live in production at v1.1.0.

## Live URLs
- https://artnode.ch — static landing page
- https://admin.artnode.ch — gallery admin (login: admin@artnode.ch / artnode2024)
- https://site.artnode.ch — public gallery website

## Infrastructure
- Server: Infomaniak VPS, Debian 13, IP 83.228.241.119
- SSH: ssh -i "C:\\Users\\edjeu\\Downloads\\server\\server\\id_rsa" debian@83.228.241.119
- Stack: Flask + PostgreSQL 15 + Garage (S3-compatible, replaces MinIO) + Gunicorn + Nginx
- Working dir: /home/debian/artnode/
- Repo: https://github.com/artnode41/main
- Docker: cd ~/artnode && docker compose up -d
- Rebuild: docker compose build --no-cache web && docker compose up -d
- Logs: docker compose logs web | tail -20
- DB: docker compose exec -T db psql -U artnode -d artnode -c "SQL"
- Migrations: always sync first: rm -rf migrations && docker compose cp web:/app/migrations ~/artnode/migrations
- Smoke test: python3 /home/debian/artnode/scripts/smoke_test.py (45 routes, all should pass)

## Nginx
- artnode.ch -> /home/debian/artnode/www/ (static files)
- admin.artnode.ch -> proxy 127.0.0.1:8069, / redirects to /admin/artworks
- site.artnode.ch -> proxy 127.0.0.1:8069, /admin blocked (403)
- /media/artnode-media/ -> proxy to Garage web server at 127.0.0.1:3902 with Host: artnode-media.web.garage.localhost
- SSL via Let's Encrypt (certbot, auto-renew)
- Configs: /etc/nginx/sites-available/

## Tech Stack (locked)
- Framework: Flask (Python)
- Database: PostgreSQL 15 + Flask-Migrate (Alembic)
- File/image storage: Garage v1.0.1 (S3-compatible, Apache-licensed, replaced MinIO at v1.0.2)
- PDF generation: WeasyPrint 60.2 + pydyf 0.10.0 (PINNED - 62.x has bug, do not upgrade)
- Payments: Payrexx (Swiss provider)
- Auth: Flask-Security (token auth for API)
- Translations: Flask-Babel (DE/FR/IT/EN)
- Deployment: Docker Compose + Gunicorn 3 workers
- XML: lxml 5.3.0 (LIDO)
- OTS: opentimestamps-client (Bitcoin anchoring)
- GPG: python-gnupg (optional signing)

## Garage Object Storage
- Replaced MinIO at v1.0.2 (MinIO dropped Docker images in 2025)
- S3 API on port 3900 (uploads/deletes via boto3/minio SDK, region="garage")
- Web server on port 3902 (public file serving via Nginx proxy)
- Config: /home/debian/artnode/garage/garage.toml
- Bucket: artnode-media
- Key ID: GKfa25686b891e60bd0cd4d097 (in .env as MINIO_ROOT_USER)
- Secret: in .env as MINIO_ROOT_PASSWORD
- All Minio() client calls require region="garage" parameter
- File paths: images/{tenant_id}/{artwork_id}/{hash}.jpg, provenance/{...}, invoices/{tenant_id}/{sale_id}/invoice_{number}.pdf

## Key Files
- app/__init__.py — app factory, blueprints, Jinja filters, Garage upload helper, context processors (inject_today, inject_csrf, inject_gallery_settings)
- app/models.py — all SQLAlchemy models
- app/kgtg.py — KGTG provenance pipeline (PDF+SHA256+OTS+GPG+Garage)
- app/blueprints/artworks/routes.py — inventory, images, provenance
- app/blueprints/artworks/provenance_forms.py — ProvenanceForm with Art. 24a fields
- app/blueprints/sales/routes.py — invoices, margin tax, invoice archiving
- app/blueprints/settings/__init__.py — gallery settings + ESTV CSV export route
- app/blueprints/public/__init__.py — public site + maintenance check (before_request)
- app/templates/base.html — admin base (sidebar, dynamic font loading via current_gallery)
- app/templates/public/base.html — public site base (dynamic font loading via gallery)
- app/templates/sales/margin_report.html — internal ESTV margin report
- app/templates/public/maintenance.html — maintenance page (shown when gallery.maintenance_mode=True)
- app/static/css/artnode.css — admin styles (--font-display/--font-ui CSS vars)
- garage/garage.toml — Garage config
- www/index.html — landing page (artnode.ch)
- www/i18n.js — landing page translations (DE/FR/IT/EN)
- scripts/smoke_test.py — 45-route smoke test

## Data Model (key fields)

### gallery (single-gallery self-hosted model)
- logo_url: base64 PNG
- maintenance_mode: Boolean — puts public site into 503 maintenance page
- font_pairing: "classic" | "architectural" | "humanist"
- vat_scheme_default: "standard" | "margin"
- public_name, about, tagline — all with JSONB translations column

### artwork
- contact_artist_id FK->contact
- is_public, is_featured, is_carousel, status (available->reserved->sold)
- price, currency, show_price — show_price controls public price display
- acquisition_cost — internal purchase price (NEVER shown to buyers)
- acquisition_date, inventory_number

### artwork_provenance (append-only KGTG log)
- event_type, event_date, source_name, source_country, description
- document_hash (SHA-256), document_path, ots_file_path, gpg_sig_path, ots_status
- attached_files[] — Garage paths
- Art. 24a fields: supplier_address, supplier_vat_status, purchase_price, purchase_invoice_number, right_of_disposal, retention_30yr

### sale
- invoice_number, invoice_date, vat_scheme ("standard" | "margin")
- invoice_pdf_path — Garage path, auto-archived on first invoice download (all sales)

### sale_line_item
- price, vat_rate, vat_amount, currency
- tax_method ("standard" | "margin")
- purchase_price_at_sale — snapshotted from artwork.acquisition_cost at sale time (never entered in front of buyer)

### contact (unified person/institution)
- roles[] array, 20 roles across 5 categories
- Artist fields: biography, birth_year, death_year, nationality, slug, cv_json, artist_website, is_active_representation

## Swiss VAT Compliance (Art. 24a MWSTG) — Full Implementation
- Acquisition: provenance form captures supplier name/address, VAT status verification, purchase price, purchase invoice number, right of disposal, 30-year retention flag (revCPTO 2026)
- Sale: select "Margenbesteuerung Art. 24a MWSTG" — acquisition cost auto-snapshotted into purchase_price_at_sale, vat_rate=0, vat_amount=0
- Customer invoice: gross total only, mandatory legal notice "Differenzbesteuerung nach Art. 24a MWSTG, kein Ausweis der Mehrwertsteuer", no VAT line
- Internal margin report: /admin/sales/<id>/margin-report — purchase price, gross margin, internal VAT (margin - margin/1.081), net margin
- ESTV CSV export: /admin/settings/export — quarterly, anti-netting max(0,margin), 11 columns incl. purchase invoice number
- Invoice archiving: all invoices auto-archived to Garage on first download. PDF Archived badge on sale detail page.

## Typography System (configurable per gallery)
Three font pairings in Settings -> Typography, applied to both admin and public site:
- classic (default): Fraunces + Instrument Sans
- architectural: Newsreader + Archivo
- humanist: Spectral + Karla
CSS vars: --font-display/--font-ui (admin), --font-serif/--font-sans (public)
Loaded dynamically via Google Fonts based on gallery.font_pairing.
Admin uses current_gallery context processor (inject_gallery_settings in __init__.py).

## Multilingual (DE/FR/IT/EN)
- UI strings: Flask-Babel, .po files in app/translations/
- After editing .po: pybabel compile -d app/translations then restart web
- Content: JSONB translations column on artwork, contact, exhibition, gallery
- CRITICAL: SQLAlchemy JSON columns require flag_modified(obj, 'translations') after mutation
- Language switcher: session-based, /lang/<code> route
- Jinja: use get_trans(obj, "field") helper, avoid naming loop vars "_" (conflicts with _() translation function)

## Maintenance Mode
- Toggle in Settings -> Public Website
- When ON: all public routes return maintenance.html with 503 (admin unaffected)
- Implemented via @bp.before_request in public blueprint
- Checkbox state saved via request.form.get("maintenance_mode") == "y" (WTForms BooleanField unreliable)
- CURRENTLY OFF — check before demo or after reset

## Public Site — Price Display
- artwork.show_price + artwork.price controls what appears on /artworks/<id>
- show_price=True + price set -> shows formatted price with currency (e.g. CHF 15'000)
- Otherwise shows "Price on request" / "Preis auf Anfrage" / "Prix sur demande" / "Prezzo su richiesta"

## API Endpoints
- GET /api/v1/artworks/<id>/lido — single artwork LIDO 1.1 XML
- GET /api/v1/lido?page=&per_page= — bulk paginated LIDO
- GET /api/v1/artworks/<id> — single artwork JSON-LD
- GET /api/v1/collection?page= — bulk JSON-LD
Auth: Authentication-Token header. Get token: docker compose exec web python3 -c "from app import create_app; from app.models import User; app=create_app(); [print(u.get_auth_token()) for u in [User.query.filter_by(email='admin@artnode.ch').first()]] if True else None" (run inside app context)

## Known Gotchas
- Templates NOT volume-mounted for sales/fairs — must docker compose cp after editing
- Migrations lost on --no-cache rebuild — always sync first
- passlib patched in Dockerfile: sed -i 's/import pkg_resources/import importlib.metadata/'
- WeasyPrint 60.2 + pydyf 0.10.0 pinned (62.x has PDF transform bug — do not upgrade)
- base64 logo in DB — intentional, avoids Garage URL proxy complexity
- GitHub token expires — regenerate at github.com/settings/tokens
- BooleanField in WTForms: use request.form.get("field") == "y" for reliable checkbox reads
- SQLAlchemy JSON columns: always flag_modified(obj, 'translations') after mutation
- Jinja _ variable collision: never use _ as loop var (conflicts with _() i18n function), use _x or _tl

## Communication Protocol
- Wait state: stop after every command, wait for output before proceeding
- Zero assumptions: ask diagnostics if unsure
- Verification step after each task
