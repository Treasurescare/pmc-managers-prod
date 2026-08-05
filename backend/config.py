import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Mongo
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# JWT
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MIN = 60 * 24
MAGIC_LINK_TTL_HOURS = 72

# Tenant — Phase 1 single default tenant. Phase 2 (AWS) derives from Cognito token.
DEFAULT_TENANT_ID = "PMC-KZ-01"

# Admin seed
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "adminsupport@pmcmanagers.com").lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123")

# Second Owner seed — the real user building this app. Same role/level as
# the master admin but keyed on a real inbox so they can log in on prod.
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "kannan@emeraldcorporates.com").lower()
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "Owner@123")

# Wave 1 — seeded staff accounts for the multi-role pipeline demo.
STAFF_SEEDS = [
    ("escrow@pmcmanagers.com",   "Escrow@123", "Escrow Agent",    ["escrow_agent"]),
    ("certifier@pmcmanagers.com","Certify@123","Site Certifier",  ["certifier"]),
    ("legal@pmcmanagers.com",    "Legal@123",  "Legal Counsel",   ["legal_counsel"]),
    ("accounts@pmcmanagers.com", "Accts@123",  "Accounting Team", ["accounting"]),
    ("committee@pmcmanagers.com","Bid@1234",   "Committee Chair", ["committee_member", "admin"]),
]

# Email (Resend via Emergent proxy)
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "PMC Managers Limited")
EMAIL_BASE_URL = "https://integrations.emergentagent.com"

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Uploads
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# KYC provider (KYC-Checks / Sumsub / Onfido). Blank = falls back to deterministic stub.
KYC_PROVIDER = os.environ.get("KYC_PROVIDER", "stub").lower()
KYC_BASE_URL = os.environ.get("KYC_BASE_URL", "")
KYC_API_KEY = os.environ.get("KYC_API_KEY", "")
KYC_WEBHOOK_SECRET = os.environ.get("KYC_WEBHOOK_SECRET", "")

# CORS
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").strip()

# KZ Licenses & Category map (from Domain_Spec §3 and §4)
KZ_LICENSE_TYPES = [
    "Construction (1st category)",
    "Electrical installation",
    "Mechanical works",
    "Plumbing & firefighting",
    "Medical gas installation",
    "HSE compliance",
]

KZ_CATEGORY_LICENSE_MAP = {
    "Medical gas pipeline systems": ["Medical gas installation"],
    "OT equipment & laminar flow systems": ["Medical gas installation"],
    "Modular operation theatres (OTs)": ["Medical gas installation", "Mechanical works"],
    "External power supply grid connection": ["Electrical installation"],
    "Substation works (HT/LT)": ["Electrical installation"],
    "Transformers procurement & installation": ["Electrical installation"],
    "Elevators & escalators": ["Mechanical works", "Electrical installation"],
    "Elevators for hostel blocks": ["Mechanical works", "Electrical installation"],
    "Elevator & escalator AMC": ["Mechanical works", "Electrical installation"],
    "Fire alarm & safety systems": ["Electrical installation", "HSE compliance"],
    "External firefighting network (hydrants)": ["Plumbing & firefighting", "HSE compliance"],
    "Fire system AMC": ["HSE compliance"],
    "Water treatment plant (WTP)": ["Plumbing & firefighting"],
    "Sewage treatment plant (STP)": ["Plumbing & firefighting"],
    "Hostel bathrooms & plumbing": ["Plumbing & firefighting"],
    "Hospital civil & superstructure works": ["Construction (1st category)", "HSE compliance"],
    "Main academic building civil works": ["Construction (1st category)"],
    "Hotel superstructure works": ["Construction (1st category)"],
}

# 30 countries (KZ default)
COUNTRIES = [
    ("KZ", "Kazakhstan",         "Казахстан",              "Қазақстан"),
    ("RU", "Russia",             "Россия",                 "Ресей"),
    ("UZ", "Uzbekistan",         "Узбекистан",             "Өзбекстан"),
    ("KG", "Kyrgyzstan",         "Кыргызстан",             "Қырғызстан"),
    ("TJ", "Tajikistan",         "Таджикистан",            "Тәжікстан"),
    ("TM", "Turkmenistan",       "Туркменистан",           "Түрікменстан"),
    ("AZ", "Azerbaijan",         "Азербайджан",            "Әзірбайжан"),
    ("AM", "Armenia",            "Армения",                "Армения"),
    ("GE", "Georgia",            "Грузия",                 "Грузия"),
    ("TR", "Turkey",             "Турция",                 "Түркия"),
    ("AE", "United Arab Emirates","Объединённые Арабские Эмираты","Біріккен Араб Әмірліктері"),
    ("SA", "Saudi Arabia",       "Саудовская Аравия",      "Сауд Арабиясы"),
    ("QA", "Qatar",              "Катар",                  "Катар"),
    ("OM", "Oman",               "Оман",                   "Оман"),
    ("BH", "Bahrain",            "Бахрейн",                "Бахрейн"),
    ("KW", "Kuwait",             "Кувейт",                 "Кувейт"),
    ("IN", "India",              "Индия",                  "Үндістан"),
    ("PK", "Pakistan",           "Пакистан",               "Пәкістан"),
    ("CN", "China",              "Китай",                  "Қытай"),
    ("KR", "South Korea",        "Южная Корея",            "Оңтүстік Корея"),
    ("JP", "Japan",              "Япония",                 "Жапония"),
    ("SG", "Singapore",          "Сингапур",               "Сингапур"),
    ("GB", "United Kingdom",     "Великобритания",         "Ұлыбритания"),
    ("DE", "Germany",            "Германия",               "Германия"),
    ("FR", "France",             "Франция",                "Франция"),
    ("IT", "Italy",              "Италия",                 "Италия"),
    ("ES", "Spain",              "Испания",                "Испания"),
    ("US", "United States",      "США",                    "АҚШ"),
    ("LU", "Luxembourg",         "Люксембург",             "Люксембург"),
    ("CH", "Switzerland",        "Швейцария",              "Швейцария"),
]
