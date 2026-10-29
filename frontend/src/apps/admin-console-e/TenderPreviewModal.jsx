import DOMPurify from "dompurify";

const FIELDS = [["work_title", "Title"], ["work_description", "Description"], ["product_category", "Category"],
  ["tender_value", "Tender value"], ["budget_amount", "Budget"], ["budget_currency", "Currency"],
  ["period_days", "Period (days)"], ["location", "Location"], ["eligibility", "Eligibility"],
  ["evaluation_method", "Evaluation"], ["emd_amount", "EMD"], ["sub_end", "Bid closes"]];

export const TenderPreviewModal = ({ tpl, onClose, actions }) => {
  const h = tpl.header || {};
  const sections = [...(tpl.sections || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  return (
    <div data-testid="tr-preview-modal" onClick={onClose}
         style={{ position: "fixed", inset: 0, background: "rgba(10,16,30,.55)", zIndex: 60, display: "flex", justifyContent: "center", padding: "32px 16px", overflowY: "auto" }}>
      <div className="pmc-panel" onClick={(e) => e.stopPropagation()}
           style={{ width: "100%", maxWidth: "860px", height: "fit-content", padding: "24px 28px", background: "var(--paper, #fff)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "flex-start" }}>
          <div>
            <div className="pmc-eyebrow">Tender preview · {tpl.owner_company_name || "Vendor"}</div>
            <h2 className="pmc-display" style={{ fontSize: "22px", margin: "4px 0 0" }} data-testid="tr-preview-title">{h.work_title || tpl.name}</h2>
          </div>
          <button className="pmc-btn pmc-btn--sm pmc-btn--ghost" data-testid="tr-preview-close" onClick={onClose}>Close</button>
        </div>
        <dl data-testid="tr-preview-header" style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: "6px 14px", fontSize: "13px", margin: "18px 0" }}>
          {FIELDS.filter(([k]) => h[k] !== undefined && h[k] !== null && h[k] !== "").map(([k, l]) => (
            <div key={k} style={{ display: "contents" }}><dt className="pmc-muted">{l}</dt><dd style={{ margin: 0 }}>{typeof h[k] === "number" ? h[k].toLocaleString() : String(h[k])}</dd></div>
          ))}
        </dl>
        <div data-testid="tr-preview-sections" style={{ display: "grid", gap: "14px" }}>
          {sections.map((s) => (
            <section key={s.code} data-testid={`tr-preview-section-${s.code}`} style={{ borderTop: "1px solid var(--line)", paddingTop: "10px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 600, margin: "0 0 6px" }}>{s.title}</h3>
              {(s.body || "").trim()
                ? <div style={{ fontSize: "13px", lineHeight: 1.6 }} dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(s.body) }} />
                : <div className="pmc-muted" style={{ fontSize: "12px", fontStyle: "italic" }}>Empty section</div>}
            </section>
          ))}
        </div>
        {actions && <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "20px", flexWrap: "wrap" }}>{actions}</div>}
      </div>
    </div>
  );
};
