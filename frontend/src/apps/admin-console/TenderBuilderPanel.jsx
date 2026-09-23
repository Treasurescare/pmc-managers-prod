import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { tenderTemplateApi, tenderProApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TenderHeaderForm from "./tender/TenderHeaderForm";
import AiDiffModal from "./tender/AiDiffModal";
import VersionHistory from "./tender/VersionHistory";
import TenderSidebar from "./tender/TenderSidebar";
import TenderSectionCard from "./tender/TenderSectionCard";
import TenderFilterBar, { applyTenderFilters } from "./tender/TenderFilterBar";
import DprGenerateModal from "./tender/DprGenerateModal";
import { exportTenderPdf } from "./tender/tenderPdf";
import { InfoDot } from "@/components/InfoDot";

/**
 * TenderBuilderPanel — Section-by-section tender/RFP/RFQ composer.
 *
 * Left column (TenderSidebar): kind picker + master library + user drafts.
 * Right column: header meta form + section cards (TenderSectionCard).
 * All heavy per-section markup was extracted into TenderSectionCard so this
 * top-level file stays under 250 lines and easy to scan.
 */
const KIND_LABEL = { section: "Section", annexure: "Annexure", form: "Form" };

export default function TenderBuilderPanel() {
  const { t } = useI18n();
  const [list, setList] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [doc, setDoc] = useState(null);
  const [kind, setKind] = useState("tender");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Bug 31c — clicking a Kind tab should NOT leak the previous doc into the
  // right pane. Reset both the selection AND the loaded document.
  const switchKind = (k) => {
    setKind(k);
    setSelectedId(null);
    setDoc(null);
    setDirty(false);
  };

  const load = useCallback(async () => {
    try { setList(await tenderTemplateApi.list()); }
    catch (e) { showApiError(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openTemplate = async (id) => {
    setSelectedId(id);
    setDirty(false);
    try { setDoc(await tenderTemplateApi.get(id)); }
    catch (e) { showApiError(e); }
  };

  const cloneMaster = async (master) => {
    setBusy(true);
    try {
      // Bug #69/#70/#71 — strip fields that don't belong on a clone.
      // The master's `attachment` refers to a file uploaded on that specific
      // template; carrying it into a clone caused the backend to fail on
      // sections with dangling file references (500). We also strip any
      // stray `_id` / `id` / server-side timestamps that pydantic rejects.
      const cleanSections = (master.sections || []).map((s) => ({
        code: s.code,
        kind: s.kind || "section",
        title: s.title,
        hint: s.hint ?? null,
        body: s.body ?? "",
        order: typeof s.order === "number" ? s.order : null,
        // deliberately omit `attachment` — clones start with no attached files
      }));
      const payload = {
        name: `${master.name} — draft ${new Date().toISOString().slice(0, 10)}`,
        kind, industry: master.industry,
        header: { ...(master.header || {}) },
        sections: cleanSections,
      };
      const created = await tenderTemplateApi.create(payload);
      toast.success(`Draft created · ${created.name}`, {
        description: "Attachments were reset — re-upload any section files on the clone.",
      });
      await load();
      await openTemplate(created.id);
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const patchSection = (idx, patch) => {
    setDoc((prev) => {
      const sections = [...(prev.sections || [])];
      sections[idx] = { ...sections[idx], ...patch };
      return { ...prev, sections };
    });
    setDirty(true);
  };

  const patchHeader = (patch) => {
    setDoc((prev) => ({ ...prev, header: { ...(prev.header || {}), ...patch } }));
    setDirty(true);
  };

  const uploadSectionAttachment = async (idx, file) => {
    if (!file || !doc?.id) return;
    setBusy(true);
    try {
      const updated = await tenderTemplateApi.uploadSectionAttachment(doc.id, doc.sections[idx].code, file);
      setDoc(updated);
      toast.success("Attachment uploaded");
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const removeSectionAttachment = async (idx) => {
    if (!doc?.id) return;
    if (!confirm("Remove this attachment?")) return;
    try {
      const updated = await tenderTemplateApi.removeSectionAttachment(doc.id, doc.sections[idx].code);
      setDoc(updated);
    } catch (e) { showApiError(e); }
  };

  const [aiBusyCode, setAiBusyCode] = useState(null);
  const [diffState, setDiffState] = useState(null); // { idx, oldBody, newBody, title }
  const runAiDraft = async (idx, opts) => {
    if (!doc?.id) return;
    const s = doc.sections[idx];
    setAiBusyCode(s.code);
    try {
      const r = await tenderTemplateApi.aiDraftSection(doc.id, s.code, opts);
      const newBody = r.body || "";
      if (s.body && s.body.trim()) {
        setDiffState({ idx, oldBody: s.body, newBody, title: s.title });
      } else {
        patchSection(idx, { body: newBody });
        toast.success(`Draft filled by AI · ${s.code}`);
      }
    } catch (e) { showApiError(e); }
    finally { setAiBusyCode(null); }
  };
  const acceptAiDraft = () => {
    if (!diffState) return;
    patchSection(diffState.idx, { body: diffState.newBody });
    toast.success("AI draft applied");
    setDiffState(null);
  };
  const rejectAiDraft = () => {
    toast.info("AI draft discarded");
    setDiffState(null);
  };

  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkReport, setBulkReport] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [pdfLang, setPdfLang] = useState("en");
  const bulkUpload = async (files) => {
    if (!doc?.id || !files?.length) return;
    setBulkBusy(true);
    try {
      const r = await tenderTemplateApi.bulkUpload(doc.id, Array.from(files));
      setDoc(r.template);
      setBulkReport(r.report);
      const matched = r.report.filter((x) => x.matched).length;
      toast.success(`${matched}/${r.report.length} files matched to sections`);
    } catch (e) { showApiError(e); }
    finally { setBulkBusy(false); }
  };

  const addBlank = (kindCode) => {
    setDoc((prev) => {
      const sections = [...(prev.sections || [])];
      const nextOrder = sections.length ? Math.max(...sections.map((s) => s.order || 0)) + 10 : 10;
      const code = `${kindCode}-${sections.length + 1}`;
      sections.push({ code, kind: kindCode, title: `New ${KIND_LABEL[kindCode]}`,
                       hint: "", body: "", order: nextOrder });
      return { ...prev, sections };
    });
    setDirty(true);
  };

  const removeSection = (idx) => {
    if (!confirm(t("panels.tender_builder.remove_section_confirm"))) return;
    setDoc((prev) => {
      const sections = [...(prev.sections || [])];
      sections.splice(idx, 1);
      return { ...prev, sections };
    });
    setDirty(true);
  };

  const move = (idx, delta) => {
    setDoc((prev) => {
      const sections = [...(prev.sections || [])];
      const target = idx + delta;
      if (target < 0 || target >= sections.length) return prev;
      [sections[idx], sections[target]] = [sections[target], sections[idx]];
      sections.forEach((s, i) => { s.order = (i + 1) * 10; });
      return { ...prev, sections };
    });
    setDirty(true);
  };

  const save = async () => {
    if (!doc) return;
    setBusy(true);
    try {
      const payload = {
        name: doc.name, kind: doc.kind || "tender",
        industry: doc.industry, header: doc.header || {},
        sections: doc.sections || [],
      };
      const updated = await tenderTemplateApi.update(doc.id, payload);
      toast.success("Saved");
      setDoc(updated);
      setDirty(false);
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const removeDraft = async () => {
    if (!doc || doc.is_master) return;
    if (!confirm(t("panels.tender_builder.delete_draft_confirm"))) return;
    try {
      await tenderTemplateApi.remove(doc.id);
      toast.success("Deleted");
      setDoc(null); setSelectedId(null);
      await load();
    } catch (e) { showApiError(e); }
  };

  const masters = list.filter((x) => x.is_master);
  const drafts = list.filter((x) => !x.is_master);
  // v45 · Phase A — client-side filter + sort of drafts
  const [filters, setFilters] = useState({ q: "", country: "", industry: "", sort: "date-desc" });
  const filteredDrafts = useMemo(() => applyTenderFilters(drafts, filters), [drafts, filters]);
  const industries = useMemo(() => [...new Set(list.map((d) => d.industry).filter(Boolean))].sort(), [list]);
  const countries  = useMemo(() => [...new Set(list.map((d) => (d.country || d.header?.country || "")).filter(Boolean))].sort(), [list]);
  const [showDpr, setShowDpr]           = useState(false);
  const [aiFillBusy, setAiFillBusy]     = useState(false);
  const [sectionSaving, setSectionSaving] = useState(null);
  // v45f · Autosave — every 30s if the open doc has unsaved edits.
  const [autosaveDirty, setAutosaveDirty] = useState(false);
  const [autoSaving, setAutoSaving] = useState(false);
  useEffect(() => {
    if (!doc?.id || !autosaveDirty) return;
    const t = setInterval(async () => {
      setAutoSaving(true);
      try {
        await tenderTemplateApi.update(doc.id, doc);
        setAutosaveDirty(false);
        toast.info("Autosaved", { duration: 1200 });
      } catch { /* silent — manual Save remains */ }
      finally { setAutoSaving(false); }
    }, 30000);
    return () => clearInterval(t);
  }, [autosaveDirty, doc]);
  useEffect(() => { if (doc?.id) setAutosaveDirty(true); }, [doc]);
  const [saveMasterBusy, setSaveMasterBusy] = useState(false);

  const runAiFillAll = async () => {
    if (!doc?.id) return;
    if (!confirm("Draft every empty section with AI? This may take up to 60 seconds.")) return;
    setAiFillBusy(true);
    try {
      const r = await tenderProApi.aiFillAll(doc.id, { only_empty: true, tone: "formal", length: "medium" });
      setDoc(r.template);
      toast.success(`AI drafted ${r.updated} section(s)`);
      await load();
    } catch (e) { showApiError(e); } finally { setAiFillBusy(false); }
  };

  const saveAsMaster = async () => {
    if (!doc?.id) return;
    const country = prompt("Save as master under which country (ISO-2, e.g. KZ, IN, MY, GB)?", (doc.country || doc.header?.country || "KZ"));
    if (!country) return;
    const industry = prompt("Industry / vertical (e.g. Public Works, Software, Consulting)?", doc.industry || "General");
    if (!industry) return;
    setSaveMasterBusy(true);
    try {
      await tenderProApi.saveAsMaster(doc.id, { country: country.trim().toUpperCase(), industry: industry.trim() });
      toast.success(`Saved as master · ${country.toUpperCase()} / ${industry}`);
      await load();
    } catch (e) { showApiError(e); } finally { setSaveMasterBusy(false); }
  };

  const genRef = async () => {
    if (!doc) return;
    const country = doc.country || doc.header?.country || prompt("Country code (ISO-2)?", "KZ");
    if (!country) return;
    try {
      const r = await tenderProApi.nextReference(country.toUpperCase(), doc.industry || "GEN", doc.kind || "tender");
      patchHeader({ tender_reference_number: r.reference, tender_id: r.reference });
      toast.success(`Reference generated · ${r.reference}`);
    } catch (e) { showApiError(e); }
  };

  const saveSection = async (idx) => {
    if (!doc?.id) return;
    const s = doc.sections[idx];
    setSectionSaving(s.code);
    try {
      await tenderProApi.patchSection(doc.id, s.code, { body: s.body, title: s.title, hint: s.hint });
      toast.success(`Section saved · ${s.code}`, { description: "Resume anytime — this section is persisted" });
    } catch (e) { showApiError(e); }
    finally { setSectionSaving(null); }
  };

  const orderedSections = useMemo(
    () => [...(doc?.sections || [])].sort((a, b) => (a.order || 0) - (b.order || 0)),
    [doc?.sections],
  );

  return (
    <div data-testid="tender-builder-panel" className="grid gap-6 lg:grid-cols-[300px_1fr]">
      <div className="space-y-4">
        <TenderFilterBar filters={filters} setFilters={setFilters}
                          industries={industries} countries={countries} />
        <button type="button" onClick={() => setShowDpr(true)}
                data-testid="tb-open-dpr"
                className="w-full px-4 py-2.5 text-[11px] font-semibold uppercase tracking-widest bg-emerald-600 text-white hover:bg-emerald-700">
          ✨ AI Generate from DPR
        </button>
        <TenderSidebar
          t={t}
          kind={kind} setKind={switchKind}
          masters={masters} drafts={filteredDrafts} busy={busy}
          selectedId={selectedId}
          cloneMaster={cloneMaster} openTemplate={openTemplate}
        />
      </div>

      <section>
        {!doc ? (
          <div className="border border-dashed border-brand-navy/20 bg-white p-16 text-center text-brand-navy/50">
            {t("panels.tender_builder.pick_a_draft")}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div className="border border-brand-navy/10 bg-white p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <div className="flex-1 min-w-[240px]">
                  <div className="pmc-label">{t("panels.tender_builder.tender_name")}<InfoDot tip="Human-readable draft name. Not shown publicly — this is only the internal handle used inside Tender Builder." /></div>
                  <input value={doc.name || ""}
                    onChange={(e) => { setDoc({ ...doc, name: e.target.value }); setDirty(true); }}
                    data-testid="tb-name"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-lg font-serif text-brand-navy" />
                </div>
                <div className="flex gap-2 flex-wrap">
                  <button onClick={save} disabled={busy || !dirty}
                    data-testid="tb-save"
                    className="px-5 py-2 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                    {busy ? t("panels.tender_builder.saving") : dirty ? t("panels.tender_builder.save") : t("panels.tender_builder.saved")}
                    <InfoDot tip="Persist header + section changes. Snapshots the previous version to History (max 20 kept). Enabled only when there are unsaved edits." />
                  </button>
                  <button onClick={() => setShowHistory(true)} disabled={!doc?.id}
                    data-testid="tb-history"
                    title="View and restore rolling snapshots of this tender"
                    className="px-3 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/10">
                    ⟲ {t("panels.tender_builder.history")}{typeof doc?.version === "number" ? ` · v${doc.version}` : ""}
                    <InfoDot tip="Every Save creates a version. Click any prior version to restore or diff." />
                  </button>
                  <button onClick={() => exportTenderPdf(doc)} disabled={!doc}
                    data-testid="tb-export-pdf"
                    title="Opens the browser print dialog — pick 'Save as PDF'"
                    className="px-4 py-2 text-[12px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
                    {t("panels.tender_builder.print_pdf")}
                    <InfoDot tip="Browser-rendered PDF. Fast preview, but layout depends on your browser's print engine." />
                  </button>
                  <select value={pdfLang} onChange={(e) => setPdfLang(e.target.value)}
                    data-testid="tb-pdf-lang"
                    title="Language for the downloaded PDF (labels only — bodies stay original)"
                    className="px-2 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy bg-white">
                    <option value="en">EN</option>
                    <option value="ru">RU</option>
                    <option value="kk">KK</option>
                  </select>
                  <button onClick={() => exportTenderPdf(doc, { download: true, lang: pdfLang })} disabled={!doc}
                    data-testid="tb-download-pdf"
                    title="Downloads a real .pdf rendered on the server"
                    className="px-4 py-2 text-[12px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/10">
                    {t("panels.tender_builder.download_pdf")}
                  </button>
                  {!doc.is_master && (
                    <button onClick={removeDraft} data-testid="tb-delete"
                      className="px-4 py-2 text-[12px] uppercase tracking-widest border border-red-500 text-red-600 hover:bg-red-50">
                      {t("panels.tender_builder.delete")}
                    </button>
                  )}
                  {/* v45 — Phase A/B/C action buttons */}
                  <button onClick={runAiFillAll} disabled={aiFillBusy}
                          data-testid="tb-ai-fill-all"
                          className="px-4 py-2 text-[12px] uppercase tracking-widest bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40">
                    {aiFillBusy ? "AI drafting…" : "✨ AI Fill All"}
                  </button>
                  <button onClick={genRef} data-testid="tb-gen-ref"
                          className="px-4 py-2 text-[12px] uppercase tracking-widest border border-brand-navy-soft text-brand-navy-soft hover:bg-brand-navy-soft hover:text-white">
                    ↻ Auto Tender ID
                  </button>
                  {!doc.is_master && (
                    <button onClick={saveAsMaster} disabled={saveMasterBusy}
                            data-testid="tb-save-master"
                            className="px-4 py-2 text-[12px] uppercase tracking-widest border border-amber-600 text-amber-700 hover:bg-amber-50 disabled:opacity-40">
                      {saveMasterBusy ? "Saving…" : "★ Save as master"}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* CPPP-style structured header */}
            <TenderHeaderForm header={doc.header} patchHeader={patchHeader} />

            {/* Bulk section attachments — drag N files, auto-match by filename */}
            <div className="border border-dashed border-brand-navy/30 bg-brand-pale/30 p-4">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div>
                  <div className="pmc-label">{t("panels.tender_builder.bulk_title")}</div>
                  <div className="text-xs text-brand-navy/60 mt-1">
                    {t("panels.tender_builder.bulk_hint")}
                  </div>
                </div>
                <label className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white cursor-pointer">
                  {bulkBusy ? t("panels.tender_builder.uploading") : t("panels.tender_builder.choose_files")}
                  <input type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx"
                         onChange={(e) => { const fs = e.target.files; if (fs?.length) bulkUpload(fs); e.target.value = ""; }}
                         disabled={bulkBusy}
                         data-testid="tb-bulk-upload"
                         className="hidden" />
                </label>
              </div>
              {bulkReport && (
                <ul className="mt-3 text-xs space-y-1" data-testid="tb-bulk-report">
                  {bulkReport.map((r, i) => (
                    <li key={i} className={r.matched ? "text-emerald-800" : "text-red-600"}>
                      {r.matched
                        ? `✓ ${r.file_name} → ${r.section_code} · ${r.section_title}`
                        : `✕ ${r.file_name} — ${r.reason === "too_large" ? "too large" : "no matching section"}`}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Sections */}
            <div className="space-y-4">
              {orderedSections.map((s, i) => (
                <TenderSectionCard
                  key={`${s.code}-${i}`}
                  section={s} idx={i}
                  patchSection={patchSection}
                  move={move}
                  removeSection={removeSection}
                  aiBusyCode={aiBusyCode}
                  runAiDraft={runAiDraft}
                  uploadSectionAttachment={uploadSectionAttachment}
                  removeSectionAttachment={removeSectionAttachment}
                  saveSection={saveSection}
                  sectionSaving={sectionSaving}
                />
              ))}
            </div>

            {/* Add row */}
            <div className="border border-dashed border-brand-navy/30 bg-white p-4 flex flex-wrap gap-2 justify-center">
              <span className="text-sm text-brand-navy/60 mr-2 self-center">{t("panels.tender_builder.add_new")}</span>
              {["section", "annexure", "form"].map((k) => (
                <button key={k} onClick={() => addBlank(k)}
                  data-testid={`tb-add-${k}`}
                  className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
                  + {KIND_LABEL[k]}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
      <AiDiffModal
        open={!!diffState}
        sectionTitle={diffState?.title || ""}
        oldBody={diffState?.oldBody || ""}
        newBody={diffState?.newBody || ""}
        onAccept={acceptAiDraft}
        onReject={rejectAiDraft}
      />
      {showHistory && doc?.id && (
        <VersionHistory
          templateId={doc.id}
          onClose={() => setShowHistory(false)}
          onRestored={(d) => { setDoc(d); setShowHistory(false); toast.info("Restored older snapshot"); }}
        />
      )}
      <DprGenerateModal
        open={showDpr}
        onClose={() => setShowDpr(false)}
        kind={kind === "all" ? "tender" : kind}
        masters={masters}
        onCloned={async (created) => { await load(); await openTemplate(created.id); }}
      />
    </div>
  );
}
