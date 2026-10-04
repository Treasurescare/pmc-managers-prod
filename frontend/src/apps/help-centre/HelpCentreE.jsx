import { useEffect, useMemo, useRef, useState } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { toast } from "sonner";

// v51l — the Help Centre was a static mockup: every card, tour, the search
// box and "Raise a ticket" were <a href="#"> dead ends. Now wired to the
// real manual served at /api/v1/meta/help and the public ticket endpoint.

const TOPICS = [
  { key: "getting-started", icon: "i-play",   title: "Getting started",       blurb: "Tour the portal, create your account, set up two-factor sign-in.", codes: ["vendor-portal", "public-board", "registration-portal"] },
  { key: "registration",    icon: "i-shield", title: "Registration & KYC",    blurb: "Documents by country and category, licences, resuming a registration.", codes: ["registration-portal", "admin-registrations", "admin-vendors"] },
  { key: "tenders",         icon: "i-search", title: "Finding tenders",       blurb: "Search, filters, KYC matching, alerts and following a notice.", codes: ["public-board", "admin-notices", "admin-tender-builder", "admin-boq", "admin-catalog", "admin-packages", "admin-corrigenda"] },
  { key: "bidding",         icon: "i-gavel",  title: "Bidding",               blurb: "Technical and commercial envelopes, drafts, withdrawal, corrigenda.", codes: ["admin-bidding", "admin-auctions", "vendor-portal"] },
  { key: "emd",             icon: "i-coin",   title: "EMD & payments",        blurb: "Escrow transfers, bank guarantees, refunds and billing.", codes: ["admin-escrow", "escrow-magic"] },
  { key: "evaluation",      icon: "i-check",  title: "Evaluation & awards",   blurb: "How committees score, L1 comparison, award letters.", codes: ["admin-evaluation", "admin-awards", "admin-vintel", "committee-magic", "admin-meetings"] },
  { key: "signatures",      icon: "i-sign",   title: "Signatures & contracts", blurb: "DocuSign signing, POs, contracts and milestones.", codes: ["admin-docusign", "admin-engagements"] },
  { key: "account",         icon: "i-lock",   title: "Account & privacy",     blurb: "Security, team members, exporting or deleting your data.", codes: ["admin-permissions", "admin-masters", "admin-audit", "staff-portal"] },
];

const SUPPLIER_SURFACES = new Set(["vendor", "public", "registration"]);
const SURFACE_LABEL = { admin: "Buyers & staff", staff: "Buyers & staff", magic: "Buyers & staff",
                        vendor: "Suppliers", public: "Suppliers", registration: "Suppliers" };

function moduleMatchesQuery(m, q) {
  if (!q) return true;
  const hay = [m.title, m.purpose, m.url_path,
    ...(m.actions || []).flatMap((a) => [a.label, a.when, a.expected, ...(a.steps || [])])]
    .join(" ").toLowerCase();
  return q.toLowerCase().split(/\s+/).every((w) => hay.includes(w));
}

function TicketModal({ onClose }) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (fullName.trim().length < 2) { toast.error("Please enter your name"); return; }
    if (message.trim().length < 5) { toast.error("Please describe the issue (at least a few words)"); return; }
    setBusy(true);
    try {
      const r = await fetch("/api/v1/auth/help-request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "other", full_name: fullName.trim(),
                               email: email.trim() || null, message: message.trim() }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${r.status}`);
      }
      toast.success("Ticket raised — the PMC desk will reply in your portal or by email.");
      onClose();
    } catch (e) {
      toast.error(`Could not raise the ticket — ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1200, background: "rgba(10,20,16,0.55)",
                  display: "grid", placeItems: "center", padding: 16 }}
         onClick={onClose} data-testid="help-ticket-modal">
      <div className="pmc-panel" style={{ width: 480, maxWidth: "100%", padding: 22 }}
           onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <b style={{ fontSize: 18 }}>Raise a ticket</b>
          <button type="button" onClick={onClose} data-testid="help-ticket-close"
                  className="pmc-btn pmc-btn--ghost pmc-btn--sm">Close</button>
        </div>
        <div style={{ display: "grid", gap: 10 }}>
          <label style={{ display: "grid", gap: 4, fontSize: 13 }}>
            <span style={{ fontWeight: 600 }}>Your name</span>
            <input className="pmc-input" value={fullName} onChange={(e) => setFullName(e.target.value)}
                   data-testid="help-ticket-name" placeholder="Full name" />
          </label>
          <label style={{ display: "grid", gap: 4, fontSize: 13 }}>
            <span style={{ fontWeight: 600 }}>Email (optional — for the reply)</span>
            <input className="pmc-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                   data-testid="help-ticket-email" placeholder="you@company.com" />
          </label>
          <label style={{ display: "grid", gap: 4, fontSize: 13 }}>
            <span style={{ fontWeight: 600 }}>What do you need help with?</span>
            <textarea className="pmc-input" rows={4} value={message} onChange={(e) => setMessage(e.target.value)}
                      data-testid="help-ticket-message" placeholder="Describe the issue…" />
          </label>
          <button type="button" onClick={submit} disabled={busy}
                  data-testid="help-ticket-submit"
                  className="pmc-btn pmc-btn--primary" style={{ justifyContent: "center" }}>
            {busy ? "Sending…" : "Submit ticket"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function HelpCentreE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [modules, setModules] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [role, setRole] = useState("supplier");
  const [topic, setTopic] = useState(null);
  const [query, setQuery] = useState("");
  const [ticketOpen, setTicketOpen] = useState(false);
  const articlesRef = useRef(null);

  useEffect(() => {
    if (!isE) return;
    let live = true;
    fetch("/api/v1/meta/help")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d) => { if (live) { setModules(d.modules || {}); setLoading(false); } })
      .catch((e) => { if (live) { setLoadError(e.message); setLoading(false); } });
    return () => { live = false; };
  }, [isE]);

  const roleModules = useMemo(() => {
    const wantSupplier = role === "supplier";
    return Object.entries(modules).filter(([, m]) =>
      wantSupplier ? SUPPLIER_SURFACES.has(m.surface) : !SUPPLIER_SURFACES.has(m.surface));
  }, [modules, role]);

  // v51m — topic cards search the ENTIRE manual regardless of the selected
  // role (each guide carries a "Suppliers / Buyers & staff" chip). Role tabs
  // only scope the unfiltered library view. Previously a supplier clicking
  // "Signatures & contracts" or "EMD & payments" got "No guide matches"
  // because those topics map to admin-surface modules.
  const allModules = useMemo(() => Object.entries(modules), [modules]);

  const visibleModules = useMemo(() => {
    const t = TOPICS.find((x) => x.key === topic);
    const base = t ? allModules : roleModules;
    return base.filter(([code, m]) =>
      (!t || t.codes.includes(code)) && moduleMatchesQuery(m, query.trim()));
  }, [allModules, roleModules, topic, query]);

  const topicCount = (t) => allModules.filter(([code]) => t.codes.includes(code)).length;

  const pickTopic = (key) => {
    setTopic((cur) => (cur === key ? null : key));
    setTimeout(() => articlesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
  };

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="help-centre-e" data-pmc-e-page="help-centre-e">
      <header className="pmc-chrome" style={{ borderBottom: "1px solid var(--chrome-line)" }}>
        <div className="hc-wrap" style={{ display: "flex", alignItems: "center", height: 64, gap: 24 }}>
          <a href="/" style={{ display: "flex", flexDirection: "column", color: "var(--on-chrome)", textDecoration: "none" }}>
            <span style={{ fontFamily: "var(--font-display)", fontSize: 22, lineHeight: "22px", fontWeight: 600 }}>PMC Managers</span>
            <span className="pmc-eyebrow" style={{ fontSize: 11 }}>Help Centre</span>
          </a>
          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button type="button" onClick={() => (window.history.length > 1 ? window.history.back() : (window.location.href = "/"))}
                    className="pmc-btn pmc-btn--onchrome" data-testid="help-back-to-board">← Back</button>
          </div>
        </div>
      </header>

      <section className="pmc-chrome" style={{ padding: "56px 0 64px" }}>
        <div className="hc-wrap" style={{ textAlign: "center" }}>
          <div className="pmc-eyebrow">Help Centre</div>
          <h1 className="pmc-display" style={{ fontSize: 60, lineHeight: "64px", margin: "10px 0 24px", color: "var(--on-chrome)" }}>What do you need to do?</h1>
          <label className="pmc-search" style={{ maxWidth: 720, margin: "0 auto", height: 56, background: "var(--surface)", borderColor: "var(--surface)" }}>
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>
            <input value={query} onChange={(e) => setQuery(e.target.value)}
                   data-testid="help-search-input"
                   placeholder="Search, e.g. “bank guarantee”, “withdraw bid”, “corrigendum”"
                   style={{ color: "var(--ink)", fontSize: 16 }} />
          </label>
          <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 20 }}>
            <div className="hc-role" role="tablist">
              <button type="button" aria-selected={role === "supplier"} onClick={() => { setRole("supplier"); setTopic(null); }}
                      data-testid="help-role-supplier">I'm a supplier</button>
              <button type="button" aria-selected={role === "staff"} onClick={() => { setRole("staff"); setTopic(null); }}
                      data-testid="help-role-staff">I'm a buyer or PMC staff</button>
            </div>
          </div>
        </div>
      </section>

      <main className="hc-wrap" style={{ padding: "48px 0 96px" }}>
        <h2 className="hc-h">Browse by topic</h2>
        <div className="hc-cats">
          {TOPICS.map((t) => (
            <button key={t.key} type="button" onClick={() => pickTopic(t.key)}
                    className="hc-cat" data-testid={`help-topic-${t.key}`}
                    style={{ textAlign: "left", cursor: "pointer", background: "none",
                             border: topic === t.key ? "2px solid var(--brass)" : undefined }}>
              <span className="hc-cat__i"><svg className="pmc-ico" aria-hidden="true"><use href={`#${t.icon}`} /></svg></span>
              <h3>{t.title}</h3>
              <p>{t.blurb}</p>
              <span className="pmc-muted" style={{ fontSize: 12, fontWeight: 600 }}>
                {topicCount(t)} guide{topicCount(t) === 1 ? "" : "s"}
              </span>
            </button>
          ))}
        </div>

        <section ref={articlesRef} style={{ marginTop: 48 }}>
          <h2 className="hc-h">
            {topic ? `${TOPICS.find((x) => x.key === topic)?.title} — guides` : (query ? `Results for “${query}”` : "Guides")}
            <span className="pmc-muted" style={{ fontSize: 13, marginLeft: 10 }}>{visibleModules.length} shown</span>
          </h2>
          {loading && <p className="pmc-muted" data-testid="help-loading">Loading guides…</p>}
          {loadError && <p className="pmc-muted" data-testid="help-load-error">Could not load the guides ({loadError}). Please try again.</p>}
          {!loading && !loadError && visibleModules.length === 0 && (
            <p className="pmc-muted" data-testid="help-no-results">No guide matches. Try a different search, or raise a ticket below.</p>
          )}
          <div style={{ display: "grid", gap: 10 }}>
            {visibleModules.map(([code, m]) => (
              <details key={code} className="pmc-faq" data-testid={`help-article-${code}`}>
                <summary>
                  {m.title}
                  <span className="pmc-muted" style={{ fontSize: 11, marginLeft: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    {SURFACE_LABEL[m.surface] || m.surface}
                  </span>
                </summary>
                <div style={{ padding: "4px 0 8px" }}>
                  {m.purpose && <p>{m.purpose}</p>}
                  {(m.prerequisites || []).length > 0 && (
                    <p className="pmc-muted" style={{ fontSize: 13 }}>
                      <b>Before you start:</b> {m.prerequisites.join(" · ")}
                    </p>
                  )}
                  {(m.actions || []).map((a) => (
                    <details key={a.id} className="pmc-faq" style={{ marginLeft: 12 }} data-testid={`help-action-${a.id}`}>
                      <summary style={{ fontSize: 14 }}>{a.label}</summary>
                      <div style={{ padding: "2px 0 6px" }}>
                        {a.when && <p className="pmc-muted" style={{ fontSize: 13, margin: "4px 0" }}>{a.when}</p>}
                        {(a.steps || []).length > 0 && (
                          <ol style={{ margin: "6px 0", paddingLeft: 20, display: "grid", gap: 4, fontSize: 14 }}>
                            {a.steps.map((s, i) => <li key={i}>{s}</li>)}
                          </ol>
                        )}
                        {a.expected && <p style={{ fontSize: 13 }}><b>Expected:</b> {a.expected}</p>}
                      </div>
                    </details>
                  ))}
                </div>
              </details>
            ))}
          </div>
        </section>

        <div style={{ display: "grid", gridTemplateColumns: "1.3fr .7fr", gap: 48, marginTop: 56 }} className="hc-lower">
          <section>
            <h2 className="hc-h">Most asked</h2>
            <div>
              <details className="pmc-faq" open><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details>
              <details className="pmc-faq"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details>
              <details className="pmc-faq"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details>
              <details className="pmc-faq"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details>
              <details className="pmc-faq"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details>
              <details className="pmc-faq"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details>
              <details className="pmc-faq"><summary>Which currencies are supported?</summary><p>Budgets and bids are shown in the tender's own currency, for example USD, KZT or INR. The tender states whether multi-currency bids are allowed.</p></details>
              <details className="pmc-faq"><summary>How are contracts signed?</summary><p>Awards, purchase orders and contracts are signed with DocuSign, either inside the portal or through a DocuSign email link. Signed copies appear under <b>Signatures</b>.</p></details>
              <details className="pmc-faq"><summary>How do I keep my account secure?</summary><p>Turn on two-factor sign-in under <b>Account &rsaquo; Security</b>. On the mobile app you can also sign in with Face ID or fingerprint.</p></details>
            </div>
          </section>
          <aside style={{ display: "grid", gap: 16, alignContent: "start" }}>
            <div className="pmc-panel" style={{ padding: 20 }}>
              <b style={{ fontSize: 16 }}>Still stuck?</b>
              <p className="pmc-muted" style={{ margin: "6px 0 14px", fontSize: 14, lineHeight: "22px" }}>
                Tickets are tracked in your portal, so you can see every reply in one place.
              </p>
              <div style={{ display: "grid", gap: 8 }}>
                <button type="button" onClick={() => setTicketOpen(true)}
                        className="pmc-btn pmc-btn--primary" data-testid="help-ticket-open"
                        style={{ justifyContent: "center" }}>
                  <svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket
                </button>
                <a href="mailto:tenders@pmcmanagers.com" className="pmc-btn pmc-btn--secondary" style={{ justifyContent: "center" }}>
                  <svg className="pmc-ico" aria-hidden="true"><use href="#i-mail" /></svg> tenders@pmcmanagers.com
                </a>
                <a href="mailto:adminsupport@pmcmanagers.com" className="pmc-btn pmc-btn--ghost" style={{ justifyContent: "center" }}>
                  Account &amp; access: adminsupport@pmcmanagers.com
                </a>
              </div>
            </div>
          </aside>
        </div>
      </main>

      {ticketOpen && <TicketModal onClose={() => setTicketOpen(false)} />}
    </div>
  );
}
