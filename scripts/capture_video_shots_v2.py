"""Video shots v2: cleaned retakes + missing screens. Usage: python capture_video_shots_v2.py '<extra.json>' '<consent_path>'"""
import asyncio
import json
import os
import re
import shutil
import sys

import fitz
import requests
from playwright.async_api import async_playwright

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
OUT = "/app/frontend/public/downloads/pmc-video-shots-v2"
PW = "Demo@Pmc2026"
X = json.loads(sys.argv[1])
CONSENT = sys.argv[2]
OPEN_BID = sys.argv[3]
INST = sys.argv[4]
cred = open("/app/memory/test_credentials.md").read().split("dmin", 1)[1]
ADMIN = (re.search(r"[\w.+-]+@[\w.-]+", cred).group(0), re.search(r"[Pp]assword[^:]*:\s*`?([^\s`]+)", cred).group(1))
HOST = BASE.split("//")[1]

CLEAN_JS = """([host]) => {
  const fixEmail = (t) => t.replace(/[\\w.+-]+@(?!demo\\.pmcmanagers\\.com)[\\w-]+(\\.[\\w-]+)+/g, 'officer@demo.pmcmanagers.com');
  const fix = (t) => fixEmail(t.split(host).join('www.pmcmanagers.com'));
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; while ((n = w.nextNode())) { const v = fix(n.nodeValue); if (v !== n.nodeValue) n.nodeValue = v; }
  document.querySelectorAll('input,textarea').forEach((i) => { if (i.value) i.value = fix(i.value); });
  const hide = (re, sel) => document.querySelectorAll(sel).forEach((el) => { if (re.test(el.textContent)) el.style.display = 'none'; });
  hide(/sakina/i, 'tr, li, [data-testid^="admin-agent-row"], [data-testid^="agent-row"]');
  const bad = /secret missing|test mode|STRIPE_API_KEY|sk_test|webhook secret/i;
  Array.from(document.querySelectorAll('div,p,section,span')).filter((el) => bad.test(el.textContent) && el.textContent.length < 600)
    .filter((el) => !Array.from(el.children).some((c) => bad.test(c.textContent) && c.textContent.length < 600 && c.tagName !== 'SPAN'))
    .forEach((el) => { el.style.display = 'none'; });
}"""


async def shot(page, name, url=None, wait=3500, full=False, before=None):
    try:
        if url:
            await page.goto(BASE + url, wait_until="domcontentloaded")
        await page.wait_for_timeout(wait)
        if before:
            await before(page)
            await page.wait_for_timeout(1500)
        await page.evaluate(CLEAN_JS, [HOST])
        await page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
        print("ok", name)
    except Exception as e:
        print("FAIL", name, str(e)[:140])


async def login(page, role, email, pw):
    await page.context.clear_cookies()
    await page.goto(f"{BASE}/login?role={role}")
    await page.wait_for_timeout(2500)
    await page.fill("[data-testid='signin-e-email']", email)
    await page.fill("[data-testid='signin-e-password']", pw)
    await page.click("[data-testid='signin-e-submit']")
    await page.wait_for_timeout(4000)


def click_text(t):
    async def f(pg):
        await pg.get_by_text(t, exact=False).first.click(timeout=8000)
    return f


def email_html():
    sys.path.insert(0, "/app/backend")
    from emails import wrap
    p = f"{OUT}/_invite.html"
    open(p, "w").write(wrap("Supplier registration invitation",
        "<p>Hello,</p><p><b>Hart Procurement Advisory (Demo)</b> (PMC partner code <b>PT-DEMO</b>) has offered to help <b>Oakline Construction (Demo)</b> register as a supplier on PMC Managers.</p>"
        "<p>Please confirm this email address and decide whether you allow this partner to fill in your registration. Nothing is sent to PMC until you review and submit it yourself. If you don't know this partner, ignore this email.</p><p>This link expires in 7 days.</p>",
        "Review & give consent", "https://www.pmcmanagers.com/supplier-invite/…"))
    return p


def record_pdf_png():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/admin/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    pdf = s.get(f"{BASE}/api/v1/bid-opening/{X['award_tender']}/record.pdf")
    if pdf.status_code != 200:
        print("FAIL record pdf", pdf.status_code, pdf.text[:100])
        return
    doc = fitz.open(stream=pdf.content, filetype="pdf")
    for i, pg in enumerate(doc):
        pg.get_pixmap(dpi=150).save(f"{OUT}/3-06-opening-record-pdf-p{i + 1}.png")
    print("ok record pdf", doc.page_count)


async def approve_ui(pg, name):
    await pg.get_by_text("Bid opening", exact=True).first.click()
    await pg.wait_for_timeout(2500)
    box = pg.locator("input[type='checkbox']").first
    if await box.count():
        await box.check()
    nm = pg.locator("input[placeholder*='name' i], input[data-testid*='signer']").first
    if await nm.count():
        await nm.fill(name)


def pick(label):
    async def f(pg):
        for sel in await pg.locator("select").all():
            opts = await sel.locator("option").all_inner_texts()
            m = next((o for o in opts if label in o), None)
            if m:
                await sel.select_option(label=m)
                return
        await pg.get_by_text(label, exact=False).first.click(timeout=8000)
    return f


async def fix_main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await (await b.new_context(viewport={"width": 1920, "height": 1080})).new_page()
        await login(page, "admin", *ADMIN)
        await shot(page, "P-04-admin-partner-detail-fee-waiver", "/admin/e/partners", full=True, before=click_text("Rao Tender"))
        async def l1(pg):
            await pick("Road resurfacing")(pg)
            await pg.wait_for_timeout(800)
            await pg.get_by_role("button", name=re.compile("L1|compar", re.I)).first.click(timeout=8000)
        await shot(page, "2-04b-l1-comparison-tender", "/admin/e/l1-award", before=l1)
        await b.close()
    shutil.make_archive(OUT, "zip", OUT)
    print("zip done")


async def fix_old():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await (await b.new_context(viewport={"width": 1920, "height": 1080})).new_page()
        await login(page, "admin", *ADMIN)
        await shot(page, "2-01b-tender-builder-draft", "/admin/e/tender-builder", before=pick("Road resurfacing"))
        await shot(page, "2-04b-l1-comparison-tender", "/admin/e/l1-award", before=pick("Road resurfacing"))
        await shot(page, "4-09-billing", "/admin/e/billing")
        await b.close()
    shutil.make_archive(OUT, "zip", OUT)
    print("zip done")


async def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await (await b.new_context(viewport={"width": 1920, "height": 1080})).new_page()
        # Partner video
        await shot(page, "P-01-partner-register", "/partner/register")
        await shot(page, "P-02-partner-join-set-password", f"/partner/join/{X['partner_join_token']}")
        await login(page, "partner", "partner@demo.pmcmanagers.com", PW)
        await shot(page, "P-05-partner-portal-suppliers", "/partner/me")
        await shot(page, "P-06-partner-wallet", None, 500, before=click_text("Commission wallet"))
        await shot(page, "P-07-partner-leaderboard", None, 500, before=click_text("Leaderboard"))
        await shot(page, "S-03-partner-filling-form-amber-banner", f"/register/resume?token={X['partner_edit_token']}&from=partner")
        # Supplier invite video
        await page.context.clear_cookies()
        await page.goto("file://" + email_html())
        await shot(page, "S-01-invitation-email", None, 800)
        await shot(page, "S-02-consent-page", CONSENT)
        await shot(page, "S-04-supplier-review-banner", f"/register/resume?token={X['supplier_review_token']}")
        await shot(page, "S-05-supplier-declarations-submit", None, 500, before=lambda pg: pg.locator("[data-testid='step-e']").click(force=True))
        # Admin screens
        await login(page, "admin", *ADMIN)
        await shot(page, "P-03-admin-partners-list", "/admin/e/partners")
        await shot(page, "P-04-admin-partner-detail-fee-waiver", None, 500, before=click_text("Anita Rao"))
        await shot(page, "3-01-admin-bid-before-opening-sealed", f"/admin/bids/{OPEN_BID}")
        await shot(page, "2-02-tenders-published", "/admin/e/notices")
        await shot(page, "2-01-tender-builder", "/admin/e/tender-builder")
        await shot(page, "2-01b-tender-builder-draft", None, 500, before=click_text("Road resurfacing"))
        await shot(page, "2-04-l1-comparison", "/admin/e/l1-award")
        await shot(page, "2-04b-l1-comparison-tender", None, 500, before=click_text("Road resurfacing"))
        await shot(page, "2-05-awards", "/admin/e/awards")
        await shot(page, "2-05b-award-documents", None, 500, before=click_text("Road resurfacing"))
        await shot(page, "4-02-supplier-management", "/admin/e/vendors")
        await shot(page, "4-02b-registrations", "/admin/e/registrations")
        await shot(page, "4-05-settings-masters", "/admin/e/masters")
        await shot(page, "4-04b-audit-ledger", "/admin/e/audit")
        await shot(page, "4-09-billing", "/admin/e/billing")
        await shot(page, "4-10-marketing", "/admin/e/marketing")
        await shot(page, "4-10b-marketing-whatsapp", None, 500, before=click_text("WhatsApp"))
        await shot(page, "4-08-partners", "/admin/e/partners")
        await shot(page, "E-02-escrow-emd-transactions", "/admin/e/escrow")
        await shot(page, "E-03-escrow-transaction-two-officers", None, 500, before=click_text("DEMO-EMD"))
        await shot(page, "E-01-escrow-institution-dashboard", f"/escrow/dashboard/{INST}")
        await shot(page, "E-04-audit-ledger-escrow", "/admin/e/audit", before=lambda pg: pg.locator("input[placeholder*='earch' i]").first.fill("escrow"))
        # Sealed bids: committee approving one by one (technical stage on DEMO-TND-OPEN)
        await login(page, "staff", "committee1@demo.pmcmanagers.com", PW)
        await shot(page, "3-02-committee-member-1-approving", "/staff", before=lambda pg: approve_ui(pg, "Priya Shah"))
        await login(page, "staff", "committee2@demo.pmcmanagers.com", PW)
        await shot(page, "3-03-committee-member-2-view", "/staff", before=click_text("Bid opening"))
        await b.close()
    record_pdf_png()
    os.remove(f"{OUT}/_invite.html")
    shutil.make_archive(OUT, "zip", OUT)
    print("zip done")


asyncio.run(fix_main() if len(sys.argv) > 5 else main())
