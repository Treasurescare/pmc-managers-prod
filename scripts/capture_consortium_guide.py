"""Consortium life-cycle guide: seeds a DEMO tender, drives the real APIs stage by stage and screenshots each screen.
Usage: python capture_consortium_guide.py run|clean"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import fitz
import requests
from bson import ObjectId
from playwright.async_api import async_playwright
from pymongo import MongoClient

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
API = f"{BASE}/api/v1"
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
OUT = "/app/frontend/public/downloads/pmc-consortium-guide"
REF = "DEMO-CONSORTIUM-2026"
TOK = "DEMO_consortium_guide_officer_link"
PW = "Demo@Pmc2026"
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
ESC = ("escrow@pmcmanagers.com", "Escrow@123")
V = {"nf": "northfield@demo.pmcmanagers.com", "bw": "brightwater@demo.pmcmanagers.com", "ks": "kestrel@demo.pmcmanagers.com"}
BANK = {"nf": ("Maybank", "KL Main", "5140-2231-8890", "MBBEMYKL"), "bw": ("CIMB Bank", "Penang", "8007-1145-0021", "CIBBMYKL"),
        "ks": ("RHB Bank", "Johor Bahru", "2620-9981-4412", "RHBBMYKL")}
SOLO = "testvendor@pmcmanagers.com"
CRIT = [
    {"id": "dgturn01", "title": "Average annual turnover (last 3 years)", "answer_type": "number", "operator": "gte", "threshold": 5000000,
     "unit": "USD", "kind": "must_pass", "consortium_rule": "lead", "proof": "Audited accounts, 3 years", "proof_required": True},
    {"id": "dgproj01", "title": "Value of similar projects completed", "answer_type": "number", "operator": "gte", "threshold": 8000000,
     "unit": "USD", "kind": "must_pass", "consortium_rule": "combined", "proof": "Completion certificates", "proof_required": False},
    {"id": "dgiso001", "title": "ISO 9001 certification", "answer_type": "yes_no", "kind": "must_pass", "consortium_rule": "each",
     "proof": "ISO certificate", "proof_required": False},
    {"id": "dgstaf01", "title": "Qualified engineers available", "answer_type": "number", "operator": "gte", "threshold": 10, "unit": "engineers",
     "kind": "scored", "max_points": 20, "scoring": "auto", "full_points_at": 30, "consortium_rule": "combined", "proof": "", "proof_required": False},
]
STEPS = []


def now(**kw):
    return (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()


def clean():
    for c in ("bids", "notices", "committees", "opening_records", "consortia"):
        DB[c].delete_many({"notice_ref": REF})
    DB.notifications.delete_many({"related_notice_ref": REF})
    DB.escrow_transactions.delete_many({"notice_ref": REF})
    DB.escrow_accounts.delete_many({"name": "DEMO Consortium Escrow Account"})
    DB.escrow_magic_tokens.delete_many({"token": TOK})
    DB.uploads.delete_many({"key": {"$regex": "DEMOGUIDE"}})
    for k, e in V.items():
        DB.vendors.update_one({"email": e, "demo_guide_bank": True},
                              {"$unset": {"bank_name": "", "bank_branch": "", "bank_account_number": "", "bank_swift": "", "demo_guide_bank": ""}})


def staff(email, pw, role):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": pw, "active_role": role})
    r.raise_for_status()
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def vendor(email):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": PW if "demo" in email else "Vendor@12345"})
    r.raise_for_status()
    if r.json().get("csrf_token"):
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def ok(r):
    if r.status_code >= 300:
        raise SystemExit(f"{r.request.method} {r.url} -> {r.status_code} {r.text[:300]}")
    return r.json()


def upload(s, name, scope="bid-docs"):
    key = f"{scope}/DEMOGUIDE{uuid.uuid4().hex[:8]}_{name}"
    ok(s.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, b"%PDF-1.4 demo", "application/pdf")}))
    return key


def vid(e):
    return str(DB.vendors.find_one({"email": e})["_id"])


def seed():
    clean()
    for k, e in V.items():
        b = BANK[k]
        DB.vendors.update_one({"email": e, "bank_account_number": {"$in": [None, ""]}},
                              {"$set": {"bank_name": b[0], "bank_branch": b[1], "bank_account_number": b[2], "bank_swift": b[3], "demo_guide_bank": True}})
        DB.vendors.update_one({"email": e, "bank_account_number": {"$exists": False}},
                              {"$set": {"bank_name": b[0], "bank_branch": b[1], "bank_account_number": b[2], "bank_swift": b[3], "demo_guide_bank": True}})
    DB.notices.insert_one({"notice_ref": REF, "title": "Design & build of district water treatment plant (DEMO)", "is_published": True,
                           "kyc_bypass": True, "category": "", "budget_amount": 12000000.0, "budget_currency": "USD",
                           "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "USD"}, "created_at": now(), "published_at": now(),
                           "submission_deadline": now(days=5), "bid_opening_date": now(days=6), "description": "DEMO tender for the consortium guide",
                           "tender_criteria": CRIT, "consortium_allowed": True, "consortium_max_members": 4, "tenant_id": "PMC-KZ-01"})
    c1 = str(DB.admin_users.find_one({"email": "committee1@demo.pmcmanagers.com"})["_id"])
    c2 = str(DB.admin_users.find_one({"email": "committee2@demo.pmcmanagers.com"})["_id"])
    DB.committees.insert_one({"notice_ref": REF, "chairperson_id": c1, "member_ids": [c2], "status": "open", "quorum": 2, "votes": [], "created_at": now()})


async def shot(page, name, title, text, url=None, wait=3500, before=None, full=False, elem=None):
    try:
        if url:
            for _ in range(3):
                try:
                    await page.goto(BASE + url, wait_until="domcontentloaded", timeout=45000)
                    break
                except Exception as e:
                    print("retry nav", str(e)[:80])
                    await page.wait_for_timeout(3000)
        await page.wait_for_timeout(wait)
        if before:
            await before(page)
            await page.wait_for_timeout(1500)
        await page.evaluate("""([h]) => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
          while ((n = w.nextNode())) { if (n.nodeValue.includes(h)) n.nodeValue = n.nodeValue.split(h).join('www.pmcmanagers.com'); }
          document.querySelectorAll('[class*="ChatWidget"], button').forEach((b) => { if (/^(Ask PMC|Help)$/.test((b.textContent||'').trim())) b.style.display='none'; }); }""",
                            [BASE.split("//")[1]])
        if elem:
            el = page.locator(elem).first
            await el.scroll_into_view_if_needed(timeout=8000)
            await page.wait_for_timeout(800)
            await el.screenshot(path=f"{OUT}/{name}.png")
        else:
            await page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
        STEPS.append((name, title, text))
        print("ok", name)
    except Exception as e:
        print("FAIL", name, str(e)[:160])


async def login(page, role, email, pw):
    await page.context.clear_cookies()
    for _ in range(3):
        try:
            await page.goto(f"{BASE}/login?role={role}", wait_until="domcontentloaded", timeout=45000)
            break
        except Exception as e:
            print("retry login nav", str(e)[:80])
            await page.wait_for_timeout(3000)
    await page.wait_for_timeout(2500)
    await page.fill("[data-testid='signin-e-email']", email)
    await page.fill("[data-testid='signin-e-password']", pw)
    await page.click("[data-testid='signin-e-submit']")
    await page.wait_for_timeout(4500)


def click(sel):
    async def f(pg):
        await pg.click(sel, timeout=8000)
    return f


def search(sel, q):
    async def f(pg):
        await pg.fill(sel, q, timeout=8000)
    return f


async def crit_open(pg, ref="DEMO-CONSORTIUM-SETUP"):
    await pg.wait_for_timeout(3000)
    await pg.locator(f"[data-testid='notice-criteria-{ref}']").first.scroll_into_view_if_needed(timeout=10000)
    await pg.click(f"[data-testid='notice-criteria-{ref}']", timeout=10000)
    await pg.wait_for_timeout(2500)


async def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    seed()
    admin = staff(*ADMIN, "admin")
    nf, bw, ks = vendor(V["nf"]), vendor(V["bw"]), vendor(V["ks"])
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/pw-browsers/chromium_headless_shell-1248/chrome-headless-shell-linux-arm64/chrome-headless-shell")
        page = await (await br.new_context(viewport={"width": 1440, "height": 900})).new_page()

        await login(page, "admin", *ADMIN)
        await shot(page, "01-criteria", "1. Buyer sets the criteria and allows consortium bids",
                   "When the tender is created, admin (or the supplier preparing the tender) sets pass/fail and scored criteria. Each criterion says who must meet it in a consortium: the lead alone, all members combined, or every member. 'Accept consortium bids' is ticked and the member limit is set (platform default 5, here 4). Once the tender is live the criteria are locked.",
                   f"/admin/e/notices?q={REF}", wait=5000, before=crit_open)

        cons = ok(nf.post(f"{API}/consortia", json={"notice_ref": REF, "name": "AquaBuild Consortium"}))
        cid = cons["id"]
        await login(page, "supplier", V["nf"], PW)
        await shot(page, "02-lead-forms", "2. The lead supplier forms the consortium",
                   "Northfield opens the bid page, chooses 'Bid as consortium lead' and names the team. The lead then invites registered, KYC-verified PMC suppliers by email or supplier ID, with what each brings and their share.",
                   f"/vendor/bid/new/{REF}", wait=5000)
        ok(nf.post(f"{API}/consortia/{cid}/members", json={"email_or_ref": V["bw"], "capability": "Membrane technology and equipment", "share_pct": 30}))
        ok(nf.post(f"{API}/consortia/{cid}/members", json={"email_or_ref": V["ks"], "capability": "Operations & maintenance", "share_pct": 20}))

        await login(page, "supplier", V["bw"], PW)
        await shot(page, "03-member-invite", "3. Each invited member accepts or declines",
                   "Brightwater gets an email and a portal notification. Under Consortia it sees the team, its share and can Accept or Decline. A member can't bid alone on the same tender while in a consortium.",
                   "/vendor/consortia")
        ok(bw.post(f"{API}/consortia/{cid}/respond", json={"accept": True}))
        ok(ks.post(f"{API}/consortia/{cid}/respond", json={"accept": True}))
        ok(nf.put(f"{API}/consortia/{cid}/terms", json={"lead_share_pct": 50, "shares": {vid(V["bw"]): 30, vid(V["ks"]): 20},
                                                       "escrow_mode": "shared", "deposit_mode": "lead_pays"}))
        for s, n in ((nf, "Arif Rahman"), (bw, "Mei Ling Tan")):
            ok(s.post(f"{API}/consortia/{cid}/agreement/sign", json={"signer_name": n, "consent": True}))

        await login(page, "supplier", V["nf"], PW)
        await shot(page, "04-terms-agreement", "4. Shares, escrow, deposit and the consortium agreement",
                   "The lead sets shares (must total 100%), chooses one shared escrow split by shares or a separate escrow per member, and who pays the bid deposit. The agreement is either uploaded signed by all, or every member signs the standard PMC agreement. The checklist shows what is still missing (here: Kestrel has not signed yet).",
                   f"/vendor/bid/new/{REF}", wait=5000, full=True)
        ok(ks.post(f"{API}/consortia/{cid}/agreement/sign", json={"signer_name": "Daniel Wong", "consent": True}))
        await shot(page, "05-criteria-per-member", "5. The bid: one sealed bid with every member's figures",
                   "Once ready, the lead fills the criteria. For 'combined' and 'every member' criteria the form asks for each member's figure; proof is attached and sealed with the bid. Price and documents are sealed until opening.",
                   f"/vendor/bid/new/{REF}", wait=5000, full=True)

        bwid, ksid = vid(V["bw"]), vid(V["ks"])
        docs = lambda s: [{"kind": "technical", "key": upload(s, "technical.pdf"), "filename": "technical.pdf", "size_bytes": 10, "uploaded_at": now()},
                          {"kind": "commercial", "key": upload(s, "price.pdf"), "filename": "price.pdf", "size_bytes": 10, "uploaded_at": now()},
                          {"kind": "technical", "key": upload(s, "audited-accounts.pdf"), "filename": "audited-accounts.pdf", "size_bytes": 10,
                           "uploaded_at": now(), "criterion_id": "dgturn01"}]
        cbid = ok(nf.post(f"{API}/bids", json={"notice_ref": REF, "price_amount": 11200000, "price_currency": "USD", "technical_notes": "Design-build approach",
                                              "commercial_notes": "Lump sum", "documents": docs(nf), "consortium_id": cid, "criteria_answers": [
            {"criterion_id": "dgturn01", "value": 7400000},
            {"criterion_id": "dgproj01", "value": 4200000, "members": {bwid: 3100000, ksid: 1500000}},
            {"criterion_id": "dgiso001", "value": True, "members": {bwid: True, ksid: True}},
            {"criterion_id": "dgstaf01", "value": 12, "members": {bwid: 9, ksid: 6}}]}))["id"]
        solo = vendor(SOLO)
        ok(solo.post(f"{API}/bids", json={"notice_ref": REF, "price_amount": 9800000, "price_currency": "USD", "technical_notes": "T",
                                          "commercial_notes": "C", "documents": docs(solo), "criteria_answers": [
            {"criterion_id": "dgturn01", "value": 3100000}, {"criterion_id": "dgproj01", "value": 6000000},
            {"criterion_id": "dgiso001", "value": True}, {"criterion_id": "dgstaf01", "value": 14}]}))

        DB.notices.update_one({"notice_ref": REF}, {"$set": {"submission_deadline": now(hours=-3), "bid_opening_date": now(hours=-2)}})
        sig = {"signer_name": "Committee", "consent": True, "typed_signature": "Committee"}
        c1, c2 = staff("committee1@demo.pmcmanagers.com", PW, "committee_member"), staff("committee2@demo.pmcmanagers.com", PW, "committee_member")
        for c in (c1, c2):
            r = c.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", **sig})
            print("tech approve", r.status_code, r.text[:200])
        await asyncio.sleep(4)

        await login(page, "admin", *ADMIN)
        await shot(page, "06-system-qualification", "6. Opening: the system qualifies every bid by itself",
                   "When the committee opens the technical envelopes, the system checks every bid against each criterion: lead-only items use the lead's figure, combined items add up all members, every-member items must be met by each. Each line shows pass/fail and the reason. The committee can't change a result; it can only raise a logged doubt on a document. Only qualified bids go on to price opening.",
                   f"/admin/bids/{cbid}", wait=6000, full=True)
        await login(page, "supplier", V["nf"], PW)
        await shot(page, "07-supplier-result", "7. Every supplier gets their own result notice",
                   "A first result is emailed and shown in My bids right after technical opening; the final result follows once doubts are settled, just before price opening. Each supplier sees only its own criteria results and how many bids qualified, never other bidders' names. Admin sees every result email and whether it was delivered, and can re-send failed ones (the demo addresses don't receive mail, so they show 'Not delivered' on the previous page).",
                   "/vendor/mybids", wait=5000, before=click(f"[data-testid='vmb-result-{cbid}'] summary"))

        for c in (c1, c2):
            r = c.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", **sig})
            print("comm approve", r.status_code, r.text[:200])
        DB.bids.update_one({"_id": ObjectId(cbid)}, {"$set": {"status": "awarded", "awarded_at": now()}})
        bref = DB.bids.find_one({"_id": ObjectId(cbid)})["bid_ref"]
        acc = DB.escrow_accounts.insert_one({"name": "DEMO Consortium Escrow Account", "institution": "Demo Trustee Bank", "currency": "USD",
                                             "pmc_officer": {"name": "PMC Officer", "email": ADMIN[0]},
                                             "escrow_officer": {"name": "Escrow Officer", "email": ESC[0]}}).inserted_id
        DB.escrow_magic_tokens.insert_one({"token": TOK, "account_id": str(acc), "officer_email": ESC[0], "revoked": False, "created_at": now()})
        s2 = {"action": "release_to_contractor", "signed_at": now()}
        tid = str(DB.escrow_transactions.insert_one({
            "bid_ref": bref, "notice_ref": REF, "amount": 1120000.0, "currency": "USD", "status": "awaiting_signatures",
            "escrow_account_id": str(acc), "signatures": {"pmc": {**s2, "email": ADMIN[0]}, "escrow_institution": {**s2, "email": ESC[0]}},
            "audit_trail": [], "created_at": now(), "created_by": "DEMO", "memo": "Milestone 1 — 10% mobilisation payment",
            "escrow_account_snapshot": {"name": "DEMO Consortium Escrow Account", "pmc_officer": {"name": "PMC Officer", "email": ADMIN[0]},
                                        "escrow_officer": {"name": "Escrow Officer", "email": ESC[0]}}}).inserted_id)
        print("release", admin.post(f"{API}/escrow/transactions/{tid}/release", json={"action": "release_to_contractor", "memo": "Milestone 1"}).status_code)
        for i in range(3):
            admin.post(f"{API}/escrow/transactions/{tid}/consortium-split/{i}/sign", json={"comment": "Checked against award"})
        await login(page, "admin", *ADMIN)
        await shot(page, "08-payment-instructions", "8. Award payment: split into one instruction per member",
                   "After award, when both escrow officers release a payment, the system splits it by the agreed shares (50/30/20) into one payment instruction per member, with the member's bank details. Here the PMC officer has signed; the escrow officer still has to.",
                   "/admin/e/escrow", wait=6000, before=search("[data-testid='escrow-tx-search']", bref), elem="[data-testid^='consortium-split-']")
        await page.context.clear_cookies()
        await shot(page, "09-escrow-officer", "9. The escrow institution officer signs from their secure link",
                   "The escrow bank's officer signs each instruction from the emailed signing link, with no PMC login needed. No payment can be recorded until both officers have signed.",
                   f"/escrow/officer/{TOK}", wait=5000, full=True)
        esc = staff(*ESC, "escrow_agent")
        for i in range(3):
            esc.post(f"{API}/escrow/transactions/{tid}/consortium-split/{i}/sign", json={"comment": "Approved"})
        for i, ref in ((0, "MBB-TT-778201"), (1, "MBB-TT-778202")):
            key = f"vendor-docs/DEMOGUIDE{uuid.uuid4().hex[:6]}_slip.pdf"
            DB.uploads.insert_one({"key": key, "content_type": "application/pdf", "size_bytes": 12, "data_b64": "JVBERi0xLjQgZGVtbw==", "created_at": now()})
            print("paid", admin.post(f"{API}/escrow/transactions/{tid}/consortium-split/{i}/paid", json={"reference": ref, "proof_key": key}).status_code)
        await login(page, "admin", *ADMIN)
        await shot(page, "10-paid-and-csv", "10. Bank payments recorded with slip, and the audit spreadsheet",
                   "Accounts makes each bank transfer, then records it with the bank reference and the payment slip. 'Consortium payments · CSV' downloads every instruction, share, bank account, both signatures and payment reference for accounts and audit.",
                   "/admin/e/escrow", wait=6000, before=search("[data-testid='escrow-tx-search']", bref), elem="[data-testid^='consortium-split-']")
        await login(page, "supplier", V["bw"], PW)
        await shot(page, "11-member-payouts", "11. Each member tracks its own payments",
                   "In Consortia → My consortium payments, each member sees its share, the account it goes to (last 4 digits), both officer signatures and, once paid, the bank reference.",
                   "/vendor/consortia", wait=5000, full=True)
        await br.close()
    build_pdf()


async def shot1():
    DB.notices.delete_many({"notice_ref": "DEMO-CONSORTIUM-SETUP"})
    DB.notices.insert_one({"notice_ref": "DEMO-CONSORTIUM-SETUP", "title": "Design & build of district water treatment plant (DEMO draft)",
                           "is_published": False, "category": "", "budget_amount": 12000000.0, "budget_currency": "USD", "created_at": now(),
                           "submission_deadline": now(days=30), "bid_opening_date": now(days=31), "description": "DEMO",
                           "tender_criteria": CRIT, "consortium_allowed": True, "consortium_max_members": 4, "tenant_id": "PMC-KZ-01"})
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/pw-browsers/chromium_headless_shell-1248/chrome-headless-shell-linux-arm64/chrome-headless-shell")
        page = await (await br.new_context(viewport={"width": 1440, "height": 900})).new_page()
        await login(page, "admin", *ADMIN)
        await page.goto(f"{BASE}/admin/e/notices", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(9000)
        print("url", page.url, "buttons", await page.locator("[data-testid^='notice-criteria-']").count())
        await page.screenshot(path="/tmp/notices_debug.png")
        await shot(page, "01-criteria", *CAP1, before=crit_open)
        await br.close()
    DB.notices.delete_many({"notice_ref": "DEMO-CONSORTIUM-SETUP"})
    if not STEPS:
        return
    path = "/app/frontend/public/downloads/pmc-consortium-guide.pdf"
    doc = fitz.open(path)
    pg = doc.new_page(pno=1, width=842, height=595)
    pg.insert_textbox(fitz.Rect(30, 20, 812, 50), CAP1[0], fontsize=15, fontname="hebo")
    pg.insert_textbox(fitz.Rect(30, 50, 812, 110), CAP1[1], fontsize=9.5, fontname="helv")
    pg.insert_image(fitz.Rect(30, 112, 812, 580), filename=f"{OUT}/01-criteria.png", keep_proportion=True)
    doc.save(path + ".tmp")
    os.replace(path + ".tmp", path)
    print("PDF pages", len(fitz.open(path)))


CAP1 = ("1. Buyer sets the criteria and allows consortium bids",
        "When the tender is created, admin (or the supplier preparing the tender) sets pass/fail and scored criteria. Each criterion says who must meet it in a consortium: the lead alone, all members combined, or every member. 'Accept consortium bids' is ticked and the member limit is set (platform default 5, here 4). Once the tender is live the criteria are locked.")


def build_pdf():
    doc = fitz.open()
    cover = doc.new_page(width=842, height=595)
    cover.insert_textbox(fitz.Rect(60, 180, 780, 420), "PMC Managers — Consortium bidding\nComplete life cycle (demo walkthrough)\n\n"
                         "Tender criteria → forming the team → agreement → sealed bid → automatic qualification → result notices → award → escrow split → payments",
                         fontsize=20, fontname="helv")
    for name, title, text in STEPS:
        pg = doc.new_page(width=842, height=595)
        pg.insert_textbox(fitz.Rect(30, 20, 812, 50), title, fontsize=15, fontname="hebo")
        pg.insert_textbox(fitz.Rect(30, 50, 812, 110), text, fontsize=9.5, fontname="helv")
        pg.insert_image(fitz.Rect(30, 112, 812, 580), filename=f"{OUT}/{name}.png", keep_proportion=True)
    doc.save("/app/frontend/public/downloads/pmc-consortium-guide.pdf")
    print("PDF pages", len(doc))


if __name__ == "__main__":
    if sys.argv[1] == "clean":
        clean()
    elif sys.argv[1] == "shot1":
        asyncio.run(shot1())
    else:
        asyncio.run(main())
