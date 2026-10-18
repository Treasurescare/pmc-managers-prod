import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { staffApi, bidApi, inspectionApi, uploadsApi, formatApiError, showApiError} from "@/lib/api";

const ROLE_LABELS = {
  admin: "Administrator",
  reviewer: "Reviewer",
  escrow_agent: "Escrow Agent", certifier: "Site Certifier",
  legal_counsel: "Legal Counsel", accounting: "Accounting Team",
  committee_member: "Bid Committee", auditor: "Auditor", support: "Support",
  management: "Management", partner: "Partner", agent: "Agent",
};

// What each role can accept AT (bid status prerequisite -> next status)
const ROLE_QUEUE_STATUS = {
  escrow_agent: "emd_paid",
  certifier: "admin_flagged",
  legal_counsel: "certifier_cleared",
  accounting: "legal_cleared",
  committee_member: "accounting_cleared",
};

export default function StaffDashboard() {
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [bids, setBids] = useState([]);
  const [inspections, setInspections] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const m = await staffApi.me();
        setMe(m);
        if (["admin", "reviewer"].includes(m.active_role)) return nav("/admin");
        await refresh(m);
      } catch {
        nav("/staff/login");
      }
    })();
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

  const logout = async () => {
    try { await staffApi.logout(); }
    catch (err) {
      if (process.env.NODE_ENV !== "production") console.debug("staff logout skipped:", err?.response?.status);
    }
    nav("/login");
  };

  // v53p — swap active role in place for multi-role staff. Re-issues JWT,
  // refreshes the queue, and routes to /admin if the new role is admin.
  const switchRole = async (newRole) => {
    if (!newRole || newRole === me?.active_role) return;
    try {
      const r = await staffApi.switchRole(newRole);
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
      await inspectionApi.addMedia(ins.id, {
        kind, key: r.key, filename: file.name,
        content_type: file.type || "image/jpeg", size_bytes: r.size_bytes,
      });
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

  const queueLabel = useMemo(() => ({
    escrow_agent: "EMD paid — awaiting Escrow acceptance",
    certifier: "Admin-flagged — awaiting Certifier",
    legal_counsel: "Certifier-cleared — awaiting Legal",
    accounting: "Legal-cleared — awaiting Accounting",
    committee_member: "Accounting-cleared — awaiting Committee",
  })[me?.active_role] || "Queue", [me]);

  if (!me) return <div className="p-10 text-slate-500">Loading…</div>;

  return (
    <div className="min-h-screen" style={{ background: "#eef2f7", color: "#0f172a" }} data-testid="staff-dashboard">
      <header className="bg-[#0b1e3f] text-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <div className="text-xs tracking-widest uppercase text-amber-300">Staff Portal</div>
            <h1 className="text-lg font-serif">{me.name} — {ROLE_LABELS[me.active_role] || me.active_role}</h1>
          </div>
          <div className="text-sm flex items-center gap-4">
            {/* v53p — in-place role swap for multi-role staff. Hidden
                when the user only holds a single role. */}
            {(me.roles || []).length > 1 && (
              <label className="text-xs flex items-center gap-2" data-testid="staff-role-switch">
                <span className="text-white/60 uppercase tracking-widest">Active role</span>
                <select value={me.active_role}
                        onChange={(e) => switchRole(e.target.value)}
                        className="bg-white/10 border border-white/20 text-white px-2 py-1 rounded"
                        data-testid="staff-role-switch-select">
                  {(me.roles || []).map((r) => (
                    <option key={r} value={r} style={{ color: "#0b1e3f" }}>
                      {ROLE_LABELS[r] || r}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <span className="text-white/70">{me.email}</span>
            <button onClick={logout} className="text-white/80 hover:text-white underline"
              data-testid="staff-logout">Sign out</button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-8">
        <EscrowSignatures />

        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700 mb-3">
            {queueLabel} · {bids.length}
          </h2>
          <div className="space-y-2" data-testid="staff-bid-queue">
            {bids.map((b) => (
              <div key={b.id} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm"
                data-testid={`staff-bid-${b.bid_ref}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs font-medium text-slate-600">{b.bid_ref} · {b.notice_ref}</div>
                    <div className="text-sm text-slate-900">{b.company_name || b.vendor_email} — 
                      <strong> {b.price_currency} {(b.price_amount || 0).toLocaleString()}</strong>
                    </div>
                    <div className="text-xs text-slate-600 mt-1">Status: {b.status}</div>
                  </div>
                  <div className="flex gap-2">
                    {me.active_role !== "committee_member" && (
                      <>
                        <button onClick={() => decide(b, "accept")}
                          className="text-xs bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700"
                          data-testid={`accept-${b.bid_ref}`}>Accept</button>
                        <button onClick={() => decide(b, "reject")}
                          className="text-xs bg-red-600 text-white px-3 py-1.5 rounded hover:bg-red-700"
                          data-testid={`reject-${b.bid_ref}`}>Reject</button>
                      </>
                    )}
                    {me.active_role === "committee_member" && (
                      <button onClick={() => committeeAward(b)}
                        className="text-xs bg-amber-500 text-white px-3 py-1.5 rounded hover:bg-amber-600"
                        data-testid={`award-${b.bid_ref}`}>Award</button>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {bids.length === 0 && <div className="text-sm text-slate-500">Queue is clear.</div>}
          </div>
        </section>

        {me.active_role === "certifier" && (
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-600 mb-3">
              My site inspections · {inspections.length}
            </h2>
            <div className="space-y-3" data-testid="certifier-inspections">
              {inspections.map((ins) => (
                <div key={ins.id} className="bg-white border rounded-lg p-4"
                  data-testid={`inspection-${ins.id}`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-xs text-slate-500">{ins.notice_ref}</div>
                      <div className="text-sm mt-0.5">
                        Scheduled: {(ins.scheduled_at || "").slice(0, 16).replace("T", " ")}
                      </div>
                      <div className="text-xs text-slate-500">Location: {ins.location || "—"}</div>
                      <div className="text-xs mt-1">Status: <strong>{ins.status}</strong> · Result: <strong>{ins.result}</strong></div>
                    </div>
                    <div className="flex gap-2">
                      <label className="text-xs bg-slate-100 border rounded px-2 py-1 cursor-pointer">
                        📷 Photo
                        <input type="file" accept="image/*" hidden
                          onChange={(e) => e.target.files?.[0] && uploadInspectionMedia(ins, e.target.files[0], "photo")} />
                      </label>
                      <label className="text-xs bg-slate-100 border rounded px-2 py-1 cursor-pointer">
                        🎥 Video
                        <input type="file" accept="video/*" hidden
                          onChange={(e) => e.target.files?.[0] && uploadInspectionMedia(ins, e.target.files[0], "video")} />
                      </label>
                    </div>
                  </div>

                  {ins.media?.length > 0 && (
                    <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
                      {ins.media.map((m, i) => (
                        <div key={`media-${m.filename || i}`} className="border rounded p-2 bg-slate-50">
                          <div className="truncate">{m.kind === "video" ? "🎥" : "📷"} {m.filename}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {ins.status !== "completed" && (
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => completeInspection(ins, "pass")}
                        className="text-xs bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700"
                        data-testid={`inspect-pass-${ins.id}`}>Complete — Pass</button>
                      <button onClick={() => completeInspection(ins, "fail")}
                        className="text-xs bg-red-600 text-white px-3 py-1.5 rounded hover:bg-red-700"
                        data-testid={`inspect-fail-${ins.id}`}>Complete — Fail</button>
                    </div>
                  )}
                </div>
              ))}
              {inspections.length === 0 && <div className="text-sm text-slate-500">No inspections assigned yet.</div>}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}


// v56f — PMC-officer escrow signing surface. Self-contained: lists the escrow
// transactions where the logged-in staff member is the named PMC officer, with
// Open in DocuSign (Safari-safe), Refresh status, and Download signed PDF.
function fmtDate(iso) {
  if (!iso) return "—";
  return String(iso).slice(0, 19).replace("T", " ");
}

function EscrowSignatures() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState("");

  const load = () =>
    staffApi.escrowSignatures()
      .then(setData)
      .catch(() => setData({ pending_signatures: [], transactions: [] }));

  useEffect(() => { load(); }, []);

  const openDocuSign = async (tid) => {
    // Safari blocks window.open() that runs AFTER an await; pre-open synchronously.
    const win = window.open("", "_blank");
    setBusy(tid);
    try {
      const r = await staffApi.escrowDocuSignUrl(tid);
      if (r?.url) {
        if (win) win.location.href = r.url; else window.location.href = r.url;
      } else {
        if (win) win.close();
        toast.info("Open your DocuSign email to sign", {
          description: r?.message || "DocuSign emailed you the hosted-signing link.",
          duration: 12000,
        });
      }
    } catch (e) {
      if (win) win.close();
      showApiError(e, { fallbackTitle: "Could not open DocuSign" });
    } finally { setBusy(""); }
  };

  const refresh = async (tid) => {
    setBusy(tid);
    try {
      const r = await staffApi.escrowRefresh(tid);
      toast.success(`DocuSign status: ${r.docusign_status || r.status || "updated"}`);
      await load();
    } catch (e) { showApiError(e, { fallbackTitle: "Refresh failed" }); }
    finally { setBusy(""); }
  };

  const download = async (tid) => {
    setBusy(tid);
    try {
      const r = await staffApi.escrowSignedDoc(tid);
      const bin = atob(r.content_b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const blob = new Blob([bytes], { type: r.content_type || "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = r.filename || "PMC-Escrow-Signed.pdf"; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { showApiError(e, { fallbackTitle: "No signed document yet" }); }
    finally { setBusy(""); }
  };

  if (!data) return null;
  const txns = data.transactions || [];
  if (txns.length === 0) return null;
  const pendingIds = new Set((data.pending_signatures || []).map((t) => t.id));

  return (
    <section data-testid="staff-escrow-signatures">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700 mb-3">
        Escrow documents — your signature · {data.pending_signatures_count || 0} pending
      </h2>
      <div className="space-y-2">
        {txns.map((t) => {
          const isPending = pendingIds.has(t.id);
          return (
            <div key={t.id}
              className={"rounded-lg p-4 border shadow-sm " +
                (isPending ? "bg-amber-50 border-amber-300" : "bg-white border-slate-200")}
              data-testid={`staff-escrow-tx-${t.bid_ref || t.id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="min-w-0">
                  <div className="text-xs font-medium text-slate-600">
                    {t.bid_ref || "—"} · {t.notice_ref || "—"}
                  </div>
                  <div className="text-sm text-slate-900">
                    {t.vendor_ref ? `${t.vendor_ref} — ` : ""}
                    <strong>{t.currency} {(t.amount || 0).toLocaleString()}</strong>
                  </div>
                  <div className="text-xs text-slate-600 mt-1">
                    {t.institution ? `${t.institution} · ` : ""}{t.account_name || ""}
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-[11px]">
                    <span className={"px-2 py-0.5 rounded-full " +
                      (t.signed_by_pmc ? "bg-emerald-100 text-emerald-800" : "bg-slate-300 text-slate-800")}>
                      You (PMC) {t.signed_by_pmc ? "✓ signed" : "· awaiting"}
                    </span>
                    <span className={"px-2 py-0.5 rounded-full " +
                      (t.signed_by_institution ? "bg-emerald-100 text-emerald-800" : "bg-slate-300 text-slate-800")}>
                      Institution {t.signed_by_institution ? "✓ signed" : "· awaiting"}
                    </span>
                    {t.docusign_status && (
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-white">
                        DocuSign: {t.docusign_status}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-2 items-end">
                  {t.docusign_envelope_id ? (
                    <>
                      {!t.signed_by_pmc && (
                        <button onClick={() => openDocuSign(t.id)} disabled={busy === t.id}
                          className="text-xs bg-[#0b1e3f] text-white px-3 py-1.5 rounded hover:bg-[#0a1733] disabled:opacity-40"
                          data-testid={`staff-escrow-sign-${t.bid_ref || t.id}`}>
                          {busy === t.id ? "Opening…" : "Open in DocuSign to sign"}
                        </button>
                      )}
                      <button onClick={() => refresh(t.id)} disabled={busy === t.id}
                        className="text-xs border border-slate-400 text-slate-800 font-medium px-3 py-1.5 rounded hover:bg-slate-100 disabled:opacity-40"
                        data-testid={`staff-escrow-refresh-${t.bid_ref || t.id}`}>
                        Refresh DocuSign
                      </button>
                      {t.has_signed_document && (
                        <button onClick={() => download(t.id)} disabled={busy === t.id}
                          className="text-xs bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700 disabled:opacity-40"
                          data-testid={`staff-escrow-download-${t.bid_ref || t.id}`}>
                          Download signed PDF
                        </button>
                      )}
                    </>
                  ) : (
                    <span className="text-xs text-slate-600 italic text-right max-w-[220px]">
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
