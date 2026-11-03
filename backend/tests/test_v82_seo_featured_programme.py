# v82: SEO (sitemap/robots) + admin-managed Featured Programme master.
# Restores featured programme doc to its original state at teardown.
import os
import re
import xml.etree.ElementTree as ET

import pytest
import requests
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = BASE + "/api/v1"
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
S = {}
KEYS = {"enabled", "eyebrow", "title", "summary", "stat_label", "tenders_link", "brief_url", "highlights"}


def _sess(path, email, pw, extra=None):
    s = requests.Session()
    r = s.post(f"{API}/{path}", json={"email": email, "password": pw, **(extra or {})})
    assert r.status_code == 200, r.text
    j = r.json()
    tok = j.get("access_token") or j.get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    if j.get("csrf_token"):
        s.headers["X-CSRF-Token"] = j["csrf_token"]
    return s


@pytest.fixture(scope="module", autouse=True)
def setup():
    S["orig_doc"] = DB.site_settings.find_one({"_id": "featured_programme"})
    S["admin"] = _sess("admin/auth/login", "adminsupport@pmcmanagers.com", "Admin@12345")
    yield
    if S["orig_doc"] is None:
        DB.site_settings.delete_one({"_id": "featured_programme"})
    else:
        DB.site_settings.replace_one({"_id": "featured_programme"}, S["orig_doc"], upsert=True)


def _payload(**kw):
    p = requests.get(f"{API}/site/featured-programme").json()
    p.update(kw)
    return p


# Public featured programme
def test_public_programme_defaults():
    r = requests.get(f"{API}/site/featured-programme")
    assert r.status_code == 200
    j = r.json()
    assert set(j.keys()) == KEYS
    if S["orig_doc"] is None:
        assert j["title"] == "Kazakhstan Integrated Development Programme"
        assert j["enabled"] is True
        assert len(j["highlights"]) == 4


# Admin save + persistence
def test_admin_save_and_persist():
    body = _payload(title="TEST_Programme X", eyebrow="TEST eyebrow", brief_url="https://example.com/b.pdf",
                    tenders_link="/tenders/live?q=x",
                    highlights=[{"title": "A", "text": "a"}, {"title": "  ", "text": "blank dropped"}])
    r = S["admin"].put(f"{API}/marketing/featured-programme", json=body)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["title"] == "TEST_Programme X"
    assert [h["title"] for h in j["highlights"]] == ["A"]
    g = requests.get(f"{API}/site/featured-programme").json()
    assert g["title"] == "TEST_Programme X" and g["brief_url"] == "https://example.com/b.pdf"
    assert g["tenders_link"] == "/tenders/live?q=x"


def test_admin_disable():
    r = S["admin"].put(f"{API}/marketing/featured-programme", json=_payload(enabled=False))
    assert r.status_code == 200
    assert requests.get(f"{API}/site/featured-programme").json()["enabled"] is False
    S["admin"].put(f"{API}/marketing/featured-programme", json=_payload(enabled=True))


@pytest.mark.parametrize("kw", [{"title": "   "}, {"title": ""}])
def test_empty_title_422(kw):
    r = S["admin"].put(f"{API}/marketing/featured-programme", json=_payload(**kw))
    assert r.status_code == 422


@pytest.mark.parametrize("kw", [{"tenders_link": "javascript:alert(1)"}, {"brief_url": "http://x.com"},
                                {"brief_url": "ftp://x"}, {"tenders_link": "tenders/live"}])
def test_bad_links_422(kw):
    r = S["admin"].put(f"{API}/marketing/featured-programme", json=_payload(**kw))
    assert r.status_code == 422, r.text


def test_missing_title_field_422():
    p = _payload()
    p.pop("title")
    assert S["admin"].put(f"{API}/marketing/featured-programme", json=p).status_code == 422


def test_unauth_rejected():
    r = requests.put(f"{API}/marketing/featured-programme", json=_payload(title="hack"))
    assert r.status_code in (401, 403)


def test_no_csrf_rejected():
    s = requests.Session()
    s.headers["Authorization"] = S["admin"].headers["Authorization"]
    r = s.put(f"{API}/marketing/featured-programme", json=_payload(title="nocsrf"))
    assert r.status_code in (401, 403), r.status_code


def test_vendor_rejected():
    try:
        v = _sess("vendor/auth/login", "testvendor@pmcmanagers.com", "Vendor@12345")
    except AssertionError:
        try:
            v = _sess("vendor/auth/login", "kestrel@demo.pmcmanagers.com", "Demo@Pmc2026")
        except AssertionError:
            pytest.skip("no vendor login")
    r = v.put(f"{API}/marketing/featured-programme", json=_payload(title="vendorhack"))
    assert r.status_code in (401, 403)


# Sitemap
def test_sitemap_xml():
    r = requests.get(f"{API}/seo/sitemap.xml")
    assert r.status_code == 200
    assert "xml" in r.headers["content-type"]
    root = ET.fromstring(r.content)
    locs = [e.text for e in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    static = [l for l in locs if "/notices/" not in l]
    assert len(static) == 12
    notices = [l for l in locs if "/notices/" in l]
    pub = list(DB.notices.find({"is_published": True}, {"notice_ref": 1, "title": 1}))
    rx = re.compile(r"\btest|demo\b|sample\b|dummy", re.I)
    expected = {n["notice_ref"] for n in pub if n.get("notice_ref") and not rx.search(n.get("title") or "")}
    assert {l.rsplit("/notices/", 1)[1] for l in notices} == expected
    print("locs:", len(locs), "published:", len(pub), "expected notices:", len(expected))


def test_robots():
    r = requests.get(f"{API}/seo/robots.txt")
    assert r.status_code == 200 and "text/plain" in r.headers["content-type"]
    assert "Sitemap:" in r.text and "Disallow: /admin" in r.text


def test_frontend_robots_static():
    r = requests.get(f"{BASE}/robots.txt")
    assert r.status_code == 200
    assert "Sitemap:" in r.text and "<html" not in r.text.lower()
