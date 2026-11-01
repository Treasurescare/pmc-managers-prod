import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";
import { ManualLink } from "./ManualLink";

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
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [guides, setGuides] = useState(null);

  // v51m — several static pages still ship their own dead mockup drawer
  // markup (search box with no handler, "Feedback" button, "New supplier?"
  // promo). Both drawers share the .pmc-drawer / .pmc-helpfab classes, so
  // the dead static one rendered on top and its search did nothing.
  // Remove the non-React duplicates on mount and on every route change.
  //
  // v51u — CRITICAL guard: real React dialogs (licence dialog on Company &
  // KYC, change-request dialog on Account) also use the .pmc-drawer-scrim
  // class. The old blanket removal yanked those scrims out from under React,
  // so closing the dialog threw NotFoundError removeChild and the panel
  // crashed ("This panel hit an error"). Now a scrim is only removed when
  // it shares a parent with a non-React static drawer, and never when it
  // carries inline display:block (React dialogs set that explicitly).
  useEffect(() => {
    if (!isE) return;
    const scrub = () => {
      document.querySelectorAll("aside.pmc-drawer").forEach((el) => {
        if (el.getAttribute("data-testid") === "pmc-help-drawer") return;
        const parent = el.parentElement;
        el.remove();
        parent?.querySelectorAll(":scope > .pmc-drawer-scrim").forEach((s) => {
          if (s.getAttribute("data-testid") === "pmc-drawer-scrim") return;
          if (s.style.display === "block") return; // React-owned dialog scrim
          s.remove();
        });
      });
      document.querySelectorAll(".pmc-helpfab").forEach((el) => {
        if (el.getAttribute("data-testid") !== "pmc-help-fab") el.remove();
      });
    };
    scrub();
    const t = setInterval(scrub, 1500); // page content can mount after us
    const stop = setTimeout(() => clearInterval(t), 8000);
    return () => { clearInterval(t); clearTimeout(stop); };
  }, [isE, pathname]);

  // v51n — the drawer searched only the 7 built-in FAQs while the Help
  // Centre searched the full 28-guide manual, so the same query ("tender")
  // returned 1 result here but 2/13 there. Load the manual on first open
  // and search both: quick answers first, matching guides below.
  useEffect(() => {
    if (!isE || !open || guides !== null) return;
    let live = true;
    fetch("/api/v1/meta/help")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d) => { if (live) setGuides(Object.entries(d.modules || {})); })
      .catch(() => { if (live) setGuides([]); });
    return () => { live = false; };
  }, [isE, open, guides]);

  useEffect(() => {
    if (!isE) return;
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
      if (e.key === "?" && !["INPUT", "TEXTAREA"].includes(e.target.tagName)) setOpen(true);
    };
    // v49w — PmcLinkPatcher dispatches this when any data-help-open
    // button is clicked. Direct state flip means the drawer opens on
    // the very first click, including the first page load.
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("pmc:open-help", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pmc:open-help", onOpen);
    };
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

  // Supplier-facing guides rank first — the floating drawer is mostly used
  // by public/vendor visitors, while admin manuals still appear below.
  const SURFACE_RANK = { vendor: 0, public: 0, registration: 0, staff: 1, admin: 2, magic: 3 };
  const guideHits = (guides || [])
    .filter(([, m]) => {
      const query = q.trim().toLowerCase();
      if (!query) return false;
      const hay = [m.title, m.purpose, m.url_path,
        ...(m.actions || []).flatMap((a) => [a.label, a.when, a.expected, ...(a.steps || [])])]
        .join(" ").toLowerCase();
      return query.split(/\s+/).every((w) => hay.includes(w));
    })
    .sort((a, b) => (SURFACE_RANK[a[1].surface] ?? 2) - (SURFACE_RANK[b[1].surface] ?? 2))
    .slice(0, 6);

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
          <ManualLink pathname={pathname} />
          <div>
            {filtered.length === 0 && guideHits.length === 0 && (
              <p className="pmc-muted">No answer matches yet. Contact the PMC desk below.</p>
            )}
            {filtered.map((f, i) => (
              <details key={i} className="pmc-faq">
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
            {q.trim() && guideHits.length > 0 && (
              <div style={{ marginTop: 14 }} data-testid="help-drawer-guides">
                <div className="pmc-eyebrow" style={{ margin: "6px 0 8px" }}>From the full manual</div>
                {guideHits.map(([code, m]) => (
                  <a key={code} href={`/help/${code}`}
                     data-testid={`help-drawer-guide-${code}`}
                     style={{ display: "block", padding: "10px 12px", marginBottom: 8,
                              border: "1px solid var(--line, #ddd)", borderRadius: 8,
                              textDecoration: "none", color: "inherit" }}>
                    <b style={{ fontSize: 14 }}>{m.title}</b>
                    <div className="pmc-muted" style={{ fontSize: 12, marginTop: 2 }}>
                      {(m.purpose || "").slice(0, 90)}{(m.purpose || "").length > 90 ? "…" : ""}
                    </div>
                  </a>
                ))}
              </div>
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
