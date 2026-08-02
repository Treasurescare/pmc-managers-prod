import { useCallback, useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { adminApi, api, mastersApi, noticeDocsApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import { toast } from "sonner";
import KanbanColumn from "./packages/KanbanColumn";
import VendorsPanel from "./VendorsPanel";
import BiddingOpsPanel from "./BiddingOpsPanel";
import EvaluationPanel from "./EvaluationPanel";
import BOQContractsPanel from "./BOQContractsPanel";
import VendorIntelPanel from "./VendorIntelPanel";
import MastersPanel from "./MastersPanel";
import AnalyticsPanel from "./AnalyticsPanel";
import NotificationBell from "./NotificationBell";
import MFASetupModal from "./MFASetupModal";
import AuditCopilotButton from "./AuditCopilotButton";
import PermissionsPanel from "./PermissionsPanel";
import useTenantSkin from "@/apps/shared/useTenantSkin";

function TabBar({ tab, setTab }) {
  const tabs = [
    ["analytics", "Dashboard"],
    ["registrations", "Registrations"],
    ["vendors", "Vendors"],
    ["notices", "Notices"],
    ["bidding", "Bidding Ops"],
    ["evaluation", "Evaluation"],
    ["boq", "BOQ & Contracts"],
    ["vintel", "Vendor Intel"],
    ["masters", "Masters"],
    ["permissions", "Permissions"],
    ["packages", "Packages"],
    ["audit", "Audit"],
  ];
  return (
    <div className="flex flex-wrap gap-2" data-testid="admin-tabs">
      {tabs.map(([code, label]) => (
        <button
          key={code}
          type="button"
          onClick={() => setTab(code)}
          data-testid={`admin-tab-${code}`}
          className={
            "px-5 py-2 text-[11px] font-semibold uppercase tracking-widest border " +
            (tab === code
              ? "bg-brand-navy text-white border-brand-navy"
              : "bg-white text-brand-navy/70 border-brand-navy/20 hover:border-brand-navy-soft/60")
          }
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function RegistrationsPanel() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("submitted");
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState("");
  const [sendingReminders, setSendingReminders] = useState(false);

  const load = useCallback(() => {
    adminApi.listRegistrations({ status })
      .then(setItems)
      .catch((e) => toast.error(formatApiError(e)));
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const sendReminders = async () => {
    setSendingReminders(true);
    try {
      const r = await api.post("/api/v1/registrations/admin/send-reminders");
      toast.success(`Reminders sent to ${r.data.reminded} of ${r.data.checked} stale drafts`);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSendingReminders(false);
    }
  };

  const decide = async (action) => {
    if (!selected) return;
    if ((action === "reject" || action === "clarify") && !notes.trim()) {
      toast.error("Notes required for this action");
      return;
    }
    try {
      await adminApi.decideRegistration(selected.id, action, notes || null);
      toast.success(`${action} recorded`);
      setSelected(null); setNotes(""); load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[5fr_7fr]" data-testid="admin-registrations-panel">
      <div>
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          {["submitted", "under_review", "needs_clarification", "approved", "rejected", "draft"].map((s) => (
            <button key={s} onClick={() => setStatus(s)} data-testid={`reg-filter-${s}`}
              className={"px-3 py-1.5 text-[10px] uppercase tracking-widest border " +
                (status === s ? "bg-brand-navy text-white border-brand-navy" : "bg-white text-brand-navy/70 border-brand-navy/20")}>{s}</button>
          ))}
          <button
            type="button"
            onClick={sendReminders}
            disabled={sendingReminders}
            data-testid="reg-send-reminders"
            className="ml-auto px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy-soft/50 text-brand-navy-soft hover:bg-brand-navy-soft hover:text-white transition-colors disabled:opacity-50"
            title="Email everyone whose draft is more than 7 days old"
          >
            {sendingReminders ? "Sending…" : "Nudge stale drafts"}
          </button>
        </div>
        <div className="border border-brand-navy/10 bg-white">
          {items.length === 0 && <div className="p-6 text-brand-navy/50 text-sm">No registrations at this status.</div>}
          {items.map((r) => (
            <button key={r.id} type="button" onClick={() => { setSelected(r); setNotes(""); }}
              data-testid={`reg-row-${r.id}`}
              className={"w-full text-left p-4 border-b border-brand-navy/10 hover:bg-brand-navy/5 " + (selected?.id === r.id ? "bg-brand-navy/5" : "")}>
              <div className="text-sm font-semibold text-brand-navy">{r.company_name || "(no company)"}</div>
              <div className="text-xs text-brand-navy/60 mt-1 font-mono">{r.email}</div>
              <div className="text-[10px] uppercase tracking-widest text-brand-navy-soft mt-1">{r.status}</div>
            </button>
          ))}
        </div>
      </div>
      <div>
        {selected ? (
          <div className="border border-brand-navy/10 bg-white p-6" data-testid="reg-detail">
            <div className="pmc-label">Company</div>
            <h3 className="font-display text-2xl text-brand-navy mt-1">{selected.company_name || "(no company)"}</h3>
            <div className="text-sm text-brand-navy/70 mt-2">{selected.email} · {selected.country}</div>
            <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div><dt className="pmc-label">Reg. number</dt><dd className="text-brand-navy">{selected.registration_number || "—"}</dd></div>
              <div><dt className="pmc-label">Entity type</dt><dd className="text-brand-navy">{selected.legal_entity_type || "—"}</dd></div>
              <div><dt className="pmc-label">Primary sector</dt><dd className="text-brand-navy">{selected.primary_sector || "—"}</dd></div>
              <div><dt className="pmc-label">KZ licenses</dt><dd className="text-brand-navy">{(selected.kz_licenses || []).join(", ") || "—"}</dd></div>
              <div className="col-span-2"><dt className="pmc-label">Business description</dt><dd className="text-brand-navy whitespace-pre-wrap">{selected.business_description || "—"}</dd></div>
            </dl>
            <div className="mt-6">
              <label className="pmc-label">Reviewer notes (required for reject / clarify)</label>
              <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="reg-notes"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy" />
            </div>
            <div className="mt-4 flex gap-2 flex-wrap">
              <button type="button" onClick={() => decide("approve")} data-testid="reg-approve" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">Approve</button>
              <button type="button" onClick={() => decide("clarify")} data-testid="reg-clarify" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">Request clarification</button>
              <button type="button" onClick={() => decide("reject")} data-testid="reg-reject" className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-red-500/50 text-red-600 hover:bg-red-50">Reject</button>
            </div>
          </div>
        ) : (
          <div className="border border-dashed border-brand-navy/20 bg-white p-14 text-center text-brand-navy/50">
            Select a registration on the left to review it.
          </div>
        )}
      </div>
    </div>
  );
}

function NoticesPanel() {
  const [items, setItems] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [matrices, setMatrices] = useState([]);
  const [primaryFile, setPrimaryFile] = useState(null);
  const [attachmentFiles, setAttachmentFiles] = useState([]);
  const [draft, setDraft] = useState({
    title: "", description: "", document_type: "tender", category: "",
    delivery_country: "KZ", submission_deadline: "", budget_currency: "USD",
    budget_amount: null, is_published: true,
    emd_config: { fixed_amount: 0, percentage: 0, currency: "USD" },
    approval_matrix_id: "",
  });

  const load = useCallback(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/notices?limit=100`)
      .then((r) => r.json())
      .then((d) => setItems(d.items || []))
      .catch((err) => console.warn("Failed to load notices:", err));
  }, []);
  useEffect(() => {
    load();
    mastersApi.listMatrices().then(setMatrices).catch(() => {});
  }, [load]);

  const create = async () => {
    if (!draft.title || !draft.description || !draft.category || !draft.submission_deadline) {
      toast.error("Title, description, category and deadline are required");
      return;
    }
    try {
      const created = await adminApi.createNotice(draft);
      // Upload primary document + attachments if provided
      if (primaryFile) {
        try {
          await noticeDocsApi.uploadPrimary(created.notice_ref, primaryFile);
        } catch (e) { toast.error(`Primary doc upload failed: ${formatApiError(e)}`); }
      }
      for (const f of attachmentFiles) {
        try {
          await noticeDocsApi.uploadAttachment(created.notice_ref, f);
        } catch (e) { toast.error(`Attachment "${f.name}" failed: ${formatApiError(e)}`); }
      }
      toast.success(`Notice created · ${created.notice_ref}`);
      setShowNew(false);
      setDraft({ ...draft, title: "", description: "" });
      setPrimaryFile(null); setAttachmentFiles([]);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  return (
    <div data-testid="admin-notices-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-brand-navy/70">Published notices — visible on the public board</div>
        <button type="button" onClick={() => setShowNew(!showNew)} data-testid="notice-new-toggle"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? "Cancel" : "New notice"}
        </button>
      </div>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-4 md:grid-cols-2" data-testid="notice-new-form">
          <label className="col-span-2"><span className="pmc-label">Title</span>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} data-testid="notice-title"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="col-span-2"><span className="pmc-label">Description</span>
            <textarea rows={4} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} data-testid="notice-description"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Category</span>
            <input value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })} data-testid="notice-category"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Document type</span>
            <select value={draft.document_type} onChange={(e) => setDraft({ ...draft, document_type: e.target.value })} data-testid="notice-doc-type"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="tender">Tender</option><option value="rfp">RFP</option><option value="rfq">RFQ</option></select></label>
          <label><span className="pmc-label">Delivery country</span>
            <input value={draft.delivery_country} onChange={(e) => setDraft({ ...draft, delivery_country: e.target.value })} data-testid="notice-country"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Submission deadline</span>
            <input type="datetime-local" value={draft.submission_deadline} onChange={(e) => setDraft({ ...draft, submission_deadline: e.target.value })} data-testid="notice-deadline"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Budget currency</span>
            <input value={draft.budget_currency} onChange={(e) => setDraft({ ...draft, budget_currency: e.target.value })} data-testid="notice-currency"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Budget amount</span>
            <input type="number" value={draft.budget_amount || ""} onChange={(e) => setDraft({ ...draft, budget_amount: parseFloat(e.target.value) || null })} data-testid="notice-budget"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">EMD — Fixed amount ({draft.budget_currency})</span>
            <input type="number" min="0" value={draft.emd_config.fixed_amount || 0}
              onChange={(e) => setDraft({ ...draft, emd_config: { ...draft.emd_config, fixed_amount: parseFloat(e.target.value) || 0, currency: draft.budget_currency } })}
              data-testid="notice-emd-fixed"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">EMD — % of budget</span>
            <input type="number" step="0.01" min="0" max="100" value={draft.emd_config.percentage || 0}
              onChange={(e) => setDraft({ ...draft, emd_config: { ...draft.emd_config, percentage: parseFloat(e.target.value) || 0, currency: draft.budget_currency } })}
              data-testid="notice-emd-percentage"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="md:col-span-2"><span className="pmc-label">Approval Matrix (Masters)</span>
            <select value={draft.approval_matrix_id || ""}
              onChange={(e) => setDraft({ ...draft, approval_matrix_id: e.target.value })}
              data-testid="notice-matrix"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="">Default pipeline (Escrow → Admin → Certifier → Legal → Accounting → Committee)</option>
              {matrices.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </label>
          <label className="col-span-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={draft.is_published} onChange={(e) => setDraft({ ...draft, is_published: e.target.checked })} data-testid="notice-publish" />
            Publish immediately (visible on public board)
          </label>

          <div className="col-span-2 border-t border-brand-navy/10 pt-4 mt-2">
            <div className="pmc-label mb-2">Tender / RFP / RFQ documents</div>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="text-sm">
                <span className="text-brand-navy/70">Primary document (PDF/DOCX, single)</span>
                <input type="file" accept=".pdf,.doc,.docx"
                       onChange={(e) => setPrimaryFile(e.target.files?.[0] || null)}
                       data-testid="notice-primary-file"
                       className="mt-1 w-full text-sm" />
                {primaryFile && <div className="mt-1 text-xs text-brand-navy/60">Selected: {primaryFile.name}</div>}
              </label>
              <label className="text-sm">
                <span className="text-brand-navy/70">Additional attachments (BOQ, drawings, addenda…)</span>
                <input type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.dwg,.jpg,.png"
                       onChange={(e) => setAttachmentFiles(Array.from(e.target.files || []))}
                       data-testid="notice-attachments"
                       className="mt-1 w-full text-sm" />
                {attachmentFiles.length > 0 && (
                  <div className="mt-1 text-xs text-brand-navy/60">
                    {attachmentFiles.length} file(s): {attachmentFiles.map(f => f.name).join(", ")}
                  </div>
                )}
              </label>
            </div>
          </div>

          <div className="col-span-2 flex justify-end">
            <button type="button" onClick={create} data-testid="notice-create"
              className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">Create notice</button>
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white">
        {items.length === 0 && <div className="p-6 text-brand-navy/50 text-sm">No published notices yet.</div>}
        {items.map((n) => (
          <div key={n.id} className="p-4 border-b border-brand-navy/10 flex items-baseline gap-4 flex-wrap" data-testid={`notice-row-${n.notice_ref}`}>
            <span className="font-mono text-xs text-brand-navy-soft">{n.notice_ref}</span>
            <span className="pmc-pill uppercase text-[10px]">{n.document_type}</span>
            <span className="text-sm font-semibold text-brand-navy flex-1">{n.title}</span>
            {n.primary_document && (
              <a href={`${process.env.REACT_APP_BACKEND_URL}${n.primary_document.url}`} target="_blank" rel="noreferrer"
                 data-testid={`notice-primary-${n.notice_ref}`}
                 className="text-xs underline text-brand-navy/70">
                📎 {n.primary_document.file_name}
              </a>
            )}
            {(n.attachments || []).length > 0 && (
              <span className="text-xs text-brand-navy/50" data-testid={`notice-attach-count-${n.notice_ref}`}>
                +{n.attachments.length} attachment(s)
              </span>
            )}
            <span className="text-xs text-brand-navy/50 font-mono">{n.submission_deadline?.slice(0, 10)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AuditPanel() {
  const [events, setEvents] = useState([]);
  const [verifyResult, setVerifyResult] = useState(null);

  useEffect(() => {
    adminApi.audit({ limit: 100 })
      .then(setEvents)
      .catch((err) => console.warn("Failed to load audit events:", err));
  }, []);

  const verify = async () => {
    try { setVerifyResult(await adminApi.verifyAudit()); }
    catch (err) { toast.error(formatApiError(err)); }
  };

  return (
    <div data-testid="admin-audit-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-brand-navy/70">SHA-256 hash-chained ledger · Phase 2 adds append-only DB triggers + Object Lock</div>
        <button type="button" onClick={verify} data-testid="audit-verify"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">Verify chain</button>
      </div>
      {verifyResult && (
        <div data-testid="audit-verify-result" className={"mb-4 border p-4 text-sm " + (verifyResult.ok ? "border-green-500/40 bg-green-50 text-green-800" : "border-red-500/40 bg-red-50 text-red-800")}>
          {verifyResult.ok
            ? <>Chain verified · {verifyResult.events_checked} events</>
            : <>Chain broken at seq #{verifyResult.at_seq} — {verifyResult.reason}</>}
        </div>
      )}
      <div className="border border-brand-navy/10 bg-white overflow-x-auto">
        <table className="pmc-table w-full text-sm">
          <thead>
            <tr className="text-left text-brand-navy/60">
              <th className="px-4 py-2">#</th><th className="px-4 py-2">Type</th><th className="px-4 py-2">Target</th><th className="px-4 py-2">Actor</th><th className="px-4 py-2">Hash</th><th className="px-4 py-2">When</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id} className="border-t border-brand-navy/10" data-testid={`audit-row-${e.seq}`}>
                <td className="px-4 py-2 font-mono">{e.seq}</td>
                <td className="px-4 py-2">{e.event_type}</td>
                <td className="px-4 py-2 font-mono text-xs">{e.target_type}:{e.target_id?.slice(-8)}</td>
                <td className="px-4 py-2 text-xs">{e.actor_email || "—"}</td>
                <td className="px-4 py-2 font-mono text-[10px] text-brand-navy/50">{e.current_hash?.slice(0, 12)}…</td>
                <td className="px-4 py-2 text-xs">{e.at?.slice(0, 19).replace("T", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PackagesPanel() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [newDraft, setNewDraft] = useState({ title: "", category: "", phase: "", value: "", float_target_date: "", status: "backlog" });

  const load = useCallback(() => {
    setLoading(true);
    adminApi.listPackages({ limit: 1000 })
      .then((d) => setPackages(d.items || []))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  const columns = [
    { code: "backlog", label: "Backlog" },
    { code: "scoping", label: "Scoping" },
    { code: "sbd_draft", label: "SBD Draft" },
    { code: "ready", label: "Ready" },
    { code: "published", label: "Published" },
    { code: "cancelled", label: "Cancelled" },
  ];
  const grouped = columns.reduce((acc, col) => {
    acc[col.code] = packages.filter((p) => p.status === col.code);
    return acc;
  }, {});

  const onDragStart = (e, pkg) => {
    e.dataTransfer.setData("text/plain", pkg.id);
    e.dataTransfer.effectAllowed = "move";
  };
  const onDragOver = (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; };
  const onDrop = async (e, targetStatus) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain");
    const pkg = packages.find((p) => p.id === id);
    if (!pkg || pkg.status === targetStatus) return;
    // Optimistic update
    setPackages((prev) => prev.map((p) => (p.id === id ? { ...p, status: targetStatus } : p)));
    try {
      await api.post(`/api/v1/packages/${id}/status`, { status: targetStatus });
      toast.success(`Moved to ${targetStatus}`);
    } catch (err) {
      toast.error(formatApiError(err));
      load();
    }
  };

  const onImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/api/v1/packages/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`Imported ${r.data.created} packages (skipped ${r.data.skipped})`);
      e.target.value = "";
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setImporting(false);
    }
  };

  const createOne = async () => {
    if (!newDraft.title || !newDraft.category) {
      toast.error("Title and category are required");
      return;
    }
    try {
      await adminApi.createPackage({
        title: newDraft.title,
        category: newDraft.category,
        phase: newDraft.phase || undefined,
        value: newDraft.value ? parseFloat(newDraft.value) : undefined,
        float_target_date: newDraft.float_target_date || undefined,
        status: newDraft.status,
      });
      toast.success("Package created");
      setShowNew(false);
      setNewDraft({ title: "", category: "", phase: "", value: "", float_target_date: "", status: "backlog" });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const fmt = (v, cur = "USD") => (v == null ? "—" : new Intl.NumberFormat("en-US", { style: "currency", currency: cur, maximumFractionDigits: 0 }).format(v));

  return (
    <div data-testid="admin-packages-panel">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="text-sm text-brand-navy/70">
          {loading ? "Loading packages…" : `${packages.length} packages in pipeline · drag cards between columns to move status`}
        </div>
        <div className="flex items-center gap-2">
          <label
            data-testid="pkg-import-label"
            className={"px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy bg-white hover:border-brand-navy-soft/60 cursor-pointer " + (importing ? "opacity-50" : "")}
          >
            {importing ? "Importing…" : "Import CSV"}
            <input type="file" accept=".csv" onChange={onImport} disabled={importing} className="hidden" data-testid="pkg-import-input" />
          </label>
          <button
            type="button"
            onClick={() => setShowNew(!showNew)}
            data-testid="pkg-new-toggle"
            className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep"
          >
            {showNew ? "Cancel" : "New package"}
          </button>
        </div>
      </div>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-3 md:grid-cols-6" data-testid="pkg-new-form">
          <input placeholder="Title" data-testid="pkg-new-title" value={newDraft.title} onChange={(e) => setNewDraft({ ...newDraft, title: e.target.value })} className="md:col-span-3 px-3 py-2 border border-brand-navy/20" />
          <input placeholder="Category" data-testid="pkg-new-category" value={newDraft.category} onChange={(e) => setNewDraft({ ...newDraft, category: e.target.value })} className="md:col-span-2 px-3 py-2 border border-brand-navy/20" />
          <input placeholder="Phase" data-testid="pkg-new-phase" value={newDraft.phase} onChange={(e) => setNewDraft({ ...newDraft, phase: e.target.value })} className="px-3 py-2 border border-brand-navy/20" />
          <input placeholder="Value (USD)" data-testid="pkg-new-value" type="number" value={newDraft.value} onChange={(e) => setNewDraft({ ...newDraft, value: e.target.value })} className="px-3 py-2 border border-brand-navy/20" />
          <input placeholder="Float target (YYYY-MM-DD)" data-testid="pkg-new-date" type="date" value={newDraft.float_target_date} onChange={(e) => setNewDraft({ ...newDraft, float_target_date: e.target.value })} className="px-3 py-2 border border-brand-navy/20" />
          <select data-testid="pkg-new-status" value={newDraft.status} onChange={(e) => setNewDraft({ ...newDraft, status: e.target.value })} className="px-3 py-2 border border-brand-navy/20">
            {columns.map((c) => (<option key={c.code} value={c.code}>{c.label}</option>))}
          </select>
          <button type="button" onClick={createOne} data-testid="pkg-new-create" className="md:col-span-2 px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">Create</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-3" data-testid="pkg-board">
        {columns.map((col) => (
          <KanbanColumn
            key={col.code}
            column={col}
            items={grouped[col.code] || []}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onDragStart={onDragStart}
            fmt={fmt}
          />
        ))}
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("analytics");
  const [mfaOpen, setMfaOpen] = useState(false);
  const tenant = useTenantSkin();

  useEffect(() => {
    adminApi.me()
      .then(setMe)
      .catch(() => { navigate("/admin/login"); });
  }, [navigate, location.pathname]);

  const logout = async () => { await adminApi.logout(); navigate("/admin/login"); };

  if (!me) return <div className="min-h-screen bg-brand-pale flex items-center justify-center text-brand-navy/60">{t("common.loading")}</div>;

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 lg:px-10 py-10">
        <div className="flex items-baseline justify-between flex-wrap gap-4">
          <div>
            <div className="pmc-label">{t("admin.dash_kicker")}</div>
            <h1 className="font-display text-3xl lg:text-4xl mt-2 text-brand-navy">{t("admin.dash_title")}</h1>
          </div>
          <div className="flex items-center gap-4">
            {tenant && (
              <div className="text-xs px-2 py-1 border border-brand-navy/20 text-brand-navy/70"
                   data-testid="admin-tenant-chip">
                Portal · {tenant.name}
              </div>
            )}
            <NotificationBell />
            <AuditCopilotButton />
            <button type="button" onClick={() => setMfaOpen(true)} data-testid="admin-mfa-open"
              className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
              Security · 2FA
            </button>
            <div className="text-right">
              <div className="pmc-label">Signed in</div>
              <div className="text-sm text-brand-navy">{me.email}</div>
            </div>
            <button type="button" onClick={logout} data-testid="admin-logout"
              className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">Sign out</button>
          </div>
          <MFASetupModal open={mfaOpen} onClose={() => setMfaOpen(false)} />
        </div>

        <div className="mt-8"><TabBar tab={tab} setTab={setTab} /></div>

        <div className="mt-8">
          {tab === "analytics" && <AnalyticsPanel />}
          {tab === "registrations" && <RegistrationsPanel />}
          {tab === "vendors" && <VendorsPanel />}
          {tab === "notices" && <NoticesPanel />}
          {tab === "bidding" && <BiddingOpsPanel />}
          {tab === "evaluation" && <EvaluationPanel />}
          {tab === "boq" && <BOQContractsPanel />}
          {tab === "vintel" && <VendorIntelPanel />}
          {tab === "masters" && <MastersPanel />}
          {tab === "permissions" && <PermissionsPanel />}
          {tab === "packages" && <PackagesPanel />}
          {tab === "audit" && <AuditPanel />}
        </div>
      </main>
    </div>
  );
}
