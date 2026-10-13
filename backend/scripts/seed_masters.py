"""Seed masters for v52cm — UNSPSC + geography + country licenses.

Idempotent. Safe to run multiple times. Call via:
    python3 -m scripts.seed_masters

Also hooked into FastAPI startup when any master collection is empty so a
fresh production deploy auto-seeds.

Data sources (local snapshots pre-staged under /app/backend/data/):
- UNSPSC v26.0801 — codebysaadbouh/unspsc-fr GitHub release (SQLite, 88 MB)
- Countries + states + cities — dr5hn/countries-states-cities-database (JSON, 50 MB)
- Country licenses — hand-curated seed for 6 geographies admin can extend
"""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING, TEXT

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")


def _db():
    from dotenv import dotenv_values
    env = dotenv_values(os.path.join(BACKEND_DIR, ".env"))
    return MongoClient(env["MONGO_URL"])[env["DB_NAME"]]


def seed_unspsc(db, src_sqlite: str, *, dry_run: bool = False) -> int:
    """Import all 150k UNSPSC commodity codes into masters_unspsc.

    The pmc 'categories' master is left alone — it stays the human-curated
    procurement category list. UNSPSC is the lookup/search universe.

    v52cm — codebysaadbouh/unspsc-fr ships one table per level
    (segments / families / classes / commodities) with translations in a
    separate `translations(code, lang, label)` table. We fold them all into
    a single flat Mongo collection so a single text search covers every
    level the user might pick.
    """
    coll = db.masters_unspsc
    if coll.count_documents({}) > 100_000:
        return coll.count_documents({})
    src = sqlite3.connect(src_sqlite)
    # Build a (code -> {en, fr}) lookup to avoid N joins.
    labels: dict[str, dict] = {}
    for code, _lvl, lang, title in src.execute(
        "SELECT code, level, lang, title FROM translations"
    ):
        labels.setdefault(str(code), {})[lang] = title
    docs = []
    for level, table, code_col in (
        ("segment", "segments", "segment_code"),
        ("family", "families", "family_code"),
        ("class", "classes", "class_code"),
        ("commodity", "commodities", "commodity_code"),
    ):
        for row in src.execute(f"SELECT {code_col}, title_en FROM {table}"):
            raw_code = str(row[0])
            code = raw_code.rjust(8, "0")
            lbl = labels.get(raw_code, {})
            docs.append({
                "code": code,
                "segment": code[:2],
                "family": code[:4],
                "class_code": code[:6],
                "commodity": code,
                "level": level,
                "title_en": lbl.get("en") or row[1] or "",
                "title_fr": lbl.get("fr", ""),
                "source": "unspsc_v26.0801",
                "is_active": True,
            })
    if not docs:
        return 0
    if dry_run:
        return len(docs)
    coll.drop()
    for i in range(0, len(docs), 10_000):
        coll.insert_many(docs[i:i + 10_000], ordered=False)
    coll.create_index([("code", ASCENDING), ("level", ASCENDING)], unique=True)
    coll.create_index([("code", ASCENDING)])
    coll.create_index([("segment", ASCENDING)])
    coll.create_index([("level", ASCENDING)])
    coll.create_index([("title_en", TEXT), ("title_fr", TEXT)])
    return coll.count_documents({})


def seed_geography(db, src_json: str) -> dict:
    """Import 250 countries, 5k states, 150k cities into masters_geography_*."""
    with open(src_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    now = datetime.now(timezone.utc).isoformat()
    countries, states, cities = [], [], []
    for c in data:
        iso2 = (c.get("iso2") or "").upper()
        if not iso2:
            continue
        countries.append({
            "code": iso2,
            "iso3": c.get("iso3"),
            "name": c.get("name"),
            "nationality": c.get("nationality"),
            "phone_code": c.get("phonecode"),
            "capital": c.get("capital"),
            "region": c.get("region"),
            "subregion": c.get("subregion"),
            "currency": c.get("currency"),
            "currency_symbol": c.get("currency_symbol"),
            "postal_code_format": c.get("postal_code_format"),
            "postal_code_regex": c.get("postal_code_regex"),
            "emoji": c.get("emoji"),
            "is_active": True,
            "updated_at": now,
        })
        for s in c.get("states", []):
            states.append({
                "country_code": iso2,
                "state_code": s.get("state_code") or s.get("iso2"),
                "name": s.get("name"),
                "is_active": True,
            })
            for ct in s.get("cities", []):
                cities.append({
                    "country_code": iso2,
                    "state_code": s.get("state_code") or s.get("iso2"),
                    "state_name": s.get("name"),
                    "name": ct.get("name"),
                    "latitude": ct.get("latitude"),
                    "longitude": ct.get("longitude"),
                    "is_active": True,
                })
    if countries:
        db.masters_countries.drop()
        db.masters_countries.insert_many(countries, ordered=False)
        db.masters_countries.create_index("code", unique=True)
    if states:
        db.masters_states.drop()
        db.masters_states.insert_many(states, ordered=False)
        db.masters_states.create_index([("country_code", ASCENDING), ("state_code", ASCENDING)])
        db.masters_states.create_index([("country_code", ASCENDING), ("name", ASCENDING)])
    if cities:
        db.masters_cities.drop()
        # insert in chunks of 10k to stay within mongo limits
        for i in range(0, len(cities), 10_000):
            db.masters_cities.insert_many(cities[i:i + 10_000], ordered=False)
        db.masters_cities.create_index([("country_code", ASCENDING), ("state_code", ASCENDING), ("name", ASCENDING)])
        db.masters_cities.create_index([("country_code", ASCENDING), ("name", ASCENDING)])
    return {
        "countries": db.masters_countries.count_documents({}),
        "states": db.masters_states.count_documents({}),
        "cities": db.masters_cities.count_documents({}),
    }


# Hand-curated seed. Admins can edit via /api/v1/masters/country-licenses/*.
LICENSE_SEED = {
    "IN": [
        {"code": "gst",       "name": "GST registration certificate",        "mandatory": True},
        {"code": "pan",       "name": "Permanent Account Number (PAN)",      "mandatory": True},
        {"code": "msme",      "name": "MSME / Udyam registration",           "mandatory": False},
        {"code": "esi",       "name": "ESI registration",                    "mandatory": False},
        {"code": "pf",        "name": "EPFO registration",                   "mandatory": False},
        {"code": "shop_est",  "name": "Shop & establishment certificate",    "mandatory": False},
    ],
    "KZ": [
        {"code": "bin",             "name": "Business Identification Number (BIN)",       "mandatory": True},
        {"code": "state_reg",       "name": "State registration certificate",             "mandatory": True},
        {"code": "construction_lic","name": "Construction licence (if applicable)",       "mandatory": False},
    ],
    "AE": [
        {"code": "trade_lic",   "name": "Trade licence (DED / Free zone)",   "mandatory": True},
        {"code": "vat",         "name": "VAT (TRN) registration",            "mandatory": True},
        {"code": "esr",         "name": "Economic Substance Regulations filing", "mandatory": False},
    ],
    "US": [
        {"code": "ein",         "name": "Employer Identification Number (EIN)", "mandatory": True},
        {"code": "state_reg",   "name": "State business registration",          "mandatory": True},
        {"code": "sam_cage",    "name": "SAM.gov / CAGE code (federal procurement)", "mandatory": False},
    ],
    "GB": [
        {"code": "ch_reg",      "name": "Companies House registration",      "mandatory": True},
        {"code": "vat",         "name": "VAT registration",                  "mandatory": False},
        {"code": "utr",         "name": "HMRC Unique Taxpayer Reference",    "mandatory": True},
    ],
    "SG": [
        {"code": "acra_uen",    "name": "ACRA UEN (business profile)",       "mandatory": True},
        {"code": "gst",         "name": "GST registration",                  "mandatory": False},
        {"code": "bca_lic",     "name": "BCA contractor licence",            "mandatory": False},
    ],
}


def seed_country_licenses(db) -> int:
    """Pre-seed license requirements for the 6 geographies the user listed.

    Idempotent — only inserts country docs that don't exist yet. Admin edits
    via the API are preserved on re-run.
    """
    coll = db.masters_country_licenses
    count = 0
    for cc, lic in LICENSE_SEED.items():
        if coll.find_one({"country_code": cc}):
            continue
        coll.insert_one({
            "country_code": cc,
            "licenses": lic,
            "seeded": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        count += 1
    coll.create_index("country_code", unique=True)
    return count


def main():
    db = _db()
    sqlite_src = os.path.join(DATA_DIR, "unspsc_v26.sqlite")
    geo_src = os.path.join(DATA_DIR, "csc.json")
    if os.path.exists(sqlite_src):
        n = seed_unspsc(db, sqlite_src)
        print(f"[masters] UNSPSC rows: {n}")
    else:
        print(f"[masters] WARN: {sqlite_src} missing — UNSPSC skip")
    if os.path.exists(geo_src):
        stats = seed_geography(db, geo_src)
        print(f"[masters] geography: {stats}")
    else:
        print(f"[masters] WARN: {geo_src} missing — geography skip")
    lic = seed_country_licenses(db)
    print(f"[masters] country licenses seeded (new countries): {lic}")


if __name__ == "__main__":
    main()
