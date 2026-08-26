import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { bidApi, committeeApi, staffApi, inspectionApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import CommitteeForm from "./bidding/CommitteeForm";
import CommitteeList from "./bidding/CommitteeList";
import BidTable from "./bidding/BidTable";
import AssignCertifierModal from "./bidding/AssignCertifierModal";

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
  const { t } = useI18n();
  const [bids, setBids] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [filter, setFilter] = useState("");
  const [committees, setCommittees] = useState([]);
  const [showCom, setShowCom] = useState(false);
  const [comDraft, setComDraft] = useState({ notice_ref: "", chair: "", members: [], quorum: 3,
                                              external_invitees: [] });
  const [extDraft, setExtDraft] = useState({ email: "", name: "", designation: "" });
  const [assignFor, setAssignFor] = useState(null);
  const [inspDraft, setInspDraft] = useState({ certifier_id: "", scheduled_at: "", location: "" });

  const load = useCallback(async () => {
    // Bug #3 fix — use allSettled so a single 403 (e.g. non-admin staff role)
    // does not kill the whole panel and leave the user with an unusable page.
    const [b, s, c] = await Promise.allSettled([
      bidApi.list(filter ? { status: filter } : {}),
      staffApi.listStaff(),
      committeeApi.list(),
    ]);
    if (b.status === "fulfilled") setBids(b.value || []);
    if (s.status === "fulfilled") setStaffList(s.value || []);
    if (c.status === "fulfilled") setCommittees(c.value || []);
    // Only surface the FIRST real error, and only if bids failed —
    // committee/staff lookups are optional decorations for the panel.
    if (b.status === "rejected") toast.error(formatApiError(b.reason));
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
        external_invitees: comDraft.external_invitees,
        quorum: Number(comDraft.quorum) || 3,
      });
      toast.success(`Committee formed${comDraft.external_invitees.length ? ` · ${comDraft.external_invitees.length} external invited by email` : ""}`);
      setShowCom(false);
      setComDraft({ notice_ref: "", chair: "", members: [], quorum: 3, external_invitees: [] });
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const certifiers = staffList.filter((s) => (s.roles || []).includes("certifier"));
  const admins = staffList.filter((s) => (s.roles || []).includes("admin"));

  return (
    <div data-testid="admin-bidding-panel">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="text-sm text-brand-navy/70">
          {bids.length} {t("panels.bidding.pipeline_hint")}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select value={filter} onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-brand-navy/20 bg-white"
            data-testid="bid-filter">
            <option value="">{t("panels.bidding.all_statuses")}</option>
            {Object.keys(STATUS_LABELS).map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
          </select>
          <button onClick={() => setShowCom(!showCom)} data-testid="committee-new-toggle"
            className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showCom ? t("panels.bidding.cancel") : t("panels.bidding.form_committee")}
          </button>
        </div>
      </div>

      {showCom && (
        <CommitteeForm
          comDraft={comDraft} setComDraft={setComDraft}
          extDraft={extDraft} setExtDraft={setExtDraft}
          staffList={staffList} admins={admins}
          onSubmit={submitCommittee}
        />
      )}

      <CommitteeList committees={committees} />

      <BidTable
        bids={bids}
        onAdminFlag={doAdminFlag}
        onReject={doReject}
        onOpenAssign={openAssign}
      />

      <AssignCertifierModal
        assignFor={assignFor}
        certifiers={certifiers}
        inspDraft={inspDraft}
        setInspDraft={setInspDraft}
        onCancel={() => setAssignFor(null)}
        onSubmit={submitAssign}
      />
    </div>
  );
}
