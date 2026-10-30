"""v52bo — Corrigendum one-page diff PDF.

Generates a compact, printable diff sheet for a corrigendum: notice ref,
corrigendum number + effective date, overall change description, the full
Field / Before / After / Reason table, deadline change (if any), and the
attachment file names. Attached to the bidder notification email on publish
so vendors receive the diff even if they never visit the public page.
"""
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

from pdf_brand import logo_flowable


def _short(dt: Optional[str]) -> str:
    if not dt:
        return "—"
    s = str(dt).replace("T", " ")
    return s[:16]


def build_corrigendum_pdf(notice: dict, corrigendum: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Corrigendum {corrigendum.get('corrigendum_no', '')} — "
              f"{notice.get('notice_ref', '')}",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"],
                          fontName="Helvetica", fontSize=9, leading=12,
                          textColor=colors.HexColor("#1a2b35"))
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10,
                           textColor=colors.HexColor("#64748b"))
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                        fontSize=16, leading=19, spaceAfter=4,
                        textColor=colors.HexColor("#0f3b2e"))
    label = ParagraphStyle("label", parent=small, fontName="Helvetica-Bold",
                           textColor=colors.HexColor("#8a6a1f"))

    story = [logo_flowable(), Spacer(1, 4)]
    story.append(Paragraph("PMC MANAGERS · GLOBAL TENDER BOARD", label))
    story.append(Paragraph(
        f"Corrigendum {corrigendum.get('corrigendum_no', '')} — {corrigendum.get('title', '')}",
        h1,
    ))
    story.append(Paragraph(
        f"Notice <b>{notice.get('notice_ref', '')}</b> &middot; "
        f"<i>{(notice.get('title') or '')[:120]}</i>",
        small,
    ))
    story.append(Paragraph(
        f"Effective: <b>{_short(corrigendum.get('effective_from') or corrigendum.get('published_at'))}</b>",
        small,
    ))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#D2B46A")))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Overall change description", label))
    story.append(Paragraph(
        (corrigendum.get("summary") or "—").replace("\n", "<br/>"),
        body,
    ))
    story.append(Spacer(1, 10))

    if corrigendum.get("new_submission_deadline"):
        story.append(Paragraph(
            f"<b>New submission deadline:</b> "
            f"{_short(corrigendum.get('new_submission_deadline'))}",
            body,
        ))
        story.append(Spacer(1, 8))

    amendments = corrigendum.get("field_amendments") or []
    if amendments:
        story.append(Paragraph("Field amendments", label))
        header = ["Field", "Before", "After", "Reason"]
        rows = [header]
        for a in amendments:
            rows.append([
                Paragraph(f"<b>{a.get('field', '')}</b>", body),
                Paragraph(str(a.get("before", "")) or "—", body),
                Paragraph(str(a.get("after", "")) or "—", body),
                Paragraph(str(a.get("note", "")) or "—", body),
            ])
        tbl = Table(
            rows,
            colWidths=[32 * mm, 44 * mm, 44 * mm, 54 * mm],
            repeatRows=1,
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F3B2E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D2B46A")),
            ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#FEF2F2")),
            ("BACKGROUND", (2, 1), (2, -1), colors.HexColor("#ECFDF5")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 10))

    attachments = corrigendum.get("attachments") or []
    if attachments:
        story.append(Paragraph("Attachments referenced", label))
        for att in attachments:
            story.append(Paragraph(
                f"&#8226; {att.get('file_name', '')}", body,
            ))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.3,
                            color=colors.HexColor("#D2B46A")))
    story.append(Paragraph(
        "This document is auto-generated by PMC Managers and hash-chained "
        "to the audit ledger. Published amendments cannot be modified — "
        "only withdrawn with a logged reason.",
        small,
    ))

    doc.build(story)
    return buf.getvalue()
