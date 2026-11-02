import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { staffApi, bidApi, inspectionApi, uploadsApi, escrowApi, showApiError } from "@/lib/api";
import { OpenCommitteesOpening } from "@/apps/admin-console-e/OpenCommitteesOpening";
import { ChallengesBody } from "@/apps/admin-console-e/AdminChallengesE";
import PortalShellE from "@/apps/shared/PortalShellE";
import PortalAvatarMenu from "@/apps/shared/PortalAvatarMenu";

const ROLE_LABELS = {
  admin: "Administrator", reviewer: "Reviewer",
  escrow_agent: "Escrow Agent", certifier: "Site Certifier",
  legal_counsel: "Legal Counsel", accounting: "Accounting Team",
  committee_member: "Bid Committee", auditor: "Auditor", support: "Support",
  management: "Management", partner: "Partner", agent: "Agent",
};

const ROLE_QUEUE_STATUS = {
  escrow_agent: "emd_paid", certifier: "admin_flagged",
  legal_counsel: "certifier_cleared", accounting: "legal_cleared",
  committee_member: "accounting_cleared",
};

const RELEASE_ACTIONS = [
  { v: "release_to_contractor", l: "Release → Contractor (winning vendor)" },
  { v: "release_to_vendor", l: "Refund → Vendor (bid did not win)" },
  { v: "forfeit", l: "Forfeit (withdrawal / mis-declaration)" },
];

// Option-E theme tokens (defined on [data-ui="e"]). Using the CSS vars keeps
// the staff portal visually identical to the admin console & escrow portals,
// and respects dark mode — while never being washed out by the global remap.
const C = {
  page: "var(--paper)", chrome: "var(--chrome)", chromeLine: "var(--chrome-line)",
  onChrome: "var(--on-chrome)", onChromeMuted: "var(--on-chrome-muted)",
  surface: "var(--surface)", sunken: "var(--surface-sunken)",
  ink: "var(--ink)", muted: "var(--ink-muted)", faint: "var(--ink-subtle)",
  line: "var(--line)", lineStrong: "var(--line-strong)",
  primary: "var(--primary)", onPrimary: "var(--on-primary)", primarySoft: "var(--primary-soft)",
  brass: "var(--brass-on-chrome)", success: "var(--success)", successSoft: "var(--success-soft)",
  danger: "var(--danger)", warning: "var(--warning)", warningSoft: "var(--warning-soft)",
  display: "var(--font-display)",
};

export default function StaffDashboard() {
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [bids, setBids] = useState([]);
  const [inspections, setInspections] = useState([]);
  const [escrow, setEscrow] = useState({ pending_signatures: [], transactions: [] });
  const [processed, setProcessed] = useState({ bids: [], count: 0 });
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    (async () => {
      try {
        const m = await staffApi.me();
        setMe(m);
        if (["admin", "reviewer"].includes(m.active_role)) return nav("/admin");
        await refresh(m);
        const esc = await loadEscrow();
        loadProcessed();
        const params = new URLSearchParams(window.location.search);
        if (params.get("signed") || params.get("event")) {
          const tid = sessionStorage.getItem("pmc.signing.tid");
          window.history.replaceState({}, "", "/staff");
          toast.message("Returned from DocuSign — reconciling signature…");
          setTab("escrow");
          if (tid) { try { await staffApi.escrowRefresh(tid); } catch { /* ignore */ } }
          sessionStorage.removeItem("pmc.signing.tid");
          await loadEscrow();
        } else if ((esc?.pending_signatures_count || 0) > 0) {
          setTab("escrow");
        }
      } catch { nav("/staff/login"); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nav]);

  const refresh = async (m = me) => {
    if (!m) return;
    const status = ROLE_QUEUE_STATUS[m.active_role];
    const [bidsList, inspList] = await Promise.all([
      bidApi.list(status ? { status } : {}).catch(() => []),
      m.active_role === "certifier" ? inspectionApi.list({ certifier_id: "me" }).catch(() => []) : [],
    ]);
    setBids(bidsList || []);
    setInspections(inspList || []);
  };

  const loadEscrow = async () => {
    try { const d = await staffApi.escrowSignatures(); setEscrow(d); return d; }
    catch { setEscrow({ pending_signatures: [], transactions: [] }); return null; }
  };

  const loadProcessed = () =>
    staffApi.myProcessedBids().then(setProcessed).catch(() => setProcessed({ bids: [], count: 0 }));

  const logout = async () => { try { await staffApi.logout(); } catch { /* ignore */ } nav("/login"); };

  const switchRole = async (newRole) => {
    if (!newRole || newRole === me?.active_role) return;
    try {
      await staffApi.switchRole(newRole);
      toast.success(`Switched to ${ROLE_LABELS[newRole] || newRole}`);
      if (newRole === "admin") return nav("/admin");
      const m = await staffApi.me();
      setMe(m);
      await refresh(m);
    } catch (err) { showApiError(err); }
  };

  const decide = async (bid, action, notes) => {
    try {
      await bidApi.decide(bid.id, { action, role: me.active_role, notes: notes || "" });
      toast.success(`Bid ${bid.bid_ref}: ${action}`);
      await refresh();
      loadProcessed();
    } catch (err) { showApiError(err, { fallbackTitle: "Decision failed" }); }
  };

  const committeeAward = async (bid, notes) => {
    try {
      await bidApi.decide(bid.id, { action: "award", role: "committee", notes: notes || "" });
      toast.success(`Bid ${bid.bid_ref} awarded`);
      await refresh();
    } catch (err) { showApiError(err, { fallbackTitle: "Award failed" }); }
  };

  const uploadInspectionMedia = async (ins, file, kind) => {
    try {
      const p = await uploadsApi.presign(file.name, file.type || "image/jpeg", "site-media", file.size);
      const r = await uploadsApi.direct(p.key, file);
      await inspectionApi.addMedia(ins.id, { kind, key: r.key, filename: file.name,
        content_type: file.type || "image/jpeg", size_bytes: r.size_bytes });
      toast.success("Uploaded");
      await refresh();
    } catch (err) { showApiError(err); }
  };

  const completeInspection = async (ins, result) => {
    try {
      await inspectionApi.update(ins.id, { status: "completed", result });
      toast.success("Inspection recorded");
      await refresh();
    } catch (err) { showApiError(err); }
  };

  // ---- Escrow ----
  const openDocuSign = async (tid) => {
    try {
      const r = await staffApi.escrowDocuSignUrl(tid);
      if (r?.url) { sessionStorage.setItem("pmc.signing.tid", tid); window.location.assign(r.url); }
      else toast.info("In-app DocuSign not available yet", { description: r?.message, duration: 12000 });
    } catch (e) { showApiError(e, { fallbackTitle: "Could not open DocuSign" }); }
  };
  const refreshTx = async (tid) => {
    try { const r = await staffApi.escrowRefresh(tid); toast.success(`DocuSign: ${r.docusign_status || r.status || "updated"}`); await loadEscrow(); }
    catch (e) { showApiError(e, { fallbackTitle: "Refresh failed" }); }
  };
  const signAction = async (tid, intended_action, comment) => {
    await escrowApi.sign(tid, { intended_action, comment: comment || null });
    toast.success("Signature recorded");
    await loadEscrow();
  };
  const downloadDoc = async (tid) => {
    try {
      const r = await staffApi.escrowSignedDoc(tid);
      const bin = atob(r.content_b64); const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const url = URL.createObjectURL(new Blob([bytes], { type: r.content_type || "application/pdf" }));
      const a = document.createElement("a"); a.href = url; a.download = r.filename || "PMC-Escrow-Signed.pdf"; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { showApiError(e, { fallbackTitle: "No signed document yet" }); }
  };

  const queueLabel = useMemo(() => ({
    escrow_agent: "EMD paid — awaiting Escrow acceptance",
    certifier: "Admin-flagged — awaiting Certifier",
    legal_counsel: "Certifier-cleared — awaiting Legal",
    accounting: "Legal-cleared — awaiting Accounting",
    committee_member: "Accounting-cleared — awaiting Committee",
  })[me?.active_role] || "Work queue", [me]);

  if (!me) return <div style={{ padding: 40, color: C.muted, background: C.page, minHeight: "100vh" }}>Loading…</div>;

  const escrowTxns = escrow.transactions || [];
  const pendingCount = escrow.pending_signatures_count || (escrow.pending_signatures || []).length || 0;
  const pendingIds = new Set((escrow.pending_signatures || []).map((t) => t.id));

  const navItems = [
    { key: "overview", label: "Overview" },
    { key: "escrow", label: "Escrow signatures", badge: pendingCount || null },
    { key: "queue", label: queueLabel.split(" — ")[0] || "Work queue", badge: bids.length || null },
    { key: "completed", label: "Completed", badge: processed.count || null },
    ...(me?.active_role === "committee_member" ? [{ key: "opening", label: "Bid opening" }, { key: "challenges", label: "Bid challenges" }] : []),
  ];
  if (me.active_role === "certifier") navItems.push({ key: "inspections", label: "Site inspections", badge: inspections.length || null });

  const NAV_ICONS = { overview: "i-home", escrow: "i-sign", queue: "i-gavel", completed: "i-check", inspections: "i-eye" };
  const shellNav = navItems.map((it) => ({ key: it.key, label: it.label, icon: NAV_ICONS[it.key] || "i-file", badge: it.badge, testid: `staff-nav-${it.key}` }));
  const activeLabel = (navItems.find((n) => n.key === tab) || {}).label || "Overview";

  return (
    <PortalShellE
      rootTestId="staff-dashboard"
      sideTestId="staff-sidebar"
      brand={{ title: "PMC Managers", sub: "Staff portal" }}
      items={shellNav}
      activeKey={tab}
      onSelect={setTab}
      crumb={<>Staff / <b>{activeLabel}</b></>}
      header={
        <div className="pmc-atop__r">
          {(me.roles || []).length > 1 && (
            <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }} data-testid="staff-role-switch">
              <span className="pmc-muted" style={{ textTransform: "uppercase", letterSpacing: "0.12em" }}>Role</span>
              <select value={me.active_role} onChange={(e) => switchRole(e.target.value)}
                style={{ border: "1px solid var(--line-strong)", color: "var(--ink)", background: "var(--surface)", padding: "6px 8px", borderRadius: "var(--radius-sm)", fontSize: 13 }}
                data-testid="staff-role-switch-select">
                {(me.roles || []).map((r) => <option key={r} value={r}>{ROLE_LABELS[r] || r}</option>)}
              </select>
            </label>
          )}
          <PortalAvatarMenu
            initial={(me.name || me.email || "S").trim().charAt(0).toUpperCase()}
            title={me.email}
            sub={ROLE_LABELS[me.active_role] || me.active_role}
            items={[{ label: "Sign out", onClick: logout, danger: true, testid: "staff-logout" }]}
            testId="staff-avatar"
          />
        </div>
      }
    >
          {tab === "overview" && (
            <section data-testid="staff-overview" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
              <StatCard label="Escrow documents to sign" value={pendingCount} hint="Awaiting your signature" onClick={() => setTab("escrow")} />
              <StatCard label={queueLabel} value={bids.length} hint="In your work queue" onClick={() => setTab("queue")} />
              <StatCard label="Completed by you" value={processed.count} hint="Your decision history" onClick={() => setTab("completed")} />
              {me.active_role === "certifier" && <StatCard label="Site inspections" value={inspections.length} hint="Assigned to you" onClick={() => setTab("inspections")} />}
            </section>
          )}

          {tab === "opening" && me.active_role === "committee_member" && (
            <section data-testid="staff-bid-opening">
              <Heading>Bid opening — your approval</Heading>
              <OpenCommitteesOpening />
            </section>
          )}

          {tab === "challenges" && me.active_role === "committee_member" && (
            <section data-testid="staff-bid-challenges">
              <Heading>Bid challenges — your vote</Heading>
              <ChallengesBody staff />
            </section>
          )}

          {tab === "escrow" && (
            <section data-testid="staff-escrow-signatures">
              <Heading>Escrow documents — your signature · {pendingCount} pending</Heading>
              {escrowTxns.length === 0 && <Empty>You have no escrow transactions assigned for signature.</Empty>}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {escrowTxns.map((t) => (
                  <EscrowRow key={t.id} t={t} pending={pendingIds.has(t.id)}
                    onOpen={openDocuSign} onRefresh={refreshTx} onDownload={downloadDoc} onSignAction={signAction} />
                ))}
              </div>
            </section>
          )}

          {tab === "queue" && (
            <section>
              <Heading>{queueLabel} · {bids.length}</Heading>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }} data-testid="staff-bid-queue">
                {bids.map((b) => (
                  <BidRow key={b.id} b={b} committee={me.active_role === "committee_member"}
                    onDecide={decide} onAward={committeeAward} />
                ))}
                {bids.length === 0 && <Empty>Queue is clear.</Empty>}
              </div>
            </section>
          )}

          {tab === "inspections" && me.active_role === "certifier" && (
            <section data-testid="certifier-inspections">
              <Heading>My site inspections · {inspections.length}</Heading>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {inspections.map((ins) => (
                  <div key={ins.id} style={card()} data-testid={`inspection-${ins.id}`}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                      <div>
                        <div style={{ fontSize: 12, color: C.muted }}>{ins.notice_ref}</div>
                        <div style={{ fontSize: 14 }}>Scheduled: {(ins.scheduled_at || "").slice(0, 16).replace("T", " ")}</div>
                        <div style={{ fontSize: 12, color: C.muted }}>Location: {ins.location || "—"}</div>
                        <div style={{ fontSize: 12, marginTop: 4 }}>Status: <strong>{ins.status}</strong> · Result: <strong>{ins.result}</strong></div>
                      </div>
                      <div style={{ display: "flex", gap: 8 }}>
                        <label style={pill()}>Photo<input type="file" accept="image/*" hidden onChange={(e) => e.target.files?.[0] && uploadInspectionMedia(ins, e.target.files[0], "photo")} /></label>
                        <label style={pill()}>Video<input type="file" accept="video/*" hidden onChange={(e) => e.target.files?.[0] && uploadInspectionMedia(ins, e.target.files[0], "video")} /></label>
                      </div>
                    </div>
                    {ins.status !== "completed" && (
                      <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                        <button onClick={() => completeInspection(ins, "pass")} style={btn(C.success)} data-testid={`inspect-pass-${ins.id}`}>Complete — Pass</button>
                        <button onClick={() => completeInspection(ins, "fail")} style={btn(C.danger)} data-testid={`inspect-fail-${ins.id}`}>Complete — Fail</button>
                      </div>
                    )}
                  </div>
                ))}
                {inspections.length === 0 && <Empty>No inspections assigned yet.</Empty>}
              </div>
            </section>
          )}
          {tab === "completed" && <CompletedPanel processed={processed} />}
    </PortalShellE>
  );
}

const card = () => ({ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 8, padding: 16, boxShadow: "var(--shadow-1)" });
const pill = () => ({ fontSize: 12, background: C.sunken, border: `1px solid ${C.line}`, borderRadius: 4, padding: "4px 8px", cursor: "pointer" });
function btn(bg, fg) { return { fontSize: 12, fontWeight: 600, background: bg, color: fg || C.onPrimary, padding: "7px 14px", borderRadius: 4, border: "none", cursor: "pointer" }; }
function Heading({ children }) { return <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: C.muted, marginBottom: 12 }}>{children}</h2>; }
function Empty({ children }) { return <div style={{ ...card(), fontSize: 14, color: C.muted }}>{children}</div>; }
function StatCard({ label, value, hint, onClick }) {
  return (
    <button onClick={onClick} style={{ ...card(), textAlign: "left", cursor: "pointer" }}>
      <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: C.muted }}>{label}</div>
      <div style={{ fontSize: 34, fontWeight: 600, color: C.ink, marginTop: 4, fontFamily: C.display }}>{value}</div>
      <div style={{ fontSize: 12, color: C.faint }}>{hint}</div>
    </button>
  );
}
function Chip({ ok, children }) {
  return <span style={{ fontSize: 11, borderRadius: 999, padding: "2px 10px", background: ok ? C.successSoft : C.sunken, color: ok ? C.success : C.muted }}>{children}</span>;
}

function CompletedPanel({ processed }) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [action, setAction] = useState("");

  const rows = [];
  (processed.bids || []).forEach((b) =>
    (b.my_actions || []).forEach((a) => rows.push({
      bid_ref: b.bid_ref, notice_ref: b.notice_ref, company: b.company_name || b.vendor_email,
      status: b.status, action: a.action, from_status: a.from_status, to_status: a.to_status,
      notes: a.notes, at: a.at,
    })));
  const actionOpts = Array.from(new Set(rows.map((r) => r.action).filter(Boolean)));
  const filtered = rows.filter((r) => {
    const d = (r.at || "").slice(0, 10);
    if (from && d < from) return false;
    if (to && d > to) return false;
    if (action && r.action !== action) return false;
    return true;
  });

  const exportCsv = () => {
    const head = ["bid_ref", "notice_ref", "company", "action", "from_status", "to_status", "comment", "at"];
    const data = [head, ...filtered.map((r) => [r.bid_ref, r.notice_ref, r.company, r.action, r.from_status, r.to_status, r.notes || "", r.at || ""])];
    const csv = data.map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url; a.download = "pmc-my-decisions.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  const fin = { width: "100%", border: `1px solid ${C.lineStrong}`, borderRadius: 4, padding: "7px 9px", background: C.surface, color: C.ink, fontSize: 13 };

  return (
    <section data-testid="staff-completed">
      <Heading>Completed / processed by you · {filtered.length}</Heading>
      <div style={{ ...card(), display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 10 }} data-testid="staff-completed-filters">
        <label style={{ flex: "1 1 140px" }}><div style={{ fontSize: 11, color: C.muted, marginBottom: 2 }}>From</div>
          <input type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} style={fin} data-testid="completed-filter-from" /></label>
        <label style={{ flex: "1 1 140px" }}><div style={{ fontSize: 11, color: C.muted, marginBottom: 2 }}>To</div>
          <input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} style={fin} data-testid="completed-filter-to" /></label>
        <label style={{ flex: "1 1 180px" }}><div style={{ fontSize: 11, color: C.muted, marginBottom: 2 }}>Action</div>
          <select value={action} onChange={(e) => setAction(e.target.value)} style={fin} data-testid="completed-filter-action">
            <option value="">All actions</option>
            {actionOpts.map((a) => <option key={a} value={a}>{a.replace(/_/g, " ")}</option>)}
          </select></label>
        <button onClick={() => { setFrom(""); setTo(""); setAction(""); }} style={{ ...btn("transparent", C.ink), border: `1px solid ${C.lineStrong}` }} data-testid="completed-filter-clear">Clear</button>
        <button onClick={exportCsv} style={btn(C.primary)} data-testid="completed-export-csv">Export CSV</button>
      </div>
      {filtered.length === 0 && <Empty>No processed items match. Items you Accept/Reject appear here with their audit trail.</Empty>}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.map((r, i) => (
          <div key={i} style={card()} data-testid={`staff-completed-${r.bid_ref}`}>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.muted }}>{r.bid_ref} · {r.notice_ref}</div>
            <div style={{ fontSize: 14, color: C.ink }}>{r.company}</div>
            <div style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>Current status: <strong>{r.status}</strong></div>
            <div style={{ marginTop: 8, borderTop: `1px solid ${C.line}`, paddingTop: 8, fontSize: 12 }}>
              <Chip ok>{(r.action || "").replace(/_/g, " ")}</Chip>
              <span style={{ color: C.muted, marginLeft: 8 }}>{r.from_status} → {r.to_status} · {(r.at || "").slice(0, 16).replace("T", " ")}</span>
              {r.notes && <div style={{ color: C.faint, marginTop: 2, fontStyle: "italic" }}>“{r.notes}”</div>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function BidRow({ b, committee, onDecide, onAward }) {
  const [comment, setComment] = useState("");
  return (
    <div style={card()} data-testid={`staff-bid-${b.bid_ref}`}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.muted }}>{b.bid_ref} · {b.notice_ref}</div>
          <div style={{ fontSize: 14, color: C.ink }}>{b.company_name || b.vendor_email} — <strong>{b.price_currency} {(b.price_amount || 0).toLocaleString()}</strong></div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Status: {b.status}</div>
        </div>
      </div>
      <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} placeholder="Add your review comment (optional) — saved to the audit trail"
        style={{ width: "100%", marginTop: 10, border: `1px solid ${C.line}`, borderRadius: 4, padding: "8px 10px", background: C.surface, color: C.ink, fontSize: 13 }}
        data-testid={`staff-bid-comment-${b.bid_ref}`} />
      <div style={{ display: "flex", gap: 8, marginTop: 10, justifyContent: "flex-end" }}>
        {!committee ? (
          <>
            <button onClick={() => onDecide(b, "accept", comment)} style={btn(C.success)} data-testid={`accept-${b.bid_ref}`}>Accept &amp; forward</button>
            <button onClick={() => onDecide(b, "reject", comment)} style={btn(C.danger)} data-testid={`reject-${b.bid_ref}`}>Reject</button>
          </>
        ) : (
          <button onClick={() => onAward(b, comment)} style={btn(C.primary)} data-testid={`award-${b.bid_ref}`}>Award</button>
        )}
      </div>
    </div>
  );
}

function EscrowRow({ t, pending, onOpen, onRefresh, onDownload, onSignAction }) {
  const [action, setAction] = useState(
    ["release_to_contractor", "release_to_vendor", "forfeit"].includes(t.pmc_action)
      ? t.pmc_action : "release_to_contractor");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState("");
  const finalized = ["released_to_contractor", "released_to_vendor", "forfeited", "cancelled"].includes(t.status);
  const awarded = t.bid_status === "awarded";
  const contractorLocked = action === "release_to_contractor" && !awarded;

  const run = async (fn, key) => { setBusy(key); try { await fn(); } catch (e) { showApiError(e, { fallbackTitle: "Action failed" }); } finally { setBusy(""); } };

  return (
    <div data-testid={`staff-escrow-tx-${t.bid_ref || t.id}`}
      style={{ ...card(), background: pending ? C.warningSoft : C.surface, border: `1px solid ${pending ? C.warning : C.line}` }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.muted }}>{t.bid_ref || "—"} · {t.notice_ref || "—"}</div>
          <div style={{ fontSize: 14, color: C.ink }}>{t.vendor_ref ? `${t.vendor_ref} — ` : ""}<strong>{t.currency} {(t.amount || 0).toLocaleString()}</strong></div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>{t.institution ? `${t.institution} · ` : ""}{t.account_name || ""}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
            <Chip ok={t.signed_by_pmc}>You (PMC) {t.signed_by_pmc ? `✓ ${(t.pmc_action || "signed").replace(/_/g, " ")}` : "· awaiting"}</Chip>
            <Chip ok={t.signed_by_institution}>Institution {t.signed_by_institution ? `✓ ${(t.institution_action || "signed").replace(/_/g, " ")}` : "· awaiting"}</Chip>
            {t.docusign_status && <span style={{ fontSize: 11, borderRadius: 999, padding: "2px 10px", background: C.chrome, color: C.onChrome }}>DocuSign: {t.docusign_status}</span>}
          </div>
          {t.signed_by_pmc && t.signed_by_institution && t.pmc_action && t.institution_action && t.pmc_action !== t.institution_action && (
            <div style={{ marginTop: 8, fontSize: 12, color: C.danger }}>
              ⚠ Action mismatch — you signed <b>{t.pmc_action.replace(/_/g, " ")}</b>, institution signed <b>{t.institution_action.replace(/_/g, " ")}</b>. Both must sign the SAME action before admin can release. Re-sign the matching action below.
            </div>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
          {t.docusign_envelope_id && !t.signed_by_pmc && (
            <button onClick={() => onOpen(t.id)} disabled={!!busy} style={btn(C.chrome)} data-testid={`staff-escrow-sign-${t.bid_ref || t.id}`}>Acknowledge via DocuSign</button>
          )}
          {t.docusign_envelope_id && (
            <button onClick={() => run(() => onRefresh(t.id), "r")} disabled={!!busy} style={{ ...btn("transparent", C.ink), border: `1px solid ${C.lineStrong}` }} data-testid={`staff-escrow-refresh-${t.bid_ref || t.id}`}>Refresh DocuSign</button>
          )}
          {t.has_signed_document && (
            <button onClick={() => run(() => onDownload(t.id), "d")} disabled={!!busy} style={btn(C.success)} data-testid={`staff-escrow-download-${t.bid_ref || t.id}`}>Download signed PDF</button>
          )}
        </div>
      </div>

      {!finalized && (
        <div style={{ marginTop: 12, borderTop: `1px solid ${C.line}`, paddingTop: 12 }} data-testid={`staff-escrow-release-panel-${t.bid_ref || t.id}`}>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em" }}>Sign release decision (PMC officer)</div>
          <div style={{ display: "flex", gap: 10, marginTop: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
            <label style={{ flex: "1 1 260px" }}>
              <div style={{ fontSize: 11, color: C.muted, marginBottom: 2 }}>Intended action</div>
              <select value={action} onChange={(e) => setAction(e.target.value)} data-testid={`staff-escrow-action-${t.bid_ref || t.id}`}
                style={{ width: "100%", border: `1px solid ${C.lineStrong}`, borderRadius: 4, padding: "8px 10px", background: C.surface, color: C.ink, fontSize: 13 }}>
                {RELEASE_ACTIONS.map((a) => {
                  const locked = a.v === "release_to_contractor" && !awarded;
                  return <option key={a.v} value={a.v} disabled={locked}>{a.l}{locked ? " — locked until awarded" : ""}</option>;
                })}
              </select>
            </label>
            <label style={{ flex: "2 1 300px" }}>
              <div style={{ fontSize: 11, color: C.muted, marginBottom: 2 }}>Comment (optional)</div>
              <input value={comment} onChange={(e) => setComment(e.target.value)} data-testid={`staff-escrow-comment-${t.bid_ref || t.id}`}
                style={{ width: "100%", border: `1px solid ${C.lineStrong}`, borderRadius: 4, padding: "8px 10px", background: C.surface, color: C.ink, fontSize: 13 }} />
            </label>
            <button onClick={() => {
                if (t.signed_by_institution && t.institution_action && t.institution_action !== action) {
                  const ok = window.confirm(
                    `The escrow institution already signed "${t.institution_action.replace(/_/g, " ")}", but you chose "${action.replace(/_/g, " ")}".\n\nBoth officers must sign the SAME action or the release stays blocked. Sign anyway?`);
                  if (!ok) return;
                }
                run(() => onSignAction(t.id, action, comment), "s");
              }} disabled={busy === "s" || contractorLocked}
              title={contractorLocked ? "Release to contractor is locked until the bid is awarded (certifier → legal → accounting → committee)." : ""}
              style={{ ...btn(C.primary), opacity: (busy === "s" || contractorLocked) ? 0.5 : 1, cursor: contractorLocked ? "not-allowed" : "pointer" }} data-testid={`staff-escrow-release-sign-${t.bid_ref || t.id}`}>
              {busy === "s" ? "Signing…" : (contractorLocked ? "Locked until awarded" : (t.signed_by_pmc ? "Update my signature" : "Sign this action"))}
            </button>
          </div>
          <div style={{ fontSize: 11, color: C.faint, marginTop: 6 }}>
            Both officers must sign the SAME action; then an admin fires the final release.
            {!awarded && <span style={{ color: C.warning, display: "block", marginTop: 2 }}>
              ⚠ Release to contractor unlocks only once this bid is <b>awarded</b> (certifier → legal → accounting → committee). Current bid status: {t.bid_status || "unknown"}.
            </span>}
          </div>
        </div>
      )}
    </div>
  );
}
