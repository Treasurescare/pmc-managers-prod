#!/usr/bin/env python3
"""One-shot VAPID keypair generator for the Web Push router.

Run:  python3 tools/push/generate_vapid_keys.py

Prints three lines you can paste into:
   backend/.env                 → VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_CLAIM_EMAIL
   frontend/.env                → REACT_APP_VAPID_PUBLIC_KEY  (same value as backend public)

The private key stays server-side only; the public key is safe to ship in the
browser bundle by design.
"""
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


def main() -> None:
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key()

    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    raw = pub.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")

    print("# --- backend/.env (single-line escape \\n between lines) ---")
    print("VAPID_PRIVATE_KEY=" + priv_pem.replace("\n", "\\n"))
    print("VAPID_PUBLIC_KEY=" + pub_b64)
    print("VAPID_CLAIM_EMAIL=mailto:admin@pmcmanagers.com")
    print()
    print("# --- frontend/.env (same public key) ---")
    print("REACT_APP_VAPID_PUBLIC_KEY=" + pub_b64)


if __name__ == "__main__":
    main()
