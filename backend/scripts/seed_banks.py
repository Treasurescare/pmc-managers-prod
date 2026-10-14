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
    # v52cz rev7 — more neobanks + expanded India / UK / US / EU rosters.
    # Still not literally "every bank in the world"; admin can extend via
    # the masters_banks collection. UI falls back to free text when the
    # country isn't seeded.

    # India — additional PSU, private, foreign, neo
    ("IN", "Canara Bank",                 "CNRBIN", ("INR",)),
    ("IN", "Bank of India",               "BKIDIN", ("INR",)),
    ("IN", "Central Bank of India",       "CBININ", ("INR",)),
    ("IN", "Indian Bank",                 "IDIBIN", ("INR",)),
    ("IN", "Indian Overseas Bank",        "IOBAIN", ("INR",)),
    ("IN", "UCO Bank",                    "UCBAIN", ("INR",)),
    ("IN", "IDBI Bank",                   "IBKLIN", ("INR",)),
    ("IN", "IDFC FIRST Bank",             "IDFBIN", ("INR",)),
    ("IN", "Federal Bank",                "FDRLIN", ("INR",)),
    ("IN", "South Indian Bank",           "SIBLIN", ("INR",)),
    ("IN", "Karnataka Bank",              "KARBIN", ("INR",)),
    ("IN", "Karur Vysya Bank",            "KVBLIN", ("INR",)),
    ("IN", "RBL Bank",                    "RATNIN", ("INR",)),
    ("IN", "DBS Bank India",              "DBSSIN", ("INR", "USD")),
    ("IN", "Standard Chartered India",    "SCBLIN", ("INR", "USD")),
    ("IN", "Citibank India",              "CITIIN", ("INR", "USD")),
    ("IN", "Deutsche Bank India",         "DEUTIN", ("INR", "USD", "EUR")),
    ("IN", "AU Small Finance Bank",       "AUBLIN", ("INR",)),
    ("IN", "Equitas Small Finance Bank",  "ESFBIN", ("INR",)),
    ("IN", "Jio Payments Bank",           "JIOPIN", ("INR",)),
    ("IN", "Paytm Payments Bank",         "PYTMIN", ("INR",)),
    ("IN", "Airtel Payments Bank",        "ARTBIN", ("INR",)),
    ("IN", "FINO Payments Bank",          "FINOIN", ("INR",)),
    ("IN", "NSDL Payments Bank",          "NSPBIN", ("INR",)),
    # UK — more incl. neobanks
    ("GB", "Monzo Bank",                  "MONZGB", ("GBP",)),
    ("GB", "Starling Bank",               "SRLGGB", ("GBP",)),
    ("GB", "Revolut",                     "REVOGB", ("GBP", "EUR", "USD")),
    ("GB", "Wise",                        "TRWIGB", ("GBP", "EUR", "USD")),
    ("GB", "Metro Bank",                  "MYMBGB", ("GBP",)),
    ("GB", "Virgin Money",                "VMUKGB", ("GBP",)),
    ("GB", "Clydesdale Bank",             "CDLSGB", ("GBP",)),
    ("GB", "The Co-operative Bank",       "COOPGB", ("GBP",)),
    ("GB", "TSB Bank",                    "TSBSGB", ("GBP",)),
    ("GB", "Nationwide Building Society", "NAIAGB", ("GBP",)),
    ("GB", "Halifax",                     "HLFXGB", ("GBP",)),
    # US — more incl. neobanks
    ("US", "US Bank",                     "USBKUS", ("USD",)),
    ("US", "PNC Bank",                    "PNCCUS", ("USD",)),
    ("US", "Truist Bank",                 "TRBTUS", ("USD",)),
    ("US", "Capital One",                 "HIBKUS", ("USD",)),
    ("US", "Goldman Sachs",               "GSCBUS", ("USD",)),
    ("US", "Morgan Stanley",              "MSNYUS", ("USD",)),
    ("US", "Chime Financial",             "CHIMEUS", ("USD",)),
    ("US", "SoFi Bank",                   "SOFIUS", ("USD",)),
    ("US", "Mercury (Choice Fin.)",       "MRCYUS", ("USD",)),
    ("US", "Varo Bank",                   "VAROUS", ("USD",)),
    ("US", "Ally Bank",                   "ALLYUS", ("USD",)),
    ("US", "Fifth Third Bank",            "FTBCUS", ("USD",)),
    ("US", "Charles Schwab Bank",         "CSCHUS", ("USD",)),
    # Germany — more + neobanks
    ("DE", "N26",                         "NTSBDE", ("EUR",)),
    ("DE", "DKB (Deutsche Kreditbank)",   "BYLADEM1001", ("EUR",)),
    ("DE", "ING Deutschland",             "INGDDE", ("EUR",)),
    ("DE", "HypoVereinsbank (UniCredit)", "HYVEDE", ("EUR",)),
    ("DE", "Postbank",                    "PBNKDE", ("EUR",)),
    # Singapore — expand
    ("SG", "MariBank",                    "MARBSG", ("SGD",)),
    ("SG", "Trust Bank Singapore",        "TRBKSG", ("SGD",)),
    ("SG", "ANEXT Bank",                  "ANEXSG", ("SGD",)),
    # UAE — more
    ("AE", "RAKBANK",                     "NRAKAE", ("AED",)),
    ("AE", "Commercial Bank of Dubai",    "CBDUAE", ("AED",)),
    ("AE", "Union National Bank",         "UNNBAE", ("AED",)),
    ("AE", "Al Hilal Bank",               "ALHIAE", ("AED",)),
    # Kazakhstan — more
    ("KZ", "Bank CenterCredit",           "KCJBKZ", ("KZT",)),
    ("KZ", "Eurasian Bank",               "EURIKZ", ("KZT",)),
    ("KZ", "Freedom Finance Bank",        "KSNVKZ", ("KZT",)),
    ("KZ", "Nurbank",                     "NBPAKZ", ("KZT",)),
    # France — more
    ("FR", "La Banque Postale",           "PSSTFR", ("EUR",)),
    ("FR", "Credit Mutuel",               "CMCIFR", ("EUR",)),
    ("FR", "Caisse d'Epargne",            "CEPAFR", ("EUR",)),
    # Australia — more
    ("AU", "Bendigo and Adelaide Bank",   "BENDAU", ("AUD",)),
    ("AU", "Macquarie Bank",              "MACQAU", ("AUD",)),
    ("AU", "Suncorp Bank",                "METWAU", ("AUD",)),
    # International (country-agnostic neobanks — pick any country)
    ("US", "Wise USD Account",            "TRWIUS", ("USD",)),
    ("US", "Payoneer",                    "PAYOUS", ("USD",)),
    ("GB", "Payoneer Europe",             "PAYOGB", ("GBP", "EUR", "USD")),
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
