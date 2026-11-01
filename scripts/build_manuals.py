"""Build PMC manuals: user manual (every screen), master training manual, process flow + data flow diagrams."""
import io
import json
import os
from datetime import date

import fitz
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

D = "/app/frontend/public/downloads/manual"
S = f"{D}/screens"
SCREENS = json.load(open("/app/scripts/manual_screens.json"))
NAVY, GOLD, CREAM, GREEN = colors.HexColor("#14213D"), colors.HexColor("#B8892B"), colors.HexColor("#F6F1E4"), colors.HexColor("#1F6B4A")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=24, leading=28, alignment=0)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=NAVY, spaceBefore=6)
H3 = ParagraphStyle("h3", parent=ss["Heading3"], textColor=GOLD)
B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
SM = ParagraphStyle("sm", parent=B, fontSize=8, leading=10, textColor=colors.HexColor("#555555"))
TODAY = date.today().strftime("%d %B %Y")


def footer(c, doc):
    c.saveState()
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.grey)
    c.drawString(15 * mm, 8 * mm, f"PMC Managers \u00b7 {doc.title}")
    c.drawRightString(doc.pagesize[0] - 15 * mm, 8 * mm, f"Page {doc.page}")
    c.restoreState()


def shot(sid, w=180 * mm):
    p = f"{S}/{sid}.png"
    if not os.path.exists(p):
        return Paragraph("<i>(screenshot not available)</i>", SM)
    im = Image(p, width=w, height=w * 900 / 1440)
    t = Table([[im]], colWidths=[w + 2])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C9C2B0")), ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1)]))
    return t


def cover(title, sub):
    logo = "/app/backend/assets/pmc-logo-mark-256.png"
    out = [Spacer(1, 40 * mm)]
    if os.path.exists(logo):
        out.append(Image(logo, width=40 * mm, height=40 * mm, kind="proportional"))
    return out + [Spacer(1, 10 * mm), Paragraph(title, H1), Paragraph(sub, H3), Spacer(1, 6 * mm),
                  Paragraph(f"Version v59 \u00b7 {TODAY}", B), PageBreak()]


def build(path, title, story, size=A4):
    SimpleDocTemplate(path, pagesize=size, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title=title).build(
        story, onFirstPage=footer, onLaterPages=footer)


# ---------- diagrams ----------
def box(d, x, y, w, h, text, fill=CREAM, stroke=NAVY, fs=7.5, shape="rect"):
    if shape == "store":
        d.add(Line(x, y + h, x + w, y + h, strokeColor=stroke, strokeWidth=1.2))
        d.add(Line(x, y, x + w, y, strokeColor=stroke, strokeWidth=1.2))
        d.add(Rect(x, y, w, h, fillColor=fill, strokeColor=None))
    else:
        d.add(Rect(x, y, w, h, rx=4 if shape == "rect" else 0, ry=4 if shape == "rect" else 0, fillColor=fill, strokeColor=stroke, strokeWidth=0.9))
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        d.add(String(x + w / 2, y + h / 2 + (len(lines) / 2 - i - 0.75) * (fs + 1.5), ln, fontSize=fs, fontName="Helvetica-Bold" if i == 0 else "Helvetica",
                     textAnchor="middle", fillColor=NAVY))


def arrow(d, x1, y1, x2, y2, label="", col=NAVY, pts=None):
    import math
    path = pts or [(x1, y1), (x2, y2)]
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        d.add(Line(ax, ay, bx, by, strokeColor=col, strokeWidth=0.9))
    (ax, ay), (bx, by) = path[-2], path[-1]
    a = math.atan2(by - ay, bx - ax)
    d.add(Polygon([bx, by, bx - 6 * math.cos(a - 0.4), by - 6 * math.sin(a - 0.4), bx - 6 * math.cos(a + 0.4), by - 6 * math.sin(a + 0.4)], fillColor=col, strokeColor=col))
    if label:
        i = max(0, len(path) // 2 - 1)
        (ax, ay), (bx, by) = path[i], path[i + 1]
        mx, my = (ax + bx) / 2, (ay + by) / 2
        w = len(label) * 3.1 + 6
        d.add(Rect(mx - w / 2, my - 3, w, 9, fillColor=colors.white, strokeColor=None))
        d.add(String(mx, my, label, fontSize=6, textAnchor="middle", fillColor=colors.HexColor("#333333")))


def link(d, A, B, label="", col=NAVY):
    ax, ay, aw, ah = A
    bx, by, bw, bh = B
    dx, dy = (bx + bw / 2) - (ax + aw / 2), (by + bh / 2) - (ay + ah / 2)
    if abs(dx) >= abs(dy):
        s = (ax + aw, ay + ah / 2) if dx > 0 else (ax, ay + ah / 2)
        e = (bx, by + bh / 2) if dx > 0 else (bx + bw, by + bh / 2)
    else:
        s = (ax + aw / 2, ay + ah) if dy > 0 else (ax + aw / 2, ay)
        e = (bx + bw / 2, by) if dy > 0 else (bx + bw / 2, by + bh)
    arrow(d, *s, *e, label, col)


def process_flow():
    W, H = 900, 500
    d = Drawing(W, H)
    lanes = {"S": ("Supplier", 400), "A": ("PMC admin / buyer", 300), "Y": ("System + AI", 200), "C": ("Evaluation committee", 100), "E": ("Escrow & accounts", 0)}
    for i, (name, y) in enumerate(lanes.values()):
        d.add(Rect(0, y, W, 96, fillColor=colors.HexColor("#FBF8F0") if i % 2 == 0 else colors.white, strokeColor=colors.HexColor("#DDD5C2")))
        d.add(String(6, y + 84, name.upper(), fontSize=7, fontName="Helvetica-Bold", fillColor=GOLD))
    bw, bh = 78, 40
    spec = {"reg": (0, "S", "Register\n+ KYC"), "kyc": (0, "A", "Approve\nKYC"), "build": (1, "A", "Build tender\n(DPR AI / master)"),
            "crit": (2, "A", "Set criteria\nmandatory/optional"), "pub": (3, "A", "Publish\n(checklist)"), "bid": (4, "S", "Sealed bid\nanswers + proofs"),
            "emd": (4, "E", "EMD held\nin escrow"), "open": (5, "C", "Members sign\ntech. opening"), "qual": (5, "Y", "Auto check\nvs criteria"),
            "notice": (6, "S", "Result notice\n(email + portal)"), "ai": (6, "Y", "AI reads\neach proof"), "rev": (6, "C", "Every member\naccept/reject"),
            "price": (7, "C", "Price opening\n(qualified only)"), "l1": (7, "Y", "Auto L1\nranking"), "award": (8, "C", "Award to L1\n(sign-off)"),
            "pay": (8, "E", "Dual-signed\nrelease/payouts")}
    R = {}
    for k, (col, ln, t) in spec.items():
        R[k] = (14 + col * 98 + 20, lanes[ln][1] + 26, bw, bh)
        box(d, *R[k], t, fill=colors.HexColor("#E8F1EC") if ln == "Y" else CREAM)
    for a, b_, lab in [("reg", "kyc", "KYC docs"), ("kyc", "build", ""), ("build", "crit", ""), ("crit", "pub", ""), ("pub", "bid", "live"),
                       ("bid", "emd", "deposit"), ("bid", "open", "deadline"), ("open", "qual", "unseal"), ("qual", "ai", "qualified"),
                       ("ai", "rev", "findings"), ("qual", "notice", "result"), ("rev", "price", "all decided"), ("price", "l1", ""),
                       ("l1", "award", "L1"), ("award", "pay", "")]:
        link(d, R[a], R[b_], lab)
    return d


def data_flow():
    W, H = 960, 520
    d = Drawing(W, H)
    EXT, PRC, STO = colors.HexColor("#EFE7D2"), colors.HexColor("#E8F1EC"), colors.HexColor("#F4F4F4")
    R = {}
    def put(k, x, y, w, h, t, fill, shape="rect", fs=7.5):
        R[k] = (x, y, w, h)
        box(d, x, y, w, h, t, fill=fill, shape=shape, fs=fs)
    put("sup", 10, 420, 95, 44, "Supplier", EXT, "ext"); put("adm", 10, 200, 95, 44, "Admin / buyer", EXT, "ext")
    put("par", 10, 70, 95, 44, "Partner", EXT, "ext"); put("com", 855, 420, 95, 44, "Committee", EXT, "ext")
    put("gem", 855, 200, 95, 44, "Gemini AI", EXT, "ext"); put("bank", 280, 140, 105, 40, "Escrow bank", EXT, "ext")
    put("p1", 140, 420, 105, 44, "1 Registration\n& KYC", PRC); put("p2", 140, 200, 105, 44, "2 Tender &\ncriteria", PRC)
    put("p3", 420, 420, 105, 44, "3 Sealed\nbidding", PRC); put("p4", 700, 420, 105, 44, "4 Opening &\nqualification", PRC)
    put("p5", 700, 200, 105, 44, "5 Proof review", PRC); put("p6", 700, 70, 105, 44, "6 Price, L1\n& award", PRC)
    put("p7", 420, 70, 105, 44, "7 Escrow\n& payouts", PRC); put("p8", 140, 70, 105, 44, "8 Partner\nonboarding", PRC)
    put("d1", 140, 330, 105, 26, "D1 Vendors / KYC", STO, "store", 7); put("d2", 280, 270, 120, 26, "D2 Notices + criteria", STO, "store", 7)
    put("d3", 560, 330, 120, 26, "D3 Bids (encrypted)", STO, "store", 7); put("d4", 560, 260, 120, 26, "D4 Proof files (encrypted)", STO, "store", 7)
    G = GREEN
    for a, b_, lab in [("sup", "p1", "company, KYC docs"), ("p1", "d1", "KYC status"), ("adm", "p2", "DPR, criteria"), ("p2", "d2", "tender + criteria"),
                       ("d2", "p3", "live tender"), ("p3", "d3", "answers, price"), ("p3", "d4", "proof files"), ("d3", "p4", "after deadline"),
                       ("com", "p4", "e-signatures"), ("p4", "p5", "qualified bids"), ("d4", "p5", "proof files"), ("com", "p5", "accept / reject"),
                       ("p5", "p6", "all proofs decided"), ("p6", "p7", "award"), ("p7", "bank", "release instructions"), ("par", "p8", "profile, bank, agreement")]:
        link(d, R[a], R[b_], lab, G)
    x, y, w, h = R["p5"]
    gx, gy, _, _ = R["gem"]
    arrow(d, x + w, y + 30, gx, gy + 30, "proof files", G)
    arrow(d, gx, gy + 14, x + w, y + 14, "findings", G)
    sx, sy, sw, sh = R["sup"]
    px, py, pw, ph = R["p4"]
    arrow(d, 0, 0, 0, 0, "result notices", G, pts=[(px + pw / 2, py + ph), (px + pw / 2, 495), (sx + sw / 2, 495), (sx + sw / 2, sy + sh)])
    arrow(d, 0, 0, 0, 0, "sealed bid: answers, proofs, price", G, pts=[(sx + sw / 2, sy), (sx + sw / 2, 395), (472, 395), (472, 420)])
    d.add(Rect(10, 8, 940, 30, fillColor=STO, strokeColor=NAVY, strokeWidth=0.6))
    d.add(String(480, 19, "D5 Audit ledger \u2014 every process above writes a tamper-evident record here", fontSize=8, fontName="Helvetica-Bold", textAnchor="middle", fillColor=NAVY))
    return d


def diagram_pdf(name, title, drawing, notes):
    path = f"{D}/{name}.pdf"
    k = min(760 / drawing.width, 430 / drawing.height)
    drawing.scale(k, k)
    drawing.width, drawing.height = drawing.width * k, drawing.height * k
    story = [Paragraph(title, H2), drawing, Spacer(1, 2 * mm)] + [Paragraph(f"\u2022 {n}", SM) for n in notes]
    SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=8 * mm, bottomMargin=10 * mm, title=title).build(
        story, onFirstPage=footer, onLaterPages=footer)
    pg = fitz.open(path)[0]
    pg.get_pixmap(dpi=150).save(f"{D}/{name}.png")
    return path


# ---------- user manual ----------
def user_manual():
    st = cover("PMC Managers \u2014 User Manual", "Every screen, from the public website to award and payout")
    st += [Paragraph("How to use this manual", H2),
           Paragraph("The manual follows the platform portal by portal: Public website, Admin console, Supplier portal, Partner portal and Staff portal. "
                     "Each page shows the real screen, what it is for and the main actions. For a role-based, step-by-step course see the PMC Master Training Manual; "
                     "for the big picture see the Process Flow and Data Flow diagrams.", B), Spacer(1, 4 * mm), Paragraph("Contents", H2)]
    sec = None
    rows = []
    for s in SCREENS:
        if s["section"] != sec:
            sec = s["section"]
            rows.append([Paragraph(f"<b>{sec}</b>", B), ""])
        rows.append([Paragraph(f"&nbsp;&nbsp;&nbsp;{s['title']}", B), Paragraph(s["path"], SM)])
    t = Table(rows, colWidths=[110 * mm, 70 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.2, colors.HexColor("#E3DCCB"))]))
    st += [t, PageBreak()]
    sec = None
    for s in SCREENS:
        if s["section"] != sec:
            if sec:
                st.append(PageBreak())
            sec = s["section"]
            st += [Paragraph(sec, H1), Spacer(1, 3 * mm)]
        acts = "".join(f"\u2022 {a}<br/>" for a in s["actions"])
        st.append(KeepTogether([Paragraph(s["title"], H2), Paragraph(f"Screen: <font face='Courier'>{s['path']}</font>", SM), Spacer(1, 2 * mm), shot(s["id"]),
                                Spacer(1, 2 * mm), Paragraph(s["desc"], B), Paragraph(f"<b>Main actions</b><br/>{acts}", B), Spacer(1, 6 * mm)]))
    st += [PageBreak(), Paragraph("Mobile view", H2), Paragraph("Every portal works on phones; menus collapse into the top bar.", B),
           Image(f"{S}/zz-mobile-home.png", width=70 * mm, height=70 * mm * 844 / 390) if os.path.exists(f"{S}/zz-mobile-home.png") else Spacer(1, 1)]
    build(f"{D}/pmc-user-manual.pdf", "User Manual", st)


# ---------- training manual ----------
MODULES = [
    ("Module 1 \u2014 Getting started (everyone)", "All users", ["p01-home", "p06-login"], [
        "Go to the PMC website and click Sign in.", "Choose your role (Supplier, PMC staff, Admin, Escrow institution or Partner).",
        "Enter your email and password. Use Forgot password if needed.", "You land on your own portal. Your avatar menu (top right) has profile and sign-out."],
     ["Sign in to your portal", "Find your avatar menu and sign out"]),
    ("Module 2 \u2014 Supplier onboarding and KYC", "Supplier, Admin", ["p07-register", "a09-registrations", "s07-company"], [
        "Supplier registers with company details and verifies the email.", "Supplier uploads KYC documents under Company profile.",
        "Admin opens Registrations, checks the documents and approves, asks for changes or rejects with a reason.", "Only verified suppliers can bid."],
     ["Approve one test registration", "Ask a supplier for a missing document"]),
    ("Module 3 \u2014 Building a tender", "Admin / buyer", ["a04-builder", "a02-notices"], [
        "Open Tender builder. Choose AI generate from DPR (upload the project report) or clone a master template.",
        "Review every section the AI drafted; fix anything highlighted.", "Click Create notice. The notice is saved as a draft and the Criteria window opens."],
     ["Generate a tender from a DPR", "Create a notice from the draft"]),
    ("Module 4 \u2014 Setting criteria", "Admin / buyer", ["a03-criteria", "a05-crit-master"], [
        "In the Criteria window click + Add from master and pick criteria or a whole set (e.g. Standard construction). Add one-off criteria with + Blank criterion.",
        "For each criterion choose Must pass (pass/fail) or Scored, the rule (e.g. at least 500,000 GBP), proof asked for and whether proof is mandatory.",
        "Tick Mandatory for criteria every bidder must meet. Leave it unticked for optional ones and set 'at least N of the optional criteria'.",
        "Choose how the winner is picked: Lowest price (L1) or Weighted. Tick Accept consortium bids if teams may bid.",
        "Click Save criteria, then Check against tender document (AI). Save useful combinations as a set for next time."],
     ["Build a criteria set in Criteria master", "Set 3 mandatory + 2 optional criteria with 'at least 1 optional'"]),
    ("Module 5 \u2014 Publishing", "Admin", ["a02-notices"], [
        "Each draft shows 'Ready to publish?': main document attached, deadline in the future, at least one must-pass criterion.",
        "Fix anything not ticked (Add now opens the criteria). When all three are ticked, click Publish in the checklist.",
        "Live tenders with no bids can still have their criteria changed; once a bid arrives they lock. Use a corrigendum for other changes."],
     ["Publish a draft", "Issue a corrigendum"]),
    ("Module 6 \u2014 Bidding (supplier)", "Supplier", ["s02-tenders", "s03-bid", "s04-mybids"], [
        "Open the tender and click Bid. Read each criterion: Mandatory items must be answered with proof; optional items count towards the minimum.",
        "Attach proofs (PDFs or images read best). Enter the price and pay the EMD if required.",
        "Submit. Answers, proofs and price are encrypted \u2014 nobody can see them before the committee opens the bids.",
        "After the technical opening you get a result notice by email and under My bids."],
     ["Submit a practice bid on a demo tender", "Find your result notice"]),
    ("Module 7 \u2014 Consortium bids", "Supplier, Admin", ["s05-consortia"], [
        "The lead supplier chooses Bid as consortium lead, invites registered suppliers and sets shares (total 100%).",
        "Members accept and everyone signs the consortium agreement. Criteria are checked for the lead, combined or every member as set per criterion.",
        "On award, escrow creates a payment instruction per member; each member sees its payout and bank reference in the portal."],
     ["Form a 3-member consortium on a demo tender"]),
    ("Module 8 \u2014 Opening, AI proof review and doubts", "Committee", ["a11-bidding", "u01-staff"], [
        "After the deadline and opening date every committee member signs the technical opening (Bidding ops or Staff portal).",
        "The system checks every bid against the criteria and notifies suppliers. Qualified bids go to proof review.",
        "The AI reads each must-pass proof and reports Matches / Does not match / Unclear with the figure it found.",
        "Every committee member clicks Accept or Reject on each proof (comment required to reject). All must accept; one rejection fails that proof.",
        "Raise a doubt on any item if needed and resolve it with a note. Download the proof check report (PDF) for the tender file."],
     ["Review the proofs of one bid", "Download the proof check report"]),
    ("Module 9 \u2014 Price opening, L1 and award", "Committee, Admin", ["a11-bidding", "a14-l1", "a13-evaluation", "a15-awards"], [
        "When every proof is decided, all members sign the price opening. Only qualified bids' prices are opened.",
        "L1 ranking runs automatically and appears on the opening card.", "For L1 tenders a committee member clicks Award to L1, adds a note and confirms. "
        "The L1 bid must have certifier, legal and accounting clearances first.",
        "For weighted tenders use Evaluation > Award recommendation report.", "Award letters and contracts appear under Awards."],
     ["Award a demo tender to L1"]),
    ("Module 10 \u2014 Escrow and payouts", "Escrow officer, Accounts", ["a12-escrow"], [
        "EMDs and award payments are held in escrow. Releases need two signatures.",
        "For consortium awards, record each member's bank transfer reference and mark it paid. Download the payout report for audit."],
     ["Record a member payout reference"]),
    ("Module 11 \u2014 Partners", "Partner, Admin", ["t01-partner", "a10-partners"], [
        "Admin invites a partner; the partner completes four sections (profile, banking, documents, agreement) \u2014 the progress bar shows how far they are.",
        "Reminder emails go out 3 and 7 days after joining if unfinished. Admin can edit details in the same 5-section form and approve."],
     ["Invite and approve a partner"]),
    ("Module 12 \u2014 Monitoring, governance and audit", "Admin", ["a01-dashboard", "a21-audit", "a17-permissions"], [
        "Use the dashboard's Live tender progress to spot stalled tenders (gold dot = current step).",
        "Audit ledger records every action; Verify chain checks nothing was altered.", "Permissions controls roles and the sign-off order."],
     ["Find the oldest stalled tender", "Verify the audit chain"]),
]


def training_manual():
    st = cover("PMC Master Training Manual", "Role-based course with screenshots, steps and practice tasks")
    st += [Paragraph("Course map", H2)]
    t = Table([[Paragraph("<b>Module</b>", B), Paragraph("<b>Who</b>", B)]] + [[Paragraph(m[0], B), Paragraph(m[1], B)] for m in MODULES], colWidths=[125 * mm, 55 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D8D0BD")), ("BACKGROUND", (0, 0), (-1, 0), CREAM)]))
    st += [t, Spacer(1, 4 * mm), Paragraph("Practise on the preview (demo) site with the demo accounts your PMC administrator gives you. Never practise on live tenders.", B),
           Spacer(1, 4 * mm), Image(f"{D}/pmc-process-flow.png", width=180 * mm, height=180 * mm * 520 / 800 * 0.92) if os.path.exists(f"{D}/pmc-process-flow.png") else Spacer(1, 1),
           PageBreak()]
    for title, who, shots, steps, tasks in MODULES:
        st += [Paragraph(title, H1), Paragraph(f"For: {who}", H3)]
        st.append(Paragraph("<b>Steps</b><br/>" + "".join(f"{i}. {s}<br/>" for i, s in enumerate(steps, 1)), B))
        st.append(Spacer(1, 3 * mm))
        for sid in shots:
            s = next((x for x in SCREENS if x["id"] == sid), None)
            if s:
                st.append(KeepTogether([Paragraph(s["title"], H2), shot(sid, 170 * mm), Spacer(1, 3 * mm)]))
        st.append(Paragraph("<b>Practice tasks</b><br/>" + "".join(f"\u2610 {x}<br/>" for x in tasks), B))
        st.append(PageBreak())
    st += [Paragraph("Quick reference \u2014 who does what", H1)]
    roles = [("Supplier", "Register, KYC, bid with proofs, consortium, see results and payouts"), ("Admin / buyer", "Build tenders, criteria, publish, manage suppliers and partners"),
             ("Reviewer", "Approve supplier-prepared tenders; edit criteria master"), ("Committee member", "Sign openings, review proofs, doubts, score, award"),
             ("Escrow officer / accounts", "EMD, dual-signed releases, payouts, reports"), ("Partner", "Onboard suppliers, earn commission"), ("Auditor", "Read audit ledger and reports")]
    t = Table([[Paragraph(f"<b>{a}</b>", B), Paragraph(b, B)] for a, b in roles], colWidths=[50 * mm, 130 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D8D0BD"))]))
    st.append(t)
    build(f"{D}/pmc-master-training-manual.pdf", "Master Training Manual", st)


if __name__ == "__main__":
    diagram_pdf("pmc-process-flow", "PMC tender lifecycle \u2014 process flow", process_flow(), [
        "Lanes show who acts. Green boxes are automatic (system or AI). Bids stay sealed until the committee signs each opening.",
        "A bid qualifies if it meets every mandatory criterion and at least the minimum number of optional criteria; the AI only flags proofs, the committee decides (all must accept).",
        "Price opening is blocked until every proof is decided; L1 runs automatically; award needs certifier, legal and accounting clearance."])
    diagram_pdf("pmc-data-flow", "PMC platform \u2014 data flow (level 1)", data_flow(), [
        "External entities (beige), processes (green), data stores (grey). Arrows show what data moves.",
        "Proof files are sent to the AI only after the technical opening, for qualified bids only.", "Emails (result notices, reminders) are sent by the email service from processes 4 and 8."])
    user_manual()
    training_manual()
    for f in ("pmc-user-manual", "pmc-master-training-manual"):
        print(f, len(fitz.open(f"{D}/{f}.pdf")))
