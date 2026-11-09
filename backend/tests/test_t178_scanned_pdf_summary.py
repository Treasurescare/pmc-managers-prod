# Iteration 178: Supplier AI summary — scanned (image-only) PDF / JPG / PNG via vision, text PDF, notice ref, corrupted PDF
import io
import os
import random
import asyncio
import sys

import pytest
import requests
from PIL import Image, ImageDraw, ImageFont

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
CREATED = []  # ai_report ids to clean up


def _tender_image(tag):
    img = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except Exception:
        f = ImageFont.load_default()
    lines = [f"TENDER NOTICE No. TEST-SCAN-{tag}", "Buyer: Municipal Water Board, Chennai",
             "Scope: Supply and installation of 40 km HDPE water pipeline",
             "and 3 pumping stations with SCADA.",
             "Eligibility: Annual turnover of INR 25 crore in last 3 years.",
             "Experience: 2 similar pipeline works of 20 km each.",
             "EMD: INR 12,50,000 by bank guarantee.",
             "Tender fee: INR 25,000 non-refundable.",
             "Key dates: Bid submission 15 March 2026, 3 PM.",
             "Pre-bid meeting 01 March 2026. Bid opening 16 March 2026.",
             "Documents required: GST certificate, PAN, audited balance",
             "sheets, experience certificates, ISO 9001 certificate.",
             "Evaluation: L1 lowest price among technically qualified."]
    y = 80
    for ln in lines:
        d.text((80, y), ln, fill="black", font=f)
        y += 60
    return img


def _bytes(img, fmt):
    b = io.BytesIO()
    img.save(b, format=fmt)
    return b.getvalue()


@pytest.fixture(scope="module")
def vs():
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": "testvendor@pmcmanagers.com", "password": "Vendor@12345"})
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.status_code}")
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    yield s
    # cleanup ai_reports created by these tests
    if CREATED:
        sys.path.insert(0, "/app/backend")
        from bson import ObjectId
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        async def _c():
            c = AsyncIOMotorClient(os.environ["MONGO_URL"])
            r = await c[os.environ["DB_NAME"]].ai_reports.delete_many({"_id": {"$in": [ObjectId(i) for i in CREATED]}})
            print("cleaned ai_reports", r.deleted_count)
        asyncio.run(_c())


def _check_summary(r):
    assert r.status_code == 200, r.text[:400]
    d = r.json()
    if d.get("id"):
        CREATED.append(d["id"])
    res = d.get("result") or {}
    print("RESULT:", str(res)[:600])
    assert res.get("summary")
    assert isinstance(res.get("scope"), list) and res["scope"]
    assert res.get("emd") and ("12" in str(res["emd"]))
    assert isinstance(res.get("key_dates"), list) and res["key_dates"]
    assert isinstance(res.get("documents_required"), list) and res["documents_required"]
    assert isinstance(res.get("eligibility"), list) and res["eligibility"]
    return d


def test_scanned_pdf_image_only(vs):
    tag = random.randint(100000, 999999)
    pdf = _bytes(_tender_image(tag), "PDF")
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_scan.pdf", pdf, "application/pdf")}, timeout=180)
    _check_summary(r)


def test_scanned_jpg(vs):
    tag = random.randint(100000, 999999)
    jpg = _bytes(_tender_image(tag), "JPEG")
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_photo.jpg", jpg, "image/jpeg")}, timeout=180)
    _check_summary(r)


def test_scanned_png(vs):
    tag = random.randint(100000, 999999)
    png = _bytes(_tender_image(tag), "PNG")
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_photo.PNG", png, "image/png")}, timeout=180)
    _check_summary(r)


def test_text_pdf_still_works(vs):
    from reportlab.pdfgen import canvas
    tag = random.randint(100000, 999999)
    b = io.BytesIO()
    c = canvas.Canvas(b)
    y = 800
    for ln in [f"TENDER NOTICE TEST-TXT-{tag}", "Buyer: Municipal Water Board", "Scope: Supply of 40 km HDPE pipeline.",
               "Eligibility: turnover INR 25 crore.", "EMD: INR 12,50,000.", "Bid submission: 15 March 2026.",
               "Documents required: GST certificate, PAN, ISO 9001."]:
        c.drawString(50, y, ln); y -= 20
    c.save()
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_text.pdf", b.getvalue(), "application/pdf")}, timeout=180)
    d = _check_summary(r)
    assert "[scanned document" not in str(d.get("source_text", ""))


def test_notice_ref_summary(vs):
    r = vs.post(f"{API}/supplier-ai/summary", data={"notice_ref": "DEMO-TND-001", "lang": "English"}, timeout=180)
    assert r.status_code == 200, r.text[:300]
    assert (r.json().get("result") or {}).get("summary")


def test_corrupted_pdf_friendly_400(vs):
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_bad.pdf", b"not a pdf at all, garbage bytes" * 10, "application/pdf")}, timeout=60)
    assert r.status_code == 400, r.text
    det = str(r.json().get("detail"))
    print("DETAIL:", det)
    assert "Traceback" not in det and "Error" not in det


def test_truncated_pdf(vs):
    pdf = _bytes(_tender_image(1), "PDF")
    r = vs.post(f"{API}/supplier-ai/summary", data={"lang": "English"},
                files={"file": ("TEST_trunc.pdf", pdf[:300], "application/pdf")}, timeout=180)
    print("TRUNC:", r.status_code, r.text[:300])
    assert r.status_code in (400, 422), r.text[:300]
    det = str(r.json().get("detail"))
    assert "Traceback" not in det and "Exception" not in det


def test_unauth(vs):
    r = requests.post(f"{API}/supplier-ai/summary", data={"notice_ref": "DEMO-TND-001"})
    assert r.status_code == 401
