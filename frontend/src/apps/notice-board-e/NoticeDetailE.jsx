import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import NoticeShareBar from "@/apps/notice-board-e/NoticeShareBar";
import { useUiTheme } from "@/context/UiThemeContext";
import useAuthSession from "@/lib/useAuthSession";
import { adminApi, staffApi, vendorApi, corrigendaApi, publicApi, api } from "@/lib/api";
import { NoticeVendorPanel } from "./NoticeVendorPanel";

// ── local formatters (no fabricated data — everything derives from the live notice) ──
const fmtMoney = (amt, cur) => {
  if (!amt || Number(amt) <= 0) return "—";
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: cur || "USD", maximumFractionDigits: 0 }).format(amt);
  } catch { return `${cur || ""} ${Number(amt).toLocaleString()}`; }
};
const relTime = (iso) => {
  if (!iso) return "—";
  const secs = Math.max(0, Math.floor((new Date(iso) - new Date()) / 1000));
  const d = Math.floor(secs / 86400), h = Math.floor((secs % 86400) / 3600), m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
};
const shortDT = (iso) => {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return `${d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}, ${d.toISOString().slice(11, 16)} UTC`;
  } catch { return ""; }
};
const shortDay = (iso) => {
  if (!iso) return "";
  try { return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }); } catch { return ""; }
};
const fmtSize = (b) => {
  const n = Number(b) || 0;
  if (n >= 1048576) return `${(n / 1048576).toFixed(1)} MB`;
  if (n >= 1024) return `${Math.round(n / 1024)} KB`;
  return `${n} B`;
};
const fmtKind = (ct, fn) => {
  const ext = (fn || "").split(".").pop();
  if (ext && ext.length <= 5 && ext !== fn) return ext.toUpperCase();
  return String(ct || "FILE").split("/").pop().toUpperCase().slice(0, 8);
};
const docTypeLabel = (t) => {
  const v = (t || "tender").toLowerCase();
  return v === "rfp" ? "RFP" : v === "rfq" ? "RFQ" : "Tender";
};
const statusPill = (s, closed) => {
  const v = (s || "").toLowerCase();
  if (v === "awarded") return { t: "Awarded", c: "pmc-pill--info" };
  if (closed || v === "closed") return { t: "Closed", c: "pmc-pill--warning" };
  return { t: "Open for bids", c: "pmc-pill--success" };
};

export default function NoticeDetailE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const { noticeRef } = useParams();
  const { role, me, dashboardPath, loading } = useAuthSession();
  const authed = Boolean(role);
  const initial = (me?.name || me?.email || role || "?").slice(0, 1).toUpperCase();

  const [corrigenda, setCorrigenda] = useState([]);
  const [notice, setNotice] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [packUrl, setPackUrl] = useState(null);
  const [closed, setClosed] = useState(false);
  const [packBusy, setPackBusy] = useState(false);

  useEffect(() => {
    if (!isE || !noticeRef) return;
    corrigendaApi.listPublic(noticeRef)
      .then((r) => setCorrigenda(r.items || []))
      .catch(() => setCorrigenda([]));
  }, [isE, noticeRef]);

  useEffect(() => {
    if (!isE || !noticeRef) return;
    let cancelled = false;
    publicApi.getNotice(noticeRef).then((n) => {
      if (cancelled) return;
      setNotice(n || null);
      setLoaded(true);
      const isClosed = n?.status === "closed" || n?.status === "awarded"
        || (!!n?.submission_deadline && new Date(n.submission_deadline).getTime() < Date.now());
      setClosed(isClosed);
      if (n?.tender_template_id) {
        setPackUrl(`/api/v1/tender-templates/${n.tender_template_id}/public/zip?notice_ref=${encodeURIComponent(noticeRef)}`);
      } else if ((n?.primary_document && n.primary_document.url) || (Array.isArray(n?.attachments) && n.attachments.length)) {
        setPackUrl(`/api/v1/notices/${encodeURIComponent(noticeRef)}/pack`);
      } else {
        setPackUrl("");
      }
    }).catch(() => {
      if (cancelled) return;
      setNotice(null);
      setLoaded(true);
      setPackUrl("");
    });
    return () => { cancelled = true; };
  }, [isE, noticeRef]);

  const downloadPack = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!packUrl || packBusy) return;
    setPackBusy(true);
    toast.info("Preparing your download…");
    try {
      const res = await api.get(packUrl, { responseType: "blob" });
      const cd = res.headers?.["content-disposition"] || "";
      const m = cd.match(/filename="?([^";]+)"?/);
      const fname = m ? m[1] : `${noticeRef || "tender"}-pack${(res.headers?.["content-type"] || "").includes("zip") ? ".zip" : ""}`;
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      toast.success("Download started");
    } catch (err) {
      const s = err?.response?.status;
      if (s === 401) toast.error("Sign in as a registered supplier, then retry.");
      else if (s === 402) toast.error("A document download fee applies to this tender — use “Pay & unlock” above.");
      else if (s === 404) toast.error("The tender documents are no longer linked to this notice.");
      else toast.error("Couldn't download the pack. Try again.");
    } finally {
      setPackBusy(false);
    }
  };

  const signOut = async () => {
    try { await adminApi.logout(); } catch { /* ignore */ }
    try { await staffApi.logout(); } catch { /* ignore */ }
    try { await vendorApi.logout(); } catch { /* ignore */ }
    toast.success("Signed out");
    window.location.href = "/login";
  };

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  // Derived live content (safe when notice is null)
  const docs = [];
  if (notice?.primary_document && notice.primary_document.url) docs.push(notice.primary_document);
  (notice?.attachments || []).forEach((a) => { if (a && a.url) docs.push(a); });
  const docHref = (a) => `/api/v1/uploads/public-files/${(a.url || "").replace("/api/v1/uploads/files/", "")}?download=1`;

  const latestCorr = [...(corrigenda || [])]
    .filter((c) => c && c.is_active !== false)
    .sort((a, b) => (a.corrigendum_no || 0) - (b.corrigendum_no || 0))
    .pop();

  const emdText = (() => {
    if (!notice) return "—";
    const pct = notice.emd_percentage ?? notice.emd_config?.percentage;
    const amt = notice.emd_amount ?? notice.emd_config?.fixed_amount;
    const cur = notice.emd_currency || notice.emd_config?.currency || notice.budget_currency;
    if (amt && Number(amt) > 0) return pct && Number(pct) > 0 ? `${fmtMoney(amt, cur)} (${pct}% of bid)` : fmtMoney(amt, cur);
    if (pct && Number(pct) > 0) return `${pct}% of bid value`;
    return "—";
  })();

  const requiredLicenses = Array.isArray(notice?.required_licenses) ? notice.required_licenses : [];
  const sp = statusPill(notice?.status, closed);
  const startBidTo = authed && role === "vendor"
    ? `/vendor/workspace/new?notice=${noticeRef}`
    : (authed ? dashboardPath : "/register");

  return (
    <div data-testid="notice-detail-e" data-pmc-e-page="notice-detail-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <Link to="/" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></Link>
  <nav className="pmc-nav">
    <Link to="/tenders/live" className="is-on">Tenders</Link>
    <Link to="/suppliers">For suppliers</Link>
    <Link to="/buyers">For buyers</Link>
    <Link to="/trust">Trust &amp; security</Link>
    <Link to="/help">Help &amp; FAQs</Link>
  </nav>
  <div className="pmc-top__act">
    <button className="pmc-btn pmc-btn--onchrome pmc-btn--sm">
      <svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN
    </button>
    {loading ? null : authed ? (
      <>
        <Link to={dashboardPath} className="pmc-btn pmc-btn--onchrome" data-testid="notice-topbar-dashboard"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
          <span aria-hidden="true" style={{
            width: 24, height: 24, borderRadius: "50%", background: "var(--brass-on-chrome, #D2B46A)",
            color: "var(--chrome-ink, #0E1C14)", display: "inline-flex", alignItems: "center",
            justifyContent: "center", fontSize: 11, fontWeight: 700,
          }}>{initial}</span>
          Dashboard
        </Link>
        <button onClick={signOut} className="pmc-btn pmc-btn--onchrome" data-testid="notice-topbar-signout">
          Sign out
        </button>
      </>
    ) : (
      <>
        <Link to="/login" className="pmc-btn pmc-btn--onchrome" data-testid="notice-topbar-signin">Sign in</Link>
        <Link to="/register" className="pmc-btn pmc-btn--brass" data-testid="notice-topbar-register">Register as supplier</Link>
      </>
    )}
  </div>
</div></header>

{!loaded ? (
  <section className="pmc-chrome" style={{ padding: "64px 0" }} data-testid="notice-detail-loading"><div className="pmc-wrap">
    <div className="pmc-muted" style={{ fontSize: "15px" }}>Loading tender notice…</div>
  </div></section>
) : !notice ? (
  <section className="pmc-chrome" style={{ padding: "72px 0" }} data-testid="notice-detail-empty"><div className="pmc-wrap" style={{ textAlign: "center" }}>
    <div className="pmc-eyebrow" style={{ justifyContent: "center" }}>Tender notice</div>
    <h1 className="pmc-display" style={{ fontSize: "40px", lineHeight: "46px", margin: "10px 0 12px" }}>This notice isn't available</h1>
    <p className="pmc-muted" style={{ fontSize: "15px", maxWidth: "520px", margin: "0 auto 24px" }}>
      The reference you followed may have been withdrawn, closed or never published. Browse the live tender board for current notices.
    </p>
    <Link to="/tenders/live" className="pmc-btn pmc-btn--brass pmc-btn--lg" data-testid="notice-empty-browse">View open tenders</Link>
  </div></section>
) : (
<>
<section className="pmc-chrome" style={{ padding: "28px 0 32px" }}><div className="pmc-wrap">
  <div className="pmc-crumb"><Link to="/tenders/live">Tender notices</Link>/<Link to="/tenders/live">{notice.category || "General"}</Link>/<span>{notice.notice_ref}</span></div>
  {authed && role === "vendor" && <NoticeVendorPanel noticeRef={notice.notice_ref} />}
  <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "40px", alignItems: "end", margin: "16px 0 24px" }}>
    <div><div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "12px" }}><span className="pmc-tag" style={{ borderColor: "var(--chrome-line)", color: "var(--on-chrome)" }}>{docTypeLabel(notice.document_type)}</span><span className="pmc-ref">{notice.notice_ref}</span>{latestCorr && (<span className="pmc-pill pmc-pill--info">Corrigendum {latestCorr.corrigendum_no} · {shortDay(latestCorr.effective_from || latestCorr.published_at)}</span>)}<span className={`pmc-pill ${sp.c}`}>{sp.t}</span></div>
      <h1 className="pmc-display" style={{ fontSize: "48px", lineHeight: "52px", margin: "0", maxWidth: "900px" }}>{notice.title || notice.notice_ref}</h1>
      <NoticeShareBar noticeRef={notice.notice_ref} title={notice.title} />
      {(notice.published_at || notice.created_by_email) && (
        <div data-testid="notice-e-posted-by" style={{ marginTop: "10px", fontSize: "13px", letterSpacing: "0.02em", color: "#C9C2AC" }}>
          {[notice.published_at ? `Published ${String(notice.published_at).slice(0, 10)}` : null, notice.created_by_email ? `Posted by ${notice.created_by_email}` : null].filter(Boolean).join(" · ")}
        </div>
      )}
    </div>
    <div style={{ display: "flex", gap: "8px" }}>
      <button className="pmc-btn pmc-btn--onchrome"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg> Follow</button>
      {!authed ? (
        <Link to="/register" className="pmc-btn pmc-btn--onchrome" data-testid="notice-download-pack"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Download pack</Link>
      ) : packUrl ? (
        <button type="button" className="pmc-btn pmc-btn--onchrome" data-testid="notice-download-pack"
          disabled={packBusy} onClick={downloadPack}>
          <svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> {packBusy ? "Preparing…" : "Download pack"}
        </button>
      ) : (
        <button type="button" className="pmc-btn pmc-btn--onchrome" data-testid="notice-download-pack"
          data-pack-state={packUrl === null ? "loading" : "empty"}
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); toast.info(packUrl === null ? "Preparing the document list…" : "No documents available for this tender"); }}>
          <svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Download pack
        </button>
      )}
      {closed ? (
        <span className="pmc-btn pmc-btn--brass pmc-btn--lg" data-testid="notice-start-bid" aria-disabled="true" style={{ opacity: 0.55, cursor: "not-allowed", pointerEvents: "none" }}>Bidding closed</span>
      ) : (
        <Link to={startBidTo} className="pmc-btn pmc-btn--brass pmc-btn--lg" data-testid="notice-start-bid">Start bid</Link>
      )}
    </div>
  </div>
  <dl className="pmc-facts" style={{ margin: "0" }}><div><dt>Indicative budget</dt><dd>{fmtMoney(notice.budget_amount, notice.budget_currency)}</dd></div><div><dt>EMD</dt><dd>{emdText}</dd></div><div><dt>Tender fee</dt><dd>{notice.tender_fee ? fmtMoney(notice.tender_fee, notice.budget_currency) : "None"}</dd></div><div><dt>Delivery</dt><dd>{notice.delivery_country || "—"}</dd></div><div><dt>Form of contract</dt><dd>{notice.form_of_contract || "Standard"}</dd></div><div><dt>Closes in</dt><dd><span style={{ color: "var(--brass-on-chrome)", fontSize: "15px" }}>{relTime(notice.submission_deadline)}</span></dd></div></dl>
</div></section>
<div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 360px", gap: "32px", padding: "28px 0 72px", alignItems: "start" }}>
  <div>
    <div className="pmc-tabs" role="tablist" style={{ marginBottom: "24px" }}><button className="pmc-tab" aria-selected="true">Overview</button><button className="pmc-tab">Eligibility</button><button className="pmc-tab">Documents{docs.length > 0 && <span className="n">{docs.length}</span>}</button><button className="pmc-tab">Clarifications</button><button className="pmc-tab" data-testid="notice-e-tab-corrigenda"
      onClick={() => document.getElementById("notice-e-corrigenda")?.scrollIntoView({ behavior: "smooth", block: "start" })}>Corrigenda{corrigenda.length > 0 && <span className="n">{corrigenda.length}</span>}</button></div>
    <section className="dt-sec"><h2>Scope</h2>
      {notice.description
        ? <p style={{ whiteSpace: "pre-line" }}>{notice.description}</p>
        : <p className="pmc-muted">No scope summary has been published for this tender yet.</p>}
    </section>
    <section className="dt-sec"><h2>Who can bid</h2><ul className="dt-list">
      <li><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><span>Registered supplier with approved KYC on the PMC Tender Board</span></li>
      {requiredLicenses.length > 0 && (
        <li><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><span>Required licences: {requiredLicenses.map((l, i) => (<b key={i}>{i > 0 ? ", " : ""}{l}</b>))}</span></li>
      )}
      {notice.eligibility && (
        <li><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><span style={{ whiteSpace: "pre-line" }}>{notice.eligibility}</span></li>
      )}
    </ul>
      {!authed && (
        <div className="pmc-callout pmc-callout--info" style={{ marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg><div>Registered suppliers see a <b>KYC match check</b> here before starting a bid. <Link to="/login">Sign in</Link> to check yours.</div></div>
      )}</section>
    <section className="dt-sec"><h2>Documents</h2><div className="pmc-panel">
      {docs.length > 0 ? docs.map((a, i) => (
        <div className="pmc-docrow" key={i} data-testid={`notice-doc-row-${i}`}><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>{a.file_name || `Document ${i + 1}`}</b><span className="s">{fmtKind(a.content_type, a.file_name)} · {fmtSize(a.size_bytes)}</span></div><span></span><a href={docHref(a)} className="pmc-btn pmc-btn--secondary pmc-btn--sm" data-testid={`notice-doc-download-${i}`}>Download</a></div>
      )) : (
        <div className="pmc-muted" style={{ padding: "18px 4px", fontSize: "13px" }} data-testid="notice-docs-empty">No documents have been published for this tender yet.</div>
      )}
    </div></section>
    <section className="dt-sec"><h2>Clarifications</h2>
      <div className="pmc-muted" style={{ fontSize: "14px" }} data-testid="notice-clarifications-empty">No clarifications have been published for this tender yet. Answers to bidder questions appear here and are shared with all bidders.</div>
      {!closed && (
        <a href="#" className="pmc-btn pmc-btn--secondary" style={{ marginTop: "12px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Ask a question</a>
      )}
    </section>
  </div>
  <aside style={{ display: "grid", gap: "16px", position: "sticky", top: "96px" }}>
    <div className="pmc-card" style={{ padding: "22px" }}>
      <div className="pmc-eyebrow">Submission closes</div>
      <div style={{ fontSize: "28px", lineHeight: "36px", margin: "6px 0 2px" }}>{relTime(notice.submission_deadline)}</div>
      <div className="pmc-muted" style={{ fontSize: "13px" }}>{shortDT(notice.submission_deadline) || "To be announced"}</div>
      <hr style={{ border: "0", borderTop: "1px solid var(--line)", margin: "16px 0" }} />
      <dl className="pmc-kv"><dt>Withdrawal</dt><dd>Allowed before deadline</dd><dt>Currency</dt><dd>{notice.budget_currency || "USD"}</dd></dl>
      {closed ? (
        <span className="pmc-btn pmc-btn--primary pmc-btn--lg" data-testid="notice-aside-start-bid" aria-disabled="true" style={{ width: "100%", marginTop: "18px", opacity: 0.55, cursor: "not-allowed", pointerEvents: "none", textAlign: "center" }}>Bidding closed</span>
      ) : (
        <Link to={startBidTo} className="pmc-btn pmc-btn--primary pmc-btn--lg" style={{ width: "100%", marginTop: "18px" }} data-testid="notice-aside-start-bid">Start bid</Link>
      )}
      {!authed && !closed && (
        <div className="pmc-muted" style={{ fontSize: "12px", textAlign: "center", marginTop: "8px" }}>New supplier? <Link to="/register">Register first</Link> — about 15 minutes</div>
      )}
    </div>
    <div className="pmc-panel" style={{ padding: "20px" }}><b style={{ fontSize: "15px" }}>Key dates</b><div className="pmc-timeline" style={{ marginTop: "14px" }} data-testid="notice-e-key-dates">
      {(() => {
        const fmtDay = (v) => v ? new Date(v).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : null;
        const fmtDT = (v) => v ? new Date(v).toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }) : null;
        const now = Date.now();
        const rows = [];
        if (notice.published_at) rows.push({ t: new Date(notice.published_at).getTime(), label: "Published", val: fmtDay(notice.published_at) });
        (corrigenda || []).forEach((c) => {
          const d = c.effective_from || c.published_at;
          rows.push({ t: d ? new Date(d).getTime() : now, label: `Corrigendum ${c.corrigendum_no}`, val: [fmtDay(d), c.title].filter(Boolean).join(" · ") });
        });
        if (notice.pre_bid_meeting_date) rows.push({ t: new Date(notice.pre_bid_meeting_date).getTime(), label: "Pre-bid meeting", val: fmtDT(notice.pre_bid_meeting_date) });
        if (notice.clarification_deadline) rows.push({ t: new Date(notice.clarification_deadline).getTime(), label: "Clarifications close", val: fmtDT(notice.clarification_deadline) });
        if (notice.submission_deadline) rows.push({ t: new Date(notice.submission_deadline).getTime(), label: "Bid submission closes", val: fmtDT(notice.submission_deadline) });
        rows.sort((a, b) => a.t - b.t);
        if (!rows.length) return <div className="pmc-muted" style={{ fontSize: "13px" }}>Key dates will appear once this notice is published.</div>;
        const firstFuture = rows.findIndex((r) => r.t >= now);
        return rows.map((r, i) => {
          const cls = r.t < now ? "done" : (i === firstFuture ? "now" : "");
          return <div key={i} className={cls} data-testid={`notice-e-date-${i}`}><span className="dot"></span><div><b>{r.label}</b><span>{r.val}</span></div></div>;
        });
      })()}
    </div></div>
    <div className="pmc-panel" style={{ padding: "16px 20px" }}><div className="pmc-hashline"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Notice sealed on the audit ledger</span></div>{(corrigenda || []).map((c) => (<div key={c.id} className="pmc-hashline" style={{ marginTop: "6px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Corrigendum {c.corrigendum_no} issued · {(c.effective_from || c.published_at || "").slice(0, 10)}</span></div>))}</div>
  </aside>
</div>
{corrigenda.length > 0 && (
  <div className="pmc-wrap" id="notice-e-corrigenda" data-testid="notice-e-corrigenda"
       style={{ padding: "0 0 48px" }}>
    <section className="pmc-panel" style={{ padding: "24px" }}>
      <div className="pmc-eyebrow">Amendments in force</div>
      <h2 style={{ fontSize: "22px", fontWeight: 600, margin: "6px 0 6px" }}>Corrigenda &amp; amendments</h2>
      <p className="pmc-muted" style={{ fontSize: "13px", margin: "0 0 20px" }}>
        Every change to this tender is issued as a versioned corrigendum. The tables below
        show exactly which field changed, the before / after values and the reason.
      </p>
      <div style={{ display: "grid", gap: "20px" }}>
        {corrigenda.map((c) => (
          <article key={c.id} data-testid={`corr-e-${c.corrigendum_no}`}
                   style={{ border: "1px solid var(--line)", borderLeft: "3px solid var(--brass-on-chrome, #D2B46A)", padding: "18px" }}>
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "baseline", gap: "10px" }}>
              <span className="pmc-ref">Corrigendum {c.corrigendum_no}</span>
              <b style={{ fontSize: "15px", flex: 1 }}>{c.title}</b>
              <span className="pmc-muted" style={{ fontSize: "12px", fontFamily: "monospace" }}
                    data-testid={`corr-e-date-${c.corrigendum_no}`}>
                {(c.effective_from || c.published_at || "").slice(0, 10)}
              </span>
            </div>
            <p style={{ fontSize: "14px", margin: "10px 0 0", whiteSpace: "pre-line" }}>{c.summary}</p>
            {c.new_submission_deadline && (
              <div style={{ marginTop: "10px", display: "inline-block", fontSize: "12px",
                            background: "#FFF7E6", border: "1px solid #E7D3A1", padding: "6px 10px" }}>
                New bid deadline: <b>{c.new_submission_deadline.slice(0, 16).replace("T", " ")}</b>
              </div>
            )}
            {(c.field_amendments || []).length > 0 && (
              <div style={{ marginTop: "14px", overflowX: "auto", border: "1px solid var(--line)" }}
                   data-testid={`corr-e-table-${c.corrigendum_no}`}>
                <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "var(--brand-pale, #F3EFE4)", textAlign: "left" }}>
                      <th style={{ padding: "8px 10px", fontSize: "11px", letterSpacing: ".08em", textTransform: "uppercase" }}>Field</th>
                      <th style={{ padding: "8px 10px", fontSize: "11px", letterSpacing: ".08em", textTransform: "uppercase" }}>Before</th>
                      <th style={{ padding: "8px 10px", fontSize: "11px", letterSpacing: ".08em", textTransform: "uppercase" }}>After</th>
                      <th style={{ padding: "8px 10px", fontSize: "11px", letterSpacing: ".08em", textTransform: "uppercase" }}>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.field_amendments.map((a, idx) => (
                      <tr key={idx} style={{ borderTop: "1px solid var(--line)", verticalAlign: "top" }}>
                        <td style={{ padding: "8px 10px", fontWeight: 600 }}>{a.field}</td>
                        <td style={{ padding: "8px 10px", color: "#8C2B2B", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{a.before || "—"}</td>
                        <td style={{ padding: "8px 10px", color: "#1E6B44", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{a.after || "—"}</td>
                        <td style={{ padding: "8px 10px", color: "var(--ink-muted)", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{a.note || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {(c.attachments || []).length > 0 && (
              <div style={{ marginTop: "12px", display: "flex", flexWrap: "wrap", gap: "8px" }}
                   data-testid={`corr-e-attachments-${c.corrigendum_no}`}>
                {c.attachments.map((a) => (
                  <a key={a.key || a.file_name} href={a.url} target="_blank" rel="noreferrer"
                     className="pmc-btn pmc-btn--secondary pmc-btn--sm">
                    {a.file_name}
                  </a>
                ))}
              </div>
            )}
            <div style={{ marginTop: "12px", display: "flex", gap: "8px" }}
                 data-testid={`corr-e-pdf-row-${c.corrigendum_no}`}>
              <a href={`/api/v1/notices/${noticeRef}/corrigenda/${c.id}/pdf`}
                 target="_blank" rel="noreferrer"
                 data-testid={`corr-e-pdf-${c.corrigendum_no}`}
                 className="pmc-btn pmc-btn--brass pmc-btn--sm">
                Download diff PDF
              </a>
            </div>
          </article>
        ))}
      </div>
    </section>
  </div>
)}
</>
)}
<footer className="pmc-chrome" style={{ padding: "40px 0 28px", marginTop: "0" }}><div className="pmc-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
  <div className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "20px" }}>PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></div>
  <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: "20px" }} className="pmc-fcol"><Link to="/tenders/live">Open notices</Link><Link to="/help">Help Centre</Link><Link to="/trust">Trust &amp; security</Link><Link to="/privacy">Privacy</Link><span className="pmc-muted">© 2026 PMC Managers Limited</span></div>
</div></footer>

<div className="pmc-drawer-scrim" data-help-close=""></div>
<aside className="pmc-drawer" role="dialog" aria-modal="true" aria-label="Help and FAQs">
  <div className="pmc-drawer__head">
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
      <div><div className="pmc-eyebrow">Help &amp; FAQs</div><div style={{ fontSize: "20px", lineHeight: "28px", fontWeight: "600" }}>How can we help?</div></div>
      <button className="pmc-btn pmc-btn--ghost pmc-btn--sm" data-help-close="" aria-label="Close help">Close <span className="pmc-kbd">Esc</span></button>
    </div>
    <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input data-help-q="" placeholder="Search help, e.g. “bank guarantee”" /></label>
  </div>
  <div className="pmc-drawer__body">
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Tender detail</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Download the full pack</b>One ZIP with every document at its latest version.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Ask before the clarification deadline</b>Answers are shared with all bidders.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Follow this tender</b>You'll be alerted to corrigenda and deadline changes.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details><details className="pmc-faq" data-cat="emd"><summary>Which currencies are supported?</summary><p>Budgets and bids are shown in the tender's own currency, for example USD, KZT or INR. The tender states whether multi-currency bids are allowed.</p></details><details className="pmc-faq" data-cat="awards"><summary>How are contracts signed?</summary><p>Awards, purchase orders and contracts are signed with DocuSign, either inside the portal or through a DocuSign email link. Signed copies appear under <b>Signatures</b>.</p></details></div>
    <p data-help-empty="" hidden style={{ color: "var(--ink-muted)", fontSize: "14px" }}>No answer matches yet. Raise a ticket below and the PMC desk will reply.</p>
    <Link to="/help" className="pmc-btn pmc-btn--secondary" style={{ width: "100%", marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Open the full Help Centre</Link>
  </div>
  <div className="pmc-drawer__foot">
    <a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a>
    <a href="mailto:tenders@pmcmanagers.com" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-mail" /></svg> Email the desk</a>
  </div>
</aside>
<button className="pmc-helpfab" data-help-open="" aria-label="Open help"><span className="pmc-helpfab__q">?</span>Help</button>
    </div>
  );
}
