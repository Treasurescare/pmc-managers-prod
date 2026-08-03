/**
 * tenderPdf — opens a print-ready HTML view of a composed tender template
 * in a new window, then triggers window.print() so the browser's Save-as-PDF
 * dialog can render a real PDF. Zero external deps, works offline, honours
 * the RichEditor HTML so bold/lists survive.
 *
 * Security: the composed HTML is sanitised with DOMPurify before it's ever
 * handed to the new window, and we hand it off via a Blob URL (not
 * `document.write`) so an attacker who slipped raw HTML into a template
 * cannot get inline scripts to execute in the parent origin.
 */
import DOMPurify from "dompurify";

const KIND_LABEL = { section: "Section", annexure: "Annexure", form: "Form" };
const BODY_SANITIZE_CFG = {
  ALLOWED_TAGS: ["p", "br", "b", "strong", "i", "em", "u", "h2", "h3", "ul", "ol", "li",
                 "blockquote", "code", "pre", "span", "div", "a"],
  ALLOWED_ATTR: ["href", "target", "rel"],
};

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function fmtDate(v) {
  if (!v) return "";
  try {
    const d = typeof v === "string" ? new Date(v) : v;
    if (Number.isNaN(d.getTime())) return String(v);
    return d.toLocaleString();
  } catch { return String(v); }
}

function headerRows(h) {
  if (!h) return "";
  const money = (n) => (n == null || n === "") ? "" : Number(n).toLocaleString();
  const rows = [
    ["Organisation Chain", h.organisation_chain],
    ["Tender Reference Number", h.tender_reference_number],
    ["Tender ID", h.tender_id],
    ["Tender Type", h.tender_type],
    ["Form of Contract", h.form_of_contract],
    ["Tender Category", h.tender_category],
    ["No. of Covers", h.no_of_covers],
    ["Work Title", h.work_title || h.title],
    ["Work Description", h.work_description],
    ["Product Category", h.product_category],
    ["Sub Category", h.sub_category],
    ["Contract Type", h.contract_type],
    ["Tender Value (₹)", money(h.tender_value || h.budget_amount)],
    ["Currency", h.budget_currency],
    ["Bid Validity (Days)", h.bid_validity_days],
    ["Period of Work (Days)", h.period_days],
    ["Location", h.location],
    ["Pincode", h.pincode],
    ["EMD Amount (₹)", money(h.emd_amount)],
    ["EMD Payable To", h.emd_payable_to],
    ["EMD Payable At", h.emd_payable_at],
    ["Tender Fee (₹)", money(h.tender_fee_amount)],
    ["Fee Payable To", h.fee_payable_to],
    ["Fee Payable At", h.fee_payable_at],
    ["Publish Date", fmtDate(h.publish_date)],
    ["Document Download Start", fmtDate(h.doc_dl_start)],
    ["Document Download End",   fmtDate(h.doc_dl_end)],
    ["Bid Submission Start",    fmtDate(h.sub_start)],
    ["Bid Submission End",      fmtDate(h.sub_end)],
    ["Bid Opening Date",        fmtDate(h.bid_opening_date)],
    ["Bid Opening Place",       h.bid_opening_place],
    ["Pre-Bid Meeting Date",    fmtDate(h.pre_bid_date)],
    ["Pre-Bid Meeting Place",   h.pre_bid_place],
    ["Pre-Bid Meeting Address", h.pre_bid_address],
    ["Inviting Authority",      h.authority_name],
    ["Authority Address",       h.authority_address],
    ["Evaluation Method",       h.evaluation_method],
    ["Eligibility",             h.eligibility],
  ].filter(([, v]) => v !== undefined && v !== null && v !== "");
  return rows.map(([k, v]) =>
    `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join("");
}

export function buildTenderHtml(doc) {
  if (!doc) return "";
  const sections = [...(doc.sections || [])].sort((a, b) => (a.order || 0) - (b.order || 0));
  const secHtml = sections.map((s) => {
    const cleanBody = s.body
      ? DOMPurify.sanitize(s.body, BODY_SANITIZE_CFG)
      : "<em class='muted'>[to be completed]</em>";
    return `
    <section class="sec">
      <h2>${esc(KIND_LABEL[s.kind] || "Section")} · ${esc(s.title)}</h2>
      ${s.hint ? `<div class="hint">${esc(s.hint)}</div>` : ""}
      <div class="body">${cleanBody}</div>
      ${s.attachment ? `<div class="attach">Attached template: ${esc(s.attachment.file_name)}</div>` : ""}
    </section>`;
  }).join("");
  return `<!doctype html>
<html><head><meta charset="utf-8"/>
<title>${esc(doc.name || "Tender")}</title>
<style>
  * { box-sizing: border-box; }
  body { font: 12px/1.55 Georgia, "Times New Roman", serif; color: #0b1f3a; padding: 32px 44px; max-width: 820px; margin: 0 auto; }
  header.doc { border-bottom: 3px double #0b1f3a; padding-bottom: 12px; margin-bottom: 24px; }
  header.doc h1 { font-size: 22px; margin: 0 0 4px; }
  header.doc .meta { font-size: 11px; text-transform: uppercase; letter-spacing: .12em; color: #64748b; }
  table.header { width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 11px; }
  table.header th, table.header td { border: 1px solid #cbd5e1; padding: 6px 8px; vertical-align: top; text-align: left; }
  table.header th { background: #f1f5f9; width: 32%; font-weight: 600; color: #334155; }
  h2 { font-size: 14px; margin: 24px 0 6px; padding-bottom: 4px; border-bottom: 1px solid #cbd5e1; }
  .sec { page-break-inside: avoid; margin-bottom: 18px; }
  .hint { font-style: italic; color: #64748b; margin-bottom: 6px; font-size: 11px; }
  .body { white-space: pre-wrap; }
  .body ul, .body ol { padding-left: 20px; }
  .body blockquote { margin: 6px 0; padding-left: 12px; border-left: 3px solid #cbd5e1; color: #334155; }
  .attach { margin-top: 8px; font-size: 11px; color: #64748b; }
  .muted { color: #94a3b8; }
  @media print {
    body { padding: 16mm; }
    header.doc, .sec { page-break-inside: avoid; }
  }
</style></head>
<body>
  <header class="doc">
    <div class="meta">${esc((doc.kind || "tender").toUpperCase())} · ${esc(doc.industry || "")}</div>
    <h1>${esc(doc.name || "Tender")}</h1>
  </header>
  <table class="header"><tbody>${headerRows(doc.header)}</tbody></table>
  ${secHtml}
</body></html>`;
}

export function exportTenderPdf(doc) {
  const html = buildTenderHtml(doc);
  // Hand the HTML off via a Blob URL instead of `document.write` so the new
  // window loads it as a normal document with a fresh Trusted Types boundary.
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const w = window.open(url, "_blank");
  if (!w) {
    URL.revokeObjectURL(url);
    return;
  }
  const cleanup = () => {
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };
  w.onload = () => {
    setTimeout(() => {
      try { w.focus(); w.print(); }
      catch (e) {
        if (process.env.NODE_ENV !== "production") console.warn("tenderPdf print failed", e);
      }
      cleanup();
    }, 250);
  };
}
