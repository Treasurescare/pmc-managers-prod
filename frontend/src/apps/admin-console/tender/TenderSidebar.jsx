/**
 * Left column of the Tender Builder — kind picker + master library + user drafts.
 * Split out from TenderBuilderPanel.jsx for maintainability.
 */
export default function TenderSidebar({
  t, kind, setKind,
  masters, drafts, busy,
  selectedId, cloneMaster, openTemplate,
}) {
  return (
    <aside className="space-y-4">
      <div className="border border-brand-navy/10 bg-white">
        <div className="pmc-label p-3 border-b border-brand-navy/10">
          {t("panels.tender_builder.kind")}
        </div>
        <div className="p-3 flex gap-2 flex-wrap">
          {["tender", "rfp", "rfq"].map((k) => (
            <button
              key={k}
              onClick={() => setKind(k)}
              data-testid={`tb-kind-${k}`}
              className={
                "px-3 py-1.5 text-[11px] uppercase tracking-widest border " +
                (kind === k
                  ? "bg-brand-navy text-white border-brand-navy"
                  : "border-brand-navy/20 text-brand-navy")
              }
            >
              {k.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="border border-brand-navy/10 bg-white">
        <div className="pmc-label p-3 border-b border-brand-navy/10 flex justify-between items-center">
          <span>{t("panels.tender_builder.master_lib")}</span>
          <span className="text-brand-navy/40 normal-case tracking-normal">
            {masters.length}
          </span>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {masters.map((m) => (
            <div
              key={m.id}
              className="border-b border-brand-navy/10 p-3"
              data-testid={`tb-master-${m.id}`}
            >
              <div className="text-sm font-semibold text-brand-navy leading-tight">
                {m.name}
              </div>
              <div className="text-xs text-brand-navy/50 mt-1">
                {(m.sections || []).length} sections · {m.industry || "—"}
              </div>
              <button
                onClick={() => cloneMaster(m)}
                disabled={busy}
                data-testid={`tb-clone-${m.id}`}
                className="mt-2 w-full px-3 py-1.5 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40"
              >
                {t("panels.tender_builder.clone_as_draft")}
              </button>
            </div>
          ))}
          {masters.length === 0 && (
            <div className="p-6 text-sm text-brand-navy/50">
              {t("panels.tender_builder.no_masters")}
            </div>
          )}
        </div>
      </div>

      <div className="border border-brand-navy/10 bg-white">
        <div className="pmc-label p-3 border-b border-brand-navy/10 flex justify-between items-center">
          <span>{t("panels.tender_builder.your_drafts")}</span>
          <span className="text-brand-navy/40 normal-case tracking-normal">
            {drafts.length}
          </span>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {drafts.map((d) => (
            <button
              key={d.id}
              onClick={() => openTemplate(d.id)}
              data-testid={`tb-draft-${d.id}`}
              className={
                "w-full text-left border-b border-brand-navy/10 p-3 hover:bg-brand-navy/5 " +
                (selectedId === d.id ? "bg-brand-navy/10" : "")
              }
            >
              <div className="text-sm font-semibold text-brand-navy leading-tight truncate">
                {d.name}
              </div>
              <div className="text-xs text-brand-navy/50 mt-1">
                {(d.sections || []).length} sections · {d.kind?.toUpperCase()}
              </div>
            </button>
          ))}
          {drafts.length === 0 && (
            <div className="p-6 text-sm text-brand-navy/50">
              {t("panels.tender_builder.no_drafts")}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
