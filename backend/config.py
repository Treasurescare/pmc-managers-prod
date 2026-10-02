import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")


def _require_env(name: str) -> str:
    """Fetch a required env var. On failure, log a big obvious error to stdout
    (so it lands in `eb logs`/`docker logs`) and exit(1) instead of raising an
    unhandled KeyError that AWS surfaces as an opaque 502 Bad Gateway."""
    val = os.environ.get(name, "")
    if not val:
        present = sorted(k for k in os.environ.keys()
                          if k.isupper() and not k.startswith("_"))
        msg = (f"\n\n[PMC-STARTUP-FATAL] Required environment variable '{name}' is missing "
               f"or empty.\n[PMC-STARTUP-FATAL] Env vars visible to the container: "
               f"{', '.join(present)}\n[PMC-STARTUP-FATAL] Fix EB Console → Configuration → "
               f"Software → Environment properties, then Apply.\n\n")
        # Print to BOTH stdout and stderr so it shows up in eb logs regardless of channel.
        sys.stdout.write(msg)
        sys.stderr.write(msg)
        sys.stdout.flush()
        sys.stderr.flush()
        logging.critical(msg)
        sys.exit(1)
    return val


# Mongo
MONGO_URL = _require_env("MONGO_URL")
DB_NAME = _require_env("DB_NAME")

# JWT
JWT_SECRET = _require_env("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MIN = 60 * 24
MAGIC_LINK_TTL_HOURS = 72

# Tenant — Phase 1 single default tenant. Phase 2 (AWS) derives from Cognito token.
DEFAULT_TENANT_ID = "PMC-KZ-01"

# Admin seed — SEC-001: passwords MUST come from env in production.
# In non-production envs we still fall back to defaults so local dev / preview
# stays frictionless. Production ("ENV=production") is strict: missing seeds
# refuse to boot rather than silently seed weak credentials.
_IS_PROD = (os.environ.get("ENV", "").lower() == "production"
            or os.environ.get("DEPLOY_ENV", "").lower() == "production")


def _seed_password(name: str, fallback: str) -> str:
    val = os.environ.get(name, "")
    if val:
        return val
    if _IS_PROD:
        return _require_env(name)
    logging.warning(
        "[PMC-SEC-001] %s not set — using built-in default (DEV ONLY). "
        "Set %s in production to a strong value.", name, name,
    )
    return fallback


ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "adminsupport@pmcmanagers.com").lower()
ADMIN_PASSWORD = _seed_password("ADMIN_PASSWORD", "Admin@123")

# Second Owner seed — the real user building this app. Same role/level as
# the master admin but keyed on a real inbox so they can log in on prod.
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "kannan@emeraldcorporates.com").lower()
OWNER_PASSWORD = _seed_password("OWNER_PASSWORD", "Owner@123")

# Wave 1 — seeded staff accounts for the multi-role pipeline demo.
# Passwords honour env overrides so prod operators can rotate them without
# touching source. Env keys: STAFF_PW_ESCROW, STAFF_PW_CERTIFIER, …
def _staff_pw(key: str, fallback: str) -> str:
    return _seed_password(f"STAFF_PW_{key}", fallback)


STAFF_SEEDS = [
    ("escrow@pmcmanagers.com",   _staff_pw("ESCROW",    "Escrow@123"), "Escrow Agent",    ["escrow_agent"]),
    ("certifier@pmcmanagers.com",_staff_pw("CERTIFIER", "Certify@123"),"Site Certifier",  ["certifier"]),
    ("legal@pmcmanagers.com",    _staff_pw("LEGAL",     "Legal@123"),  "Legal Counsel",   ["legal_counsel"]),
    ("accounts@pmcmanagers.com", _staff_pw("ACCOUNTS",  "Accts@123"),  "Accounting Team", ["accounting"]),
    ("committee@pmcmanagers.com",_staff_pw("COMMITTEE", "Bid@1234"),   "Committee Chair", ["committee_member", "admin"]),
]

# Email — direct Resend path (preferred) or legacy relay fallback.
# When RESEND_API_KEY is set, mail goes straight to Resend's API and sends from
# EMAIL_FROM_ADDRESS on the verified pmcmanagers.com domain. Otherwise the
# legacy relay key path is used.
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "") \
            or os.environ.get("EMAIL_API_KEY", "") \
            or os.environ.get("LEGACY_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "PMC Managers Limited")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", "admin@mail.pmcmanagers.com")
# Base URL is a CONSTANT per the relay playbook — do NOT read from env.
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

# Cookie domain — set to ".pmcmanagers.com" so a browser on the apex OR www
# sees cookies from api.pmcmanagers.com as first-party (Safari ITP fix).
# Leave empty to fall back to the request host (dev / preview).
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", "").strip() or None

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
