"""Seed per-country postal (ZIP) code formats + regex into masters_countries.

The dr5hn country master ships with `postal_code_format` / `postal_code_regex`
fields but they were never populated, so ZIP validation in the registration
office editor never fired. This backfills them from a curated table derived
from the Universal Postal Union / Google libaddressinput patterns.

Idempotent — safe to re-run; only touches the two postal fields on each
country row (matched by `code`). Countries with no national postal system
(e.g. AE, HK, many island states) are intentionally omitted so ZIP stays an
optional free-text field for them.

Run: python3 -m scripts.seed_postal_formats
Also invoked from the FastAPI startup bootstrap.
"""
from __future__ import annotations
import os
from pymongo import MongoClient
from dotenv import dotenv_values

# code -> (human-readable format, validation regex)
# Regexes are anchored and tolerate an optional space/hyphen where the format
# commonly includes one, so vendors are never blocked for reasonable input.
POSTAL = {
    # ---- Asia-Pacific ----
    "MY": ("#####", r"^\d{5}$"),
    "SG": ("######", r"^\d{6}$"),
    "ID": ("#####", r"^\d{5}$"),
    "TH": ("#####", r"^\d{5}$"),
    "VN": ("######", r"^\d{6}$"),
    "PH": ("####", r"^\d{4}$"),
    "IN": ("######", r"^\d{6}$"),
    "PK": ("#####", r"^\d{5}$"),
    "BD": ("####", r"^\d{4}$"),
    "LK": ("#####", r"^\d{5}$"),
    "NP": ("#####", r"^\d{5}$"),
    "CN": ("######", r"^\d{6}$"),
    "JP": ("###-####", r"^\d{3}-?\d{4}$"),
    "KR": ("#####", r"^\d{5}$"),
    "TW": ("#####", r"^\d{3}(?:\d{2})?$"),
    "AU": ("####", r"^\d{4}$"),
    "NZ": ("####", r"^\d{4}$"),
    "KZ": ("######", r"^\d{6}$"),
    "UZ": ("######", r"^\d{6}$"),
    # ---- Middle East ----
    "SA": ("#####", r"^\d{5}$"),
    "QA": ("", None),              # no postal system
    "KW": ("#####", r"^\d{5}$"),
    "OM": ("###", r"^\d{3}$"),
    "BH": ("###|####", r"^\d{3,4}$"),
    "JO": ("#####", r"^\d{5}$"),
    "LB": ("#### ####", r"^\d{4}\s?\d{4}$"),
    "IL": ("#######", r"^\d{5}(?:\d{2})?$"),
    "IR": ("##########", r"^\d{10}$"),
    "TR": ("#####", r"^\d{5}$"),
    # ---- Europe ----
    "GB": ("AA## #AA", r"^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$"),
    "IE": ("A## AAAA", r"^[A-Z]\d[\dW] ?[A-Z\d]{4}$"),  # Eircode
    "DE": ("#####", r"^\d{5}$"),
    "FR": ("#####", r"^\d{5}$"),
    "ES": ("#####", r"^\d{5}$"),
    "IT": ("#####", r"^\d{5}$"),
    "PT": ("####-###", r"^\d{4}-?\d{3}$"),
    "NL": ("#### AA", r"^\d{4} ?[A-Z]{2}$"),
    "BE": ("####", r"^\d{4}$"),
    "LU": ("####", r"^\d{4}$"),
    "CH": ("####", r"^\d{4}$"),
    "AT": ("####", r"^\d{4}$"),
    "DK": ("####", r"^\d{4}$"),
    "NO": ("####", r"^\d{4}$"),
    "SE": ("### ##", r"^\d{3} ?\d{2}$"),
    "FI": ("#####", r"^\d{5}$"),
    "PL": ("##-###", r"^\d{2}-?\d{3}$"),
    "CZ": ("### ##", r"^\d{3} ?\d{2}$"),
    "SK": ("### ##", r"^\d{3} ?\d{2}$"),
    "HU": ("####", r"^\d{4}$"),
    "RO": ("######", r"^\d{6}$"),
    "BG": ("####", r"^\d{4}$"),
    "GR": ("### ##", r"^\d{3} ?\d{2}$"),
    "HR": ("#####", r"^\d{5}$"),
    "SI": ("####", r"^\d{4}$"),
    "RS": ("#####", r"^\d{5,6}$"),
    "UA": ("#####", r"^\d{5}$"),
    "RU": ("######", r"^\d{6}$"),
    "BY": ("######", r"^\d{6}$"),
    "LT": ("LT-#####", r"^(?:LT-)?\d{5}$"),
    "LV": ("LV-####", r"^(?:LV-)?\d{4}$"),
    "EE": ("#####", r"^\d{5}$"),
    # ---- Americas ----
    "US": ("#####-####", r"^\d{5}(?:-\d{4})?$"),
    "CA": ("A#A #A#", r"^[ABCEGHJ-NPRSTVXY]\d[A-Z] ?\d[A-Z]\d$"),
    "MX": ("#####", r"^\d{5}$"),
    "BR": ("#####-###", r"^\d{5}-?\d{3}$"),
    "AR": ("A####AAA", r"^[A-Z]?\d{4}[A-Z]{0,3}$"),
    "CL": ("#######", r"^\d{7}$"),
    "CO": ("######", r"^\d{6}$"),
    "PE": ("#####", r"^\d{5}$"),
    "UY": ("#####", r"^\d{5}$"),
    "EC": ("######", r"^\d{6}$"),
    "VE": ("####", r"^\d{4}(?:-[A-Z])?$"),
    # ---- Africa ----
    "ZA": ("####", r"^\d{4}$"),
    "NG": ("######", r"^\d{6}$"),
    "KE": ("#####", r"^\d{5}$"),
    "GH": ("", None),
    "EG": ("#####", r"^\d{5}$"),
    "MA": ("#####", r"^\d{5}$"),
    "DZ": ("#####", r"^\d{5}$"),
    "TN": ("####", r"^\d{4}$"),
    "ET": ("####", r"^\d{4}$"),
    "TZ": ("#####", r"^\d{5}$"),
    "UG": ("", None),
    "ZM": ("#####", r"^\d{5}$"),
    "ZW": ("", None),
    "SN": ("#####", r"^\d{5}$"),
}


def _db():
    env = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env"))
    return MongoClient(env["MONGO_URL"])[env["DB_NAME"]]


def seed_postal(db) -> int:
    """Backfill postal_code_format / postal_code_regex on masters_countries."""
    n = 0
    for code, (fmt, regex) in POSTAL.items():
        r = db.masters_countries.update_one(
            {"code": code},
            {"$set": {"postal_code_format": fmt or None,
                      "postal_code_regex": regex}},
        )
        if r.matched_count:
            n += 1
    return n


if __name__ == "__main__":
    db = _db()
    print(f"seeded postal formats on {seed_postal(db)} countries")
