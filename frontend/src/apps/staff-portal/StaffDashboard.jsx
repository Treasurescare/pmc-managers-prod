import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { staffApi, bidApi, inspectionApi, uploadsApi, formatApiError } from "@/lib/api";

const ROLE_LABELS = {
  escrow_agent: "Escrow Agent", certifier: "Site Certifier",
  legal_counsel: "Legal Counsel", accounting: "Accounting Team",
  committee_member: "Bid Committee", auditor: "Auditor", support: "Support",
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
    try { await staffApi.logout(); } catch { /* ignore */ }
    nav("/staff/login");
  };

  const decide = async (bid, action) => {
    try {
      await bidApi.decide(bid.id, { action, role: me.active_role, notes: "" });
      toast.success(`Bid ${bid.bid_ref}: ${action}`);
      await refresh();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const committeeAward = async (bid) => {
    try {
      await bidApi.decide(bid.id, { action: "award", role: "committee", notes: "" });
      toast.success(`Bid ${bid.bid_ref} awarded`);
      await refresh();
    } catch (err) { toast.error(formatApiError(err)); }
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
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const completeInspection = async (ins, result) => {
    try {
      await inspectionApi.update(ins.id, { status: "completed", result });
      toast.success("Inspection recorded");
      await refresh();
    } catch (err) { toast.error(formatApiError(err)); }
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
    <div className="min-h-screen bg-slate-50" data-testid="staff-dashboard">
      <header className="bg-[#0b1e3f] text-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <div className="text-xs tracking-widest uppercase text-amber-300">Staff Portal</div>
            <h1 className="text-lg font-serif">{me.name} — {ROLE_LABELS[me.active_role] || me.active_role}</h1>
          </div>
          <div className="text-sm flex items-center gap-4">
            <span className="text-white/70">{me.email}</span>
            <button onClick={logout} className="text-white/80 hover:text-white underline"
              data-testid="staff-logout">Sign out</button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-8">
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-600 mb-3">
            {queueLabel} · {bids.length}
          </h2>
          <div className="space-y-2" data-testid="staff-bid-queue">
            {bids.map((b) => (
              <div key={b.id} className="bg-white border rounded-lg p-4"
                data-testid={`staff-bid-${b.bid_ref}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500">{b.bid_ref} · {b.notice_ref}</div>
                    <div className="text-sm">{b.company_name || b.vendor_email} — 
                      <strong> {b.price_currency} {(b.price_amount || 0).toLocaleString()}</strong>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">Status: {b.status}</div>
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
                        <div key={i} className="border rounded p-2 bg-slate-50">
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
