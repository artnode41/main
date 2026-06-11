# ArtNode

Open-source gallery management platform for small contemporary art galleries. Built as a practical replacement for Excel-based workflows, targeting Swiss galleries that need inventory, contacts, exhibitions, sales, provenance tracking, and Swiss VAT compliance in one place — without the cost or complexity of commercial solutions like Artlogic.

MIT licensed. Self-hostable with Docker.

---

## Live Demo

| Interface | URL | Credentials |
|---|---|---|
| Admin | https://admin.artnode.ch | `admin@artnode.ch` / `artnode2024` |
| Public site | https://site.artnode.ch | — |
| Landing page | https://artnode.ch | — |

The demo resets periodically to a clean state (181 artworks, 23 artists). Feel free to create exhibitions, sales, contacts, etc.

---

## Features

**Artworks**
- Inventory with status state machine: `available → reserved → sold`
- Image upload (JPG/PNG) stored in Garage object storage
- Materials, techniques, dimensions, acquisition cost
- Public/private visibility, featured and carousel flags
- Multilingual descriptions and medium (DE/FR/IT/EN)

**Contacts**
- Unified model for artists, buyers, collectors, institutions, lenders, conservators
- 20 categorised roles across 5 groups
- Artist fields: biography (multilingual), birth/death year, nationality, CV, website, photo
- Representation status tracking

**Exhibitions**
- Active show drives public site carousel automatically
- Forthcoming exhibitions shown with "Coming Soon" on public site
- Per-exhibition artwork selection with sort order
- Multilingual descriptions (DE/FR/IT/EN)

**Sales & Swiss VAT**
- Line-item invoices with WeasyPrint PDF generation
- Standard VAT 8.1% or Margenbesteuerung (Art. 24a MWSTG) per sale
- Masked invoices for margin-taxed sales (legal notice, no VAT line shown)
- Internal margin report per sale for ESTV submission
- Quarterly ESTV CSV export with all mandatory fields (anti-netting applied)
- Payrexx payment link integration (Swiss provider)
- Art fair POS context

**Provenance (KGTG / Art. 24a)**
- Append-only provenance log per artwork
- Acquisition events capture: supplier name/address, VAT status verification, purchase price, purchase invoice number, right of disposal, 30-year retention flag (revCPTO 2026)
- Per-event PDF certificate → SHA-256 hash → Bitcoin timestamping via OpenTimestamps → optional GPG signature
- All documents stored in Garage object storage
- OTS status tracking: `pending → submitted → confirmed`

**Viewing Rooms**
- Password-protected, date-gated online viewing
- Shareable link, no login required for visitors
- Quick-share: select artworks from inventory and generate a public link in one click

**Blog**
- Per-language blog posts (DE/FR/IT/EN) linked by translation group
- Rich text editor (Trix)
- Smart language switcher — redirects to same post in new language

**Public Site (Multilingual DE/FR/IT/EN)**
- Artists grid with photos and artwork thumbnails
- Filterable artworks collection (artist, medium category, price range)
- Exhibitions with carousel, forthcoming, past
- Blog with language-aware routing
- About page with multilingual gallery tagline and description
- Contact form
- Burger nav all viewports, language switcher always visible

**Cultural Heritage Export**
- LIDO 1.1 XML per artwork and bulk paginated
- JSON-LD with schema.org + CIDOC-CRM vocabularies
- Token-authenticated REST API
- Export & API page in admin with LIDO download and ESTV CSV export

**User Management**
- Invite staff by email (sends password reset link)
- Assign role: Admin or Staff
- Multi-tenant architecture (one gallery row per installation)

---

## Stack

| Layer | Technology |
|---|---|
| Framework | Flask (Python) |
| Database | PostgreSQL 15 + Flask-Migrate (Alembic) |
| File storage | Garage v1.0.1 (S3-compatible, AGPLv3) |
| PDF generation | WeasyPrint 60.2 + pydyf 0.10.0 (pinned) |
| Auth | Flask-Security |
| Payments | Payrexx (Swiss provider) |
| Translations | Flask-Babel (DE/FR/IT/EN) |
| XML | lxml 5.3.0 |
| Timestamping | opentimestamps-client |
| Deployment | Docker Compose + Gunicorn + Nginx |

> **Note:** WeasyPrint is pinned at 60.2 / pydyf 0.10.0. Version 62.x has a known PDF transform bug — do not upgrade.

---

## Self-Hosting

### Requirements
- Docker + Docker Compose
- A domain with DNS control
- 1GB RAM minimum (2GB recommended)
- Debian/Ubuntu Linux

### 1. Clone

```bash
git clone https://github.com/artnode41/main artnode
cd artnode
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
SECRET_KEY=your-random-64-char-hex
POSTGRES_PASSWORD=your-db-password
MINIO_ROOT_USER=<garage-access-key-id>     # set after Garage setup below
MINIO_ROOT_PASSWORD=<garage-secret-key>    # set after Garage setup below
MINIO_BUCKET=artnode-media
```

### 3. Generate Garage RPC secret

```bash
openssl rand -hex 32
```

Paste the result into `garage/garage.toml` as `rpc_secret`.

### 4. Start services

```bash
docker compose up -d
```

### 5. Initialize Garage storage

```bash
# Get node ID
NODE_ID=$(docker compose exec garage /garage node id 2>/dev/null | head -1 | cut -d'@' -f1)

# Assign capacity (adjust size as needed)
docker compose exec garage /garage layout assign -z default -c 10G $NODE_ID
docker compose exec garage /garage layout apply --version 1

# Create access key
docker compose exec garage /garage key create artnode-key
# → note the Key ID and Secret key, add to .env

# Create bucket and grant access
docker compose exec garage /garage bucket create artnode-media
docker compose exec garage /garage bucket allow artnode-media --read --write --owner --key artnode-key
docker compose exec garage /garage bucket website --allow artnode-media
```

Update `.env` with the Key ID (`MINIO_ROOT_USER`) and Secret key (`MINIO_ROOT_PASSWORD`), then restart:

```bash
docker compose up -d --force-recreate web
```

### 6. Run migrations

```bash
docker compose exec web flask db upgrade
```

### 7. Create admin user

```bash
docker compose exec web python3 -c "
from app import create_app
from app.extensions import db
from app.models import user_datastore, Gallery
app = create_app()
with app.app_context():
    g = Gallery(name='My Gallery')
    db.session.add(g)
    db.session.flush()
    user_datastore.create_user(
        email='admin@yourgallery.com',
        password='yourpassword',
        active=True,
        tenant_id=g.id
    )
    db.session.commit()
    print('Done')
"
```

### 8. Seed demo data (optional)

Imports 181 artworks and 23 artists from the Art Institute of Chicago open-access collection:

```bash
docker compose exec web python3 scripts/seed/reset_and_seed.py
```

### 9. Nginx + SSL

Routing:
- `artnode.ch` → static files in `www/`
- `admin.artnode.ch` → proxy to `127.0.0.1:8069`, `/` redirects to `/admin/artworks`
- `site.artnode.ch` → proxy to `127.0.0.1:8069`, `/admin/*` blocked (403)
- `/media/artnode-media/` → proxy to Garage web server at `127.0.0.1:3902` with `Host: artnode-media.web.garage.localhost`

```bash
certbot --nginx -d admin.yourdomain.com -d site.yourdomain.com
```

---

## Swiss VAT Compliance (Art. 24a MWSTG)

ArtNode fully implements Swiss Margenbesteuerung for secondary art market transactions:

- **Acquisition**: Record purchase price, supplier details, and VAT status in the provenance form
- **Sale**: Select "Margenbesteuerung Art. 24a MWSTG" — acquisition cost is automatically snapshotted
- **Invoice**: Customer receives a masked invoice (gross total only, mandatory legal notice, no VAT line)
- **Internal report**: Per-sale margin report shows purchase price, gross margin, internal VAT (CHF 374.65 on CHF 5,000 margin), net margin
- **Quarterly export**: ESTV CSV export in Export & API with anti-netting logic (losses → CHF 0.00 VAT)

> Note: OpenTimestamps Bitcoin anchoring is not a qualified electronic signature under Swiss ZertES or EU eIDAS.

---

## Resetting to Clean State

```bash
docker compose exec web python3 scripts/seed/reset_and_seed.py
```

Wipes all data and re-seeds from the JSON file. Gallery name and admin credentials are preserved. Garage storage is also purged.

---

## API

All endpoints require an `Authentication-Token` header.

**Get your token:**

```bash
docker compose exec web python3 -c "
from app import create_app
from app.models import User
app = create_app()
with app.app_context():
    u = User.query.filter_by(email='admin@artnode.ch').first()
    print(u.get_auth_token())
"
```

**Endpoints:**

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/artworks/<id>` | Single artwork JSON-LD |
| GET | `/api/v1/collection?page=` | Bulk JSON-LD harvest |
| GET | `/api/v1/artworks/<id>/lido` | Single artwork LIDO 1.1 XML |
| GET | `/api/v1/lido?page=&per_page=` | Bulk paginated LIDO export |

---

## Project Structure
artnode/
├── app/
│   ├── init.py          # App factory, blueprints, Jinja filters, Garage helper
│   ├── models.py            # All SQLAlchemy models
│   ├── extensions.py        # db, login manager
│   ├── lido.py              # LIDO 1.1 XML serializer
│   ├── jsonld.py            # JSON-LD serializer (schema.org + CIDOC-CRM)
│   ├── kgtg.py              # Provenance pipeline (PDF+SHA256+OTS+GPG+Garage)
│   ├── translations/        # Flask-Babel .po/.mo files (DE/FR/IT/EN)
│   └── blueprints/
│       ├── artworks/        # Inventory, images, provenance
│       ├── contacts/        # CRM with roles
│       ├── exhibitions/
│       ├── sales/           # Invoices, margin tax, ESTV report
│       ├── fairs/           # Art fair POS
│       ├── viewing_rooms/
│       ├── blog/            # Multilingual blog
│       ├── settings/        # Gallery config, users, export
│       ├── export/          # LIDO + JSON-LD API
│       └── public/          # Public gallery website
├── garage/
│   └── garage.toml          # Garage object storage config
├── scripts/
│   └── seed/
│       ├── reset_and_seed.py
│       └── import_aic.py
├── www/                     # Static landing page (artnode.ch)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example

---

## Background

Built by a data analyst to give galleries a quick, professional solution — moving them off Excel without locking them into expensive SaaS contracts. Production-ready, MIT licensed, solo project.

If you find it useful, adapt it freely. PRs welcome.

---

## License

MIT — see [LICENSE](LICENSE).
