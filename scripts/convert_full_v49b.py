#!/usr/bin/env python3
"""PMC Option E v49b — full 55-template conversion.

1. Regenerates consolidated pmc-theme-e.css from ALL templates (dedup).
2. Regenerates PmcIconSprite.jsx from ALL templates (dedup by symbol id).
3. Converts all 55 HTML templates into React JSX components.
"""
import re
from pathlib import Path

SRC = Path("/app/scripts/pmc-designs-full")
FE = Path("/app/frontend/src")

VOID_TAGS = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr","use"}
ATTR_MAP = {"class":"className","for":"htmlFor","tabindex":"tabIndex","colspan":"colSpan","rowspan":"rowSpan",
            "readonly":"readOnly","autocomplete":"autoComplete","autofocus":"autoFocus","maxlength":"maxLength",
            "minlength":"minLength","novalidate":"noValidate","spellcheck":"spellCheck","usemap":"useMap",
            "srcset":"srcSet","srcdoc":"srcDoc","crossorigin":"crossOrigin","xlink:href":"xlinkHref"}
BOOL_ATTRS = {"disabled","checked","selected","hidden","required","open","multiple","readonly","autofocus","novalidate"}

# ---------- 1. Consolidated CSS ----------
def scope_css(css):
    css = re.sub(r':root\s*,\s*\[data-theme=light\]', '[data-ui="e"]', css)
    css = re.sub(r':root(?!\-)', '[data-ui="e"]', css)
    css = re.sub(r'\[data-theme=light\]', '[data-ui="e"]', css)
    css = re.sub(r'\[data-theme=dark\]', '[data-ui="e"][data-theme="dark"]', css)
    css = re.sub(r'(^|\n|\})\s*body\s*\{', r'\1[data-ui="e"] {', css)
    css = re.sub(r'(^|\n|\})\s*html\s*\{', r'\1[data-ui="e"] {', css)
    css = re.sub(r'(^|\n|\})\s*\*\s*\{', r'\1[data-ui="e"] * {', css)
    return css

def build_css():
    seen_hashes = set()
    seen_rules = set()
    out = []
    files = sorted(SRC.glob("*.html"), key=lambda p: p.name)
    for f in files:
        html = f.read_text()
        for m in re.finditer(r"<style>(.*?)</style>", html, re.DOTALL):
            css = m.group(1).strip()
            h = hash(css)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            # Split into top-level rules to dedupe across files
            rules = re.split(r"(?<=\})\s*\n\s*(?=\s*(?:[\.\#\[\:\@a-zA-Z\*]))", css)
            kept = []
            for r in rules:
                rh = hash(r.strip())
                if rh in seen_rules or not r.strip():
                    continue
                seen_rules.add(rh)
                kept.append(r.strip())
            if kept:
                out.append(f"/* === {f.name} === */\n" + "\n\n".join(kept))
    full = "\n\n".join(out)
    scoped = scope_css(full)
    (FE / "pmc-theme-e.css").write_text(
        "/* PMC v49b - Option E design system (scoped under [data-ui=\"e\"], 55 templates) */\n\n" + scoped
    )
    print(f"CSS: {len(scoped)} chars")

# ---------- 2. Icon sprite ----------
def build_sprite():
    seen = set()
    symbols = []
    for f in sorted(SRC.glob("*.html")):
        html = f.read_text()
        for m in re.finditer(r"<symbol[^>]*id=\"([^\"]+)\"[^>]*>.*?</symbol>", html, re.DOTALL):
            sid = m.group(1)
            if sid not in seen:
                seen.add(sid)
                symbols.append(m.group(0))
    comp = (
        'import React from "react";\n\n'
        '/** PMC v49b - Global SVG icon sprite (Option E). */\n'
        'export default function PmcIconSprite() {\n'
        '  return (\n'
        '    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">\n'
        + "\n".join("      " + s for s in symbols) + "\n"
        '    </svg>\n'
        '  );\n'
        '}\n'
    )
    (FE / "components" / "PmcIconSprite.jsx").write_text(comp)
    print(f"Sprite: {len(symbols)} unique symbols")

# ---------- 3. Components ----------
def convert_attr_tag(match):
    tag = match.group(1)
    attrs_str = match.group(2) or ""
    self_close = match.group(3) or ""
    attrs = []
    for am in re.finditer(r'([a-zA-Z_:][a-zA-Z0-9_:\-]*)(?:\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+)))?', attrs_str):
        name = am.group(1)
        val = am.group(3) if am.group(3) is not None else am.group(4) if am.group(4) is not None else am.group(5)
        if name.lower().startswith("on"):
            continue
        new_name = ATTR_MAP.get(name.lower(), name)
        if new_name == "style" and val:
            css_map = {}
            for prop in val.split(";"):
                if ":" not in prop: continue
                k, v = prop.split(":", 1)
                k = k.strip(); v = v.strip()
                if not k: continue
                kk = re.sub(r"-([a-z])", lambda m: m.group(1).upper(), k)
                v_esc = v.replace('"', '\\"').replace("{","(").replace("}",")")
                css_map[kk] = v_esc
            style_parts = ", ".join(f'{k}: "{v}"' for k, v in css_map.items())
            attrs.append(f"style={{{{ {style_parts} }}}}")
            continue
        if val is None:
            if new_name.lower() in BOOL_ATTRS:
                attrs.append(f"{new_name}")
            else:
                attrs.append(f'{new_name}=""')
            continue
        val_escaped = val.replace("{", "&#123;").replace("}", "&#125;")
        attrs.append(f'{new_name}="{val_escaped}"')
    attrs_out = (" " + " ".join(attrs)) if attrs else ""
    if tag.lower() in VOID_TAGS or self_close.strip() == "/":
        return f"<{tag}{attrs_out} />"
    return f"<{tag}{attrs_out}>"

def convert_html_to_jsx(html):
    body_m = re.search(r"<body[^>]*>(.*?)</body>", html, flags=re.DOTALL | re.IGNORECASE)
    body = body_m.group(1) if body_m else html
    body = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r'<svg width="0" height="0"[^>]*>.*?</svg>', "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<!--(.*?)-->", lambda m: "{/*" + m.group(1).replace("*/", "* /") + "*/}", body, flags=re.DOTALL)
    body = re.sub(r">([^<]*)<", lambda m: ">" + m.group(1).replace("{", "&#123;").replace("}", "&#125;") + "<", body)
    tag_re = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^>]*?)?)(\s*/?)>")
    body = tag_re.sub(convert_attr_tag, body)
    for vt in VOID_TAGS:
        body = re.sub(rf"<{vt}([^/>]*)>", rf"<{vt}\1 />", body, flags=re.IGNORECASE)
    return body.strip()

def make_component(name, jsx_body, testid):
    return (
        'import { useEffect } from "react";\n'
        'import { useUiTheme } from "@/context/UiThemeContext";\n\n'
        f'export default function {name}({{ legacy: Legacy }}) {{\n'
        '  const { isE } = useUiTheme();\n'
        '  useEffect(() => {\n'
        '    if (!isE) return;\n'
        '    const tick = () => {\n'
        '      document.querySelectorAll("[data-in]").forEach((el) => {\n'
        '        const secs = parseInt(el.getAttribute("data-in") || "0", 10);\n'
        '        if (!secs) return;\n'
        '        const d = Math.floor(secs/86400), h = Math.floor((secs%86400)/3600), m = Math.floor((secs%3600)/60);\n'
        '        el.textContent = d>0 ? `${d}d ${h}h` : h>0 ? `${h}h ${m}m` : `${m}m`;\n'
        '      });\n'
        '    };\n'
        '    tick();\n'
        '  }, [isE]);\n'
        '  if (!isE && Legacy) return <Legacy />;\n'
        '  if (!isE) return null;\n'
        f'  return (\n    <div data-testid="{testid}" data-pmc-e-page="{testid}">\n{jsx_body}\n    </div>\n  );\n'
        '}\n'
    )

MAPPING = {
    # --- Public ---
    "01-Homepage.html":              ("HomeE","notice-board-e/HomeE.jsx","home-e"),
    "02-Tender-Notices.html":        ("TendersListE","notice-board-e/TendersListE.jsx","tenders-list-e"),
    "03-Tender-Detail.html":         ("NoticeDetailE","notice-board-e/NoticeDetailE.jsx","notice-detail-e"),
    "04-Completed-and-Awarded.html": ("AwardsPublicE","notice-board-e/AwardsPublicE.jsx","awards-public-e"),
    "05-Supplier-Registration.html": ("RegistrationE","registration-e/RegistrationE.jsx","registration-e"),
    "06-Sign-In.html":               ("SignInE","auth-e/SignInE.jsx","sign-in-e"),
    "07-For-Suppliers.html":         ("ForSuppliersE","notice-board-e/ForSuppliersE.jsx","for-suppliers-e"),
    "08-For-Buyers.html":            ("ForBuyersE","notice-board-e/ForBuyersE.jsx","for-buyers-e"),
    "09-About-and-Vision.html":      ("AboutVisionE","notice-board-e/AboutVisionE.jsx","about-vision-e"),
    "10-Trust-and-Security.html":    ("TrustSecurityE","notice-board-e/TrustSecurityE.jsx","trust-security-e"),
    "11-Contact.html":               ("ContactE","notice-board-e/ContactE.jsx","contact-e"),
    "12-Privacy-and-Terms.html":     ("PrivacyTermsE","notice-board-e/PrivacyTermsE.jsx","privacy-terms-e"),
    "13-Help-Centre.html":           ("HelpCentreE","help-centre/HelpCentreE.jsx","help-centre-e"),
    "14-Help-Article.html":          ("HelpArticleE","help-centre/HelpArticleE.jsx","help-article-e"),
    # --- Vendor portal ---
    "01-Supplier-Home.html":         ("VendorHomeE","vendor-portal-e/VendorHomeE.jsx","vendor-home-e"),
    "02-Find-Tenders.html":          ("VendorFindTendersE","vendor-portal-e/VendorFindTendersE.jsx","vendor-find-tenders-e"),
    "03-My-Bids.html":               ("VendorMyBidsE","vendor-portal-e/VendorMyBidsE.jsx","vendor-mybids-e"),
    "04-Bid-Workspace.html":         ("VendorBidWorkspaceE","vendor-portal-e/VendorBidWorkspaceE.jsx","vendor-bid-workspace-e"),
    "05-EMD-and-Payments.html":      ("VendorEmdE","vendor-portal-e/VendorEmdE.jsx","vendor-emd-e"),
    "06-Signatures.html":            ("VendorSignaturesE","vendor-portal-e/VendorSignaturesE.jsx","vendor-signatures-e"),
    "07-Alerts.html":                ("VendorAlertsE","vendor-portal-e/VendorAlertsE.jsx","vendor-alerts-e"),
    "08-Reviews.html":               ("VendorReviewsE","vendor-portal-e/VendorReviewsE.jsx","vendor-reviews-e"),
    "09-Company-and-KYC.html":       ("VendorCompanyKycE","vendor-portal-e/VendorCompanyKycE.jsx","vendor-company-kyc-e"),
    "10-Account-and-Security.html":  ("VendorAccountE","vendor-portal-e/VendorAccountE.jsx","vendor-account-e"),
    # --- Admin console ---
    "01-Dashboard.html":             ("AdminDashboardE","admin-console-e/AdminDashboardE.jsx","admin-dashboard-e"),
    "01-Programme-at-a-Glance.html": ("AdminProgrammeE","admin-console-e/AdminProgrammeE.jsx","admin-programme-e"),
    "02-Audit-Ledger.html":          ("AdminAuditE","admin-console-e/AdminAuditE.jsx","admin-audit-e"),
    "03-Notices.html":               ("AdminNoticesE","admin-console-e/AdminNoticesE.jsx","admin-notices-e"),
    "04-Tender-Builder.html":        ("AdminTenderBuilderE","admin-console-e/AdminTenderBuilderE.jsx","admin-tender-builder-e"),
    "05-Corrigenda.html":            ("AdminCorrigendaE","admin-console-e/AdminCorrigendaE.jsx","admin-corrigenda-e"),
    "06-Work-Packages.html":         ("AdminWorkPackagesE","admin-console-e/AdminWorkPackagesE.jsx","admin-work-packages-e"),
    "07-Catalog.html":               ("AdminCatalogE","admin-console-e/AdminCatalogE.jsx","admin-catalog-e"),
    "08-BOQ-and-Contracts.html":     ("AdminBoqContractsE","admin-console-e/AdminBoqContractsE.jsx","admin-boq-contracts-e"),
    "09-Vendors.html":               ("AdminVendorsE","admin-console-e/AdminVendorsE.jsx","admin-vendors-e"),
    "10-Registrations.html":         ("AdminRegistrationsE","admin-console-e/AdminRegistrationsE.jsx","admin-registrations-e"),
    "11-Vendor-KYC-Review.html":     ("AdminVendorKycE","admin-console-e/AdminVendorKycE.jsx","admin-vendor-kyc-e"),
    "12-Vendor-Intel.html":          ("AdminVendorIntelE","admin-console-e/AdminVendorIntelE.jsx","admin-vendor-intel-e"),
    "13-Engagements.html":           ("AdminEngagementsE","admin-console-e/AdminEngagementsE.jsx","admin-engagements-e"),
    "14-Bidding-Ops.html":           ("AdminBiddingOpsE","admin-console-e/AdminBiddingOpsE.jsx","admin-bidding-ops-e"),
    "15-Escrow-EMD.html":            ("AdminEscrowE","admin-console-e/AdminEscrowE.jsx","admin-escrow-e"),
    "16-Billing.html":               ("AdminBillingE","admin-console-e/AdminBillingE.jsx","admin-billing-e"),
    "17-Evaluation.html":            ("AdminEvaluationListE","admin-console-e/AdminEvaluationListE.jsx","admin-evaluation-list-e"),
    "18-Evaluation-Room.html":       ("AdminEvaluationE","admin-console-e/AdminEvaluationE.jsx","admin-evaluation-e"),
    "19-L1-Comparison-and-Award.html":("AdminL1AwardE","admin-console-e/AdminL1AwardE.jsx","admin-l1-award-e"),
    "20-Awards.html":                ("AdminAwardsE","admin-console-e/AdminAwardsE.jsx","admin-awards-e"),
    "21-DocuSign.html":              ("AdminDocuSignE","admin-console-e/AdminDocuSignE.jsx","admin-docusign-e"),
    "22-Permissions.html":           ("AdminPermissionsE","admin-console-e/AdminPermissionsE.jsx","admin-permissions-e"),
    "23-Events-and-Alerts.html":     ("AdminEventsE","admin-console-e/AdminEventsE.jsx","admin-events-e"),
    # --- Reference / showcase ---
    "01-Dialogs.html":               ("DialogsE","reference-e/DialogsE.jsx","dialogs-e"),
    "02-Empty-and-Error-States.html":("StatesE","reference-e/StatesE.jsx","states-e"),
    "03-Emails.html":                ("EmailsE","reference-e/EmailsE.jsx","emails-e"),
    "04-Printable-Documents.html":   ("PrintablesE","reference-e/PrintablesE.jsx","printables-e"),
    # --- Mobile ---
    "01-Mobile-Supplier.html":       ("MobileSupplierE","mobile-e/MobileSupplierE.jsx","mobile-supplier-e"),
    "02-Mobile-Public.html":         ("MobilePublicE","mobile-e/MobilePublicE.jsx","mobile-public-e"),
}

def build_components():
    ok, missing = 0, 0
    for html_name, (comp_name, rel_out, testid) in MAPPING.items():
        html_path = SRC / html_name
        if not html_path.exists():
            print(f"  MISSING: {html_name}")
            missing += 1
            continue
        jsx = convert_html_to_jsx(html_path.read_text())
        comp = make_component(comp_name, jsx, testid)
        (FE / "apps" / rel_out).write_text(comp)
        ok += 1
    print(f"Components: {ok} generated, {missing} missing")

if __name__ == "__main__":
    build_css()
    build_sprite()
    build_components()
