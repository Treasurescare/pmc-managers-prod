import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { tenderTemplateApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TenderHeaderForm from "./tender/TenderHeaderForm";
import AiDiffModal from "./tender/AiDiffModal";
import VersionHistory from "./tender/VersionHistory";
import TenderSidebar from "./tender/TenderSidebar";
import TenderSectionCard from "./tender/TenderSectionCard";
import { exportTenderPdf } from "./tender/tenderPdf";

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

  const load = useCallback(async () => {
    try { setList(await tenderTemplateApi.list()); }
    catch (e) { toast.error(formatApiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openTemplate = async (id) => {
    setSelectedId(id);
    setDirty(false);
    try { setDoc(await tenderTemplateApi.get(id)); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const cloneMaster = async (master) => {
    setBusy(true);
    try {
      const payload = {
        name: `${master.name} — draft ${new Date().toISOString().slice(0, 10)}`,
        kind, industry: master.industry,
        header: { ...(master.header || {}) },
        sections: (master.sections || []).map((s) => ({ ...s })),
      };
      const created = await tenderTemplateApi.create(payload);
      toast.success("Draft created");
      await load();
      await openTemplate(created.id);
    } catch (e) { toast.error(formatApiError(e)); }
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
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const removeSectionAttachment = async (idx) => {
    if (!doc?.id) return;
    if (!confirm("Remove this attachment?")) return;
    try {
      const updated = await tenderTemplateApi.removeSectionAttachment(doc.id, doc.sections[idx].code);
      setDoc(updated);
    } catch (e) { toast.error(formatApiError(e)); }
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
    } catch (e) { toast.error(formatApiError(e)); }
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
    } catch (e) { toast.error(formatApiError(e)); }
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
    } catch (e) { toast.error(formatApiError(e)); }
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
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const masters = list.filter((x) => x.is_master);
  const drafts = list.filter((x) => !x.is_master);
  const orderedSections = useMemo(
    () => [...(doc?.sections || [])].sort((a, b) => (a.order || 0) - (b.order || 0)),
    [doc?.sections],
  );

  return (
    <div data-testid="tender-builder-panel" className="grid gap-6 lg:grid-cols-[300px_1fr]">
      <TenderSidebar
        t={t}
        kind={kind} setKind={setKind}
        masters={masters} drafts={drafts} busy={busy}
        selectedId={selectedId}
        cloneMaster={cloneMaster} openTemplate={openTemplate}
      />

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
                  <div className="pmc-label">{t("panels.tender_builder.tender_name")}</div>
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
                  </button>
                  <button onClick={() => setShowHistory(true)} disabled={!doc?.id}
                    data-testid="tb-history"
                    title="View and restore rolling snapshots of this tender"
                    className="px-3 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/10">
                    ⟲ {t("panels.tender_builder.history")}{typeof doc?.version === "number" ? ` · v${doc.version}` : ""}
                  </button>
                  <button onClick={() => exportTenderPdf(doc)} disabled={!doc}
                    data-testid="tb-export-pdf"
                    title="Opens the browser print dialog — pick 'Save as PDF'"
                    className="px-4 py-2 text-[12px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
                    {t("panels.tender_builder.print_pdf")}
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
    </div>
  );
}
