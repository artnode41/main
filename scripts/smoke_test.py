#!/usr/bin/env python3
"""ArtNode Smoke Test — hits every GET route and checks HTTP status codes."""
import requests, sys
from html.parser import HTMLParser

ADMIN_BASE = "https://admin.artnode.ch"
PUBLIC_BASE = "https://site.artnode.ch"
EMAIL = "admin@artnode.ch"
PASSWORD = "artnode2024"

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m~\033[0m"
results = {"pass": 0, "fail": 0, "warn": 0}

def check(label, response, expected=200):
    code = response.status_code
    if code == expected:
        print(f"  {PASS} {label} [{code}]")
        results["pass"] += 1
    elif code in (301, 302):
        print(f"  {WARN} {label} [{code} redirect]")
        results["warn"] += 1
    else:
        print(f"  {FAIL} {label} [{code}]")
        results["fail"] += 1

class CSRFParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "csrf_token":
            self.token = attrs.get("value")

print("\n== Auth ==")
session = requests.Session()
login_page = session.get(f"{ADMIN_BASE}/login")
check("GET /login", login_page)

parser = CSRFParser()
parser.feed(login_page.text)
csrf = parser.token

login_resp = session.post(f"{ADMIN_BASE}/login", data={
    "email": EMAIL, "password": PASSWORD, "csrf_token": csrf
}, allow_redirects=True)
if "/admin" in login_resp.url or "artworks" in login_resp.url:
    print(f"  {PASS} POST /login [authenticated]")
    results["pass"] += 1
else:
    print(f"  {FAIL} POST /login [failed]")
    sys.exit(1)

print("\n== Admin — Artworks ==")
check("GET /admin/artworks",               session.get(f"{ADMIN_BASE}/admin/artworks"))
check("GET /admin/artworks/new",           session.get(f"{ADMIN_BASE}/admin/artworks/new"))
check("GET /admin/artworks/182",            session.get(f"{ADMIN_BASE}/admin/artworks/182"))
check("GET /admin/artworks/182/edit",       session.get(f"{ADMIN_BASE}/admin/artworks/182/edit"))
check("GET /admin/artworks/182/provenance/add", session.get(f"{ADMIN_BASE}/admin/artworks/182/provenance/add"))

print("\n== Admin — Contacts ==")
check("GET /admin/contacts",               session.get(f"{ADMIN_BASE}/admin/contacts"))
check("GET /admin/contacts/new",           session.get(f"{ADMIN_BASE}/admin/contacts/new"))
check("GET /admin/contacts/26",            session.get(f"{ADMIN_BASE}/admin/contacts/26"))
check("GET /admin/contacts/26/edit",       session.get(f"{ADMIN_BASE}/admin/contacts/26/edit"))

print("\n== Admin — Exhibitions ==")
check("GET /admin/exhibitions",            session.get(f"{ADMIN_BASE}/admin/exhibitions"))
check("GET /admin/exhibitions/new",        session.get(f"{ADMIN_BASE}/admin/exhibitions/new"))
check("GET /admin/exhibitions/5",          session.get(f"{ADMIN_BASE}/admin/exhibitions/5"))
check("GET /admin/exhibitions/5/edit",     session.get(f"{ADMIN_BASE}/admin/exhibitions/5/edit"))

print("\n== Admin — Sales ==")
check("GET /admin/sales",                  session.get(f"{ADMIN_BASE}/admin/sales"))
check("GET /admin/sales/29",               session.get(f"{ADMIN_BASE}/admin/sales/29"))
check("GET /admin/sales/29/invoice",       session.get(f"{ADMIN_BASE}/admin/sales/29/invoice"))
check("GET /admin/sales/29/margin-report", session.get(f"{ADMIN_BASE}/admin/sales/29/margin-report"))

print("\n== Admin — Blog ==")
check("GET /admin/blog",                   session.get(f"{ADMIN_BASE}/admin/blog"))
check("GET /admin/blog/new",               session.get(f"{ADMIN_BASE}/admin/blog/new"))

print("\n== Admin — Fairs ==")
check("GET /admin/fairs",                  session.get(f"{ADMIN_BASE}/admin/fairs"))
check("GET /admin/fairs/new",              session.get(f"{ADMIN_BASE}/admin/fairs/new"))

print("\n== Admin — Viewing Rooms ==")
check("GET /admin/viewing-rooms",          session.get(f"{ADMIN_BASE}/admin/viewing-rooms"))

print("\n== Admin — Settings ==")
check("GET /admin/settings",               session.get(f"{ADMIN_BASE}/admin/settings"))
check("GET /admin/settings/export",        session.get(f"{ADMIN_BASE}/admin/settings/export"))
check("GET /admin/settings/users",         session.get(f"{ADMIN_BASE}/admin/settings/users"))
check("GET ESTV CSV export",               session.get(f"{ADMIN_BASE}/admin/settings/export/estv-csv"))

print("\n== Admin — API ==")
check("GET /api/v1/artworks/1/lido",       session.get(f"{ADMIN_BASE}/api/v1/artworks/1/lido"))
check("GET /api/v1/lido",                  session.get(f"{ADMIN_BASE}/api/v1/lido"))

print("\n== Public Site ==")
pub = requests.Session()
check("GET /",                             pub.get(f"{PUBLIC_BASE}/"))
check("GET /artists",                      pub.get(f"{PUBLIC_BASE}/artists"))
check("GET /artworks",                     pub.get(f"{PUBLIC_BASE}/artworks"))
check("GET /exhibitions",                  pub.get(f"{PUBLIC_BASE}/exhibitions"))
check("GET /blog",                         pub.get(f"{PUBLIC_BASE}/blog"))
check("GET /about",                        pub.get(f"{PUBLIC_BASE}/about"))
check("GET /contact",                      pub.get(f"{PUBLIC_BASE}/contact"))
check("GET /artworks/182",                 pub.get(f"{PUBLIC_BASE}/artworks/182"))
check("GET /artists/26",                   pub.get(f"{PUBLIC_BASE}/artists/26"))

print("\n== Public — Language Switching ==")
for lang in ["de", "fr", "it", "en"]:
    check(f"GET /lang/{lang}", pub.get(f"{PUBLIC_BASE}/lang/{lang}", allow_redirects=True))

print("\n== Garage Media ==")
check("GET artwork image from Garage",
    requests.get("https://site.artnode.ch/media/artnode-media/images/1/363/0751285813674ec7b4851ba379817b80.jpg"))

print("\n== Landing Page ==")
check("GET artnode.ch", requests.get("https://artnode.ch/"))

total = results["pass"] + results["fail"] + results["warn"]
print(f"\n{'='*50}")
print(f"Results: {results['pass']}/{total} passed, {results['fail']} failed, {results['warn']} warnings")
if results["fail"] == 0:
    print("All checks passed.")
else:
    print(f"{results['fail']} check(s) failed.")
    sys.exit(1)
