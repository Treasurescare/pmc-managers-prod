"""PMC v49b — Option-E branded email wrapper.

Ports the 6 email designs from /design/emails.html into a single wrapper that
mirrors the "PMC Managers · Global Tender Board" look: forest green header,
Cormorant Garamond heading (via CSS webfont fallback), brass CTA, KV table for
key facts, and a hash-chained footer.

Consumers call `wrap_e(title, intro_html, kv=[(label, value), ...],
cta_label=..., cta_url=..., note=...)` and pass the result to `send_email()`
in /app/backend/emails.py.

Kept 100% inline-styled (no external CSS) because email clients strip <link>
and most <style> blocks. Any Option-E page-CSS is irrelevant here.
"""
from typing import Iterable, Optional, Tuple

PRIMARY = "#0F3B2E"       # forest green
BRASS = "#B08E4A"         # gold accent
PAPER = "#F6F0DC"         # cream background
INK = "#1C1C1B"
INK_MUTED = "#5A5A57"
CHROME = "#0B1A14"        # deep chrome for header


def _kv_row(label: str, value: str) -> str:
    return (
        f'<tr>'
        f'<td style="padding:8px 0;color:{INK_MUTED};font:11px/16px \'Public Sans\',Helvetica,Arial,sans-serif;'
        f'letter-spacing:0.14em;text-transform:uppercase;width:38%;vertical-align:top">{label}</td>'
        f'<td style="padding:8px 0;color:{INK};font:14px/20px \'JetBrains Mono\',ui-monospace,SFMono-Regular,Menlo,monospace;'
        f'text-align:right">{value}</td>'
        f'</tr>'
    )


def wrap_e(
    title: str,
    intro_html: str,
    kv: Optional[Iterable[Tuple[str, str]]] = None,
    cta_label: Optional[str] = None,
    cta_url: Optional[str] = None,
    note: Optional[str] = None,
    ref: Optional[str] = None,
) -> str:
    """Return an Option-E styled HTML email body ready for Resend."""
    kv_html = ""
    if kv:
        rows = "".join(_kv_row(k, v) for k, v in kv)
        kv_html = (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-top:1px solid {BRASS};border-bottom:1px solid {BRASS};margin:20px 0">{rows}</table>'
        )

    cta = ""
    if cta_label and cta_url:
        cta = (
            f'<div style="margin:24px 0 8px">'
            f'<a href="{cta_url}" style="background:{BRASS};color:{CHROME};text-decoration:none;'
            f'padding:14px 28px;font:600 14px/1 \'Public Sans\',Helvetica,Arial,sans-serif;'
            f'letter-spacing:0.02em;display:inline-block;border-radius:2px">{cta_label}</a>'
            f'</div>'
        )

    note_html = ""
    if note:
        note_html = (
            f'<p style="margin:22px 0 0;padding:14px 16px;background:{PAPER};border-left:3px solid {BRASS};'
            f'color:{INK_MUTED};font:13px/20px \'Public Sans\',Helvetica,Arial,sans-serif">{note}</p>'
        )

    ref_html = ""
    if ref:
        ref_html = (
            f'<div style="margin-top:8px;color:{INK_MUTED};font:11px/16px \'JetBrains Mono\',ui-monospace,monospace;'
            f'letter-spacing:0.06em">{ref}</div>'
        )

    return f"""<!doctype html><html><body style="margin:0;background:{PAPER};padding:32px 0;font-family:'Public Sans',Helvetica,Arial,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid {BRASS}22">
    <tr><td style="background:{CHROME};color:#FFFFFF;padding:22px 32px">
      <div style="font:11px/16px 'Public Sans',Helvetica,Arial,sans-serif;color:{BRASS};letter-spacing:0.22em;text-transform:uppercase">PMC Managers Limited</div>
      <div style="font:400 22px/28px Georgia,'Cormorant Garamond',serif;color:#FFFFFF;margin-top:6px">Global Tender Board</div>
    </td></tr>
    <tr><td style="padding:36px 32px 28px">
      <h1 style="margin:0 0 12px;font:400 28px/34px Georgia,'Cormorant Garamond',serif;color:{PRIMARY}">{title}</h1>
      {ref_html}
      <div style="color:{INK};font:15px/24px 'Public Sans',Helvetica,Arial,sans-serif;margin-top:14px">{intro_html}</div>
      {kv_html}
      {cta}
      {note_html}
    </td></tr>
    <tr><td style="border-top:1px solid {BRASS}44;padding:18px 32px;background:#FAFAF7">
      <div style="color:{INK_MUTED};font:11px/16px 'Public Sans',Helvetica,Arial,sans-serif">
        Sent by PMC Managers Limited &middot; Global Tender Board &middot; This message is time-stamped and hash-chained to the audit ledger.
      </div>
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


# --- Convenience builders matching the 6 templates from /design/emails ---

def email_new_tender_match(vendor_name, notice_ref, title, deadline_local, budget, cta_url):
    return wrap_e(
        title=f"New tender matches your profile",
        intro_html=(
            f"Hello {vendor_name}, a new opportunity has been published that matches your registered "
            f"licences and categories. Here are the key facts:"
        ),
        kv=[
            ("Reference", notice_ref),
            ("Title", title),
            ("Closes", deadline_local),
            ("Indicative budget", budget),
        ],
        cta_label="View & prepare bid",
        cta_url=cta_url,
        note="Bids are sealed until deadline. Every action is logged on the audit ledger.",
        ref=notice_ref,
    )


def email_corrigendum(vendor_name, notice_ref, title, change_summary, cta_url):
    return wrap_e(
        title="Corrigendum issued",
        intro_html=(
            f"Hello {vendor_name}, a corrigendum has been issued for a tender you follow. "
            f"Please review the changes below:"
        ),
        kv=[("Reference", notice_ref), ("Title", title), ("Change", change_summary)],
        cta_label="See corrigendum",
        cta_url=cta_url,
        note="Your bid remains valid; you may unseal and edit until the (possibly new) deadline.",
        ref=notice_ref,
    )


def email_deadline_approaching(vendor_name, notice_ref, title, time_left, cta_url):
    return wrap_e(
        title="Deadline is close",
        intro_html=f"Hello {vendor_name}, this is a reminder that a bid deadline is approaching.",
        kv=[("Reference", notice_ref), ("Title", title), ("Time left", time_left)],
        cta_label="Open bid workspace",
        cta_url=cta_url,
        note="Unsealed drafts do not count. Seal your envelope before the deadline.",
        ref=notice_ref,
    )


def email_emd_received(vendor_name, bid_ref, amount, reference, cta_url):
    return wrap_e(
        title="EMD received",
        intro_html=f"Hello {vendor_name}, we have confirmed your Earnest Money Deposit.",
        kv=[("Bid", bid_ref), ("Amount", amount), ("Reference", reference), ("Status", "Held in escrow")],
        cta_label="Open bid",
        cta_url=cta_url,
        note="Your EMD is refundable per the notice's terms. Refunds are automatic after evaluation.",
        ref=bid_ref,
    )


def email_award_issued(vendor_name, award_ref, title, value, cta_url):
    return wrap_e(
        title="Letter of award",
        intro_html=(
            f"Congratulations {vendor_name}. Following evaluation and committee sign-off, the "
            f"following award has been issued to your company:"
        ),
        kv=[("Award reference", award_ref), ("Title", title), ("Value", value)],
        cta_label="Review & sign with DocuSign",
        cta_url=cta_url,
        note="Please sign within 7 days. The signed award is chained to the audit ledger.",
        ref=award_ref,
    )


def email_result_published(vendor_name, notice_ref, title, result_summary, cta_url):
    return wrap_e(
        title="Evaluation result published",
        intro_html=f"Hello {vendor_name}, the result for the following tender has been published.",
        kv=[("Reference", notice_ref), ("Title", title), ("Outcome", result_summary)],
        cta_label="See public result",
        cta_url=cta_url,
        note="A written debrief is available in your portal within 3 working days.",
        ref=notice_ref,
    )
