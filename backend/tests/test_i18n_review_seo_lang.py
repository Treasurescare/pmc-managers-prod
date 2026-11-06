# v83: Translation review admin endpoints (stats/phrases/save) + language-prefixed sitemap/robots.
# Only TEST_ phrases are created; they are deleted by exact (lang, h) at teardown.
import hashlib
import os
import re
import uuid
import xml.etree.ElementTree as ET

import pytest
import requests
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = BASE + "/api/v1"
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
LANGS = ["ru", "kk", "zh-Hans", "zh-Hant", "es", "fr", "de", "hi", "ms", "id", "ko", "ja", "ar"]
S = {"created": []}


def _h(s):
    return hashlib.sha1(s.encode()).hexdigest()


def _sess(path, email, pw):
    s = requests.Session()
    r = s.post(f"{API}/{path}", json={"email": email, "password": pw}, timeout=30)
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
    S["admin"] = _sess("admin/auth/login", "adminsupport@pmcmanagers.com", "Admin@12345")
    yield
    for lg, src in S["created"]:
        DB.i18n_cache.delete_one({"lang": lg, "h": _h(src)})


# --- stats
def test_stats_admin():
    r = S["admin"].get(f"{API}/i18n/admin/stats", timeout=30)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert [i["lang"] for i in items] == LANGS
    for i in items:
        assert isinstance(i["total"], int) and isinstance(i["reviewed"], int)
        assert i["total"] > 1000 and 0 <= i["reviewed"] <= i["total"]
        assert i["name"]


def test_stats_unauth_401():
    r = requests.get(f"{API}/i18n/admin/stats", timeout=30)
    assert r.status_code in (401, 403)


def test_stats_vendor_forbidden():
    try:
        v = _sess("vendor/auth/login", "testvendor@pmcmanagers.com", "Vendor@12345")
    except AssertionError:
        pytest.skip("vendor login failed")
    r = v.get(f"{API}/i18n/admin/stats", timeout=30)
    assert r.status_code in (401, 403)
    r = v.put(f"{API}/i18n/admin/phrases", json={"lang": "fr", "src": "TEST_x", "out": "y"}, timeout=30)
    assert r.status_code in (401, 403)


def test_stats_reviewer_allowed():
    try:
        rv = _sess("admin/auth/login", "reviewerqa@pmcmanagers.com", "Reviewer@12345")
    except AssertionError:
        pytest.skip("reviewer login failed")
    r = rv.get(f"{API}/i18n/admin/stats", timeout=30)
    assert r.status_code == 200


# --- list / filter / paginate
def test_phrases_paginate():
    a = S["admin"].get(f"{API}/i18n/admin/phrases", params={"lang": "ar", "status": "all", "limit": 5}, timeout=30).json()
    b = S["admin"].get(f"{API}/i18n/admin/phrases", params={"lang": "ar", "status": "all", "limit": 5, "skip": 5}, timeout=30).json()
    assert a["total"] > 1000 and len(a["items"]) == 5 and len(b["items"]) == 5
    assert not {i["src"] for i in a["items"]} & {i["src"] for i in b["items"]}
    assert set(a["items"][0]) == {"src", "out", "reviewed", "reviewed_by", "reviewed_at"}


def test_phrases_status_counts_add_up():
    g = lambda st: S["admin"].get(f"{API}/i18n/admin/phrases", params={"lang": "ar", "status": st, "limit": 1}, timeout=30).json()["total"]
    assert g("pending") + g("reviewed") == g("all")


def test_phrases_search():
    r = S["admin"].get(f"{API}/i18n/admin/phrases", params={"lang": "fr", "q": "supplier", "status": "all", "limit": 200}, timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    assert all("supplier" in (i["src"] + i["out"]).lower() for i in items)


def test_phrases_regex_safe():
    r = S["admin"].get(f"{API}/i18n/admin/phrases", params={"lang": "fr", "q": "(.*[", "status": "all"}, timeout=30)
    assert r.status_code == 200


@pytest.mark.parametrize("params", [{"lang": "xx"}, {"lang": "en"}, {"lang": "ar", "status": "bogus"},
                                    {"lang": "ar", "limit": 0}, {"lang": "ar", "limit": 500}, {"lang": "ar", "skip": -1}])
def test_phrases_invalid_422(params):
    r = S["admin"].get(f"{API}/i18n/admin/phrases", params=params, timeout=30)
    assert r.status_code == 422


# --- save
def test_save_requires_csrf():
    s = requests.Session()
    s.headers.update({k: v for k, v in S["admin"].headers.items() if k == "Authorization"})
    s.cookies.update(S["admin"].cookies)
    s.cookies.set("csrf_token", None)
    r = s.put(f"{API}/i18n/admin/phrases", json={"lang": "fr", "src": "TEST_nocsrf", "out": "x"}, timeout=30)
    assert r.status_code == 403


@pytest.mark.parametrize("body", [{"lang": "xx", "src": "TEST_a", "out": "b"}, {"lang": "fr", "src": "", "out": "b"},
                                  {"lang": "fr", "src": "TEST_a", "out": "   "}, {"lang": "fr", "src": "TEST_a"}])
def test_save_invalid_422(body):
    r = S["admin"].put(f"{API}/i18n/admin/phrases", json=body, timeout=30)
    assert r.status_code == 422


def test_save_fix_live_everywhere_and_not_overwritten():
    src = f"TEST_ Review phrase {uuid.uuid4().hex[:8]}"
    out = "TEST_ Phrase corrigée par un relecteur"
    S["created"].append(("fr", src))
    before = S["admin"].get(f"{API}/i18n/admin/stats", timeout=30).json()["items"]
    r = S["admin"].put(f"{API}/i18n/admin/phrases", json={"lang": "fr", "src": "  " + src + " ", "out": out}, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["src"] == src and j["out"] == out and j["reviewed"] is True
    assert j["reviewed_by"] == "adminsupport@pmcmanagers.com" and j["reviewed_at"]
    # review list
    lst = S["admin"].get(f"{API}/i18n/admin/phrases", params={"lang": "fr", "q": src, "status": "reviewed"}, timeout=30).json()
    assert lst["total"] == 1 and lst["items"][0]["out"] == out and lst["items"][0]["reviewed"] is True
    pend = S["admin"].get(f"{API}/i18n/admin/phrases", params={"lang": "fr", "q": src, "status": "pending"}, timeout=30).json()
    assert pend["total"] == 0
    # stats incremented
    after = S["admin"].get(f"{API}/i18n/admin/stats", timeout=30).json()["items"]
    bf, af = [next(i for i in x if i["lang"] == "fr") for x in (before, after)]
    assert af["reviewed"] >= bf["reviewed"] + 1
    # public dict + translate return the fix (no AI call overwrites it)
    d = requests.get(f"{API}/i18n/dict/fr", timeout=60).json()["map"]
    assert d.get(src) == out
    t = requests.post(f"{API}/i18n/translate", json={"lang": "fr", "texts": [src]}, timeout=60).json()["map"]
    assert t.get(src) == out
    doc = DB.i18n_cache.find_one({"lang": "fr", "h": _h(src)})
    assert doc["out"] == out and doc["reviewed"] is True
    # second edit overwrites the reviewed fix
    r2 = S["admin"].put(f"{API}/i18n/admin/phrases", json={"lang": "fr", "src": src, "out": out + " v2"}, timeout=30)
    assert r2.status_code == 200
    assert requests.post(f"{API}/i18n/translate", json={"lang": "fr", "texts": [src]}, timeout=60).json()["map"][src] == out + " v2"
    # audit entry
    aud = DB.audit_logs.find_one({"action": "i18n.phrase_reviewed", "details.src": src}) or \
        DB.audit_log.find_one({"action": "i18n.phrase_reviewed"})
    print("audit found:", bool(aud))


# --- sitemap / robots
def test_sitemap_language_urls():
    r = requests.get(f"{API}/seo/sitemap.xml", timeout=30)
    assert r.status_code == 200 and "xml" in r.headers["content-type"]
    root = ET.fromstring(r.content)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    locs = [u.find("s:loc", ns).text for u in root.findall("s:url", ns)]
    paths = {re.sub(r"^https?://[^/]+", "", l) for l in locs}
    for p in ["/fr/buyers", "/ar", "/ja", "/de/about", "/zh-Hans/suppliers", "/ar/tenders/live", "/buyers", "/"]:
        assert p in paths, p
    assert "/fr/register" not in paths and "/fr/admin" not in paths
    url = next(u for u in root.findall("s:url", ns) if u.find("s:loc", ns).text.endswith("/fr/buyers"))
    alts = {a.get("hreflang"): a.get("href") for a in url.findall("x:link", ns)}
    assert len(alts) == 15 and "x-default" in alts and alts["en"].endswith("/buyers") and alts["ar"].endswith("/ar/buyers")
    assert len(locs) == len(set(locs)), "duplicate <loc>"


def test_robots_disallows_lang_private():
    t = requests.get(f"{API}/seo/robots.txt", timeout=30).text
    for line in ["Disallow: /admin", "Disallow: /*/admin", "Disallow: /*/staff", "Disallow: /*/vendor", "Sitemap:"]:
        assert line in t
