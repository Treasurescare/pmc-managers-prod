"""PMC v46p — data-flow diagram generator.

Produces:
  * /app/deliverables/v46_manual/build/PMC_v46p_Data_Flow.svg
  * /app/deliverables/v46_manual/build/PMC_v46p_Data_Flow.pdf

Shows every principal data domain (vendors, notices, bids, escrow, evaluation,
contracts, audit, AI) and the direction of data movement between them.
"""
from pathlib import Path
from weasyprint import HTML

OUT = Path("/app/deliverables/v46_manual/build")
OUT.mkdir(parents=True, exist_ok=True)


def _svg() -> str:
    W, H = 1800, 1200
    NAVY = "#0B132B"
    GOLD = "#D4AF37"
    INK = "#0f1f3a"
    MUTED = "#64748b"

    nodes = [
        # (x, y, w, h, title, subtitle, fill)
        (60,  60, 360, 90, "Public Notice Board", "Anonymous read · GET /api/v1/notices", "#eef2f8"),
        (60, 180, 360, 90, "Vendor Registration", "registrations · magic_token flow", "#eef2f8"),
        (60, 300, 360, 90, "Vendor Portal", "vendors · KYC · licences · scorecard", "#e2ecff"),
        (60, 420, 360, 90, "Bids", "bids · price · docs · EMD reference", "#e2ecff"),
        (60, 540, 360, 90, "Reverse Auctions", "auctions · live_bids · winners", "#e2ecff"),

        (720, 60, 360, 90, "Admin Console", "admin_users · CSRF+Bearer session", "#fff4d6"),
        (720, 180, 360, 90, "Tender Builder", "tender_templates (masters + drafts)", "#fff4d6"),
        (720, 300, 360, 90, "Notices Publisher", "notices · corrigenda · attachments", "#fff4d6"),
        (720, 420, 360, 90, "Evaluations & Rubrics", "rubrics · scores · lock_envelopes", "#fff4d6"),
        (720, 540, 360, 90, "Awards & Contracts", "awards · contracts · milestones", "#fff4d6"),

        (1380, 60, 360, 90, "Emergent LLM Proxy", "DPR extract · section drafter · anomaly", "#f3e8ff"),
        (1380, 180, 360, 90, "Escrow (EMD)", "escrow_accounts · escrow_transactions", "#e8f8ee"),
        (1380, 300, 360, 90, "DocuSign Envelopes", "LOA · PO · Contract · NDA", "#e8f8ee"),
        (1380, 420, 360, 90, "Payments (Stripe / Kaspi / SWIFT)", "settlements · refunds", "#e8f8ee"),
        (1380, 540, 360, 90, "Audit Trail (immutable)", "audits · actor · entity · when", "#fde2e2"),

        (60,  720, 1680, 90, "MongoDB Atlas (primary EU · warm ME · read-only DR)", "Replication oplog · 60 s RPO · 30 min RTO", NAVY),
        (60,  840, 820, 90, "S3 · CloudFront (public assets + downloads)", "pmc-uploads · pmc-downloads · CRR to me-south-1", NAVY),
        (920, 840, 820, 90, "External integrations", "Resend · Snapchat · Instagram · Telegram · WhatsApp · LSEG · Firebase", NAVY),
        (60,  960, 1680, 90, "PMC v46p Platform · Observability · CloudWatch + Sentry + custom audit log", "Every actor, every entity, every action — immutable trail", GOLD),
    ]

    edges = [
        # (from_idx, to_idx, label)
        (0, 1, "Register-as-supplier CTA"),
        (1, 2, "Approved · vendor_ref issued"),
        (2, 3, "Submit bid"),
        (2, 4, "Join auction"),
        (3, 8, "Score technical + commercial"),
        (4, 9, "Winning bid → award"),
        (5, 6, "Master → clone"),
        (6, 7, "Save + Publish"),
        (7, 0, "Public detail cache"),
        (7, 8, "Rubric + envelope lock"),
        (8, 9, "Award report → contract"),
        (10, 6, "AI section drafter"),
        (10, 3, "Bid anomaly detector"),
        (11, 3, "EMD posted per bid"),
        (11, 9, "EMD refund on close"),
        (12, 9, "Signed LOA / PO"),
        (13, 11, "Settlements per escrow tx"),
        (14, 0, "Read-only audit query"),
        (14, 8, "Evaluation lineage"),
    ]

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}'>",
        f"<rect x='0' y='0' width='{W}' height='{H}' fill='#f7f5f0'/>",
        # header
        f"<text x='60' y='40' font-family='Georgia' font-size='24' fill='{NAVY}' font-weight='700'>PMC Managers v46p — Data Flow</text>",
        f"<text x='{W-60}' y='40' font-family='Georgia' font-size='11' fill='{MUTED}' text-anchor='end'>CONFIDENTIAL — INTERNAL USE ONLY</text>",
        # arrow-head marker
        "<defs><marker id='arr' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto-start-reverse'>"
        f"<path d='M 0 0 L 10 5 L 0 10 z' fill='{INK}'/></marker></defs>",
    ]

    # boxes
    for i, (x, y, w, h, t, s, fill) in enumerate(nodes):
        stroke = NAVY if fill.startswith("#0") or fill == GOLD else "#cbd5e1"
        text_col = "#fff" if fill == NAVY else ("#0b1f3a" if fill != GOLD else NAVY)
        sub_col = "rgba(255,255,255,0.75)" if fill == NAVY else ("#0b1f3a" if fill == GOLD else MUTED)
        parts.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='6' ry='6' fill='{fill}' stroke='{stroke}' stroke-width='1.5'/>")
        parts.append(f"<text x='{x+16}' y='{y+34}' font-family='Georgia' font-size='16' font-weight='700' fill='{text_col}'>{t}</text>")
        parts.append(f"<text x='{x+16}' y='{y+58}' font-family='Georgia' font-size='11' fill='{sub_col}'>{s}</text>")

    # edges
    def center(idx):
        x, y, w, h, *_ = nodes[idx]
        return x + w/2, y + h/2

    for a, b, label in edges:
        ax, ay = center(a); bx, by = center(b)
        # bezier midpoint
        mx = (ax + bx) / 2
        my = (ay + by) / 2 - 20
        parts.append(f"<path d='M {ax} {ay} Q {mx} {my} {bx} {by}' fill='none' stroke='{INK}' stroke-width='1.2' opacity='0.55' marker-end='url(#arr)'/>")
        parts.append(f"<text x='{mx}' y='{my-6}' font-family='Georgia' font-size='9' fill='{MUTED}' text-anchor='middle'>{label}</text>")

    # legend
    lx, ly = 60, 1080
    legend = [
        ("Vendor domain", "#e2ecff"),
        ("Admin domain", "#fff4d6"),
        ("AI / Money / Docs", "#e8f8ee"),
        ("Immutable audit", "#fde2e2"),
        ("Infrastructure", NAVY),
        ("Gold seal", GOLD),
    ]
    for i, (label, colour) in enumerate(legend):
        x = lx + i * 280
        parts.append(f"<rect x='{x}' y='{ly}' width='24' height='16' fill='{colour}' stroke='#cbd5e1'/>")
        parts.append(f"<text x='{x+30}' y='{ly+13}' font-family='Georgia' font-size='11' fill='{INK}'>{label}</text>")

    parts.append("</svg>")
    return "".join(parts)


def main():
    svg = _svg()
    (OUT / "PMC_v46p_Data_Flow.svg").write_text(svg)
    html = f"""<!doctype html><html><head><meta charset='utf-8'>
<style>
  @page {{ size: 420mm 300mm; margin: 6mm; }}
  html, body {{ margin: 0; padding: 0; }}
  svg {{ display: block; width: 100%; height: auto; }}
</style></head><body>{svg}</body></html>"""
    HTML(string=html).write_pdf(str(OUT / "PMC_v46p_Data_Flow.pdf"))
    print(f"Data-flow written: {(OUT/'PMC_v46p_Data_Flow.pdf').stat().st_size/1024:.1f} KB")


if __name__ == "__main__":
    main()
