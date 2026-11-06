# i18n auto-translate API tests (translate map, unsupported lang, dict cache)
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
LANGS = ["ru", "kk", "zh-Hans", "zh-Hant", "es", "fr", "de", "hi", "ms", "id", "ko", "ja", "ar"]


class TestTranslate:
    def test_translate_cached_phrase_fr(self):
        r = requests.post(f"{BASE_URL}/api/v1/i18n/translate", json={"lang": "fr", "texts": ["Register as supplier"]}, timeout=60)
        assert r.status_code == 200
        m = r.json()["map"]
        assert isinstance(m, dict)
        assert "Register as supplier" in m
        assert m["Register as supplier"] and m["Register as supplier"] != "Register as supplier"

    def test_unsupported_lang_422(self):
        r = requests.post(f"{BASE_URL}/api/v1/i18n/translate", json={"lang": "xx", "texts": ["Hello"]}, timeout=30)
        assert r.status_code == 422

    def test_en_lang_422(self):
        r = requests.post(f"{BASE_URL}/api/v1/i18n/translate", json={"lang": "en", "texts": ["Hello"]}, timeout=30)
        assert r.status_code == 422

    def test_too_many_texts_422(self):
        r = requests.post(f"{BASE_URL}/api/v1/i18n/translate", json={"lang": "fr", "texts": ["a b"] * 121}, timeout=30)
        assert r.status_code == 422

    def test_empty_texts(self):
        r = requests.post(f"{BASE_URL}/api/v1/i18n/translate", json={"lang": "fr", "texts": []}, timeout=30)
        assert r.status_code == 200
        assert r.json()["map"] == {}

    def test_live_llm_uncached_then_cached(self):
        phrase = f"TEST_ Please review the bid summary {uuid.uuid4().hex[:6]}"
        t0 = time.time()
        r = requests.post(f"{BASE_URL}/api/v1/i18n/translate", json={"lang": "de", "texts": [phrase]}, timeout=90)
        assert r.status_code == 200
        m = r.json()["map"]
        print("live latency", time.time() - t0, m)
        assert phrase in m, "LLM live translation returned nothing"
        d = requests.get(f"{BASE_URL}/api/v1/i18n/dict/de", timeout=60).json()["map"]
        assert d.get(phrase) == m[phrase]


class TestDict:
    def test_dict_fr(self):
        r = requests.get(f"{BASE_URL}/api/v1/i18n/dict/fr", timeout=60)
        assert r.status_code == 200
        m = r.json()["map"]
        assert len(m) > 1000
        assert "Register as supplier" in m
        print("dict size bytes", len(r.content))

    def test_dict_unsupported(self):
        r = requests.get(f"{BASE_URL}/api/v1/i18n/dict/xx", timeout=30)
        assert r.status_code == 422

    @pytest.mark.parametrize("lang", LANGS)
    def test_dict_all_langs_seeded(self, lang):
        r = requests.get(f"{BASE_URL}/api/v1/i18n/dict/{lang}", timeout=60)
        assert r.status_code == 200
        assert len(r.json()["map"]) > 2000, f"{lang} has {len(r.json()['map'])}"
