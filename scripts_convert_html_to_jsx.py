#!/usr/bin/env python3
"""HTML template → React JSX component converter.

Takes each PMC HTML template, extracts the body content (minus svg sprite),
converts HTML attribute names, self-closes void tags, escapes braces,
and wraps into a React component. Keeps handlers/events inert (removed).
"""

import re
import sys
from pathlib import Path

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr", "use",
}

ATTR_MAP = {
    "class": "className",
    "for": "htmlFor",
    "tabindex": "tabIndex",
    "colspan": "colSpan",
    "rowspan": "rowSpan",
    "readonly": "readOnly",
    "autocomplete": "autoComplete",
    "autofocus": "autoFocus",
    "maxlength": "maxLength",
    "minlength": "minLength",
    "novalidate": "noValidate",
    "spellcheck": "spellCheck",
    "usemap": "useMap",
    "srcset": "srcSet",
    "srcdoc": "srcDoc",
    "crossorigin": "crossOrigin",
    "onclick": "_onClick_strip",  # stripped
    "onsubmit": "_onSubmit_strip",
    "onchange": "_onChange_strip",
    "oninput": "_oninput_strip",
    "onload": "_onload_strip",
}

BOOL_ATTRS = {"disabled", "checked", "selected", "hidden", "required", "open", "multiple", "readonly", "autofocus", "novalidate"}


def strip_scripts(body: str) -> str:
    return re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)


def strip_style_blocks(body: str) -> str:
    return re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)


def strip_svg_sprite(body: str) -> str:
    return re.sub(r'<svg width="0" height="0"[^>]*>.*?</svg>', "", body, flags=re.DOTALL | re.IGNORECASE)


def escape_jsx_text(body: str) -> str:
    # Escape { and } outside tags. Simple approach: replace all {, } in text nodes.
    # Since HTML has few braces we replace text-node braces.
    # We'll only escape at the end after tag processing.
    return body


def convert_attributes(match):
    tag = match.group(1)
    attrs_str = match.group(2) or ""
    self_close = match.group(3) or ""

    # Parse attributes (handles quoted and unquoted)
    attrs = []
    pos = 0
    inline_style_map = None
    for am in re.finditer(r'([a-zA-Z_:][a-zA-Z0-9_:\-]*)(?:\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+)))?', attrs_str):
        name = am.group(1)
        val = am.group(3) if am.group(3) is not None else am.group(4) if am.group(4) is not None else am.group(5)

        # Skip event handlers entirely
        if name.lower().startswith("on"):
            continue

        # Map attribute names
        new_name = ATTR_MAP.get(name.lower(), name)
        if new_name.startswith("_") and new_name.endswith("_strip"):
            continue

        # Convert style="a:b;c:d" into style={{a: "b", c: "d"}}
        if new_name == "style" and val:
            css_map = {}
            for prop in val.split(";"):
                if ":" not in prop: continue
                k, v = prop.split(":", 1)
                k = k.strip()
                v = v.strip()
                if not k: continue
                # Kebab-case → camelCase
                kk = re.sub(r"-([a-z])", lambda m: m.group(1).upper(), k)
                # Escape " in value
                v_escaped = v.replace('"', '\\"')
                css_map[kk] = v_escaped
            style_parts = ", ".join(f'{k}: "{v}"' for k, v in css_map.items())
            attrs.append(f"style={{{{ {style_parts} }}}}")
            continue

        # Handle boolean attributes
        if val is None:
            if new_name.lower() in BOOL_ATTRS:
                attrs.append(f"{new_name}")
            else:
                attrs.append(f'{new_name}=""')
            continue

        # Escape braces in string attribute values
        val_escaped = val.replace("{", "&#123;").replace("}", "&#125;")
        # If attribute name has a hyphen (e.g. data-*, aria-*) it's fine as-is
        # If new_name starts with data- or aria- keep original case
        if new_name.startswith("data-") or new_name.startswith("aria-"):
            attrs.append(f'{new_name}="{val_escaped}"')
        else:
            attrs.append(f'{new_name}="{val_escaped}"')

    attrs_out = (" " + " ".join(attrs)) if attrs else ""
    if tag.lower() in VOID_TAGS or self_close.strip() == "/":
        return f"<{tag}{attrs_out} />"
    return f"<{tag}{attrs_out}>"


def convert_html_to_jsx(html: str) -> str:
    # Extract body content
    body_m = re.search(r"<body[^>]*>(.*?)</body>", html, flags=re.DOTALL | re.IGNORECASE)
    body = body_m.group(1) if body_m else html

    body = strip_scripts(body)
    body = strip_style_blocks(body)
    body = strip_svg_sprite(body)

    # Convert HTML comments to JSX comments
    body = re.sub(r"<!--(.*?)-->", lambda m: "{/*" + m.group(1).replace("*/", "*\\/") + "*/}", body, flags=re.DOTALL)

    # Process opening tags. Match: <tagname attrs...> or <tagname attrs.../>
    tag_re = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^>]*?)?)(\s*/?)>")
    body = tag_re.sub(convert_attributes, body)

    # Self-close void tags that weren't self-closed
    for vt in VOID_TAGS:
        body = re.sub(rf"<{vt}([^/>]*)>", rf"<{vt}\1 />", body, flags=re.IGNORECASE)

    # Handle &nbsp; &amp; etc — JSX handles most, but replace bare & with &amp; where needed
    # We'll trust the browser here; JSX allows html entities.

    # Escape { and } in text nodes (between > and <)
    def esc_text(m):
        text = m.group(0)
        return text.replace("{", "&#123;").replace("}", "&#125;")
    body = re.sub(r">([^<]*)<", lambda m: ">" + m.group(1).replace("{", "&#123;").replace("}", "&#125;") + "<", body)

    return body.strip()


def make_component(name: str, jsx_body: str, testid: str) -> str:
    return f"""import {{ useEffect }} from "react";
import {{ Link }} from "react-router-dom";
import {{ useUiTheme }} from "@/context/UiThemeContext";

/**
 * PMC v49a — Option E design template.
 * When ?ui=e is active this replaces the legacy view.
 * Wired to legacy fallback when Option E is off.
 */
export default function {name}({{ legacy: Legacy }}) {{
  const {{ isE }} = useUiTheme();
  useEffect(() => {{
    // Countdown timers
    const tick = () => {{
      document.querySelectorAll("[data-in]").forEach((el) => {{
        const secs = parseInt(el.getAttribute("data-in") || "0", 10);
        if (!secs) return;
        const d = Math.floor(secs / 86400);
        const h = Math.floor((secs % 86400) / 3600);
        const m = Math.floor((secs % 3600) / 60);
        el.textContent = d > 0 ? `${{d}}d ${{h}}h` : h > 0 ? `${{h}}h ${{m}}m` : `${{m}}m`;
      }});
    }};
    tick();
  }}, [isE]);

  if (!isE && Legacy) return <Legacy />;

  return (
    <div data-testid="{testid}">
      {jsx_body}
    </div>
  );
}}
"""


def main():
    src = Path("/tmp/pmc-designs")
    mapping = {
        # Public
        "01-Homepage.html": ("HomeE", "/app/frontend/src/apps/notice-board-e/HomeE.jsx", "home-e"),
        "02-Tender-Notices.html": ("TendersListE", "/app/frontend/src/apps/notice-board-e/TendersListE.jsx", "tenders-list-e"),
        "03-Tender-Detail.html": ("NoticeDetailE", "/app/frontend/src/apps/notice-board-e/NoticeDetailE.jsx", "notice-detail-e"),
        "04-Completed-and-Awarded.html": ("AwardsPublicE", "/app/frontend/src/apps/notice-board-e/AwardsPublicE.jsx", "awards-public-e"),
        "05-Supplier-Registration.html": ("RegistrationE", "/app/frontend/src/apps/registration-e/RegistrationE.jsx", "registration-e"),
        "06-Sign-In.html": ("SignInE", "/app/frontend/src/apps/auth-e/SignInE.jsx", "sign-in-e"),
        "07-About-and-Vision.html": ("AboutVisionE", "/app/frontend/src/apps/notice-board-e/AboutVisionE.jsx", "about-vision-e"),
        "08-Trust-and-Security.html": ("TrustSecurityE", "/app/frontend/src/apps/notice-board-e/TrustSecurityE.jsx", "trust-security-e"),
        "09-Help-Centre.html": ("HelpCentreE", "/app/frontend/src/apps/help-centre/HelpCentreE.jsx", "help-centre-e"),
        "10-Help-Article.html": ("HelpArticleE", "/app/frontend/src/apps/help-centre/HelpArticleE.jsx", "help-article-e"),
        # Vendor
        "01-Supplier-Home.html": ("VendorHomeE", "/app/frontend/src/apps/vendor-portal-e/VendorHomeE.jsx", "vendor-home-e"),
        "02-My-Bids.html": ("VendorMyBidsE", "/app/frontend/src/apps/vendor-portal-e/VendorMyBidsE.jsx", "vendor-mybids-e"),
        "03-Bid-Workspace.html": ("VendorBidWorkspaceE", "/app/frontend/src/apps/vendor-portal-e/VendorBidWorkspaceE.jsx", "vendor-bid-workspace-e"),
        "04-EMD-and-Payments.html": ("VendorEmdE", "/app/frontend/src/apps/vendor-portal-e/VendorEmdE.jsx", "vendor-emd-e"),
        "05-Signatures.html": ("VendorSignaturesE", "/app/frontend/src/apps/vendor-portal-e/VendorSignaturesE.jsx", "vendor-signatures-e"),
        "06-Company-and-KYC.html": ("VendorCompanyKycE", "/app/frontend/src/apps/vendor-portal-e/VendorCompanyKycE.jsx", "vendor-company-kyc-e"),
        "07-Account-and-Security.html": ("VendorAccountE", "/app/frontend/src/apps/vendor-portal-e/VendorAccountE.jsx", "vendor-account-e"),
        # Admin
        "01-Dashboard.html": ("AdminDashboardE", "/app/frontend/src/apps/admin-console-e/AdminDashboardE.jsx", "admin-dashboard-e"),
        "02-Audit-Ledger.html": ("AdminAuditE", "/app/frontend/src/apps/admin-console-e/AdminAuditE.jsx", "admin-audit-e"),
        "03-Notices.html": ("AdminNoticesE", "/app/frontend/src/apps/admin-console-e/AdminNoticesE.jsx", "admin-notices-e"),
        "04-Tender-Builder.html": ("AdminTenderBuilderE", "/app/frontend/src/apps/admin-console-e/AdminTenderBuilderE.jsx", "admin-tender-builder-e"),
        "05-BOQ-and-Contracts.html": ("AdminBoqContractsE", "/app/frontend/src/apps/admin-console-e/AdminBoqContractsE.jsx", "admin-boq-contracts-e"),
        "06-Vendor-Intel.html": ("AdminVendorIntelE", "/app/frontend/src/apps/admin-console-e/AdminVendorIntelE.jsx", "admin-vendor-intel-e"),
        "07-Vendor-KYC-Review.html": ("AdminVendorKycE", "/app/frontend/src/apps/admin-console-e/AdminVendorKycE.jsx", "admin-vendor-kyc-e"),
        "08-Bidding-Ops.html": ("AdminBiddingOpsE", "/app/frontend/src/apps/admin-console-e/AdminBiddingOpsE.jsx", "admin-bidding-ops-e"),
        "09-Escrow-EMD.html": ("AdminEscrowE", "/app/frontend/src/apps/admin-console-e/AdminEscrowE.jsx", "admin-escrow-e"),
        "10-Evaluation-Room.html": ("AdminEvaluationE", "/app/frontend/src/apps/admin-console-e/AdminEvaluationE.jsx", "admin-evaluation-e"),
        "11-L1-Comparison-and-Award.html": ("AdminL1AwardE", "/app/frontend/src/apps/admin-console-e/AdminL1AwardE.jsx", "admin-l1-award-e"),
        "12-DocuSign.html": ("AdminDocuSignE", "/app/frontend/src/apps/admin-console-e/AdminDocuSignE.jsx", "admin-docusign-e"),
        "13-Permissions.html": ("AdminPermissionsE", "/app/frontend/src/apps/admin-console-e/AdminPermissionsE.jsx", "admin-permissions-e"),
    }

    for html_name, (comp_name, out_path, testid) in mapping.items():
        html_path = src / html_name
        if not html_path.exists():
            print(f"MISSING: {html_name}")
            continue
        html = html_path.read_text()
        jsx = convert_html_to_jsx(html)
        component = make_component(comp_name, jsx, testid)
        Path(out_path).write_text(component)
        print(f"  {html_name} → {out_path} ({len(component)} chars)")


if __name__ == "__main__":
    main()
