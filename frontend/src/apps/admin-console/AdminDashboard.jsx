import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { adminApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import { toast } from "sonner";

function TabBar({ tab, setTab }) {
  const tabs = [
    ["registrations", "Registrations"],
    ["notices", "Notices"],
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

  const load = () => adminApi.listRegistrations({ status }).then(setItems).catch((e) => toast.error(formatApiError(e)));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

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
        <div className="flex items-center gap-2 mb-3">
          {["submitted", "under_review", "needs_clarification", "approved", "rejected"].map((s) => (
            <button key={s} onClick={() => setStatus(s)} data-testid={`reg-filter-${s}`}
              className={"px-3 py-1.5 text-[10px] uppercase tracking-widest border " +
                (status === s ? "bg-brand-navy text-white border-brand-navy" : "bg-white text-brand-navy/70 border-brand-navy/20")}>{s}</button>
          ))}
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
  const [draft, setDraft] = useState({
    title: "", description: "", document_type: "tender", category: "",
    delivery_country: "KZ", submission_deadline: "", budget_currency: "USD",
    budget_amount: null, is_published: true,
  });

  useEffect(() => {
    // Public listing suffices here (only published shows on board); admin
    // uses this to see what's live. Extra endpoint for drafts left for later.
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/notices?limit=100`)
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);

  const create = async () => {
    if (!draft.title || !draft.description || !draft.category || !draft.submission_deadline) {
      toast.error("Title, description, category and deadline are required");
      return;
    }
    try {
      await adminApi.createNotice(draft);
      toast.success("Notice created");
      setShowNew(false);
      setDraft({ ...draft, title: "", description: "" });
      // Reload
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/notices?limit=100`);
      const d = await r.json(); setItems(d.items || []);
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
          <label className="col-span-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={draft.is_published} onChange={(e) => setDraft({ ...draft, is_published: e.target.checked })} data-testid="notice-publish" />
            Publish immediately (visible on public board)
          </label>
          <div className="col-span-2 flex justify-end">
            <button type="button" onClick={create} data-testid="notice-create"
              className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">Create notice</button>
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white">
        {items.length === 0 && <div className="p-6 text-brand-navy/50 text-sm">No published notices yet.</div>}
        {items.map((n) => (
          <div key={n.id} className="p-4 border-b border-brand-navy/10 flex items-baseline gap-4" data-testid={`notice-row-${n.notice_ref}`}>
            <span className="font-mono text-xs text-brand-navy-soft">{n.notice_ref}</span>
            <span className="pmc-pill uppercase text-[10px]">{n.document_type}</span>
            <span className="text-sm font-semibold text-brand-navy flex-1">{n.title}</span>
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
    adminApi.audit({ limit: 100 }).then(setEvents).catch(() => {});
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
  return (
    <div className="border border-dashed border-brand-navy/20 bg-white p-14 text-center text-brand-navy/60" data-testid="admin-packages-panel">
      Package Tracker (App 2) — CSV import + status board · coming next iteration.
    </div>
  );
}

export default function AdminDashboard() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("registrations");

  useEffect(() => {
    adminApi.me().then(setMe).catch(() => { navigate("/admin/login"); });
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
            <div className="text-right">
              <div className="pmc-label">Signed in</div>
              <div className="text-sm text-brand-navy">{me.email}</div>
            </div>
            <button type="button" onClick={logout} data-testid="admin-logout"
              className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">Sign out</button>
          </div>
        </div>

        <div className="mt-8"><TabBar tab={tab} setTab={setTab} /></div>

        <div className="mt-8">
          {tab === "registrations" && <RegistrationsPanel />}
          {tab === "notices" && <NoticesPanel />}
          {tab === "packages" && <PackagesPanel />}
          {tab === "audit" && <AuditPanel />}
        </div>
      </main>
    </div>
  );
}
