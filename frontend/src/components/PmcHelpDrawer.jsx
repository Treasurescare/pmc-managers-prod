import { useEffect, useState } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

/**
 * PMC v49a — Global floating help FAB + slide-in help drawer.
 * Only mounts when Option E theme is active.
 */
const FAQS = [
  { q: "Where do I find live tenders?", a: "Open the Tenders board or use search — filter by category, country, and budget.", cat: "tenders" },
  { q: "How do I register as a supplier?", a: "Use Register on the top bar. You'll complete KYC in 4 short steps.", cat: "kyc" },
  { q: "What does the seal on each notice mean?", a: "Every notice is sealed, time-stamped, and SHA-256 chained to the audit ledger.", cat: "trust" },
  { q: "How is EMD paid?", a: "EMD is paid to a segregated escrow account. Refunds are automatic once evaluation concludes.", cat: "emd" },
  { q: "Can I withdraw my bid?", a: "Yes — until submission close. After close, only PMC can withdraw with a corrigendum.", cat: "bids" },
  { q: "What is the L1 comparison?", a: "The lowest technically compliant priced bid; committee sign-off is mandatory before award.", cat: "awards" },
  { q: "How does DocuSign work here?", a: "Awards and contracts are signed via DocuSign; envelope hash is logged to the audit chain.", cat: "sign" },
];

export default function PmcHelpDrawer() {
  const { isE } = useUiTheme();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!isE) return;
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
      if (e.key === "?" && !["INPUT", "TEXTAREA"].includes(e.target.tagName)) setOpen(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isE]);

  useEffect(() => {
    if (isE) {
      if (open) document.documentElement.classList.add("pmc-help-open");
      else document.documentElement.classList.remove("pmc-help-open");
    }
    return () => document.documentElement.classList.remove("pmc-help-open");
  }, [open, isE]);

  if (!isE) return null;

  const filtered = FAQS.filter(
    (f) => !q || f.q.toLowerCase().includes(q.toLowerCase()) || f.a.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <>
      <button
        type="button"
        className="pmc-helpfab"
        onClick={() => setOpen(true)}
        aria-label="Open help"
        data-testid="pmc-help-fab"
      >
        <svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>
        <span>Help</span>
      </button>
      <div
        className="pmc-drawer-scrim"
        onClick={() => setOpen(false)}
        aria-hidden={!open}
        data-testid="pmc-drawer-scrim"
      />
      <aside
        className="pmc-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Help & FAQs"
        data-testid="pmc-help-drawer"
      >
        <div className="pmc-drawer__head">
          <div>
            <div className="pmc-eyebrow">Help &amp; FAQs</div>
            <b>Search or ask</b>
          </div>
          <button
            type="button"
            className="pmc-btn pmc-btn--ghost pmc-btn--sm"
            onClick={() => setOpen(false)}
            data-testid="pmc-help-close"
          >
            Close <span className="pmc-kbd">Esc</span>
          </button>
        </div>
        <div className="pmc-drawer__body">
          <label className="pmc-search" style={{ margin: "12px 0" }}>
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>
            <input
              className="pmc-input"
              placeholder="Type a keyword…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              data-testid="pmc-help-search"
            />
          </label>
          <div>
            {filtered.length === 0 ? (
              <p className="pmc-muted">No answer matches yet. Contact the PMC desk below.</p>
            ) : (
              filtered.map((f, i) => (
                <details key={i} className="pmc-faq">
                  <summary>{f.q}</summary>
                  <p>{f.a}</p>
                </details>
              ))
            )}
          </div>
        </div>
        <div className="pmc-drawer__foot">
          <a href="mailto:admin@mail.pmcmanagers.com" className="pmc-btn pmc-btn--secondary pmc-btn--sm">
            Email the desk
          </a>
          <a href="/help" className="pmc-btn pmc-btn--brass pmc-btn--sm">
            Open Help Centre
          </a>
        </div>
      </aside>
    </>
  );
}
