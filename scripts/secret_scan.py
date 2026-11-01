"""Block download bundles that contain API keys, private keys or passwords. Usage: secret_scan.py <file-or-zip>..."""
import re
import sys
import zipfile

PATTERNS = {
    "Resend key": r"\bre_[A-Za-z0-9]{8,}_[A-Za-z0-9_]{8,}",
    "Stripe live/test key": r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}",
    "OpenAI/Emergent key": r"\bsk-(proj-|emergent-)?[A-Za-z0-9]{20,}",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "Google OAuth secret": r"\bGOCSPX-[A-Za-z0-9_-]{20,}",
    "GitHub token": r"\bgh[pousr]_[A-Za-z0-9]{30,}",
    "Slack token": r"\bxox[abposr]-[A-Za-z0-9-]{10,}",
    "Private key block": r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "Database URL with password": r"mongodb(\+srv)?://[^:/\s\"']+:[^@\s\"']{3,}@",
    "Secret assignment": r"(?i)\b(api[_-]?key|secret[_-]?key|password|passwd|private[_-]?key|client[_-]?secret|auth[_-]?token)\b[\"']?\s*[:=]\s*[\"'](?!\$|\{|<|your|xxx|changeme|placeholder|example)[A-Za-z0-9+/_\-!@#%^&*.]{12,}[\"']",
}
SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".pdf", ".zip", ".mp4", ".svg", ".map")
SKIP_PARTS = ("node_modules/", "/tests/", "secret_scan.py", "generate_vapid_keys.py")
RX = {k: re.compile(v) for k, v in PATTERNS.items()}


def scan_text(name, text):
    return [(name, k) for k, rx in RX.items() if rx.search(text)]


def scan(path):
    hits = []
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                base = n.rsplit("/", 1)[-1]
                if base in (".env",) or base.endswith((".pem", ".key")):
                    hits.append((n, "secret file"))
                    continue
                if n.endswith("/") or n.lower().endswith(SKIP_EXT) or any(s in n for s in SKIP_PARTS):
                    continue
                hits += scan_text(n, z.read(n).decode("utf-8", "ignore"))
    else:
        hits += scan_text(path, open(path, encoding="utf-8", errors="ignore").read())
    return hits


if __name__ == "__main__":
    found = [h for p in sys.argv[1:] for h in scan(p)]
    for name, kind in found:
        print(f"BLOCKED: {kind} in {name}")
    if found:
        print(f"Secret scan FAILED: {len(found)} finding(s). Remove the secret (keep it only in server settings) and rebuild.")
        sys.exit(1)
    print("Secret scan passed.")
