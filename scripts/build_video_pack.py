"""Build the PMC promotional video pack PDF → frontend/public/downloads/pmc-video-pack.pdf"""
import sys
from html import escape as h

sys.path.insert(0, "/app/backend")
from weasyprint import HTML  # noqa: E402
from pdf_brand import brand_html  # noqa: E402

BRAND = ("Brand: PMC Managers. Colours: deep forest green #0F3B2E, warm brass/gold #A8843A, cream background #F4EFE4. "
         "Serif headings, clean sans-serif body. Logo bottom-right on the last frame. Calm, trustworthy, professional — "
         "government/enterprise procurement, not flashy. No stock 'handshake' clichés. End card: pmcmanagers.com")

VIDEOS = [
    {
        "title": "1 · Become a PMC Partner",
        "audience": "Consultants, agents and business introducers who know suppliers",
        "wingman": f"""Create a 25-second vertical (9:16) promotional video for PMC Managers' Partner programme.
Scenes: (1) A consultant at a laptop, text on screen "Know good suppliers?" (2) Animated badge "Become a PMC Partner".
(3) Three quick icons with text: "Invite suppliers", "Help them register", "Earn commission when they're approved".
(4) Text "Your own partner code and sign-up link" with a code chip "PT-0001". (5) Text "Monthly statement & leaderboard".
(6) End card: "Apply at pmcmanagers.com/partner/register".
Voice-over (warm, confident, British English): "Know reliable suppliers? Become a PMC Partner. Invite them, help them register, and earn commission when they're approved — with your own partner code, monthly statements and a leaderboard. Apply today at PMC Managers."
{BRAND}""",
        "vo": [
            ("0–8s", "Know businesses that should be winning tenders? Become a PMC Partner.", "Homepage → scroll to 'Partners of the month' → click 'Become a PMC partner'."),
            ("8–20s", "Sign up in minutes. Confirm your email, set your password, add your profile, bank details and documents.", "/partner/register form → join page (password) → the 4 steps in the partner portal."),
            ("20–32s", "PMC reviews your application. Registration fees are set per country — and can be waived.", "Admin → Partners → open the partner → 'Waive registration fee' tick-box (blur personal data)."),
            ("32–50s", "Once approved, you get a partner code and a personal sign-up link to share on WhatsApp or email.", "Partner portal → My suppliers → 'Your personal sign-up link' → Copy / Share on WhatsApp."),
            ("50–70s", "Every supplier you bring is tracked. Commission is added to your wallet when they're approved — and for deals they complete.", "Commission wallet tab: due / paid totals and entries."),
            ("70–85s", "Get a monthly PDF statement, earn badges and climb the leaderboard.", "Leaderboard tab → badges → Download statement PDF."),
            ("85–90s", "PMC Managers. Apply at pmcmanagers.com.", "End card with logo."),
        ],
    },
    {
        "title": "2 · Partner invites a Supplier",
        "audience": "Suppliers (and partners) — shows the supplier stays in control",
        "wingman": f"""Create a 25-second square (1:1) promotional video explaining that suppliers stay in control when a PMC partner helps them register.
Scenes: (1) Email arriving with text "Your PMC partner has invited you" and a code chip "PT-0001". (2) A consent screen with ticks appearing: "Data privacy", "You review everything", "Only you submit".
(3) Split screen: "Partner fills the form" / "or fill it yourself". (4) Text "Every partner change is logged". (5) A big "Submit" button pressed by the supplier.
(6) End card: "Register free at pmcmanagers.com".
Voice-over: "Invited by a PMC partner? You stay in control. Give consent, let your partner fill the form — or do it yourself. Every change is logged, and only you can submit. Register on PMC Managers."
{BRAND}""",
        "vo": [
            ("0–10s", "A PMC partner can invite any supplier with just a company name, email and mobile.", "Partner portal → My suppliers → Invite a supplier form → Send invitation."),
            ("10–25s", "The supplier receives an email showing the partner's name and partner code.", "Show the invitation email (use a demo inbox)."),
            ("25–40s", "Nothing happens without consent. The supplier confirms their email, reads six clear statements and signs with their name — or chooses to fill the form themselves.", "/supplier-invite page → tick statements → type name → 'Let the partner fill it' (mention 'I'll fill it myself')."),
            ("40–55s", "The partner completes the registration. Every field they change is logged with their code. Declarations and signature are locked for the supplier.", "Partner opens 'Fill form' → amber partner banner → section E locked message."),
            ("55–75s", "The supplier reviews what the partner filled, can remove the partner at any time, then signs and submits.", "Supplier's link → banner listing partner-filled fields → 'Remove partner access' button → submit."),
            ("75–90s", "After approval, the partner code stays with the supplier on bids, contracts and payments. Simple, fair and fully auditable.", "Admin vendor record showing 'Introduced by partner'. End card."),
        ],
    },
    {
        "title": "3 · Sealed Bids — no one opens early",
        "audience": "Buyers, government bodies and suppliers who worry about fairness",
        "wingman": f"""Create a 30-second horizontal (16:9) cinematic promotional video about tamper-proof sealed bidding on PMC Managers.
Scenes: (1) A digital envelope sealing with a lock, text "Your bid is sealed". (2) Text "Encrypted until opening day" over a calendar.
(3) A row of committee members each pressing "Approve" — the lock opens only after the last one. (4) A signed PDF "Bid opening record" with an audit stamp and check code.
(5) Text "No early peeking. Not even the admin." (6) End card "PMC Managers — fair tendering".
Voice-over: "On PMC Managers, every technical and commercial bid is encrypted the moment it's submitted. Until opening day, staff see only who bid and when. Envelopes open only after every committee member approves — and a signed opening record is emailed to the whole committee. Fair tendering, by design."
{BRAND}""",
        "vo": [
            ("0–12s", "When a supplier submits a bid on PMC Managers, the technical and commercial envelopes are encrypted immediately.", "Supplier bid workspace → Submit bid → 'Sealed' status in My bids."),
            ("12–28s", "Before opening, staff see only the bidder's name, submission time and whether the deposit is paid. No prices. No files.", "Admin bid view before opening: sealed placeholders instead of price/documents."),
            ("28–45s", "Envelopes can only be opened on or after the bid opening date.", "Committee opening panel showing opening date / disabled button before date."),
            ("45–65s", "And only when every committee member has approved. One missing approval — no opening.", "Committee panel: members approving one by one; opening button enables after the last."),
            ("65–80s", "A signed bid-opening record PDF — with each member's electronic signature and an audit-ledger check code — is emailed to the committee.", "Open the opening record PDF; show signatures and check code; verify page."),
            ("80–90s", "Fair tendering, by design. PMC Managers.", "End card."),
        ],
    },
    {
        "title": "4 · Escrow Security for deposits (EMD)",
        "audience": "Suppliers paying bid deposits, banks/trustees, buyers",
        "wingman": f"""Create a 25-second horizontal (16:9) promotional video about secure escrow for bid deposits on PMC Managers.
Scenes: (1) A supplier paying a bid deposit, text "Your deposit is protected". (2) A joint escrow account visual held by a bank/trustee, text "Held in a joint escrow account".
(3) Two signatures side by side — "PMC officer" and "Escrow institution officer" — text "Released only with two signatures". (4) Text "Escrow checks deposit proof — nothing else".
(5) Audit trail timeline ticking. (6) End card "PMC Managers — secure tendering".
Voice-over: "Bid deposits on PMC Managers are held in joint escrow accounts with approved banks and trustees. Escrow sees only the deposit proof — never your bid. Funds are released only with two independent signatures, and every step is recorded in the audit trail."
{BRAND}""",
        "vo": [
            ("0–12s", "Many tenders need a bid deposit — the EMD. On PMC Managers it's protected by escrow.", "Supplier pays EMD on a tender (demo payment)."),
            ("12–30s", "Deposits sit in joint escrow accounts with approved escrow institutions — banks and trustees verified by PMC.", "Admin → Escrow institutions list (approved status) → Joint escrow accounts."),
            ("30–45s", "Before bids open, escrow can see only the deposit proof — never the technical or commercial bid. The bid doesn't move ahead until escrow confirms.", "Escrow institution dashboard → transaction → deposit proof file only."),
            ("45–65s", "Release or refund needs two signatures: a PMC officer and an escrow institution officer, signed electronically.", "Escrow transaction → DocuSign signing for both officers → both signed status."),
            ("65–80s", "The signed document is emailed to both officers, and every step is recorded in the audit ledger.", "Admin → Audit ledger filtered to the escrow transaction."),
            ("80–90s", "Secure deposits, fair tenders. PMC Managers.", "End card."),
        ],
    },
]

STEPS = [
    ("Get the Wingman teasers", "Open Wingman → ask for a video → paste one 'Wingman prompt' box at a time. Ask for the format shown (9:16 for WhatsApp/Instagram stories, 1:1 for LinkedIn/Facebook feed, 16:9 for website/YouTube). Review, ask Wingman for changes, download."),
    ("Prepare a safe demo", "Record screen demos on the preview site with demo data only — never on the live site with real suppliers. Ask me to build the 'Demo Showcase Account' first (sample tenders, suppliers, partners, a sealed bid and an escrow transaction)."),
    ("Record the screen demos", "Use Loom (easiest) or OBS Studio (free). Browser full screen, zoom 110–125%, hide bookmarks, close other tabs and notifications. Follow the 'On screen' column; pause 1–2 seconds on each screen."),
    ("Add the voice", "Read the 'Voice-over' column yourself, or paste it into ElevenLabs (or Wingman) for a professional AI voice. Keep ~140 words per minute."),
    ("Edit and brand", "Canva → Video or CapCut: add the voice, trim pauses, add captions (most people watch muted), your logo and the end card 'pmcmanagers.com'. Export 1080p."),
    ("Publish", "Homepage hero/feature sections, LinkedIn and Facebook pages, WhatsApp status, partner onboarding emails. Share partner videos with each new partner after approval."),
]


def card(v: dict) -> str:
    rows = "".join(f"<tr><td class=t>{h(t)}</td><td>{h(vo)}</td><td class=s>{h(s)}</td></tr>" for t, vo, s in v["vo"])
    return f"""<div class=video><h2>{h(v['title'])}</h2><div class=aud>Audience: {h(v['audience'])}</div>
      <h3>A · Wingman prompt — 15–30 second teaser (copy and paste)</h3><pre>{h(v['wingman'])}</pre>
      <h3>B · Screen demo — 60–90 seconds</h3>
      <table><thead><tr><th>Time</th><th>Voice-over</th><th>On screen</th></tr></thead><tbody>{rows}</tbody></table></div>"""


html = f"""<html><head><style>
 @page {{ size:A4; margin:15mm; }} body {{ font-family:Helvetica,Arial,sans-serif; font-size:10px; color:#14261F; line-height:1.45; }}
 h1 {{ font-size:22px; color:#0F3B2E; margin:4px 0; }} h2 {{ font-size:16px; color:#0F3B2E; border-bottom:2px solid #A8843A; padding-bottom:4px; margin:0 0 4px; }}
 h3 {{ font-size:10.5px; text-transform:uppercase; letter-spacing:1px; color:#8A6A1F; margin:12px 0 6px; }}
 .video {{ page-break-before:always; }} .aud {{ color:#5B6B63; margin-bottom:6px; }}
 pre {{ white-space:pre-wrap; font-family:Helvetica,Arial,sans-serif; background:#F4EFE4; border:1px solid #E2D6B8; padding:10px; font-size:9.5px; }}
 table {{ width:100%; border-collapse:collapse; }} th, td {{ border-bottom:1px solid rgba(15,59,46,.15); padding:6px; vertical-align:top; text-align:left; }}
 th {{ font-size:8.5px; text-transform:uppercase; letter-spacing:1px; color:#5B6B63; }} td.t {{ width:48px; font-weight:bold; }} td.s {{ width:38%; color:#33463E; }}
 ol li {{ margin-bottom:6px; }}
</style></head><body>
 <h1>PMC Managers · Promotional video pack</h1>
 <div>Four videos: Partners · Supplier invite · Sealed bids · Escrow security. Each has a Wingman teaser prompt and a screen-demo script.</div>
 <h3>How to proceed</h3><ol>{''.join(f'<li><b>{h(a)}.</b> {h(b)}</li>' for a, b in STEPS)}</ol>
 <h3>Checklist before publishing</h3><ul>
  <li>No real supplier names, emails, prices or bank details visible (blur if needed).</li>
  <li>Claims match what the platform actually does — keep the wording in this pack.</li>
  <li>Captions on, logo on the end card, link pmcmanagers.com.</li></ul>
 {''.join(card(v) for v in VIDEOS)}
</body></html>"""

out = "/app/frontend/public/downloads/pmc-video-pack.pdf"
HTML(string=brand_html(html)).write_pdf(out)
print("wrote", out)
