# v62: Ask PMC language replies, translated help videos manifests, translated training manuals
import os
import re
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
LANGS = ["ru", "kk", "zh-Hans", "zh-Hant", "es", "fr", "de", "hi", "ms", "id", "ko", "ja", "ar"]
SIDS = []


def _chat(lang=None, msg="How do I register as a supplier?"):
    sid = "TEST" + uuid.uuid4().hex[:20]
    SIDS.append(sid)
    body = {"session_id": sid, "message": msg, "mode": "public"}
    if lang is not None:
        body["lang"] = lang
    return requests.post(f"{BASE_URL}/api/v1/assistant/chat", json=body, timeout=90)


# Ask PMC assistant language
class TestAssistantLang:
    def test_japanese_reply(self):
        r = _chat("ja")
        assert r.status_code == 200, r.text
        rep = r.json()["reply"]
        print("JA:", rep[:200])
        assert re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", rep), "reply has no Japanese chars"

    def test_arabic_reply(self):
        r = _chat("ar")
        assert r.status_code == 200, r.text
        rep = r.json()["reply"]
        print("AR:", rep[:200])
        assert re.search(r"[\u0600-\u06ff]", rep)

    def test_no_lang_english(self):
        r = _chat(None)
        assert r.status_code == 200, r.text
        d = r.json()
        rep = d["reply"]
        print("EN:", rep[:200])
        assert not re.search(r"[\u0600-\u06ff\u3040-\u30ff\u4e00-\u9fff]", rep)
        assert re.search(r"\b(the|register|supplier)\b", rep, re.I)
        assert isinstance(d["videos"], list)

    def test_lang_too_long_rejected(self):
        r = _chat("x" * 11)
        assert r.status_code == 422


# Help video manifests and files
class TestHelpVideos:
    def test_en_manifest(self):
        r = requests.get(f"{BASE_URL}/help-videos/manifest.json", timeout=30)
        assert r.status_code == 200
        m = r.json()
        assert m["languages"]["file"] == "/help-videos/languages.mp4"

    def test_fr_manifest_and_video(self):
        r = requests.get(f"{BASE_URL}/help-videos/fr/manifest.json", timeout=30)
        assert r.status_code == 200
        m = r.json()
        assert m["languages"]["file"] == "/help-videos/fr/languages.mp4"
        assert m["languages"]["lang"] == "fr"
        v = requests.head(f"{BASE_URL}/help-videos/fr/languages.mp4", timeout=30)
        assert v.status_code == 200 and "video" in v.headers.get("content-type", "")

    def test_all_lang_manifest_files_exist(self):
        bad = []
        for lg in LANGS:
            r = requests.get(f"{BASE_URL}/help-videos/{lg}/manifest.json", timeout=30)
            ct = r.headers.get("content-type", "")
            if r.status_code != 200 or "json" not in ct:
                print(lg, "no manifest yet", r.status_code, ct)
                continue
            for slug, v in list(r.json().items())[:2]:
                h = requests.head(f"{BASE_URL}{v['file']}", timeout=30)
                if h.status_code != 200 or "video" not in h.headers.get("content-type", ""):
                    bad.append((lg, slug, h.status_code))
        assert not bad, bad


# Training manuals
class TestManuals:
    @pytest.mark.parametrize("lg", LANGS)
    def test_translated_pdf(self, lg):
        r = requests.get(f"{BASE_URL}/downloads/manual/PMC_Master_Training_Manual_{lg}.pdf", timeout=60, stream=True)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")
        assert next(r.iter_content(5)) == b"%PDF-"

    def test_en_pdf(self):
        r = requests.head(f"{BASE_URL}/downloads/manual/PMC_v4_Master_Training_Manual.pdf", timeout=30)
        assert r.status_code == 200 and "application/pdf" in r.headers.get("content-type", "")

    @pytest.mark.parametrize("lg", LANGS)
    def test_sections_map(self, lg):
        r = requests.get(f"{BASE_URL}/downloads/manual/sections_{lg}.json", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["file"] == f"/downloads/manual/PMC_Master_Training_Manual_{lg}.pdf"
        assert len(d["pages"]) >= 50, f"only {len(d['pages'])} screen pages mapped"


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    if not SIDS:
        return
    try:
        import asyncio
        import sys
        sys.path.insert(0, "/app/backend")
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        c = AsyncIOMotorClient(os.environ["MONGO_URL"])
        asyncio.get_event_loop().run_until_complete(
            c[os.environ["DB_NAME"]].assistant_sessions.delete_many({"session_id": {"$in": SIDS}}))
    except Exception as e:
        print("cleanup failed", e)
