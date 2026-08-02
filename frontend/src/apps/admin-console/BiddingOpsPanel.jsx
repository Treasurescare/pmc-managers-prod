import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { bidApi, committeeApi, staffApi, inspectionApi, formatApiError } from "@/lib/api";

const STATUS_LABELS = {
  emd_pending: "EMD pending", emd_paid: "EMD paid — Awaits Escrow",
  escrow_accepted: "Escrow accepted — Awaits Admin flag",
  admin_flagged: "Admin flagged — Awaits Certifier",
  certifier_cleared: "Certifier cleared — Awaits Legal",
  legal_cleared: "Legal cleared — Awaits Accounting",
  accounting_cleared: "Accounting cleared — Awaits Committee",
  awarded: "AWARDED", rejected: "Rejected", withdrawn: "Withdrawn", closed: "Closed",
};

export default function BiddingOpsPanel() {
  const [bids, setBids] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [filter, setFilter] = useState("");
  const [committees, setCommittees] = useState([]);
  const [showCom, setShowCom] = useState(false);
  const [comDraft, setComDraft] = useState({ notice_ref: "", chair: "", members: [], quorum: 3 });
  const [assignFor, setAssignFor] = useState(null); // bid we're assigning certifier to
  const [inspDraft, setInspDraft] = useState({ certifier_id: "", scheduled_at: "", location: "" });

  const load = useCallback(async () => {
    try {
      const [b, s, c] = await Promise.all([
        bidApi.list(filter ? { status: filter } : {}),
        staffApi.listStaff(),
        committeeApi.list(),
      ]);
      setBids(b || []); setStaffList(s || []); setCommittees(c || []);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [filter]);
  useEffect(() => { load(); }, [load]);

  const doAdminFlag = async (b) => {
    try {
      await bidApi.decide(b.id, { action: "accept", role: "admin", notes: "" });
      toast.success("Bid flagged to certifier");
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const doReject = async (b) => {
    try {
      await bidApi.decide(b.id, { action: "reject", role: "admin", notes: "" });
      toast.success("Bid rejected");
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const openAssign = (b) => {
    setAssignFor(b);
    setInspDraft({ certifier_id: "", scheduled_at: "", location: "" });
  };

  const submitAssign = async () => {
    if (!inspDraft.certifier_id || !inspDraft.scheduled_at) {
      return toast.error("Certifier and date are required");
    }
    try {
      await bidApi.assignCertifier(assignFor.id, inspDraft.certifier_id);
      await inspectionApi.assign({
        notice_ref: assignFor.notice_ref, bid_id: assignFor.id,
        certifier_id: inspDraft.certifier_id,
        scheduled_at: new Date(inspDraft.scheduled_at).toISOString(),
        location: inspDraft.location, notes: "",
      });
      toast.success("Certifier assigned & inspection scheduled");
      setAssignFor(null);
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const submitCommittee = async () => {
    if (!comDraft.notice_ref || !comDraft.chair || comDraft.members.length === 0) {
      return toast.error("Notice ref, chair and at least one member required");
    }
    try {
      await committeeApi.create({
        notice_ref: comDraft.notice_ref,
        chairperson_id: comDraft.chair,
        member_ids: comDraft.members,
        quorum: Number(comDraft.quorum) || 3,
      });
      toast.success("Committee formed");
      setShowCom(false);
      setComDraft({ notice_ref: "", chair: "", members: [], quorum: 3 });
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const certifiers = staffList.filter((s) => (s.roles || []).includes("certifier"));
  const admins = staffList.filter((s) => (s.roles || []).includes("admin"));

  return (
    <div data-testid="admin-bidding-panel">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="text-sm text-brand-navy/70">
          {bids.length} bids in pipeline · sequential Escrow → Admin → Certifier → Legal → Accounting → Committee
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select value={filter} onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-brand-navy/20 bg-white"
            data-testid="bid-filter">
            <option value="">All statuses</option>
            {Object.keys(STATUS_LABELS).map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
          </select>
          <button onClick={() => setShowCom(!showCom)} data-testid="committee-new-toggle"
            className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showCom ? "Cancel" : "Form Committee"}
          </button>
        </div>
      </div>

      {showCom && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-3 md:grid-cols-4"
          data-testid="committee-new-form">
          <label className="md:col-span-2 text-sm">
            <span className="pmc-label">Notice ref (e.g. PMC-NOT-2026-0001)</span>
            <input value={comDraft.notice_ref}
              onChange={(e) => setComDraft({ ...comDraft, notice_ref: e.target.value })}
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20"
              data-testid="committee-notice-ref" />
          </label>
          <label className="text-sm">
            <span className="pmc-label">Chairperson</span>
            <select value={comDraft.chair}
              onChange={(e) => setComDraft({ ...comDraft, chair: e.target.value })}
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20"
              data-testid="committee-chair">
              <option value="">Select…</option>
              {admins.map((a) => <option key={a.id} value={a.id}>{a.email}</option>)}
            </select>
          </label>
          <label className="text-sm">
            <span className="pmc-label">Quorum</span>
            <input type="number" min="1" value={comDraft.quorum}
              onChange={(e) => setComDraft({ ...comDraft, quorum: e.target.value })}
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="md:col-span-4 text-sm">
            <span className="pmc-label">Members (hold Ctrl/Cmd to multi-select)</span>
            <select multiple value={comDraft.members}
              onChange={(e) => setComDraft({
                ...comDraft,
                members: Array.from(e.target.selectedOptions, (o) => o.value),
              })}
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20 h-32"
              data-testid="committee-members">
              {admins.map((a) => <option key={a.id} value={a.id}>{a.email}</option>)}
            </select>
          </label>
          <div className="md:col-span-4 flex justify-end">
            <button onClick={submitCommittee} data-testid="committee-create-submit"
              className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              Form committee
            </button>
          </div>
        </div>
      )}

      {committees.length > 0 && (
        <div className="mb-6">
          <div className="pmc-label mb-2">Active committees</div>
          <div className="grid gap-2 md:grid-cols-2">
            {committees.map((c) => (
              <div key={c.id} className="border border-brand-navy/10 bg-white p-3 text-sm"
                data-testid={`committee-row-${c.notice_ref}`}>
                <div className="font-mono text-xs text-brand-navy-soft">{c.notice_ref}</div>
                <div>Status: <strong>{c.status}</strong> · {c.member_ids?.length || 0} members · quorum {c.quorum}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white overflow-x-auto" data-testid="bid-table">
        <table className="w-full text-sm">
          <thead className="text-left text-brand-navy/60 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-3 py-2">Bid ref</th><th className="px-3 py-2">Notice</th>
              <th className="px-3 py-2">Vendor</th><th className="px-3 py-2">Price</th>
              <th className="px-3 py-2">EMD</th><th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {bids.map((b) => (
              <tr key={b.id} className="border-t border-brand-navy/10" data-testid={`bid-row-${b.bid_ref}`}>
                <td className="px-3 py-2 font-mono text-xs">{b.bid_ref}</td>
                <td className="px-3 py-2 font-mono text-xs">{b.notice_ref}</td>
                <td className="px-3 py-2">{b.company_name || b.vendor_email}</td>
                <td className="px-3 py-2">{b.price_currency} {(b.price_amount || 0).toLocaleString()}</td>
                <td className="px-3 py-2 text-xs">
                  {b.emd_currency} {(b.emd_due_amount || 0).toLocaleString()}
                  {b.emd_paid_at && <div className="text-emerald-600">✓ paid</div>}
                </td>
                <td className="px-3 py-2 text-xs">{STATUS_LABELS[b.status] || b.status}</td>
                <td className="px-3 py-2 flex gap-1 flex-wrap">
                  {b.status === "escrow_accepted" && (
                    <button onClick={() => doAdminFlag(b)} data-testid={`admin-flag-${b.bid_ref}`}
                      className="text-[10px] bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700">Flag→Certifier</button>
                  )}
                  {b.status === "admin_flagged" && !b.assigned_certifier_id && (
                    <button onClick={() => openAssign(b)} data-testid={`assign-certifier-${b.bid_ref}`}
                      className="text-[10px] bg-amber-500 text-white px-2 py-1 rounded hover:bg-amber-600">Assign Certifier</button>
                  )}
                  {["emd_paid", "escrow_accepted", "admin_flagged"].includes(b.status) && (
                    <button onClick={() => doReject(b)} data-testid={`admin-reject-${b.bid_ref}`}
                      className="text-[10px] bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700">Reject</button>
                  )}
                </td>
              </tr>
            ))}
            {bids.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-brand-navy/40">No bids yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {assignFor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          data-testid="assign-certifier-modal">
          <div className="bg-white rounded-lg p-6 max-w-md w-full space-y-4">
            <h3 className="text-lg font-serif">Assign certifier — {assignFor.bid_ref}</h3>
            <label className="block text-sm">
              <span>Certifier</span>
              <select value={inspDraft.certifier_id}
                onChange={(e) => setInspDraft({ ...inspDraft, certifier_id: e.target.value })}
                className="mt-1 w-full border rounded px-3 py-2 text-sm" data-testid="assign-cert-select">
                <option value="">Select…</option>
                {certifiers.map((c) => <option key={c.id} value={c.id}>{c.email}</option>)}
              </select>
            </label>
            <label className="block text-sm">
              <span>Scheduled site visit</span>
              <input type="datetime-local" value={inspDraft.scheduled_at}
                onChange={(e) => setInspDraft({ ...inspDraft, scheduled_at: e.target.value })}
                className="mt-1 w-full border rounded px-3 py-2 text-sm" data-testid="assign-cert-date" />
            </label>
            <label className="block text-sm">
              <span>Location</span>
              <input value={inspDraft.location}
                onChange={(e) => setInspDraft({ ...inspDraft, location: e.target.value })}
                className="mt-1 w-full border rounded px-3 py-2 text-sm" placeholder="Site address" />
            </label>
            <div className="flex justify-end gap-2">
              <button onClick={() => setAssignFor(null)}
                className="px-4 py-2 text-sm border rounded">Cancel</button>
              <button onClick={submitAssign} data-testid="assign-cert-submit"
                className="px-4 py-2 text-sm bg-slate-900 text-white rounded">Assign</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
