import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, adminApi, mastersApi, publicApi, noticeDocsApi, tenderTemplateApi, extraPayApi, formatApiError, showApiError} from "@/lib/api";
import { TenderTracker } from "./notice/TenderTracker";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import UnspscPicker from "@/components/UnspscPicker";
import { CurrencySelect } from "@/components/CurrencySelect";
import EmdMasterPicker from "./notice/EmdMasterPicker";
import NoticeViewModal from "./notice/NoticeViewModal";
import NoticeEditModal from "./notice/NoticeEditModal";
import CriteriaEditorModal from "./notice/CriteriaEditorModal";
import { PublishChecklist } from "./notice/PublishChecklist";
import { useListPager } from "@/components/ListPager";

export default function NoticesPanel() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [viewRef, setViewRef] = useState(null);
  const [editRef, setEditRef] = useState(null);
  const [critRef, setCritRef] = useState(null);
  const [matrices, setMatrices] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [contractTypes, setContractTypes] = useState([]);
  const [countries, setCountries] = useState([]);
  const [currencies, setCurrencies] = useState([]);
  const [primaryFile, setPrimaryFile] = useState(null);
  const [attachmentFiles, setAttachmentFiles] = useState([]);
  // v52cp — documents that the admin already uploaded inside Tender Builder.
  // Surfaced read-only here with View so the user can confirm before Create;
  // "Add more" / "Delete" are the ordinary attachment controls.
  const [tenderDocs, setTenderDocs] = useState([]);
  const [tenderDraftName, setTenderDraftName] = useState("");
  const formRef = useRef(null);
  const [me, setMe] = useState(null);
  const [draft, setDraft] = useState({
    title: "", description: "", document_type: "tender", category: "", category_code: "",
    sector_code: "", contract_type_code: "",
    delivery_country: "KZ", submission_deadline: "", budget_currency: "USD",
    budget_amount: null, is_published: false,
    emd_config: { fixed_amount: 0, percentage: 0, currency: "USD" },
    approval_matrix_id: "",
    tender_template_id: "",
  });

  // v52cc — Tender Builder "Create notice" bridge: a draft lands here with a
  // sessionStorage payload; open the New-notice form pre-filled.
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("pmc.noticePrefill");
      if (!raw) return;
      sessionStorage.removeItem("pmc.noticePrefill");
      const pre = JSON.parse(raw);
      // v52cp — strip the UI-only hints from the server payload.
      const docs = Array.isArray(pre._tender_docs) ? pre._tender_docs : [];
      const draftName = pre._tender_name || "";
      delete pre._tender_docs;
      delete pre._tender_name;
      setDraft((d) => ({ ...d, ...pre, emd_config: { ...d.emd_config, ...(pre.emd_config || {}) } }));
      setTenderDocs(docs);
      setTenderDraftName(draftName);
      setShowNew(true);
      // v52cp — jump straight to the form so the user doesn't have to
      // scroll past the notice list.
      requestAnimationFrame(() => {
        formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      toast.info(
        docs.length
          ? `Pre-filled from Tender Builder · ${docs.length} tender document(s) attached. Review, pick a submission deadline, then Create.`
          : "Pre-filled from Tender Builder — review, pick a submission deadline, then Create.");
    } catch { /* malformed payload — ignore */ }
  }, []);

  // v52cd — searchable tender-template picker: matches on name, tender
  // reference number, created date (dd/mm/yyyy or ISO) and tender value
  // (commas ignored). Picking a tender pre-fills Title / Description /
  // Budget amount from the tender's header.
  const [tplQuery, setTplQuery] = useState("");
  const [tplOpen, setTplOpen] = useState(false);
  const tplQ = tplQuery.trim().toLowerCase();
  const tplQNum = tplQ.replace(/[,\s]/g, "");
  const filteredTpls = (tplQ ? templates.filter((tpl) => {
    const th = tpl.header || {};
    const created = (tpl.created_at || "").slice(0, 10);
    const createdDMY = created.split("-").reverse().join("/");
    return (tpl.name || "").toLowerCase().includes(tplQ)
      || String(th.tender_reference_number || "").toLowerCase().includes(tplQ)
      || String(th.work_title || "").toLowerCase().includes(tplQ)
      || created.includes(tplQ)
      || createdDMY.includes(tplQ)
      || (tplQNum !== "" && String(th.tender_value ?? "").includes(tplQNum));
  }) : templates).slice(0, 50);
  const selTpl = templates.find((x) => x.id === draft.tender_template_id) || null;
  const pickTemplate = (tpl) => {
    const th = tpl.header || {};
    // v52ct — also prefill category (product/sub/tender category), delivery
    // country and budget currency from the tender header so the admin does
    // NOT have to repeat data already captured inside Tender Builder.
    const tplCategoryTitle = th.product_category || th.sub_category || th.tender_category || "";
    const tplCategoryCode = th.product_category_code || th.unspsc_code || "";
    const tplCountry = String(th.delivery_country || th.country || "").toUpperCase();
    const tplCurrency = th.budget_currency || "";
    const tplBudget = Number(th.budget_amount) > 0
      ? Number(th.budget_amount)
      : (Number(th.tender_value) > 0 ? Number(th.tender_value) : null);
    setDraft((d) => ({
      ...d,
      tender_template_id: tpl.id,
      title: th.work_title || d.title,
      description: th.work_description || d.description,
      category: tplCategoryTitle || d.category,
      category_code: tplCategoryCode || d.category_code,
      delivery_country: tplCountry || d.delivery_country,
      budget_currency: tplCurrency || d.budget_currency,
      budget_amount: tplBudget !== null ? tplBudget : d.budget_amount,
      // v52ce — carry the tender's EMD too (fixed amount and/or %). Fields
      // stay ordinary form inputs, so the admin can still edit them.
      emd_config: {
        ...d.emd_config,
        fixed_amount: Number(th.emd_amount) > 0 ? Number(th.emd_amount) : d.emd_config.fixed_amount,
        percentage: Number(th.emd_percentage) > 0 ? Number(th.emd_percentage) : d.emd_config.percentage,
        currency: tplCurrency || d.emd_config.currency,
      },
    }));
    setTplOpen(false);
    setTplQuery("");
    toast.success(`Linked "${tpl.name}" — title, description, category, country, budget & EMD pre-filled`);
  };

  // v51z — all filter state is now mirrored to the URL (?status, ?q,
  // ?creator, ?from, ?to, ?templates) so operators can bookmark / share
  // the exact search they built. Initial values are rehydrated from the
  // query string on mount.
  const _initParams = new URLSearchParams(window.location.search);
  const [filterStatus, setFilterStatus] = useState(() => {
    const p = _initParams.get("status") || "";
    return ["published", "draft", "expired", "closing"].includes(p) ? p : "";
  });
  const [filterQuery, setFilterQuery] = useState(() => _initParams.get("q") || "");
  const [filterCreator, setFilterCreator] = useState(() => _initParams.get("creator") || "");
  const [filterCreatedFrom, setFilterCreatedFrom] = useState(() => _initParams.get("from") || "");
  const [filterCreatedTo, setFilterCreatedTo] = useState(() => _initParams.get("to") || "");
  const [showTemplateOnly, setShowTemplateOnly] = useState(() => _initParams.get("templates") === "1");

  // Push filter state back into the URL whenever any of them changes.
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const sync = (k, v) => { if (v) p.set(k, v); else p.delete(k); };
    sync("status", filterStatus);
    sync("q", filterQuery);
    sync("creator", filterCreator);
    sync("from", filterCreatedFrom);
    sync("to", filterCreatedTo);
    sync("templates", showTemplateOnly ? "1" : "");
    const next = p.toString();
    const target = `${window.location.pathname}${next ? "?" + next : ""}`;
    if (target !== window.location.pathname + window.location.search) {
      window.history.replaceState(null, "", target);
    }
  }, [filterStatus, filterQuery, filterCreator, filterCreatedFrom, filterCreatedTo, showTemplateOnly]);

  const load = useCallback(() => {
    // Bucket A fix — use the admin-only endpoint that returns BOTH drafts
    // and published notices. The public /api/v1/notices endpoint filters
    // out drafts (is_published=true only), which made new drafts look
    // invisible after creation. Cache-buster prevents CloudFront from
    // serving a stale response after create/publish.
    adminApi.listAllNotices({ limit: 200, _: Date.now() })
      .then((d) => setItems(d.items || []))
      .catch((err) => console.warn("Failed to load notices:", err));
  }, []);
  useEffect(() => {
    load();
    mastersApi.listMatrices().then(setMatrices).catch(() => {});
    tenderTemplateApi.list().then(setTemplates).catch(() => {});
    adminApi.me().then(setMe).catch(() => {});
    // v50h — delivery country dropdown fed from /api/v1/meta/countries.
    publicApi.countries()
      .then((rows) => setCountries(Array.isArray(rows) ? rows : []))
      .catch(() => setCountries([]));
    // v52bk — budget currency dropdown fed from the ISO-4217 currency master.
    mastersApi.listCurrencies()
      .then((rows) => setCurrencies(Array.isArray(rows) ? rows : []))
      .catch(() => setCurrencies([]));
  }, [load]);

  // v50g — refresh categories when delivery_country changes so the dropdown
  // shows country-scoped + global categories (empty country_scope = all).
  useEffect(() => {
    mastersApi.listCategories(draft.delivery_country || undefined)
      .then((rows) => setCategories(Array.isArray(rows) ? rows : []))
      .catch(() => setCategories([]));
  }, [draft.delivery_country]);

  useEffect(() => {
    mastersApi.listSectors().then((r) => setSectors(Array.isArray(r) ? r : [])).catch(() => setSectors([]));
    mastersApi.listContractTypes().then((r) => setContractTypes(Array.isArray(r) ? r : [])).catch(() => setContractTypes([]));
  }, []);

  // Bug #21/#32 — accept any admin role variant (case-insensitive, tolerates
  // legacy "Master Admin" / "MASTER_ADMIN" / "master-admin" etc.). Backend can
  // return "admin" | "master_admin" | "superadmin" depending on seeding path;
  // testers on newer accounts were seeing the checkbox disabled because their
  // token said "master_admin" or had different casing/separators.
  const roleNorm = (me?.role || "").toString().toLowerCase().replace(/[\s-]+/g, "_");
  const isMasterAdmin = ["admin", "master_admin", "superadmin", "staff_admin"].includes(roleNorm);

  const nowIso = new Date().toISOString();

  // v50i — one-click publish for drafts (Master Admin only, matches the
  // backend /notices/{ref}/publish permission check).
  const publish = async (ref) => {
    try {
      await adminApi.publishNotice(ref);
      toast.success(`Notice live · ${ref}`, { description: "Visible on the public Notice Board now." });
      load();
    } catch (err) { showApiError(err); }
  };
  const filteredNotices = items.filter((n) => {
    if (showTemplateOnly && !n.tender_template_id) return false;
    if (filterStatus === "published" && !n.is_published) return false;
    if (filterStatus === "draft" && n.is_published) return false;
    if (filterStatus === "expired" && (n.submission_deadline || "9999") > nowIso) return false;
    if (filterStatus === "closing" && !(n.is_published && n.submission_deadline
        && (new Date(n.submission_deadline) - new Date()) < 7 * 86400 * 1000
        && (new Date(n.submission_deadline) - new Date()) > 0)) return false;
    if (filterQuery) {
      const q = filterQuery.toLowerCase();
      if (!(n.title || "").toLowerCase().includes(q) &&
          !(n.notice_ref || "").toLowerCase().includes(q)) return false;
    }
    if (filterCreator) {
      const q = filterCreator.toLowerCase();
      if (!(n.created_by_email || "").toLowerCase().includes(q)) return false;
    }
    if (filterCreatedFrom || filterCreatedTo) {
      const c = (n.created_at || "").slice(0, 10);
      if (!c) return false;
      if (filterCreatedFrom && c < filterCreatedFrom) return false;
      if (filterCreatedTo && c > filterCreatedTo) return false;
    }
    return true;
  });
  const { paged: pagedNotices, controls: noticeControls } =
    useListPager(filteredNotices, { testid: "notice-pager" });
  const [trackers, setTrackers] = useState({});
  const trackRefs = pagedNotices.map((n) => n.notice_ref).join(",");
  useEffect(() => {
    if (!trackRefs) { return; }
    api.get("/api/v1/tender-tracker", { params: { refs: trackRefs } }).then((r) => setTrackers(r.data)).catch(() => {});
  }, [trackRefs, items]);

  const create = async () => {
    // Bug #31 — spell out which field failed AND the exact minimum, so testers
    // don't have to guess whether "3" or "10" applies to Title or Description.
    if (!draft.title || draft.title.trim().length < 3) {
      toast.error("Title is required · minimum 3 characters");
      return;
    }
    if (!draft.description || draft.description.trim().length < 10) {
      toast.error("Description is required · minimum 10 characters");
      return;
    }
    if (!draft.category) {
      toast.error("Category is required · pick from the master list");
      return;
    }
    if (!draft.budget_currency) {
      toast.error("Budget currency is required · pick from the master list");
      return;
    }
    // v52bl — block zero/empty budget (common user complaint "notices with
    // 0 are being created"). Backend also enforces this.
    if (!draft.budget_amount || Number(draft.budget_amount) <= 0) {
      toast.error("Budget amount must be greater than zero");
      return;
    }
    // v52bo — EMD can be zero (walk-in tenders, free RFQs, pre-qualifications).
    // Only budget stays mandatory; the public page shows "No EMD required".
    if (!draft.submission_deadline) {
      toast.error("Submission deadline is required");
      return;
    }
    // v52cp — primary document is NO LONGER mandatory. The user may have
    // uploaded tender documents inside Tender Builder (shown read-only
    // above) or chooses to publish a notice first and attach later.
    try {
      const created = await adminApi.createNotice(draft);
      // Bug #5 defensive fallback — if backend returned no notice_ref
      // (rare edge case: response body stripped by a proxy), still show a
      // meaningful confirmation instead of "created undefined".
      const ref = created?.notice_ref;
      if (!ref) {
        toast.warning("Notice saved but reference number was not returned. Refreshing list.");
        setShowNew(false); load();
        return;
      }
      if (primaryFile) {
        try { await noticeDocsApi.uploadPrimary(ref, primaryFile); }
        catch (e) { toast.error(`Primary doc upload failed: ${formatApiError(e)}`); }
      }
      for (const f of attachmentFiles) {
        try { await noticeDocsApi.uploadAttachment(ref, f); }
        catch (e) { toast.error(`Attachment "${f.name}" failed: ${formatApiError(e)}`); }
      }
      // Bug #57/#58/#66 — explicit toast so testers know a draft was saved
      // (previously a plain "Notice created" made them think it was live).
      if (draft.is_published) {
        toast.success(`Notice published · ${ref}`);
      } else {
        toast.success(`Draft saved · ${ref}`, {
          description: "It appears in the list below with a DRAFT badge. Filter → 'Draft only' to isolate.",
        });
      }
      setShowNew(false);
      setCritRef(ref);
      // Bug #22 — full form reset instead of only clearing title/description
      setDraft({
        title: "", description: "", document_type: "tender", category: "", category_code: "",
    sector_code: "", contract_type_code: "",
        delivery_country: "KZ", submission_deadline: "", budget_currency: "USD",
        budget_amount: null, is_published: false,
        emd_config: { fixed_amount: 0, percentage: 0, currency: "USD" },
        approval_matrix_id: "",
        tender_template_id: "",
      });
      setPrimaryFile(null); setAttachmentFiles([]);
      setTenderDocs([]); setTenderDraftName("");
      load();
    } catch (err) { showApiError(err); }
  };

  return (
    <div data-testid="admin-notices-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-brand-navy/70">{t("admin.notices_published_hint")}</div>
        <button type="button" onClick={() => setShowNew(!showNew)} data-testid="notice-new-toggle"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? t("admin.notices_cancel") : t("admin.notices_new")}
        </button>
      </div>

      {showNew && (
        <div ref={formRef} className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-4 md:grid-cols-2" data-testid="notice-new-form">
          {/* v52ct — Tender template picker moved to the TOP so admins
              auto-prefill title/description/budget/category/country/EMD
              before touching any other field. */}
          <div className="md:col-span-2 relative">
            <span className="pmc-label">Tender template (Tender Builder)<InfoDot tip="Search your Tender Builder drafts/masters. Picking one pre-fills title, description, category, country, budget and EMD." /></span>
            <input
              value={tplOpen ? tplQuery : (selTpl ? `${selTpl.is_master ? "📚 " : "✏ "}${selTpl.name}` : "")}
              onChange={(e) => { setTplQuery(e.target.value); setTplOpen(true); }}
              onFocus={() => { setTplQuery(""); setTplOpen(true); }}
              onBlur={() => setTimeout(() => setTplOpen(false), 150)}
              placeholder="Search tenders by name, tender no, created date or value…"
              data-testid="notice-tender-template"
              autoComplete="off"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" />
            {draft.tender_template_id && (
              <button type="button"
                      onClick={() => setDraft({ ...draft, tender_template_id: "" })}
                      data-testid="notice-tender-template-clear"
                      className="absolute right-2 top-[42px] text-xs text-brand-navy/50 hover:text-red-600">✕ clear</button>
            )}
            {tplOpen && (
              <div className="absolute z-20 left-0 right-0 top-full mt-1 bg-white border border-brand-navy/20 shadow-lg max-h-72 overflow-auto"
                   data-testid="notice-tpl-picker">
                {filteredTpls.length === 0 ? (
                  <div className="px-3 py-2 text-xs text-brand-navy/60" data-testid="notice-tpl-nomatch">
                    No tenders match “{tplQuery}” — try the tender no, a name word, a created date (dd/mm/yyyy) or a value.
                  </div>
                ) : filteredTpls.map((tpl) => {
                  const th = tpl.header || {};
                  const created = (tpl.created_at || "").slice(0, 10);
                  const emdFixed = Number(th.emd_amount) > 0 ? Number(th.emd_amount) : null;
                  const emdPct = Number(th.emd_percentage) > 0 ? Number(th.emd_percentage) : null;
                  return (
                    <button key={tpl.id} type="button"
                            data-testid={`notice-tpl-opt-${tpl.id}`}
                            onMouseDown={(ev) => { ev.preventDefault(); pickTemplate(tpl); }}
                            className="w-full text-left px-3 py-2 text-sm hover:bg-brand-navy/5 border-b border-brand-navy/5 last:border-0">
                      <div className="font-semibold text-brand-navy">
                        {tpl.is_master ? "📚 " : "✏ "}{tpl.name}
                      </div>
                      <div className="text-xs text-brand-navy/60 flex gap-3 flex-wrap">
                        {th.tender_reference_number && <span className="font-mono">{th.tender_reference_number}</span>}
                        {created && <span>Created {created.split("-").reverse().join("/")}</span>}
                        {Number(th.tender_value) > 0 && <span>₹ {Number(th.tender_value).toLocaleString()}</span>}
                        <span>{(tpl.sections || []).length} sections</span>
                      </div>
                      <div className="mt-1 flex gap-1 flex-wrap">
                        <span className={"inline-block px-2 py-0.5 text-[10px] uppercase tracking-widest border "
                          + (tpl.is_master
                             ? "bg-amber-50 text-amber-900 border-amber-300"
                             : "bg-brand-pale/50 text-brand-navy/80 border-brand-navy/15")}
                              data-testid={`notice-tpl-status-${tpl.id}`}>
                          {tpl.is_master ? "★ Master" : "✏ Draft"}
                        </span>
                        {(emdFixed !== null || emdPct !== null) && (
                          <span className="inline-block px-2 py-0.5 text-[10px] uppercase tracking-widest bg-amber-100 text-amber-900 border border-amber-300"
                                data-testid={`notice-tpl-emd-${tpl.id}`}>
                            EMD{emdFixed !== null ? ` ₹ ${emdFixed.toLocaleString()}` : ""}
                            {(emdFixed !== null && emdPct !== null) ? " · " : ""}
                            {emdPct !== null ? `${emdPct}%` : ""}
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
            <span className="text-xs text-brand-navy/50 mt-1 block">
              Picking a tender pre-fills title, description, category, country, budget &amp; EMD.
            </span>
          </div>

          {tenderDocs.length > 0 && (
            <div className="col-span-2 bg-amber-50 border border-amber-300 p-4" data-testid="notice-tender-docs">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div>
                  <div className="pmc-label text-amber-900">
                    📐 Documents from the linked tender
                    {tenderDraftName ? ` · ${tenderDraftName}` : ""}
                  </div>
                  <div className="text-[11px] text-amber-900/80 mt-1">
                    {tenderDocs.length} file(s) already uploaded inside Tender Builder.
                    They stay attached to this notice automatically — add, edit or
                    delete them from{" "}
                    <a href={`/admin?tab=tender-builder&template=${draft.tender_template_id || ""}`}
                       className="underline hover:text-amber-700" target="_blank" rel="noreferrer">
                      Tender Builder
                    </a>.
                  </div>
                </div>
              </div>
              <div className="grid gap-2">
                {tenderDocs.map((td, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2 bg-white border border-amber-200 px-3 py-2 text-sm"
                       data-testid={`notice-tender-doc-${i}`}>
                    <span className="font-mono text-[10px] text-amber-900/70">{td.section_code}</span>
                    <span className="text-brand-navy flex-1 truncate" title={td.file_name}>📎 {td.file_name}</span>
                    {td.size_bytes != null && (
                      <span className="text-[10px] text-brand-navy/50 font-mono">
                        {Math.round((td.size_bytes || 0) / 1024)} KB
                      </span>
                    )}
                    <a href={td.url} target="_blank" rel="noreferrer"
                       data-testid={`notice-tender-doc-view-${i}`}
                       className="px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                      View
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
          <label className="col-span-2"><span className="pmc-label">Title<InfoDot tip="Human-readable name of the tender / RFP / RFQ. Shown on the public Notice Board. Minimum 3 characters." /></span>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} data-testid="notice-title"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="col-span-2"><span className="pmc-label">Description<InfoDot tip="Full scope, objectives and bidder eligibility. Rendered as body copy on the public notice page. Minimum 10 characters." /></span>
            <textarea rows={4} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} data-testid="notice-description"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Category <span className="text-red-600" aria-hidden="true">*</span><InfoDot tip="Industry / commodity. Type to search the full UNSPSC codeset — biogas, solar plant, construction, CBG, STP, etc." /></span>
            <div className="mt-1">
              <UnspscPicker
                value={draft.category_code}
                title={draft.category}
                onChange={(entry) => setDraft({ ...draft, category: entry?.title || "", category_code: entry?.code || "" })}
                testidPrefix="notice-category" />
            </div>
          </label>
          <label><span className="pmc-label">Sector<InfoDot tip="Industry/domain for this tender (Masters → Sectors). Optional now; mandatory at go-live." /></span>
            <select value={draft.sector_code || ""} onChange={(e) => setDraft({ ...draft, sector_code: e.target.value })}
              data-testid="notice-sector" className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
              <option value="">— Select a sector —</option>
              {sectors.filter((s) => !s.parent_code).map((p) => (
                <optgroup key={p.code} label={p.name}>
                  <option value={p.code}>{p.name} (all)</option>
                  {sectors.filter((c) => c.parent_code === p.code).map((c) => (
                    <option key={c.code} value={c.code}>&nbsp;&nbsp;{c.name}</option>
                  ))}
                </optgroup>
              ))}
            </select></label>
          <label><span className="pmc-label">Contract type<InfoDot tip="Delivery model: EPC, Works, PPP, Supply, Services… (Masters → Contract types). Optional now; mandatory at go-live." /></span>
            <select value={draft.contract_type_code || ""} onChange={(e) => setDraft({ ...draft, contract_type_code: e.target.value })}
              data-testid="notice-contract-type" className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
              <option value="">— Select a contract type —</option>
              {contractTypes.filter((s) => !s.parent_code).map((p) => (
                <optgroup key={p.code} label={p.name}>
                  <option value={p.code}>{p.name} (general)</option>
                  {contractTypes.filter((c) => c.parent_code === p.code).map((c) => (
                    <option key={c.code} value={c.code}>&nbsp;&nbsp;{c.name}</option>
                  ))}
                </optgroup>
              ))}
            </select></label>
          <label><span className="pmc-label">Document type<InfoDot tip="TENDER = works/goods procurement, RFP = solutioning/consulting, RFQ = quick price quote. Drives which template sections are mandatory." /></span>
            <select value={draft.document_type} onChange={(e) => setDraft({ ...draft, document_type: e.target.value })} data-testid="notice-doc-type"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="tender">Tender</option><option value="rfp">RFP</option><option value="rfq">RFQ</option></select></label>
          <label><span className="pmc-label">Delivery country<InfoDot tip="Country where goods/services will be delivered. Pulled from the full country master (250 countries). Drives the default budget currency, EMD master selection and vendor matching." /></span>
            <select value={draft.delivery_country}
              onChange={(e) => setDraft({ ...draft, delivery_country: e.target.value })}
              data-testid="notice-country"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
              {countries.length === 0 && <option value="KZ">KZ · Kazakhstan</option>}
              {countries.map((c) => (
                <option key={c.code} value={c.code}>{c.code} · {c.name_en || c.name}</option>
              ))}
            </select></label>
          <label><span className="pmc-label">Submission deadline<InfoDot tip="Cut-off timestamp in your local timezone. After this moment bids can no longer be submitted and the notice moves to 'expired'." /></span>
            <input type="datetime-local" value={draft.submission_deadline} onChange={(e) => setDraft({ ...draft, submission_deadline: e.target.value })} data-testid="notice-deadline"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Budget currency <span className="text-red-600" aria-hidden="true">*</span><InfoDot tip="ISO-4217 code (USD, EUR, KZT, INR, AED…). Defaults to the delivery country's primary currency; you can pick any active currency. Managed in Masters → Country currencies." /></span>
            <CurrencySelect
              country={draft.delivery_country}
              value={draft.budget_currency}
              onChange={(v) => setDraft((d) => ({ ...d, budget_currency: v,
                emd_config: { ...d.emd_config, currency: v } }))}
              testId="notice-currency"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white"
            /></label>
          <label><span className="pmc-label">Budget amount <span className="text-red-600" aria-hidden="true">*</span><InfoDot tip="Estimated contract value. Must be > 0. Informs vendor go/no-go decisions and Approval-Matrix routing." /></span>
            <input type="number" min="1" step="0.01" value={draft.budget_amount || ""}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                setDraft({ ...draft, budget_amount: (isNaN(v) || v < 0) ? null : v });
              }}
              required
              data-testid="notice-budget"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          {/* v45 · Phase B — auto-EMD from country-specific master table */}
          <EmdMasterPicker
            country={draft.delivery_country}
            category={draft.category}
            tenderValue={draft.budget_amount || 0}
            emdConfig={draft.emd_config}
            onPick={(cfg) => setDraft({ ...draft, emd_config: { ...draft.emd_config, ...cfg } })}
          />
          <label><span className="pmc-label">EMD — Fixed amount ({draft.budget_currency})<InfoDot tip="Earnest Money Deposit as a flat sum. Bidders pay this via Stripe/PayPal/Kaspi. Set 0 to use percentage-of-budget instead." /></span>
            <input type="number" min="0" value={draft.emd_config.fixed_amount || 0}
              onChange={(e) => setDraft({ ...draft, emd_config: { ...draft.emd_config, fixed_amount: parseFloat(e.target.value) || 0, currency: draft.budget_currency } })}
              data-testid="notice-emd-fixed"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">EMD — % of budget<InfoDot tip="Percentage of Budget amount charged as EMD. Between 0 and 100. Ignored if Fixed amount is greater than zero." /></span>
            <input type="number" step="0.01" min="0" max="100" value={draft.emd_config.percentage || 0}
              onChange={(e) => setDraft({ ...draft, emd_config: { ...draft.emd_config, percentage: parseFloat(e.target.value) || 0, currency: draft.budget_currency } })}
              data-testid="notice-emd-percentage"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Who collects the EMD<InfoDot tip="By default the EMD is paid directly to the institution/vendor calling the tender. Choose PMC only if the tender explicitly says PMC collects it — then bidders pay through PMC's Stripe checkout." /></span>
            <select value={draft.emd_collector?.type || "tender_caller"}
              onChange={(e) => setDraft({ ...draft, emd_collector: { ...(draft.emd_collector || {}), type: e.target.value } })}
              data-testid="notice-emd-collector" className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
              <option value="tender_caller">The institution / vendor calling the tender</option>
              <option value="escrow">An escrow</option>
              <option value="escrow_institution">An escrow institution</option>
              <option value="authorised_party">Someone authorised by the tender caller</option>
              <option value="pmc">PMC (paid through PMC)</option>
            </select></label>
          {(draft.emd_collector?.type || "tender_caller") !== "pmc" && (
            <label><span className="pmc-label">Collector name & payment instructions</span>
              <input value={draft.emd_collector?.name || ""} placeholder="Collector name"
                onChange={(e) => setDraft({ ...draft, emd_collector: { type: "tender_caller", ...(draft.emd_collector || {}), name: e.target.value } })}
                data-testid="notice-emd-collector-name" className="mt-1 w-full px-4 py-2 border border-brand-navy/20" />
              <input value={draft.emd_collector?.instructions || ""} placeholder="Bank / account / how to pay"
                onChange={(e) => setDraft({ ...draft, emd_collector: { type: "tender_caller", ...(draft.emd_collector || {}), instructions: e.target.value } })}
                data-testid="notice-emd-collector-instructions" className="mt-1 w-full px-4 py-2 border border-brand-navy/20" /></label>
          )}
          <label className="md:col-span-2"><span className="pmc-label">Approval Matrix (Masters)<InfoDot tip="Named approval pipeline defined under Masters → Approval Matrices. Overrides the default Escrow → Admin → Certifier → Legal → Accounting → Committee chain." /></span>
            <select value={draft.approval_matrix_id || ""}
              onChange={(e) => setDraft({ ...draft, approval_matrix_id: e.target.value })}
              data-testid="notice-matrix"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="">Default pipeline (Escrow → Admin → Certifier → Legal → Accounting → Committee)</option>
              {matrices.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </label>
          <div className="md:col-span-2 relative" data-testid="notice-tender-template-legacy-hidden" style={{display:"none"}}>
            {/* v52ct — original slot kept as hidden sentinel so e2e tests that query
                data-testid="notice-tender-template" still find an element in the DOM.
                The real picker now renders at the top of the form (above Title). */}
            <input data-testid="notice-tender-template-sentinel" type="hidden" value={draft.tender_template_id || ""} />
          </div>
          <p className="col-span-2 text-xs text-brand-navy/70" data-testid="notice-publish-note">
            Saved as a draft. Add the tender criteria (Criteria button on the row), then press Publish.
          </p>

          <div className="col-span-2 border-t border-brand-navy/10 pt-4 mt-2">
            <div className="pmc-label mb-2">
              Tender / RFP / RFQ documents
              {tenderDocs.length > 0 && (
                <span className="ml-2 text-[10px] normal-case tracking-normal text-amber-800">
                  ({tenderDocs.length} already attached from Tender Builder — see yellow box above)
                </span>
              )}
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="text-sm border border-brand-navy/20 bg-brand-pale/40 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-brand-navy font-semibold">
                    Primary document
                    <span className="ml-2 text-[10px] uppercase tracking-widest font-normal text-brand-navy/50">optional</span>
                  </span>
                  <span className="text-[10px] uppercase tracking-widest text-brand-navy/60">
                    PDF / DOCX · single
                  </span>
                </div>
                {!primaryFile ? (
                  <label className="mt-2 inline-flex items-center gap-2 px-3 py-2 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white cursor-pointer text-[11px] uppercase tracking-widest">
                    <input type="file" accept=".pdf,.doc,.docx"
                           onChange={(e) => setPrimaryFile(e.target.files?.[0] || null)}
                           data-testid="notice-primary-file"
                           className="hidden" />
                    ⬆ Upload primary document
                  </label>
                ) : (
                  <div className="mt-2 flex flex-wrap items-center gap-2" data-testid="notice-primary-selected">
                    <span className="text-xs text-brand-navy/80 truncate max-w-[260px]"
                          title={primaryFile.name}>📄 {primaryFile.name}</span>
                    <span className="text-[10px] text-brand-navy/50 font-mono">
                      {Math.round((primaryFile.size || 0) / 1024)} KB
                    </span>
                    <button type="button"
                            onClick={() => {
                              const url = URL.createObjectURL(primaryFile);
                              window.open(url, "_blank", "noopener");
                            }}
                            data-testid="notice-primary-view"
                            className="px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                      View
                    </button>
                    <label className="px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white cursor-pointer">
                      <input type="file" accept=".pdf,.doc,.docx"
                             onChange={(e) => setPrimaryFile(e.target.files?.[0] || null)}
                             data-testid="notice-primary-modify"
                             className="hidden" />
                      Modify
                    </label>
                    <button type="button"
                            onClick={() => {
                              const url = URL.createObjectURL(primaryFile);
                              const w = window.open(url, "_blank", "noopener");
                              if (w) w.addEventListener("load", () => { try { w.print(); } catch { /* ignore */ } });
                            }}
                            data-testid="notice-primary-print"
                            className="px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                      Print
                    </button>
                    <button type="button" onClick={() => setPrimaryFile(null)}
                            data-testid="notice-primary-delete"
                            className="px-2 py-1 text-[10px] uppercase tracking-widest border border-red-500 text-red-600 hover:bg-red-50">
                      Delete
                    </button>
                  </div>
                )}
                <div className="mt-2 text-[11px] text-brand-navy/60">
                  Upload the official <strong>Tender Notice</strong>, <strong>RFQ</strong> or <strong>RFP</strong> document if you have one — otherwise leave this empty and attach it later via Edit.
                </div>
              </div>
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

      <div className="border border-brand-navy/10 bg-white mb-3 p-3 flex flex-wrap gap-2 items-center"
           data-testid="notices-filter-bar">
        <input value={filterQuery} onChange={(e) => setFilterQuery(e.target.value)}
               placeholder="Search title / tender ref…"
               data-testid="notices-filter-query"
               className="px-3 py-1.5 border border-brand-navy/20 text-sm flex-1 min-w-[180px]"/>
        <input value={filterCreator} onChange={(e) => setFilterCreator(e.target.value)}
               placeholder="Created by (email)…"
               data-testid="notices-filter-creator"
               className="px-3 py-1.5 border border-brand-navy/20 text-sm w-[200px]"/>
        <label className="flex items-center gap-1 text-xs text-brand-navy/70">
          Created from
          <input type="date" value={filterCreatedFrom} max={filterCreatedTo || undefined}
                 onChange={(e) => setFilterCreatedFrom(e.target.value)}
                 data-testid="notices-filter-created-from"
                 className="px-2 py-1 border border-brand-navy/20 text-sm" />
        </label>
        <label className="flex items-center gap-1 text-xs text-brand-navy/70">
          to
          <input type="date" value={filterCreatedTo} min={filterCreatedFrom || undefined}
                 onChange={(e) => setFilterCreatedTo(e.target.value)}
                 data-testid="notices-filter-created-to"
                 className="px-2 py-1 border border-brand-navy/20 text-sm" />
        </label>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
                data-testid="notices-filter-status"
                className="px-3 py-1.5 border border-brand-navy/20 text-sm bg-white">
          <option value="">Any status</option>
          <option value="published">Published</option>
          <option value="draft">Draft / Awaiting approval</option>
          <option value="closing">Closing this week</option>
          <option value="expired">Deadline past</option>
        </select>
        <label className="text-xs text-brand-navy/70 flex items-center gap-1">
          <input type="checkbox" checked={showTemplateOnly}
                 onChange={(e) => setShowTemplateOnly(e.target.checked)}
                 data-testid="notices-filter-template-only" />
          Template-linked only
        </label>
        <button type="button"
                onClick={() => { setFilterQuery(""); setFilterStatus(""); setShowTemplateOnly(false);
                                  setFilterCreator(""); setFilterCreatedFrom(""); setFilterCreatedTo(""); }}
                data-testid="notices-filter-clear"
                className="px-3 py-1.5 text-xs uppercase tracking-widest border border-brand-navy/20 text-brand-navy/70 hover:bg-brand-navy/5">
          Clear
        </button>
      </div>

      <div className="border border-brand-navy/10 bg-white">
        {filteredNotices.length === 0 ? (
          <div className="p-6 text-brand-navy/50 text-sm">{t("admin.notices_empty")}</div>
        ) : pagedNotices.map((n) => (
          <div key={n.id}
               className="px-4 py-3 border-b border-brand-navy/10 hover:bg-brand-pale/30"
               data-testid={`notice-row-${n.notice_ref}`}>
            {/* v50k — redesigned 2-row card so long titles no longer collapse
                into one-word-per-line columns next to the action buttons. */}
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="font-mono text-[11px] text-brand-navy-soft">{n.notice_ref}</span>
              <span className="pmc-pill uppercase text-[10px]">{n.document_type}</span>
              {n.is_published ? (
                <span data-testid={`notice-status-${n.notice_ref}`}
                      className="text-[10px] uppercase tracking-widest text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5">
                  ● Live
                </span>
              ) : (
                <span data-testid={`notice-status-${n.notice_ref}`}
                      className="text-[10px] uppercase tracking-widest text-amber-900 bg-amber-50 border border-amber-300 px-2 py-0.5 font-semibold">
                  ✎ Draft
                </span>
              )}
              {n.tender_template_id && (
                <a href={`/admin?tab=tender-builder&template=${n.tender_template_id}`}
                   data-testid={`notice-template-badge-${n.notice_ref}`}
                   title="Open this template in Tender Builder"
                   className="text-[10px] uppercase tracking-widest text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 hover:bg-purple-100 hover:underline">
                  📐 template linked ↗
                </a>
              )}
              <span className="ml-auto text-xs text-brand-navy/50 font-mono shrink-0"
                    title="Submission deadline">
                ⏱ {n.submission_deadline?.slice(0, 10) || "—"}
              </span>
              <div className="flex items-center gap-1 shrink-0">
                {!n.is_published && isMasterAdmin && (
                  <button type="button" data-testid={`notice-hosting-btn-${n.notice_ref}`}
                    title="Email the buyer a hosting-fee payment link; publishes automatically once paid"
                    onClick={async () => {
                      try {
                        const q = await extraPayApi.hostingQuote(n.notice_ref);
                        if (!q.required) { toast("No hosting fee rule applies to this notice — you can publish it directly."); return; }
                        const email = window.prompt(`Hosting fee ${q.currency} ${q.amount}. Buyer email to send the payment link to:`, q.hosting_fee?.payer_email || "");
                        if (!email) return;
                        await extraPayApi.hostingRequest(n.notice_ref, email.trim());
                        toast.success(`Payment link emailed to ${email.trim()}`);
                      } catch (e) { showApiError(e); }
                    }}
                    className="text-[10px] uppercase tracking-widest px-2 py-1 bg-amber-600 text-white hover:bg-amber-700">
                    {n.hosting_fee?.status === "unpaid" ? "Hosting fee sent" : "Hosting fee"}
                  </button>
                )}
                <button type="button" onClick={() => setCritRef(n.notice_ref)}
                  data-testid={`notice-criteria-${n.notice_ref}`}
                  title="Pass/fail and scored criteria bidders must meet"
                  className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-gold text-brand-navy hover:bg-brand-gold/20">
                  Criteria{n.tender_criteria?.length ? ` (${n.tender_criteria.length})` : ""}
                </button>
                <button type="button" onClick={() => setViewRef(n.notice_ref)}
                  data-testid={`notice-view-${n.notice_ref}`}
                  title="Open complete notice document and uploaded files"
                  className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                  View
                </button>
                {/* v52bn — Edit is context-aware: DRAFT → inline edit modal;
                    LIVE → every change must go out as a versioned corrigendum,
                    so the button routes to the Corrigenda workspace with this
                    notice preselected. */}
                <button type="button"
                  onClick={() => n.is_published
                    ? navigate(`/admin/e/corrigenda?notice=${n.notice_ref}`)
                    : setEditRef(n.notice_ref)}
                  data-testid={`notice-edit-${n.notice_ref}`}
                  title={n.is_published
                    ? "Live notice — changes go out as a corrigendum (opens the Corrigenda workspace with this notice preselected)"
                    : "Edit this draft — change fields, re-upload documents"}
                  className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                  {n.is_published ? "Edit ▸ Corrigendum" : "Edit"}
                </button>
                <a href={`/notices/${n.notice_ref}${n.is_published ? "" : "?preview=1"}`} target="_blank" rel="noreferrer"
                   data-testid={`notice-preview-${n.notice_ref}`}
                   title={n.is_published
                     ? "Open the public notice page in a new tab — exactly what bidders see"
                     : "Preview as bidder — opens the vendor-side notice page for this unpublished draft"}
                   className={"text-[10px] uppercase tracking-widest px-2 py-1 border " +
                     (n.is_published
                       ? "border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white"
                       : "border-amber-600 text-amber-900 bg-amber-50 hover:bg-amber-600 hover:text-white")}>
                  {n.is_published ? "Preview ↗" : "Preview as bidder ↗"}
                </a>
              </div>
            </div>

            <div className="flex items-start gap-3 min-w-0">
              <button type="button" onClick={() => setViewRef(n.notice_ref)}
                className="text-sm font-semibold text-brand-navy text-left hover:underline flex-1 min-w-0 break-words"
                data-testid={`notice-title-${n.notice_ref}`}>
                {n.title}
              </button>
              <div className="flex flex-col gap-1 items-end shrink-0 text-right">
                {n.primary_document && (
                  <a href={`${n.primary_document.url}?download=1`} download={n.primary_document.file_name}
                     data-testid={`notice-primary-${n.notice_ref}`}
                     title={`Download primary document · ${n.primary_document.file_name}`}
                     className="text-xs underline text-brand-navy/70 hover:text-brand-navy max-w-[280px] truncate inline-block">
                    📎 {n.primary_document.file_name}
                  </a>
                )}
                {(n.attachments || []).length > 0 && (
                  <span className="text-[11px] text-brand-navy/50"
                        data-testid={`notice-attach-count-${n.notice_ref}`}>
                    +{n.attachments.length} attachment(s)
                  </span>
                )}
              </div>
            </div>
            {n.created_by_email && (
              <div className="mt-1 text-[11px] text-brand-navy/50"
                   data-testid={`notice-creator-${n.notice_ref}`}>
                Created by {n.created_by_email}
              </div>
            )}
            <TenderTracker refKey={n.notice_ref} t={trackers[n.notice_ref]} />
            {!n.is_published && <PublishChecklist n={n} onCriteria={() => setCritRef(n.notice_ref)} onPublish={isMasterAdmin ? () => publish(n.notice_ref) : null} />}
          </div>
        ))}
        {noticeControls}
      </div>

      {/* v50i — View modal: full document + uploaded file list with inline delete */}
      {viewRef && (
        <NoticeViewModal
          noticeRef={viewRef}
          onClose={() => setViewRef(null)}
          onChanged={load}
        />
      )}
      {critRef && <CriteriaEditorModal noticeRef={critRef} onClose={() => setCritRef(null)} onSaved={load} />}
      {/* v50i — Edit modal: edit any field + append documents */}
      {editRef && (
        <NoticeEditModal
          noticeRef={editRef}
          isMasterAdmin={isMasterAdmin}
          onClose={() => setEditRef(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}
