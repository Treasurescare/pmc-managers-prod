"""PMC v61 process-flow and data-flow diagram pack (PDF + one PNG per diagram)."""
import os
import sys

import fitz
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

sys.path.insert(0, "/app/scripts")
from build_manuals import CREAM, D, GOLD, GREEN, H2, NAVY, SM, B, arrow, box, data_flow, footer, link, process_flow  # noqa: E402

EXT, PRC, STO, AUTO = colors.HexColor("#EFE7D2"), colors.HexColor("#E8F1EC"), colors.HexColor("#F4F4F4"), colors.HexColor("#E8F1EC")


def lanes_drawing(W, lanes, spec, flows, col_w=98, bw=80, bh=40):
    d = Drawing(W, len(lanes) * 100)
    ys = {}
    for i, (k, name) in enumerate(lanes):
        y = (len(lanes) - 1 - i) * 100
        ys[k] = y
        d.add(Rect(0, y, W, 96, fillColor=colors.HexColor("#FBF8F0") if i % 2 == 0 else colors.white, strokeColor=colors.HexColor("#DDD5C2")))
        d.add(String(6, y + 84, name.upper(), fontSize=7, fontName="Helvetica-Bold", fillColor=GOLD))
    R = {}
    for k, (col, ln, t) in spec.items():
        R[k] = (14 + col * col_w + 20, ys[ln] + 26, bw, bh)
        box(d, *R[k], t, fill=AUTO if ln == "Y" else CREAM)
    for a, b_, lab in flows:
        link(d, R[a], R[b_], lab)
    return d


def marketplace_process():
    lanes = [("S", "Supplier (seller)"), ("A", "PMC admin"), ("Y", "System"), ("B", "Verified buyer"), ("E", "Payments")]
    spec = {"list": (0, "S", "Add product /\nAI catalogue"), "draft": (1, "S", "Submit\ndraft"), "appr": (2, "A", "Approve or\nreject (bulk)"),
            "live": (3, "Y", "Listing live\n+ category alerts"), "watch": (3, "B", "Save to\nwatchlist"), "bid": (4, "B", "Bid / offer /\nbuy now"),
            "remind": (4, "Y", "Outbid + 1h\nclosing alerts"), "order": (5, "Y", "Order created\n(win / accept)"), "pay": (6, "B", "Pay securely"),
            "paid": (6, "E", "Payment\nreceived"), "ship": (7, "S", "Mark dispatched\n/ delivered"), "recv": (8, "B", "I received it"),
            "payout": (8, "A", "Record seller\npayout (net of fee)")}
    flows = [("list", "draft", ""), ("draft", "appr", "pending"), ("appr", "live", "approved"), ("live", "watch", ""), ("live", "bid", ""),
             ("bid", "remind", ""), ("bid", "order", "close / accept"), ("order", "pay", "notify"), ("pay", "paid", ""), ("paid", "ship", "notify seller"),
             ("ship", "recv", "notify"), ("recv", "payout", "")]
    return lanes_drawing(900, lanes, spec, flows)


def buyer_onboarding():
    lanes = [("B", "Buyer"), ("Y", "System"), ("A", "PMC admin"), ("O", "Buyer org main user")]
    spec = {"reg": (0, "B", "Register free\n(name, mobile,\ncountry, city)"), "mail": (1, "Y", "Email confirm\nlink (3 days)"), "conf": (2, "B", "Confirm email"),
            "queue": (3, "Y", "Application in\nadmin queue"), "appr": (4, "A", "Approve\nbuyer"), "add": (3, "A", "\u2014 or \u2014\nadmin adds\nbuyer directly"),
            "org": (5, "Y", "Buyer org\ncreated + notified"), "inv": (6, "O", "Invite\ncolleague"), "ok": (7, "A", "Approve\ninvite"),
            "link": (8, "Y", "Sign-in link\nemailed (7 days)")}
    flows = [("reg", "mail", ""), ("mail", "conf", ""), ("conf", "queue", ""), ("queue", "appr", ""), ("appr", "org", "verified"),
             ("add", "org", "direct"), ("org", "inv", ""), ("inv", "ok", "pending"), ("ok", "link", "")]
    d = lanes_drawing(900, lanes, spec, flows)
    return d


def supplier_onboarding():
    lanes = [("S", "Supplier"), ("Y", "System"), ("A", "PMC admin"), ("P", "Partner (optional)")]
    spec = {"ref": (0, "P", "Refer supplier\n(partner link)"), "reg": (1, "S", "Register\n(~15 min)"), "kyc": (2, "S", "Company + KYC\ndocuments"),
            "chk": (3, "Y", "Checks +\nadmin queue"), "rev": (4, "A", "Review KYC"), "ok": (5, "Y", "Approved \u2192\nportal unlocked"),
            "cat": (6, "S", "Categories +\nalerts"), "bid": (7, "S", "Bid on tenders\n/ sell products"), "com": (8, "P", "Commission\nstatement")}
    flows = [("ref", "reg", "referral"), ("reg", "kyc", ""), ("kyc", "chk", ""), ("chk", "rev", ""), ("rev", "ok", "approve"), ("ok", "cat", ""),
             ("cat", "bid", ""), ("bid", "com", "")]
    return lanes_drawing(900, lanes, spec, flows)


def marketplace_dfd():
    W, H = 960, 470
    d = Drawing(W, H)
    R = {}

    def put(k, x, y, w, h, t, fill, shape="rect", fs=7.5):
        R[k] = (x, y, w, h)
        box(d, x, y, w, h, t, fill=fill, shape=shape, fs=fs)
    put("sup", 10, 380, 95, 44, "Supplier", EXT, "ext"); put("buy", 855, 380, 95, 44, "Verified buyer", EXT, "ext")
    put("adm", 10, 160, 95, 44, "PMC admin", EXT, "ext"); put("ai", 140, 40, 105, 40, "AI (catalogue\nreader)", EXT, "ext")
    put("stripe", 855, 250, 95, 44, "Payment\nprovider", EXT, "ext"); put("mail", 855, 40, 95, 40, "Email service", EXT, "ext")
    put("p1", 140, 380, 105, 44, "M1 Listings &\ncatalogue import", PRC); put("p2", 140, 160, 105, 44, "M2 Approval &\nfees", PRC)
    put("p3", 430, 380, 105, 44, "M3 Bidding,\noffers, buy now", PRC); put("p4", 700, 380, 105, 44, "M4 Buyer portal\n& watchlist", PRC)
    put("p5", 430, 160, 105, 44, "M5 Orders &\npayments", PRC); put("p6", 700, 160, 105, 44, "M6 Delivery &\npayouts", PRC)
    put("p7", 430, 40, 105, 40, "M7 Notifications\n& reminders", PRC)
    put("d1", 280, 300, 125, 26, "D6 mkt_listings / media", STO, "store", 7); put("d2", 570, 300, 110, 26, "D7 mkt_bids", STO, "store", 7)
    put("d3", 570, 250, 110, 26, "D8 mkt_watch", STO, "store", 7); put("d4", 280, 250, 125, 26, "D9 mkt_orders", STO, "store", 7)
    put("d5", 640, 100, 140, 26, "D10 notifications", STO, "store", 7); put("d6", 10, 290, 110, 26, "D11 buyers / tenants", STO, "store", 7)
    G = GREEN
    for a, b_, lab in [("sup", "p1", "products, catalogue PDF"), ("p1", "ai", "pages"), ("p1", "d1", "draft listings"), ("adm", "p2", "approve, fee"),
                       ("d1", "p2", "pending"), ("p2", "d1", "live"), ("buy", "p4", "save, profile"), ("p4", "d3", "watch"), ("p4", "p3", "bid / offer"),
                       ("p3", "d2", "bids"), ("p3", "p5", "win / accept"), ("p5", "d4", "order"), ("p5", "stripe", "checkout"), ("p6", "d4", "delivery status"),
                       ("sup", "p3", "accept offer"), ("p5", "p6", "paid"), ("p7", "mail", "emails"), ("p7", "d5", "bell items"), ("adm", "d6", "add / approve buyer")]:
        link(d, R[a], R[b_], lab, G)
    d.add(Rect(10, 4, 940, 22, fillColor=STO, strokeColor=NAVY, strokeWidth=0.6))
    d.add(String(480, 11, "D5 Audit ledger \u2014 approvals, orders, payouts, team changes and password changes are recorded here", fontSize=7.5, fontName="Helvetica-Bold", textAnchor="middle", fillColor=NAVY))
    return d


def context_dfd():
    W, H = 900, 420
    d = Drawing(W, H)
    box(d, 360, 170, 180, 80, "PMC Global\nTender Grid\n(web app + API)", fill=PRC, fs=10)
    ents = [("Suppliers", 30, 330, "KYC, bids, products", "notices, results, orders"), ("Buyers / tender owners", 30, 170, "tenders, bids, payments", "results, deliveries"),
            ("Partners", 30, 20, "referrals, bank", "commission statements"), ("Committee & staff", 720, 330, "signatures, decisions", "sealed bids after opening"),
            ("Escrow banks", 720, 170, "EMD / release confirm", "dual-signed instructions"), ("AI + email + payments", 720, 20, "AI findings, payment status", "documents, emails, checkout")]
    for name, x, y, inn, out in ents:
        box(d, x, y, 150, 60, name, fill=EXT, shape="ext", fs=9)
        cx, cy = (x + 150, y + 30) if x < 400 else (x, y + 30)
        tx, ty = (360, 210) if x < 400 else (540, 210)
        arrow(d, cx, cy + 6, tx, ty + 6, inn, GREEN)
        arrow(d, tx, ty - 6, cx, cy - 6, out, NAVY)
    return d


DIAGRAMS = [
    ("pmc-flow-1-tender-process", "Process flow 1 \u2014 Tender lifecycle (supplier \u2192 award \u2192 escrow)", process_flow,
     ["Lanes show who acts. Green boxes are automatic (system or AI). Bids stay sealed until the committee signs each opening.",
      "A bid qualifies if it meets every mandatory criterion and the minimum number of optional ones; AI only flags proofs, the committee decides.",
      "Price opening waits until every proof is decided; L1 runs automatically; award needs certifier, legal and accounting clearance."]),
    ("pmc-flow-2-supplier-onboarding", "Process flow 2 \u2014 Supplier onboarding", supplier_onboarding,
     ["Suppliers register free in about 15 minutes; KYC is reviewed by PMC before bidding or selling unlocks.", "Partners earn commission on suppliers they refer."]),
    ("pmc-flow-3-buyer-onboarding", "Process flow 3 \u2014 Buyer onboarding & team", buyer_onboarding,
     ["Self-registered buyers confirm their email, then PMC approves; only verified buyers can bid or buy.",
      "PMC can also add a buyer directly (sign-in emailed). Colleagues invited by the main buyer need PMC approval; removal is immediate."]),
    ("pmc-flow-4-marketplace", "Process flow 4 \u2014 Supplier marketplace (list \u2192 approve \u2192 sell \u2192 deliver \u2192 payout)", marketplace_process,
     ["Every listing is approved by PMC (one by one or in bulk). Sale modes: timed auction, best offer by deadline, fixed price.",
      "Buyers get outbid alerts and a reminder about an hour before a watched auction closes. PMC pays the seller net of the sale fee."]),
    ("pmc-dfd-0-context", "Data flow \u2014 Level 0 (context)", context_dfd,
     ["One system, six groups of outside parties. Green arrows: data in; navy arrows: data out."]),
    ("pmc-dfd-1-tendering", "Data flow \u2014 Level 1: tendering", data_flow,
     ["External entities (beige), processes (green), data stores (grey).", "Proof files go to the AI only after the technical opening, for qualified bids only."]),
    ("pmc-dfd-2-marketplace", "Data flow \u2014 Level 1: marketplace & buyer portal", marketplace_dfd,
     ["Catalogue pages go to the AI only to propose product drafts; the supplier chooses what to keep.",
      "Card details are handled by the payment provider; PMC stores only the order and payment status."]),
]


def render(fn):
    dr = fn()
    k = min(760 / dr.width, 400 / dr.height)
    dr.scale(k, k)
    dr.width, dr.height = dr.width * k, dr.height * k
    return dr


def build():
    story = [Paragraph("PMC Managers \u2014 Process flow & data flow diagrams", H2),
             Paragraph("Edition v61 (testing). Process flows show who does what and in which order; data flow diagrams show what information moves between people, processes and data stores.", B),
             Spacer(1, 4 * mm)] + [Paragraph(f"\u2022 {t}", SM) for _, t, _, _ in DIAGRAMS] + [PageBreak()]
    for i, (name, title, fn, notes) in enumerate(DIAGRAMS):
        story += [Paragraph(title, H2), render(fn), Spacer(1, 2 * mm)] + [Paragraph(f"\u2022 {n}", SM) for n in notes]
        if i < len(DIAGRAMS) - 1:
            story.append(PageBreak())
        one = f"/tmp/{name}.pdf"
        SimpleDocTemplate(one, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=8 * mm, bottomMargin=10 * mm, title=title).build(
            [Paragraph(title, H2), render(fn), Spacer(1, 2 * mm)] + [Paragraph(f"\u2022 {n}", SM) for n in notes], onFirstPage=footer)
        fitz.open(one)[0].get_pixmap(dpi=150).save(f"{D}/{name}.png")
    path = f"{D}/PMC_Process_and_Data_Flow_Diagrams.pdf"
    SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=8 * mm, bottomMargin=10 * mm,
                      title="PMC Process & Data Flow Diagrams").build(story, onFirstPage=footer, onLaterPages=footer)
    return path


if __name__ == "__main__":
    print(build(), len(fitz.open(f"{D}/PMC_Process_and_Data_Flow_Diagrams.pdf")), "pages")
    print([n for n, *_ in DIAGRAMS if os.path.exists(f"{D}/{n}.png")])
