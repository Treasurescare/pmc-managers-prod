import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { staffApi, bidApi, inspectionApi, uploadsApi, escrowApi, showApiError } from "@/lib/api";

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
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    (async () => {
      try {
        const m = await staffApi.me();
        setMe(m);
        if (["admin", "reviewer"].includes(m.active_role)) return nav("/admin");
        await refresh(m);
        const esc = await loadEscrow();
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
  ];
  if (me.active_role === "certifier") navItems.push({ key: "inspections", label: "Site inspections", badge: inspections.length || null });

  return (
    <div style={{ minHeight: "100vh", background: C.page, color: C.ink, fontFamily: "var(--font-sans)" }} data-testid="staff-dashboard">
      <header style={{ background: C.chrome, color: C.onChrome }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: C.brass, fontWeight: 600 }}>Staff Portal</div>
            <h1 style={{ fontSize: 22, fontFamily: C.display, fontWeight: 500, margin: 0 }}>{me.name} — {ROLE_LABELS[me.active_role] || me.active_role}</h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 14 }}>
            {(me.roles || []).length > 1 && (
              <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }} data-testid="staff-role-switch">
                <span style={{ color: C.onChromeMuted, textTransform: "uppercase", letterSpacing: "0.12em" }}>Active role</span>
                <select value={me.active_role} onChange={(e) => switchRole(e.target.value)}
                  style={{ background: "rgba(255,255,255,0.08)", border: `1px solid ${C.chromeLine}`, color: C.onChrome, padding: "4px 8px", borderRadius: 4 }}
                  data-testid="staff-role-switch-select">
                  {(me.roles || []).map((r) => <option key={r} value={r} style={{ color: "#14201a" }}>{ROLE_LABELS[r] || r}</option>)}
                </select>
              </label>
            )}
            <span style={{ color: C.onChromeMuted }}>{me.email}</span>
            <button onClick={logout} style={{ color: C.onChrome, textDecoration: "underline", background: "none", border: "none", cursor: "pointer" }} data-testid="staff-logout">Sign out</button>
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", gap: 24, padding: 24, alignItems: "flex-start" }}>
        <aside style={{ width: 236, flexShrink: 0 }} data-testid="staff-sidebar">
          <nav style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 8, overflow: "hidden", position: "sticky", top: 24 }}>
            {navItems.map((it) => {
              const active = tab === it.key;
              return (
                <button key={it.key} onClick={() => setTab(it.key)} data-testid={`staff-nav-${it.key}`}
                  style={{ width: "100%", textAlign: "left", padding: "12px 16px", display: "flex", alignItems: "center", justifyContent: "space-between",
                    border: "none", cursor: "pointer", fontSize: 14, background: active ? C.primary : "transparent",
                    color: active ? C.onPrimary : C.ink, borderLeft: active ? `3px solid ${C.brass}` : "3px solid transparent" }}>
                  <span>{it.label}</span>
                  {it.badge ? <span style={{ minWidth: 22, textAlign: "center", fontSize: 12, fontWeight: 700, borderRadius: 999, padding: "1px 7px", background: active ? C.brass : C.primary, color: active ? "#1b1606" : C.onPrimary }}>{it.badge}</span> : null}
                </button>
              );
            })}
          </nav>
        </aside>

        <main style={{ flex: 1, minWidth: 0 }}>
          {tab === "overview" && (
            <section data-testid="staff-overview" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
              <StatCard label="Escrow documents to sign" value={pendingCount} hint="Awaiting your signature" onClick={() => setTab("escrow")} />
              <StatCard label={queueLabel} value={bids.length} hint="In your work queue" onClick={() => setTab("queue")} />
              {me.active_role === "certifier" && <StatCard label="Site inspections" value={inspections.length} hint="Assigned to you" onClick={() => setTab("inspections")} />}
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
        </main>
      </div>
    </div>
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
  const [action, setAction] = useState(t.pmc_action || "release_to_contractor");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState("");
  const finalized = ["released_to_contractor", "released_to_vendor", "forfeited", "cancelled"].includes(t.status);

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
                {RELEASE_ACTIONS.map((a) => <option key={a.v} value={a.v}>{a.l}</option>)}
              </select>
            </label>
            <label style={{ flex: "2 1 300px" }}>
              <div style={{ fontSize: 11, color: C.muted, marginBottom: 2 }}>Comment (optional)</div>
              <input value={comment} onChange={(e) => setComment(e.target.value)} data-testid={`staff-escrow-comment-${t.bid_ref || t.id}`}
                style={{ width: "100%", border: `1px solid ${C.lineStrong}`, borderRadius: 4, padding: "8px 10px", background: C.surface, color: C.ink, fontSize: 13 }} />
            </label>
            <button onClick={() => run(() => onSignAction(t.id, action, comment), "s")} disabled={busy === "s"}
              style={{ ...btn(C.primary), opacity: busy === "s" ? 0.5 : 1 }} data-testid={`staff-escrow-release-sign-${t.bid_ref || t.id}`}>
              {busy === "s" ? "Signing…" : (t.signed_by_pmc ? "Update my signature" : "Sign this action")}
            </button>
          </div>
          <div style={{ fontSize: 11, color: C.faint, marginTop: 6 }}>
            Both officers must sign the SAME action; then an admin fires the final release.
          </div>
        </div>
      )}
    </div>
  );
}
