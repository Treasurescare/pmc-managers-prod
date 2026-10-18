import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { staffApi, bidApi, inspectionApi, uploadsApi, showApiError } from "@/lib/api";

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

// Explicit palette — inline styles so the global [data-ui="e"] slate→dark
// remap can never wash the staff portal out again.
const C = {
  page: "#eef2f7", chrome: "#0b1e3f", surface: "#ffffff",
  ink: "#14201a", muted: "#5b6b62", faint: "#7c8a81",
  border: "#d9e0ea", amberBg: "#fdf6d8", amberBorder: "#e3b55c",
  emerald: "#059669", red: "#dc2626", navy: "#0b1e3f",
  chipBg: "#e2e8f0", chipInk: "#334155", okBg: "#d1fae5", okInk: "#065f46",
};

export default function StaffDashboard() {
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [bids, setBids] = useState([]);
  const [inspections, setInspections] = useState([]);
  const [escrow, setEscrow] = useState({ pending_signatures: [], transactions: [] });
  const [tab, setTab] = useState("overview");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const m = await staffApi.me();
        setMe(m);
        if (["admin", "reviewer"].includes(m.active_role)) return nav("/admin");
        await refresh(m);
        await loadEscrow();
        // Returning from a DocuSign embedded signing ceremony?
        const params = new URLSearchParams(window.location.search);
        if (params.get("signed") || params.get("event")) {
          const tid = sessionStorage.getItem("pmc.signing.tid");
          window.history.replaceState({}, "", "/staff");
          toast.message("Returned from DocuSign — reconciling signature…");
          setTab("escrow");
          if (tid) { try { await staffApi.escrowRefresh(tid); } catch { /* ignore */ } }
          sessionStorage.removeItem("pmc.signing.tid");
          await loadEscrow();
        } else if ((await staffApi.escrowSignatures().catch(() => null))?.pending_signatures_count) {
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

  const loadEscrow = () =>
    staffApi.escrowSignatures()
      .then(setEscrow)
      .catch(() => setEscrow({ pending_signatures: [], transactions: [] }));

  const logout = async () => {
    try { await staffApi.logout(); } catch { /* ignore */ }
    nav("/login");
  };

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

  const decide = async (bid, action) => {
    try {
      await bidApi.decide(bid.id, { action, role: me.active_role, notes: "" });
      toast.success(`Bid ${bid.bid_ref}: ${action}`);
      await refresh();
    } catch (err) { showApiError(err); }
  };

  const committeeAward = async (bid) => {
    try {
      await bidApi.decide(bid.id, { action: "award", role: "committee", notes: "" });
      toast.success(`Bid ${bid.bid_ref} awarded`);
      await refresh();
    } catch (err) { showApiError(err); }
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

  // ---- Escrow embedded signing ----
  const openDocuSign = async (tid) => {
    setBusy(tid);
    try {
      const r = await staffApi.escrowDocuSignUrl(tid);
      if (r?.url) {
        sessionStorage.setItem("pmc.signing.tid", tid);
        window.location.assign(r.url); // top-level nav; DocuSign returns to /staff?signed=1
      } else {
        toast.info("In-app signing not available yet", {
          description: r?.message || "Ask PMC admin to re-issue the DocuSign envelope.",
          duration: 12000,
        });
      }
    } catch (e) { showApiError(e, { fallbackTitle: "Could not open DocuSign" }); }
    finally { setBusy(""); }
  };

  const refreshTx = async (tid) => {
    setBusy(tid);
    try {
      const r = await staffApi.escrowRefresh(tid);
      toast.success(`DocuSign status: ${r.docusign_status || r.status || "updated"}`);
      await loadEscrow();
    } catch (e) { showApiError(e, { fallbackTitle: "Refresh failed" }); }
    finally { setBusy(""); }
  };

  const downloadDoc = async (tid) => {
    setBusy(tid);
    try {
      const r = await staffApi.escrowSignedDoc(tid);
      const bin = atob(r.content_b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const url = URL.createObjectURL(new Blob([bytes], { type: r.content_type || "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = r.filename || "PMC-Escrow-Signed.pdf"; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { showApiError(e, { fallbackTitle: "No signed document yet" }); }
    finally { setBusy(""); }
  };

  const queueLabel = useMemo(() => ({
    escrow_agent: "EMD paid — awaiting Escrow acceptance",
    certifier: "Admin-flagged — awaiting Certifier",
    legal_counsel: "Certifier-cleared — awaiting Legal",
    accounting: "Legal-cleared — awaiting Accounting",
    committee_member: "Accounting-cleared — awaiting Committee",
  })[me?.active_role] || "Work queue", [me]);

  if (!me) return <div style={{ padding: 40, color: C.muted }}>Loading…</div>;

  const escrowTxns = escrow.transactions || [];
  const pendingCount = escrow.pending_signatures_count || (escrow.pending_signatures || []).length || 0;

  const navItems = [
    { key: "overview", label: "Overview" },
    { key: "escrow", label: "Escrow signatures", badge: pendingCount || null },
    { key: "queue", label: queueLabel.split(" — ")[0] || "Work queue", badge: bids.length || null },
  ];
  if (me.active_role === "certifier") navItems.push({ key: "inspections", label: "Site inspections", badge: inspections.length || null });

  return (
    <div style={{ minHeight: "100vh", background: C.page, color: C.ink }} data-testid="staff-dashboard">
      {/* Top bar */}
      <header style={{ background: C.chrome, color: "#fff" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: "#fcd34d" }}>Staff Portal</div>
            <h1 style={{ fontSize: 20, fontFamily: "'Cormorant Garamond', Georgia, serif", margin: 0 }}>
              {me.name} — {ROLE_LABELS[me.active_role] || me.active_role}
            </h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 14 }}>
            {(me.roles || []).length > 1 && (
              <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }} data-testid="staff-role-switch">
                <span style={{ color: "rgba(255,255,255,0.6)", textTransform: "uppercase", letterSpacing: "0.12em" }}>Active role</span>
                <select value={me.active_role} onChange={(e) => switchRole(e.target.value)}
                  style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)", color: "#fff", padding: "4px 8px", borderRadius: 6 }}
                  data-testid="staff-role-switch-select">
                  {(me.roles || []).map((r) => (
                    <option key={r} value={r} style={{ color: C.navy }}>{ROLE_LABELS[r] || r}</option>
                  ))}
                </select>
              </label>
            )}
            <span style={{ color: "rgba(255,255,255,0.75)" }}>{me.email}</span>
            <button onClick={logout} style={{ color: "rgba(255,255,255,0.85)", textDecoration: "underline", background: "none", border: "none", cursor: "pointer" }} data-testid="staff-logout">Sign out</button>
          </div>
        </div>
      </header>

      {/* Sidebar + main */}
      <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", gap: 24, padding: "24px" }}>
        <aside style={{ width: 232, flexShrink: 0 }} data-testid="staff-sidebar">
          <nav style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, overflow: "hidden", position: "sticky", top: 24 }}>
            {navItems.map((it) => {
              const active = tab === it.key;
              return (
                <button key={it.key} onClick={() => setTab(it.key)}
                  data-testid={`staff-nav-${it.key}`}
                  style={{
                    width: "100%", textAlign: "left", padding: "12px 16px",
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    border: "none", cursor: "pointer", fontSize: 14,
                    background: active ? C.navy : "transparent",
                    color: active ? "#fff" : C.ink,
                    borderLeft: active ? `3px solid #fcd34d` : "3px solid transparent",
                  }}>
                  <span>{it.label}</span>
                  {it.badge ? (
                    <span style={{
                      minWidth: 22, textAlign: "center", fontSize: 12, fontWeight: 600,
                      borderRadius: 999, padding: "1px 7px",
                      background: active ? "#fcd34d" : C.navy, color: active ? C.navy : "#fff",
                    }}>{it.badge}</span>
                  ) : null}
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
              {me.active_role === "certifier" && (
                <StatCard label="Site inspections" value={inspections.length} hint="Assigned to you" onClick={() => setTab("inspections")} />
              )}
            </section>
          )}

          {tab === "escrow" && (
            <EscrowList txns={escrowTxns} pendingIds={new Set((escrow.pending_signatures || []).map((t) => t.id))}
              busy={busy} onOpen={openDocuSign} onRefresh={refreshTx} onDownload={downloadDoc} />
          )}

          {tab === "queue" && (
            <section>
              <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: C.muted, marginBottom: 12 }}>
                {queueLabel} · {bids.length}
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }} data-testid="staff-bid-queue">
                {bids.map((b) => (
                  <div key={b.id} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16 }} data-testid={`staff-bid-${b.bid_ref}`}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: C.muted }}>{b.bid_ref} · {b.notice_ref}</div>
                        <div style={{ fontSize: 14, color: C.ink }}>{b.company_name || b.vendor_email} — <strong>{b.price_currency} {(b.price_amount || 0).toLocaleString()}</strong></div>
                        <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Status: {b.status}</div>
                      </div>
                      <div style={{ display: "flex", gap: 8 }}>
                        {me.active_role !== "committee_member" ? (
                          <>
                            <button onClick={() => decide(b, "accept")} style={btn(C.emerald)} data-testid={`accept-${b.bid_ref}`}>Accept</button>
                            <button onClick={() => decide(b, "reject")} style={btn(C.red)} data-testid={`reject-${b.bid_ref}`}>Reject</button>
                          </>
                        ) : (
                          <button onClick={() => committeeAward(b)} style={btn("#d97706")} data-testid={`award-${b.bid_ref}`}>Award</button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {bids.length === 0 && <div style={{ fontSize: 14, color: C.muted }}>Queue is clear.</div>}
              </div>
            </section>
          )}

          {tab === "inspections" && me.active_role === "certifier" && (
            <section data-testid="certifier-inspections">
              <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: C.muted, marginBottom: 12 }}>
                My site inspections · {inspections.length}
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {inspections.map((ins) => (
                  <div key={ins.id} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16 }} data-testid={`inspection-${ins.id}`}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                      <div>
                        <div style={{ fontSize: 12, color: C.muted }}>{ins.notice_ref}</div>
                        <div style={{ fontSize: 14 }}>Scheduled: {(ins.scheduled_at || "").slice(0, 16).replace("T", " ")}</div>
                        <div style={{ fontSize: 12, color: C.muted }}>Location: {ins.location || "—"}</div>
                        <div style={{ fontSize: 12, marginTop: 4 }}>Status: <strong>{ins.status}</strong> · Result: <strong>{ins.result}</strong></div>
                      </div>
                      <div style={{ display: "flex", gap: 8 }}>
                        <label style={{ fontSize: 12, background: C.page, border: `1px solid ${C.border}`, borderRadius: 6, padding: "4px 8px", cursor: "pointer" }}>
                          Photo<input type="file" accept="image/*" hidden onChange={(e) => e.target.files?.[0] && uploadInspectionMedia(ins, e.target.files[0], "photo")} />
                        </label>
                        <label style={{ fontSize: 12, background: C.page, border: `1px solid ${C.border}`, borderRadius: 6, padding: "4px 8px", cursor: "pointer" }}>
                          Video<input type="file" accept="video/*" hidden onChange={(e) => e.target.files?.[0] && uploadInspectionMedia(ins, e.target.files[0], "video")} />
                        </label>
                      </div>
                    </div>
                    {ins.status !== "completed" && (
                      <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                        <button onClick={() => completeInspection(ins, "pass")} style={btn(C.emerald)} data-testid={`inspect-pass-${ins.id}`}>Complete — Pass</button>
                        <button onClick={() => completeInspection(ins, "fail")} style={btn(C.red)} data-testid={`inspect-fail-${ins.id}`}>Complete — Fail</button>
                      </div>
                    )}
                  </div>
                ))}
                {inspections.length === 0 && <div style={{ fontSize: 14, color: C.muted }}>No inspections assigned yet.</div>}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function btn(bg) {
  return { fontSize: 12, background: bg, color: "#fff", padding: "6px 12px", borderRadius: 6, border: "none", cursor: "pointer" };
}

function StatCard({ label, value, hint, onClick }) {
  return (
    <button onClick={onClick} style={{ textAlign: "left", background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 20, cursor: "pointer" }}>
      <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: C.muted }}>{label}</div>
      <div style={{ fontSize: 36, fontWeight: 600, color: C.ink, marginTop: 4 }}>{value}</div>
      <div style={{ fontSize: 12, color: C.faint }}>{hint}</div>
    </button>
  );
}

function Chip({ ok, children }) {
  return (
    <span style={{ fontSize: 11, borderRadius: 999, padding: "2px 10px", background: ok ? C.okBg : C.chipBg, color: ok ? C.okInk : C.chipInk }}>
      {children}
    </span>
  );
}

function EscrowList({ txns, pendingIds, busy, onOpen, onRefresh, onDownload }) {
  return (
    <section data-testid="staff-escrow-signatures">
      <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: C.muted, marginBottom: 12 }}>
        Escrow documents — your signature · {pendingIds.size} pending
      </h2>
      {txns.length === 0 && (
        <div style={{ fontSize: 14, color: C.muted, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20 }}>
          You have no escrow transactions assigned for signature.
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {txns.map((t) => {
          const isPending = pendingIds.has(t.id);
          return (
            <div key={t.id} data-testid={`staff-escrow-tx-${t.bid_ref || t.id}`}
              style={{ background: isPending ? C.amberBg : C.surface, border: `1px solid ${isPending ? C.amberBorder : C.border}`, borderRadius: 10, padding: 16 }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: C.muted }}>{t.bid_ref || "—"} · {t.notice_ref || "—"}</div>
                  <div style={{ fontSize: 14, color: C.ink }}>{t.vendor_ref ? `${t.vendor_ref} — ` : ""}<strong>{t.currency} {(t.amount || 0).toLocaleString()}</strong></div>
                  <div style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>{t.institution ? `${t.institution} · ` : ""}{t.account_name || ""}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                    <Chip ok={t.signed_by_pmc}>You (PMC) {t.signed_by_pmc ? "✓ signed" : "· awaiting"}</Chip>
                    <Chip ok={t.signed_by_institution}>Institution {t.signed_by_institution ? "✓ signed" : "· awaiting"}</Chip>
                    {t.docusign_status && (
                      <span style={{ fontSize: 11, borderRadius: 999, padding: "2px 10px", background: C.navy, color: "#fff" }}>DocuSign: {t.docusign_status}</span>
                    )}
                  </div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
                  {t.docusign_envelope_id ? (
                    <>
                      {!t.signed_by_pmc && (
                        <button onClick={() => onOpen(t.id)} disabled={busy === t.id} style={{ ...btn(C.navy), opacity: busy === t.id ? 0.5 : 1 }} data-testid={`staff-escrow-sign-${t.bid_ref || t.id}`}>
                          {busy === t.id ? "Opening…" : "Open in DocuSign to sign"}
                        </button>
                      )}
                      <button onClick={() => onRefresh(t.id)} disabled={busy === t.id}
                        style={{ fontSize: 12, background: "transparent", color: C.ink, fontWeight: 600, padding: "6px 12px", borderRadius: 6, border: `1px solid ${C.muted}`, cursor: "pointer", opacity: busy === t.id ? 0.5 : 1 }}
                        data-testid={`staff-escrow-refresh-${t.bid_ref || t.id}`}>
                        Refresh DocuSign
                      </button>
                      {t.has_signed_document && (
                        <button onClick={() => onDownload(t.id)} disabled={busy === t.id} style={{ ...btn(C.emerald), opacity: busy === t.id ? 0.5 : 1 }} data-testid={`staff-escrow-download-${t.bid_ref || t.id}`}>
                          Download signed PDF
                        </button>
                      )}
                    </>
                  ) : (
                    <span style={{ fontSize: 12, color: C.muted, fontStyle: "italic", textAlign: "right", maxWidth: 220 }}>
                      Awaiting PMC admin to issue the DocuSign envelope.
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
