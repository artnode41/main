# ArtNode

Open-source gallery management platform for small contemporary art galleries. Built as a practical replacement for Excel-based workflows, targeting Swiss galleries that need inventory, contacts, exhibitions, sales, and provenance tracking in one place — without the cost or complexity of commercial solutions like Artlogic.

MIT licensed. Self-hostable with Docker in under 10 minutes.

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
- Materials, techniques, dimensions, provenance
- Public/private visibility flag, featured and carousel flags
- IIIF image support + MinIO storage

**Contacts**
- Unified model for artists, buyers, collectors, institutions, lenders, conservators
- 20 categorised roles across 5 groups
- Artist-specific fields: biography, birth/death year, nationality, CV, website, representation status

**Exhibitions**
- Active show drives public site carousel automatically
- Per-exhibition artwork selection with sort order

**Sales**
- Line-item invoices with WeasyPrint PDF generation
- Payrexx payment link integration (Swiss provider)
- Art fair POS context

**Viewing Rooms**
- Password-protected, date-gated online viewing
- Shareable link, no login required for visitors
- Quick-share: select artworks from the inventory list and generate a public link in one click

**Provenance (KGTG)**
- Per-event PDF certificate → SHA-256 hash → Bitcoin timestamping via OpenTimestamps → optional GPG signature
- All documents stored in MinIO
- OTS status tracking: `pending → submitted → confirmed`

**Cultural Heritage Export (Phase 8)**
- LIDO 1.1 XML per artwork and bulk paginated
- JSON-LD with schema.org + CIDOC-CRM vocabularies
- Token-authenticated REST API
- Export & API page in admin (`/admin/settings/export`) — token display, endpoint reference, one-click LIDO XML download

---

## Stack

| Layer | Technology |
|---|---|
| Framework | Flask (Python) |
| Database | PostgreSQL 15 + Flask-Migrate (Alembic) |
| File storage | MinIO |
| PDF generation | WeasyPrint 60.2 + pydyf 0.10.0 (pinned) |
| Auth | Flask-Security |
| Payments | Payrexx |
| XML | lxml 5.3.0 |
| Timestamping | opentimestamps-client |
| Deployment | Docker Compose + Gunicorn (3 workers) + Nginx |

> **Note:** WeasyPrint is pinned at 60.2 / pydyf 0.10.0. Version 62.x has a known PDF transform bug — do not upgrade.

---

## Public Site

The public gallery website (`site.artnode.ch`) is fully mobile-responsive. All 9 public templates include `@media (max-width: 768px)` breakpoints — hamburger nav, stacked layouts, adjusted padding.

**Public pages:**
- `/artists` — image grid with artist thumbnails, artist photo upload in admin
- `/artworks` — filterable collection (artist, medium category, price range)
- `/exhibitions` — current, forthcoming, past
- `/blog` — posts per language, smart language switching
- `/about`, `/contact` — gallery info and contact form

**Multilingual (DE/FR/IT/EN):**
- UI strings via Flask-Babel
- Artist biography, artwork description/medium, exhibition description — JSONB translation tabs in admin
- Gallery tagline and about text — translation tabs in settings
- Blog posts — separate records per language linked by translation group
- Language switcher in nav, session-based, browser language detection on first visit

## User Management

Multiple gallery staff can be invited via `/admin/settings/users`:
- Invite by email (sends password reset link)
- Assign role: Admin or Staff
- Delete users

## Self-Hosting

### Requirements
- Docker + Docker Compose
- A domain with DNS control (for Nginx + SSL)
- 1GB RAM minimum

### 1. Clone

```bash
git clone https://github.com/artnode41/main artnode
cd artnode
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your-random-secret-key
POSTGRES_PASSWORD=your-db-password
MINIO_ROOT_PASSWORD=your-minio-password
```

### 3. Start

```bash
docker compose up -d
```

### 4. Run migrations

```bash
docker compose exec web flask db upgrade
```

### 5. Create admin user

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

### 6. Seed demo data (optional)

Imports 181 artworks and 23 artists from the bundled contemporary art JSON:

```bash
docker compose exec web python3 scripts/seed/reset_and_seed.py
```

### 7. Nginx + SSL

Sample Nginx configs are not included in the repo (they contain server-specific paths), but the routing is:

- `artnode.ch` → static files in `www/`
- `admin.artnode.ch` → proxy to `127.0.0.1:8069`, `/` redirects to `/admin/artworks`
- `site.artnode.ch` → proxy to `127.0.0.1:8069`, `/admin/*` blocked (403)

Use Certbot for SSL:

```bash
certbot --nginx -d admin.yourdomain.com -d site.yourdomain.com
```

---

## Resetting to Clean State

Wipes all data (exhibitions, sales, contacts, provenance, logo) and re-seeds from the JSON file. Gallery name and admin credentials are preserved.

```bash
docker compose exec web python3 scripts/seed/reset_and_seed.py
```

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

The JSON-LD output uses schema.org + CIDOC-CRM vocabularies. LIDO follows the LIDO 1.1 schema. Note: OpenTimestamps anchoring is not qualified under Swiss ZertES or EU eIDAS.

---

## Project Structure
artnode/
├── app/
│   ├── init.py          # App factory, blueprints, Jinja filters
│   ├── models.py            # All SQLAlchemy models
│   ├── extensions.py        # db, login manager
│   ├── lido.py              # LIDO 1.1 XML serializer
│   ├── jsonld.py            # JSON-LD serializer
│   ├── kgtg.py              # Provenance pipeline (PDF+SHA256+OTS+GPG+MinIO)
│   └── blueprints/
│       ├── artworks/
│       ├── contacts/
│       ├── exhibitions/
│       ├── sales/
│       ├── fairs/
│       ├── viewing_rooms/
│       ├── settings/
│       ├── export/          # LIDO + JSON-LD API routes
│       └── public/          # Public site
├── scripts/
│   └── seed/
│       ├── reset_and_seed.py
│       └── import_aic.py
├── www/                     # Static landing page
├── artnode_seed_contemporary.json
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example

---

## Background

I'm a data analyst who built this to give a quick, professional solution to galleries I work with — moving them off Excel without locking them into expensive SaaS contracts. It's a solo project. All 8 development phases are complete and it's running in production.

If you find it useful, adapt it freely. PRs are welcome but I can't promise a quick review turnaround.

---

## License

MIT — see [LICENSE](LICENSE).
