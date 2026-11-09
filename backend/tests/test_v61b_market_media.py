# v61b — Marketplace photo/spec-sheet upload, AI catalogue import, bulk drafts, needs_details gate, foreign media ids
# Requires: python tests/mkt_v61b_seed.py create (TEST_ vendor #2) and python tests/make_test_catalogue.py (/tmp/test_catalogue.pdf)
# Cleanup: python tests/mkt_v61b_seed.py clean (uses /tmp/mkt_v61b_created.json written by this module)
import base64
import io
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api/v1/market"
S = {}


def vlogin(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


def png_bytes(size=(300, 200), mode="RGBA"):
    b = io.BytesIO()
    Image.new(mode, size, (200, 30, 30, 255) if mode == "RGBA" else (200, 30, 30)).save(b, "PNG")
    return b.getvalue()


def pdf_bytes():
    import fitz
    d = fitz.open(); p = d.new_page(); p.insert_text((50, 60), "TEST_ spec sheet")
    return d.tobytes()


@pytest.fixture(scope="module")
def tracked():
    t = {"listings": [], "media": [], "imports": []}
    yield t
    json.dump(t, open("/tmp/mkt_v61b_created.json", "w"))


@pytest.fixture(scope="module")
def v1():
    return vlogin("testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def v2():
    return vlogin("test_mkt_v2_v61b@example.com", "Vendor@12345")


def future(h=48):
    return (datetime.now(timezone.utc) + timedelta(hours=h)).isoformat()


class TestMedia:
    def test_upload_photo_png_reencoded_jpeg(self, v1, tracked):
        r = v1.post(f"{API}/media", files={"file": ("TEST_p.png", png_bytes(), "image/png")}, data={"kind": "photo"})
        assert r.status_code == 200, r.text
        d = r.json(); tracked["media"].append(d["id"]); S["photo"] = d["id"]
        assert d["kind"] == "photo" and isinstance(d["id"], str)
        g = requests.get(f"{API}/media/{d['id']}")
        assert g.status_code == 200 and g.headers["content-type"].startswith("image/jpeg")
        assert g.content[:3] == b"\xff\xd8\xff"

    def test_upload_document_pdf(self, v1, tracked):
        r = v1.post(f"{API}/media", files={"file": ("TEST_spec.pdf", pdf_bytes(), "application/pdf")}, data={"kind": "document"})
        assert r.status_code == 200, r.text
        d = r.json(); tracked["media"].append(d["id"]); S["doc"] = d["id"]
        g = requests.get(f"{API}/media/{d['id']}?download=true")
        assert g.status_code == 200 and g.headers["content-type"] == "application/pdf"
        assert "attachment" in g.headers.get("content-disposition", "")

    def test_reject_wrong_types(self, v1):
        assert v1.post(f"{API}/media", files={"file": ("x.gif", b"GIF89a", "image/gif")}, data={"kind": "photo"}).status_code == 400
        assert v1.post(f"{API}/media", files={"file": ("x.png", b"not an image", "image/png")}, data={"kind": "photo"}).status_code == 400
        assert v1.post(f"{API}/media", files={"file": ("x.pdf", b"hello", "application/pdf")}, data={"kind": "document"}).status_code == 400
        assert v1.post(f"{API}/media", files={"file": ("x.docx", b"PK", "application/octet-stream")}, data={"kind": "document"}).status_code == 400
        assert v1.post(f"{API}/media", files={"file": ("x.png", png_bytes(), "image/png")}, data={"kind": "video"}).status_code == 400

    def test_photo_too_large(self, v1):
        big = b"\x89PNG" + os.urandom(8 * 1024 * 1024 + 10)
        assert v1.post(f"{API}/media", files={"file": ("big.png", big, "image/png")}, data={"kind": "photo"}).status_code == 413

    def test_upload_requires_auth_and_csrf(self, v1):
        assert requests.post(f"{API}/media", files={"file": ("x.png", png_bytes(), "image/png")}, data={"kind": "photo"}).status_code in (401, 403)
        s = requests.Session(); s.cookies.update(v1.cookies)
        assert s.post(f"{API}/media", files={"file": ("x.png", png_bytes(), "image/png")}, data={"kind": "photo"}).status_code == 403

    def test_media_404(self):
        assert requests.get(f"{API}/media/doesnotexist123").status_code == 404

    def test_b64_upload_path(self, v1, tracked):
        payload = {"fields": [{"name": "kind", "value": "photo"}], "files": [{"name": "file", "filename": "TEST_b64.png", "type": "image/png",
                                                                              "b64": base64.b64encode(png_bytes()).decode()}]}
        r = v1.post(f"{API}/media", json=payload, headers={"X-PMC-Upload": "b64"})
        if r.status_code == 200:
            tracked["media"].append(r.json()["id"])
        assert r.status_code == 200, r.text


class TestListingsMedia:
    def test_create_with_photos_and_docs(self, v1, tracked):
        r = v1.post(f"{API}/listings", json={"title": "TEST_ v61b photo listing", "sale_modes": ["fixed"], "buy_now_price": 50,
                                             "photos": [S["photo"]], "documents": [{"id": S["doc"], "name": "Spec.pdf"}]})
        assert r.status_code == 200, r.text
        S["lid"] = r.json()["id"]; tracked["listings"].append(S["lid"])
        mine = v1.get(f"{API}/mine").json()["items"]
        l = next(x for x in mine if x["id"] == S["lid"])
        assert l["photos"] == [S["photo"]] and l["documents"] == [{"id": S["doc"], "name": "Spec.pdf"}]

    def test_create_rejects_foreign_photo(self, v2):
        r = v2.post(f"{API}/listings", json={"title": "TEST_ foreign", "sale_modes": ["fixed"], "buy_now_price": 5, "photos": [S["photo"]]})
        assert r.status_code == 400

    def test_create_rejects_foreign_document(self, v2):
        r = v2.post(f"{API}/listings", json={"title": "TEST_ foreign doc", "sale_modes": ["fixed"], "buy_now_price": 5,
                                             "documents": [{"id": S["doc"], "name": "x"}]})
        assert r.status_code == 400

    def test_update_rejects_foreign_and_accepts_own(self, v1, v2, tracked):
        r = v2.post(f"{API}/media", files={"file": ("TEST_v2.png", png_bytes(), "image/png")}, data={"kind": "photo"})
        assert r.status_code == 200; S["v2photo"] = r.json()["id"]; tracked["media"].append(S["v2photo"])
        body = {"title": "TEST_ v61b photo listing", "sale_modes": ["fixed"], "buy_now_price": 60, "photos": [S["v2photo"]]}
        assert v1.put(f"{API}/listings/{S['lid']}", json=body).status_code == 400
        body["photos"] = [S["photo"]]
        assert v1.put(f"{API}/listings/{S['lid']}", json=body).status_code == 200


class TestBulk:
    def test_bulk_rejects_foreign(self, v1):
        r = v1.post(f"{API}/listings/bulk", json={"items": [{"title": "TEST_ bulk foreign", "photos": [S["v2photo"]]}]})
        assert r.status_code == 400

    def test_bulk_creates_needs_details_drafts(self, v1, tracked):
        r = v1.post(f"{API}/listings/bulk", json={"items": [
            {"title": "TEST_ bulk A", "description": "d", "unit": "unit", "photos": [S["photo"]]},
            {"title": "TEST_ bulk B", "documents": [{"id": S["doc"], "name": "cat.pdf"}]}]})
        assert r.status_code == 200, r.text
        d = r.json(); assert d["created"] == 2; tracked["listings"].extend(d["ids"]); S["bulk"] = d["ids"]
        mine = {x["id"]: x for x in v1.get(f"{API}/mine").json()["items"]}
        a = mine[d["ids"][0]]
        assert a["needs_details"] is True and a["status"] == "draft" and a["source"] == "catalogue_ai" and a["photos"] == [S["photo"]]

    def test_submit_blocked_until_edit(self, v1):
        lid = S["bulk"][0]
        r = v1.post(f"{API}/listings/{lid}/submit")
        assert r.status_code == 400 and "Edit" in r.json()["detail"]
        r = v1.put(f"{API}/listings/{lid}", json={"title": "TEST_ bulk A", "sale_modes": ["fixed"], "buy_now_price": 99, "photos": [S["photo"]]})
        assert r.status_code == 200
        l = next(x for x in v1.get(f"{API}/mine").json()["items"] if x["id"] == lid)
        assert l["needs_details"] is False and l["buy_now_price"] == 99
        r = v1.post(f"{API}/listings/{lid}/submit")
        assert r.status_code in (200, 402), r.text
        S["submitted"] = r.status_code == 200

    def test_partial_bulk_on_foreign_id(self, v1, tracked):
        # second item is foreign -> whole request 400; check whether first item leaked as a draft
        r = v1.post(f"{API}/listings/bulk", json={"items": [{"title": "TEST_ bulk leak check"}, {"title": "TEST_ bulk bad", "photos": [S["v2photo"]]}]})
        assert r.status_code == 400
        leaked = [x for x in v1.get(f"{API}/mine").json()["items"] if x["title"] == "TEST_ bulk leak check"]
        tracked["listings"].extend(x["id"] for x in leaked)
        assert not leaked, "bulk is not atomic: first item created despite 400"


class TestCatalogueImport:
    def test_reject_wrong_type(self, v1):
        assert v1.post(f"{API}/catalogue/import", files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 400
        assert v1.post(f"{API}/catalogue/import", files={"file": ("x.pdf", b"%PDF-broken", "application/pdf")}).status_code == 400

    def test_pdf_import_end_to_end(self, v1, v2, tracked):
        r = v1.post(f"{API}/catalogue/import", files={"file": ("TEST_catalogue.pdf", open("/tmp/test_catalogue.pdf", "rb").read(), "application/pdf")})
        assert r.status_code == 200, r.text
        d = r.json(); assert d["status"] == "reading"; iid = d["id"]; tracked["imports"].append(iid)
        assert v2.get(f"{API}/catalogue/import/{iid}").status_code == 404
        res = None
        for _ in range(45):
            time.sleep(4)
            res = v1.get(f"{API}/catalogue/import/{iid}").json()
            if res["status"] != "reading":
                break
        assert res["status"] == "done", res
        if res.get("catalogue_doc"):
            tracked["media"].append(res["catalogue_doc"]["id"])
        prods = res["products"]
        assert len(prods) >= 2, prods
        titles = " ".join(p["title"] for p in prods).lower()
        assert "pump" in titles and "skid" in titles
        for p in prods:
            assert set(["title", "description", "category", "unit", "specs", "page", "photos"]) <= set(p)
            assert p["photos"], f"no photo for {p['title']}"
        assert len(res["images"]) >= 2 and res["catalogue_doc"]["id"]
        pump = next(p for p in prods if "pump" in p["title"].lower())
        assert pump["page"] == 1
        S["import"] = res
        # photos & catalogue doc usable in bulk
        r = v1.post(f"{API}/listings/bulk", json={"items": [{"title": "TEST_ " + pump["title"][:100], "description": pump["description"],
                                                            "photos": pump["photos"], "documents": [res["catalogue_doc"]]}]})
        assert r.status_code == 200, r.text
        tracked["listings"].extend(r.json()["ids"])

    def test_png_import(self, v1, tracked):
        import fitz
        pix = fitz.open("/tmp/test_catalogue.pdf")[0].get_pixmap(dpi=110).tobytes("png")
        r = v1.post(f"{API}/catalogue/import", files={"file": ("TEST_page.png", pix, "image/png")})
        assert r.status_code == 200, r.text
        iid = r.json()["id"]; tracked["imports"].append(iid)
        for _ in range(40):
            time.sleep(4)
            res = v1.get(f"{API}/catalogue/import/{iid}").json()
            if res["status"] != "reading":
                break
        assert res["status"] == "done", res
        assert res["catalogue_doc"] is None and len(res["products"]) >= 1
        assert any(p["photos"] for p in res["products"])
