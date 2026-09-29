"""PMC v50 — Option E email rendering engine.

Registers all 52 HTML templates (shipped with the design) and exposes:

  render_email(name, ctx)  -> (subject, html)   generic renderer
  send_e_email(name, to, ctx, category=..., cc=None, bcc=None)
                                -> forwards to backend.emails.send_email

Each template is a full HTML document with Jinja-style `{{placeholder}}`s.
The renderer does simple `{{key}}` substitution (safe HTML escaping only for
non-URL placeholders); we deliberately keep the templates as-is so designers
can edit them without touching Python.

Typed convenience builders (matching every real event that fires an email in
the app today) sit at the bottom. Each accepts kwargs, applies sensible
defaults, and returns (subject, html) ready for `send_email`.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

TEMPLATES_DIR = Path(__file__).parent / "email_templates"

log = logging.getLogger(__name__)

_CACHE: Dict[str, str] = {}
_META_CACHE: Dict[str, Dict[str, str]] = {}
_CACHE: Dict[str, str] = {}
_META_CACHE: Dict[str, Dict[str, str]] = {}

# Regex to pull <title>…</title> for automatic subject fallback.
_TITLE_RX = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# All 52 templates keyed by their real trigger event.
# Keys map cleanly to send-email call sites (search codebase for the key).
TEMPLATES: Dict[str, str] = {
    "account.verify_email":         "01-account-verify-email.html",
    "account.password_reset":       "02-password-reset.html",
    "account.password_changed":     "03-password-changed.html",
    "account.two_factor_enabled":   "04-2fa-enabled.html",
    "account.two_factor_disabled":  "05-2fa-disabled.html",
    "account.new_device_signin":    "06-new-device-signin.html",
    "account.team_invite":          "07-team-invite.html",
    "account.refund_account_changed": "08-refund-account-changed.html",
    "account.data_export_ready":    "09-data-export-ready.html",
    "account.data_deleted":         "10-data-deleted.html",

    "registration.resume":          "11-registration-resume.html",
    "registration.submitted":       "12-registration-submitted.html",

    "kyc.approved":                 "13-kyc-approved.html",
    "kyc.changes_requested":        "14-kyc-changes-requested.html",
    "kyc.rejected":                 "15-kyc-rejected.html",
    "kyc.licence_expiring":         "16-licence-expiring.html",
    "kyc.vendor_invited":           "17-vendor-invited.html",

    "tender.followed":              "18-tender-followed.html",
    "tender.saved_search_created":  "19-saved-search-created.html",
    "clarification.received":       "20-clarification-received.html",
    "clarification.answered":       "21-clarification-answered.html",
    "corrigendum.issued":           "22-corrigendum-issued.html",
    "deadline.extended":            "23-deadline-extended.html",
    "tender.cancelled":             "24-tender-cancelled.html",

    "bid.envelope_sealed":          "25-envelope-sealed.html",
    "bid.submitted":                "26-bid-submitted.html",
    "bid.unsealed":                 "27-bid-unsealed.html",
    "bid.withdrawn":                "28-bid-withdrawn.html",
    "deadline.reminder":            "29-deadline-reminder.html",

    "emd.payment_submitted":        "30-emd-payment-submitted.html",
    "emd.confirmed":                "31-emd-confirmed.html",
    "bg.accepted":                  "32-bg-accepted.html",
    "bg.rejected":                  "33-bg-rejected.html",
    "bg.expiring":                  "34-bg-expiring.html",
    "emd.refunded":                 "35-emd-refunded.html",

    "billing.invoice_issued":       "36-invoice-issued.html",
    "billing.payment_received":     "37-payment-received.html",
    "evaluation.technical_result":  "38-technical-result.html",

    "award.notification":           "39-award-notification.html",
    "award.not_awarded":            "40-not-awarded.html",
    "docusign.document_to_sign":    "41-document-to-sign.html",
    "docusign.document_signed":     "42-document-signed.html",
    "contract.activated":           "43-contract-activated.html",
    "contract.milestone_certified": "44-milestone-certified.html",

    "support.ticket_received":      "45-ticket-received.html",
    "support.ticket_replied":       "46-ticket-replied.html",

    "staff.approval_requested":     "47-staff-approval-requested.html",
    "staff.notice_published":       "48-staff-notice-published.html",
    "committee.invitation":         "49-committee-invitation.html",
    "committee.scores_locked":      "50-committee-scores-locked.html",
    "award.signoff_requested":      "51-award-signoff-requested.html",
    "escrow.action_needed":         "52-escrow-action-needed.html",
}


def _load(name: str) -> str:
    if name in _CACHE:
        return _CACHE[name]
    fname = TEMPLATES.get(name)
    if not fname:
        raise KeyError(f"Unknown email template: {name!r}")
    path = TEMPLATES_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Template file missing: {path}")
    body = path.read_text(encoding="utf-8")
    _CACHE[name] = body
    # Extract subject from <title>
    m = _TITLE_RX.search(body)
    _META_CACHE[name] = {"subject": m.group(1).strip() if m else "PMC Managers"}
    return body


def _sub(body: str, ctx: Dict[str, Any]) -> str:
    """Substitute `{{key}}` placeholders with ctx values.

    URL-like placeholders (keys ending in _url/href/link) are inserted raw
    (they belong in href/src). All other values are HTML-escaped for safety.
    """
    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        val = ctx.get(key)
        if val is None:
            return ""
        val_str = str(val)
        # Leave URL placeholders raw so href/src stay valid.
        if key.endswith(("_url", "href", "link")) or key.startswith("http"):
            return val_str
        # Also keep already-safe HTML fragments intact if flagged via key suffix.
        if key.endswith("_html"):
            return val_str
        return html.escape(val_str, quote=True)
    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", replace, body)


def render_email(name: str, ctx: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """Render a template into (subject, html)."""
    ctx = dict(ctx or {})
    # Sensible defaults consumed by many templates
    ctx.setdefault("help_url", "https://pmcmanagers.com/help")
    ctx.setdefault("ledger_ref", f"pmc:{name}:{int(datetime.utcnow().timestamp())}")
    ctx.setdefault("year", datetime.utcnow().year)
    body = _load(name)
    html_out = _sub(body, ctx)
    subject_raw = _META_CACHE.get(name, {}).get("subject", "PMC Managers")
    subject = _sub(subject_raw, ctx)
    return subject, html_out


def all_template_names() -> List[str]:
    """Return every registered event key."""
    return list(TEMPLATES.keys())


def preview_all(default_ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, str]]:
    """Render every template with a demo context (used by admin preview endpoint)."""
    demo = {
        "first_name": "Aisha",
        "company_name": "Emerald Corporates",
        "email": "aisha@example.com",
        "expires_at": "24 hours",
        "verify_url": "https://pmcmanagers.com/verify/abc123",
        "reset_url": "https://pmcmanagers.com/reset/abc123",
        "signin_time": "28 Feb 2026, 14:22 UTC",
        "device": "Chrome on macOS · Kazakhstan",
        "invite_url": "https://pmcmanagers.com/invite/abc123",
        "invited_by": "Nurlan A.",
        "role": "Committee reviewer",
        "vendor_ref": "PMC-VEN-000023",
        "notice_ref": "PMC-NOT-2026-0055",
        "tender_title": "Turnkey IVF Laboratory Setup",
        "tender_url": "https://pmcmanagers.com/notices/PMC-NOT-2026-0055",
        "deadline": "30 Sep 2026, 21:48 (UTC+5)",
        "budget": "USD 2,100,000",
        "bid_ref": "PMC-BID-2026-00017",
        "bid_url": "https://pmcmanagers.com/vendor/mybids",
        "corrigendum_ref": "PMC-COR-2026-0011",
        "change_summary": "Deadline extended by 7 days; BOQ v2 attached.",
        "amount": "USD 31,600",
        "reference": "TXN-882312",
        "sign_url": "https://pmcmanagers.com/vendor/signatures",
        "sign_by": "5 Mar 2026",
        "award_ref": "PMC-AWD-2026-00007",
        "award_value": "USD 2,090,000",
        "invoice_ref": "PMC-INV-2026-00191",
        "invoice_amount": "USD 4,200",
        "invoice_url": "https://pmcmanagers.com/vendor/emd",
        "ticket_ref": "PMC-TIC-000418",
        "ticket_url": "https://pmcmanagers.com/help",
        "milestone": "MS-3 · Structural completion",
        "certificate_url": "https://pmcmanagers.com/vendor/signatures",
        "help_url": "https://pmcmanagers.com/help",
    }
    demo.update(default_ctx or {})
    out: Dict[str, Dict[str, str]] = {}
    for key in TEMPLATES:
        try:
            subj, htmlout = render_email(key, demo)
            out[key] = {"subject": subj, "html": htmlout}
        except Exception as exc:
            out[key] = {"error": str(exc)}
    return out


# ────────────────────────────────────────────────────────────────────
# Convenience: send helpers. Late-bind Resend to avoid import cycles.
# ────────────────────────────────────────────────────────────────────
async def send_e_email(
    template: str,
    to: str,
    ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Render a v50 email template and dispatch via the existing Resend integration."""
    subject, body_html = render_email(template, ctx)
    try:
        from emails import send_email  # existing Resend integration
    except Exception as exc:
        log.error("send_e_email: emails.send_email not importable: %s", exc)
        return {"ok": False, "error": "email backend unavailable"}
    ok = await send_email(to_email=to, subject=subject, html=body_html)
    return {"ok": bool(ok), "template": template, "to": to, "subject": subject}
