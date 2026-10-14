"""v52cz rev4 — seed country-specific business-identifier formats.

Writes `masters_country_formats`, one row per country we have coverage for.
Each row describes the display label, example and regex for:
  - reg_number   (incorporation / company number)
  - tax_id       (headline tax identifier, e.g. PAN, EIN, TIN)
  - vat          (indirect-tax identifier, e.g. GSTIN, VAT)

Idempotent — safe to re-run; it UPSERTs on country_code.

Why a dedicated collection: the dr5hn country master already carries postal
regex, phone code and emoji; stuffing more identifier regexes in there would
bloat the public countries payload. A separate lookup keeps `/masters/countries`
cheap and makes it trivial to add new identifier types later (DUNS, LEI).
"""
from __future__ import annotations
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import dotenv_values


def _load_env():
    cfg = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env"))
    return cfg["MONGO_URL"], cfg["DB_NAME"]


# Hand-curated. Keep regexes permissive enough to accept the common formats
# users actually type (with or without spaces/hyphens) but tight enough to
# reject obvious junk. Each entry is a dict so the frontend can render the
# label + example as a hint and use the regex for live validation.
FORMATS = [
    # ---- Asia-Pacific ----
    {"country_code": "IN",
     "reg_number": {"label": "CIN (Company Identification Number)",
                     "example": "L17110MH1973PLC019786",
                     "regex": r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$"},
     "tax_id":     {"label": "PAN", "example": "AAAPL1234C",
                     "regex": r"^[A-Z]{5}\d{4}[A-Z]$"},
     "vat":        {"label": "GSTIN", "example": "27AAAPL1234C1Z5",
                     "regex": r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]Z[A-Z\d]$"}},
    {"country_code": "KZ",
     "reg_number": {"label": "BIN", "example": "060140000385",
                     "regex": r"^\d{12}$"},
     "tax_id":     {"label": "IIN / BIN", "example": "060140000385",
                     "regex": r"^\d{12}$"},
     "vat":        {"label": "VAT series + no.", "example": "60001-1234567",
                     "regex": r"^\d{5}-?\d{7}$"}},
    {"country_code": "SG",
     "reg_number": {"label": "UEN", "example": "201612345A",
                     "regex": r"^(?:\d{9}[A-Z]|\d{4}\d{5}[A-Z]|[STR]\d{2}[A-Z]{2}\d{4}[A-Z])$"},
     "tax_id":     {"label": "GST registration no.", "example": "M90123456X",
                     "regex": r"^[A-Z]\d{8}[A-Z]$"},
     "vat":        None},
    {"country_code": "JP",
     "reg_number": {"label": "Corporate Number", "example": "7000012050002",
                     "regex": r"^\d{13}$"},
     "tax_id":     {"label": "Corporate Number", "example": "7000012050002",
                     "regex": r"^\d{13}$"},
     "vat":        None},
    {"country_code": "CN",
     "reg_number": {"label": "USCI (统一社会信用代码)", "example": "91110000710926094P",
                     "regex": r"^[0-9A-HJ-NPQRTUWXY]{18}$"},
     "tax_id":     {"label": "USCI", "example": "91110000710926094P",
                     "regex": r"^[0-9A-HJ-NPQRTUWXY]{18}$"},
     "vat":        None},
    {"country_code": "AU",
     "reg_number": {"label": "ACN", "example": "123 456 789",
                     "regex": r"^\d{3}\s?\d{3}\s?\d{3}$"},
     "tax_id":     {"label": "ABN", "example": "51 824 753 556",
                     "regex": r"^\d{2}\s?\d{3}\s?\d{3}\s?\d{3}$"},
     "vat":        None},
    # ---- Middle East ----
    {"country_code": "AE",
     "reg_number": {"label": "Trade licence no.", "example": "1012345",
                     "regex": r"^\d{5,10}$"},
     "tax_id":     {"label": "TRN (Tax Registration Number)",
                     "example": "100123456700003",
                     "regex": r"^\d{15}$"},
     "vat":        {"label": "VAT TRN", "example": "100123456700003",
                     "regex": r"^\d{15}$"}},
    {"country_code": "SA",
     "reg_number": {"label": "CR (Commercial Registration)",
                     "example": "1010123456", "regex": r"^\d{10}$"},
     "tax_id":     {"label": "TIN", "example": "300123456700003",
                     "regex": r"^\d{15}$"},
     "vat":        {"label": "VAT TIN", "example": "300123456700003",
                     "regex": r"^\d{15}$"}},
    # ---- Europe ----
    {"country_code": "GB",
     "reg_number": {"label": "Companies House number", "example": "12345678",
                     "regex": r"^(?:\d{8}|[A-Z]{2}\d{6}|OC\d{6}|SC\d{6}|NI\d{6})$"},
     "tax_id":     {"label": "UTR", "example": "1234567890",
                     "regex": r"^\d{10}$"},
     "vat":        {"label": "VAT number", "example": "GB123456789",
                     "regex": r"^(?:GB)?\d{9}(?:\d{3})?$"}},
    {"country_code": "DE",
     "reg_number": {"label": "Handelsregister-Nr.", "example": "HRB 123456",
                     "regex": r"^HR[ABPG]\s?\d{1,7}$"},
     "tax_id":     {"label": "Steuernummer", "example": "123/456/78901",
                     "regex": r"^\d{2,3}\/\d{3}\/\d{4,5}$"},
     "vat":        {"label": "USt-IdNr.", "example": "DE123456789",
                     "regex": r"^DE\d{9}$"}},
    {"country_code": "FR",
     "reg_number": {"label": "SIREN", "example": "552 120 222",
                     "regex": r"^\d{3}\s?\d{3}\s?\d{3}$"},
     "tax_id":     {"label": "SIRET", "example": "552 120 222 00013",
                     "regex": r"^\d{3}\s?\d{3}\s?\d{3}\s?\d{5}$"},
     "vat":        {"label": "TVA intracom.", "example": "FR40303265045",
                     "regex": r"^FR[0-9A-Z]{2}\d{9}$"}},
    # ---- Americas ----
    {"country_code": "US",
     "reg_number": {"label": "State filing / entity no.",
                     "example": "varies by state (6–12 chars)",
                     "regex": r"^[A-Z0-9\-]{4,20}$"},
     "tax_id":     {"label": "EIN", "example": "12-3456789",
                     "regex": r"^\d{2}-?\d{7}$"},
     "vat":        None},
    {"country_code": "BR",
     "reg_number": {"label": "CNPJ", "example": "12.345.678/0001-90",
                     "regex": r"^\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}$"},
     "tax_id":     {"label": "CNPJ", "example": "12.345.678/0001-90",
                     "regex": r"^\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}$"},
     "vat":        None},
    # ---- Africa ----
    {"country_code": "ZA",
     "reg_number": {"label": "Company Registration no.",
                     "example": "2015/123456/07",
                     "regex": r"^\d{4}\/\d{6,7}\/\d{2}$"},
     "tax_id":     {"label": "Income Tax no.", "example": "9123456789",
                     "regex": r"^\d{10}$"},
     "vat":        {"label": "VAT no.", "example": "4123456789",
                     "regex": r"^4\d{9}$"}},
    {"country_code": "NG",
     "reg_number": {"label": "RC number", "example": "RC 1234567",
                     "regex": r"^(?:RC\s?)?\d{4,8}$"},
     "tax_id":     {"label": "TIN", "example": "12345678-0001",
                     "regex": r"^\d{8,10}(?:-\d{4})?$"},
     "vat":        None},
    # ---- CIS ----
    {"country_code": "RU",
     "reg_number": {"label": "OGRN", "example": "1027700132195",
                     "regex": r"^\d{13}$"},
     "tax_id":     {"label": "INN (юр.лицо)", "example": "7707083893",
                     "regex": r"^\d{10}(?:\d{2})?$"},
     "vat":        {"label": "VAT no.", "example": "7707083893",
                     "regex": r"^\d{10}$"}},
    {"country_code": "UA",
     "reg_number": {"label": "EDRPOU", "example": "12345678",
                     "regex": r"^\d{8}$"},
     "tax_id":     {"label": "EDRPOU / INN",
                     "example": "12345678", "regex": r"^\d{8,10}$"},
     "vat":        None},
]


async def main():
    url, name = _load_env()
    client = AsyncIOMotorClient(url)
    db = client[name]
    n_up = n_in = 0
    for row in FORMATS:
        row = {k: v for k, v in row.items() if v is not None}
        cc = row["country_code"]
        existing = await db.masters_country_formats.find_one({"country_code": cc})
        await db.masters_country_formats.update_one(
            {"country_code": cc}, {"$set": row}, upsert=True)
        if existing: n_up += 1
        else: n_in += 1
    await db.masters_country_formats.create_index("country_code", unique=True)
    print(f"seeded masters_country_formats: inserted {n_in}, updated {n_up}, total {len(FORMATS)}")

if __name__ == "__main__":
    asyncio.run(main())
