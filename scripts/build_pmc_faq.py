from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

GREEN = RGBColor(0x16, 0x29, 0x21)
GOLD = RGBColor(0x9A, 0x7B, 0x2F)
OUT = "/app/frontend/public/downloads/PMC_Managers_FAQ.docx"
LOGO = "/app/frontend/public/downloads/pmc-logo-full-ivory.png"

QA = [
    ("1) What is PMC?", [
        "PMC Managers is a project management consultancy (PMC = Project Management Consultant) operating globally. "
        "Its platform, the Global Tender Grid, is an online e-tendering system where project owners publish tenders and "
        "suppliers anywhere in the world bid on them. Every step is recorded on a tamper-evident audit ledger:",
        ["registration and supplier checks (KYC)", "sealed technical and price bids", "committee evaluation",
         "price comparison and award", "e-signed contracts and milestones"]]),
    ("2) Where does it come from?", [
        "PMC Managers is a newly established global organisation. Its registered office is The PMC Managers Limited, "
        "Chiswick Park, 566 Chiswick High Road, London W4 5YG, United Kingdom. Offices are open in the United Kingdom "
        "and Malaysia, and offices are in the process of opening in India, the United States and Kazakhstan. "
        "The platform is open to buyers and suppliers in every country."]),
    ("3) How does PMC compare to Google, Amazon, Shopee or Alibaba?", [
        "It is a different kind of service:",
        ["Google helps you find things. PMC runs the formal tender itself, from notice to signed contract.",
         "Amazon and Shopee sell finished products at fixed prices to anyone. PMC handles projects, works, services and "
         "bulk supply: buyers set requirements and qualified suppliers compete with sealed bids.",
         "Alibaba is the closest comparison, because it is business-to-business sourcing, but Alibaba deals are negotiated "
         "privately. PMC adds a formal, auditable process: sealed envelopes, deadlines fixed to server time, evaluation "
         "committees, a deposit (EMD) held in escrow, a challenge and appeal route, and a hash-chained record that "
         "auditors and lenders can check."],
        "In short, it is a procurement and tender platform for projects, not a shop or a search engine."]),
    ("4) Who is the target audience?", [
        ["Buyers: governments and public bodies, development and infrastructure programmes, institutions (hospitals, "
         "universities), and private companies or EPC (engineering, procurement and construction) contractors running "
         "large purchases.",
         "Suppliers: contractors, manufacturers, distributors, consultants and service providers that want international tenders."]]),
    ("5) Who is supposed to participate?", [
        ["Buyers and issuers, who publish tenders.",
         "Suppliers, who register, complete KYC and bid. Any verified supplier can bid on public tenders; private tenders are by invitation.",
         "Evaluation committees and external advisers, who score bids.",
         "Escrow institutions and banks, who hold and release deposits.",
         "Partners, who bring suppliers onto the platform and earn commission.",
         "PMC staff and admins, who run the desk."]]),
    ("6) What benefit do I get if I subscribe?", [
        "For suppliers:",
        ["one KYC check reused on every bid", "alerts for tenders in your categories",
         "access to bid on public tenders worldwide", "sealed bids, so nobody sees your price early",
         "deposit (EMD) paid by escrow or bank guarantee",
         "a debrief after every award (your score and how your price compared with the lowest bid)",
         "e-signature and contract tracking", "the option to add more categories and Data Intel market insights"],
        "For buyers:",
        ["an AI tender builder", "committees with quorum rules", "price comparison and anomaly checks",
         "escrowed deposits", "a full audit trail"],
        "Pricing: subscription and fee pricing is not yet finalised. Please contact tenders@pmcmanagers.com for current terms."]),
    ("7) What area does PMC cover?", [
        ["Geography: global. Buyers and suppliers can join from any country. Offices are open in the United Kingdom and "
         "Malaysia, with India, the United States and Kazakhstan opening.",
         "Sectors: all goods, works and services, classified with the full UNSPSC product and service code list. Examples "
         "include construction and civil works, medical, education, energy (solar, wind, biomass), IT and utilities."]]),
    ("8) Is auction available on PMC?", [
        "Yes. The platform has live reverse auctions, where suppliers bid prices down in real time, alongside standard "
        "sealed tenders, RFPs and RFQs."]),
    ("9) Is PMC in the area of AI or SI (synthetic intelligence)?", [
        "PMC uses AI as a tool. It drafts tenders from project reports, reviews supporting documents, flags unusual bids, "
        "and powers the \u201cAsk PMC\u201d assistant. Decisions stay with people: committees score and award, and every AI "
        "output is recorded. \u201cSynthetic intelligence\u201d is not a separate category PMC claims, so the accurate "
        "description is AI-assisted procurement."]),
    ("10) What is PMC Managers\u2019 track record?", [
        "PMC Managers is a new company. Our first programmes are being onboarded now, and verified results (tenders run, "
        "suppliers registered, programmes managed) will be published here as they are completed. What we offer from day one "
        "is a process that can be checked: every tender, bid, evaluation and award is recorded on a tamper-evident audit "
        "ledger that buyers, auditors and lenders can verify."]),
]


def para(doc, text, size=11, bold=False, color=None, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic or "[placeholder" in text
    if color:
        r.font.color.rgb = color
    p.paragraph_format.space_after = Pt(6)
    return p


def main():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(0.9)
    doc.add_picture(LOGO, width=Inches(2.8))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.LEFT
    para(doc, "Frequently asked questions", 22, True, GREEN)
    para(doc, "PMC Managers Limited \u00b7 Global Tender Grid \u00b7 www.pmcmanagers.com \u00b7 tenders@pmcmanagers.com", 10, color=GOLD)
    para(doc, "Registered office: Chiswick Park, 566 Chiswick High Road, London W4 5YG, United Kingdom", 10, color=GOLD)
    for q, body in QA:
        h = para(doc, q, 14, True, GREEN)
        h.paragraph_format.space_before = Pt(12)
        for item in body:
            if isinstance(item, list):
                for b in item:
                    p = doc.add_paragraph(b, style="List Bullet")
                    p.paragraph_format.space_after = Pt(2)
            else:
                para(doc, item)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
