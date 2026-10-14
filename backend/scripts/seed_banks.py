"""v52cz rev6 — seed `masters_banks` for the escrow banking step.

Each entry is minimal and curated per country: name, country_code, a
SWIFT prefix (first 6 chars — bank code + country), and an optional
IBAN country prefix. The frontend uses this to drive a type-ahead and
auto-fill SWIFT when the user picks a specific bank; a free-text
fallback keeps the form usable in countries we haven't seeded yet.

Idempotent — safe to re-run; upserts on (country_code, name).

Admin UI can extend this later; this is the floor, not the ceiling.
"""
from __future__ import annotations
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import dotenv_values


def _load_env():
    cfg = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env"))
    return cfg["MONGO_URL"], cfg["DB_NAME"]


# ~10 countries × top banks each. The SWIFT prefix is "BANKCC" (6 chars).
BANKS = [
    # India
    ("IN", "State Bank of India",         "SBININ", ("INR",)),
    ("IN", "HDFC Bank",                   "HDFCIN", ("INR",)),
    ("IN", "ICICI Bank",                  "ICICIN", ("INR",)),
    ("IN", "Axis Bank",                   "AXISIN", ("INR",)),
    ("IN", "Punjab National Bank",        "PUNBIN", ("INR",)),
    ("IN", "Kotak Mahindra Bank",         "KKBKIN", ("INR",)),
    ("IN", "Bank of Baroda",              "BARBIN", ("INR",)),
    ("IN", "IndusInd Bank",               "INDBIN", ("INR",)),
    ("IN", "Yes Bank",                    "YESBIN", ("INR",)),
    ("IN", "Union Bank of India",         "UBININ", ("INR",)),
    # Kazakhstan
    ("KZ", "Halyk Bank",                  "HSBKKZ", ("KZT", "USD")),
    ("KZ", "Kaspi Bank",                  "CASPKZ", ("KZT",)),
    ("KZ", "Sberbank Kazakhstan",         "SABRKZ", ("KZT", "USD")),
    ("KZ", "ForteBank",                   "IRTYKZ", ("KZT",)),
    ("KZ", "Jusan Bank",                  "TSESKZ", ("KZT",)),
    # United Kingdom
    ("GB", "HSBC UK",                     "HBUKGB", ("GBP", "USD", "EUR")),
    ("GB", "Barclays Bank",               "BARCGB", ("GBP", "USD", "EUR")),
    ("GB", "NatWest",                     "NWBKGB", ("GBP",)),
    ("GB", "Lloyds Bank",                 "LOYDGB", ("GBP",)),
    ("GB", "Standard Chartered Bank",     "SCBLGB", ("GBP", "USD", "EUR")),
    ("GB", "Santander UK",                "ABBYGB", ("GBP",)),
    # UAE
    ("AE", "Emirates NBD",                "EBILAE", ("AED", "USD")),
    ("AE", "First Abu Dhabi Bank",        "FABMAE", ("AED", "USD")),
    ("AE", "Abu Dhabi Commercial Bank",   "ADCBAE", ("AED", "USD")),
    ("AE", "Mashreq Bank",                "BOMLAE", ("AED",)),
    ("AE", "Dubai Islamic Bank",          "DUIBAE", ("AED",)),
    # Saudi Arabia
    ("SA", "Saudi National Bank",         "NCBKSA", ("SAR", "USD")),
    ("SA", "Al Rajhi Bank",               "RJHISA", ("SAR",)),
    ("SA", "Riyad Bank",                  "RIBLSA", ("SAR",)),
    ("SA", "Banque Saudi Fransi",         "BSFRSA", ("SAR",)),
    # Singapore
    ("SG", "DBS Bank",                    "DBSSSG", ("SGD", "USD")),
    ("SG", "OCBC Bank",                   "OCBCSG", ("SGD", "USD")),
    ("SG", "United Overseas Bank",        "UOVBSG", ("SGD", "USD")),
    ("SG", "Standard Chartered Bank SG",  "SCBLSG", ("SGD", "USD")),
    # United States
    ("US", "JPMorgan Chase Bank",         "CHASUS", ("USD",)),
    ("US", "Bank of America",             "BOFAUS", ("USD",)),
    ("US", "Wells Fargo Bank",            "WFBIUS", ("USD",)),
    ("US", "Citibank",                    "CITIUS", ("USD",)),
    ("US", "HSBC USA",                    "MRMDUS", ("USD",)),
    # Germany
    ("DE", "Deutsche Bank",               "DEUTDE", ("EUR", "USD")),
    ("DE", "Commerzbank",                 "COBADE", ("EUR", "USD")),
    ("DE", "DZ Bank",                     "GENODE", ("EUR",)),
    ("DE", "KfW",                         "KFWIDE", ("EUR",)),
    # France
    ("FR", "BNP Paribas",                 "BNPAFR", ("EUR", "USD")),
    ("FR", "Credit Agricole",             "AGRIFR", ("EUR",)),
    ("FR", "Societe Generale",            "SOGEFR", ("EUR", "USD")),
    # Brazil
    ("BR", "Itau Unibanco",               "ITAUBR", ("BRL", "USD")),
    ("BR", "Banco do Brasil",             "BRASBR", ("BRL",)),
    ("BR", "Banco Bradesco",              "BBDEBR", ("BRL",)),
    # South Africa
    ("ZA", "Standard Bank of South Africa", "SBZAZA", ("ZAR", "USD")),
    ("ZA", "FirstRand Bank",              "FIRNZA", ("ZAR",)),
    ("ZA", "Nedbank",                     "NEDSZA", ("ZAR",)),
    ("ZA", "ABSA Bank",                   "ABSAZA", ("ZAR",)),
    # Russia
    ("RU", "Sberbank",                    "SABRRU", ("RUB", "USD")),
    ("RU", "VTB Bank",                    "VTBRRU", ("RUB",)),
    ("RU", "Alfa-Bank",                   "ALFARU", ("RUB",)),
    # Nigeria
    ("NG", "Zenith Bank",                 "ZEIBNG", ("NGN", "USD")),
    ("NG", "Guaranty Trust Bank",         "GTBING", ("NGN", "USD")),
    ("NG", "Access Bank",                 "ABNGNG", ("NGN",)),
    # Australia
    ("AU", "Commonwealth Bank of Australia", "CTBAAU", ("AUD", "USD")),
    ("AU", "Westpac Banking Corporation", "WPACAU", ("AUD",)),
    ("AU", "ANZ Banking Group",           "ANZBAU", ("AUD",)),
    ("AU", "National Australia Bank",     "NATAAU", ("AUD",)),
    # Japan
    ("JP", "MUFG Bank",                   "BOTKJP", ("JPY", "USD")),
    ("JP", "Mizuho Bank",                 "MHCBJP", ("JPY",)),
    ("JP", "Sumitomo Mitsui Banking Corp", "SMBCJP", ("JPY", "USD")),
    # China
    ("CN", "Industrial & Commercial Bank of China", "ICBKCN", ("CNY", "USD")),
    ("CN", "Bank of China",               "BKCHCN", ("CNY", "USD")),
    ("CN", "China Construction Bank",     "PCBCCN", ("CNY",)),
    ("CN", "Agricultural Bank of China",  "ABOCCN", ("CNY",)),
    # Ukraine
    ("UA", "PrivatBank",                  "PBANUA", ("UAH", "USD")),
    ("UA", "Oschadbank",                  "COSBUA", ("UAH",)),
    ("UA", "Raiffeisen Bank Ukraine",     "AVALUA", ("UAH",)),
]


ROWS = [
    {"country_code": cc, "name": name, "swift_prefix": swift,
     "currencies": list(currencies), "aliases": []}
    for (cc, name, swift, currencies) in BANKS
]


async def main():
    url, name_db = _load_env()
    client = AsyncIOMotorClient(url)
    db = client[name_db]
    n_up = n_in = 0
    for row in ROWS:
        existing = await db.masters_banks.find_one(
            {"country_code": row["country_code"], "name": row["name"]})
        await db.masters_banks.update_one(
            {"country_code": row["country_code"], "name": row["name"]},
            {"$set": row}, upsert=True)
        if existing: n_up += 1
        else: n_in += 1
    await db.masters_banks.create_index(
        [("country_code", 1), ("name", 1)], unique=True)
    await db.masters_banks.create_index([("name", "text"), ("swift_prefix", "text")])
    print(f"seeded masters_banks: inserted {n_in}, updated {n_up}, total {len(ROWS)}")


if __name__ == "__main__":
    asyncio.run(main())
