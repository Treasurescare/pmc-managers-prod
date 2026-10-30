import base64
import os
import re

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "pmc-logo-mark-256.png")
with open(LOGO_PATH, "rb") as _f:
    _LOGO_B64 = base64.b64encode(_f.read()).decode()

_HEADER = (
    "<div style='display:flex;align-items:center;gap:10px;margin:0 0 14px;padding-bottom:10px;"
    "border-bottom:1px solid #D2B46A'>"
    f"<img src='data:image/png;base64,{_LOGO_B64}' style='width:40px;height:40px;border-radius:7px' alt='PMC Managers'/>"
    "<div style='font-family:Helvetica,Arial,sans-serif'><div style='font-size:13px;font-weight:700;color:#0F3B2E'>PMC Managers</div>"
    "<div style='font-size:8px;letter-spacing:2px;text-transform:uppercase;color:#8A6A1F'>Global Tender Board</div></div></div>"
)


def brand_html(html: str) -> str:
    """Insert the PMC logo header right after the first <body> tag."""
    return re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + _HEADER, html, count=1)


def logo_flowable():
    from reportlab.lib.units import mm
    from reportlab.platypus import Image
    img = Image(LOGO_PATH, width=14 * mm, height=14 * mm)
    img.hAlign = "LEFT"
    return img
