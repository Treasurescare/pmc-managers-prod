import AiDraftMenu from "./AiDraftMenu";
import RichEditor from "./RichEditor";

const KIND_LABEL = { section: "Section", annexure: "Annexure", form: "Form" };
const KIND_TONE = {
  section: "bg-brand-navy/5 border-brand-navy/20 text-brand-navy",
  annexure: "bg-amber-50 border-amber-200 text-amber-900",
  form: "bg-emerald-50 border-emerald-200 text-emerald-900",
};

/**
 * One section card in the Tender Builder — header row + body editor + attachment.
 * Split out from TenderBuilderPanel.jsx for maintainability.
 */
export default function TenderSectionCard({
  section: s, idx: i,
  patchSection, move, removeSection,
  aiBusyCode, runAiDraft,
  uploadSectionAttachment, removeSectionAttachment,
}) {
  const backendUrl = process.env.REACT_APP_BACKEND_URL;
  return (
    <article
      className={`border p-5 ${KIND_TONE[s.kind] || KIND_TONE.section}`}
      data-testid={`tb-section-${s.code}`}
    >
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <div className="text-[10px] uppercase tracking-widest opacity-60">
            {KIND_LABEL[s.kind] || s.kind}
          </div>
          <input
            value={s.title}
            onChange={(e) => patchSection(i, { title: e.target.value })}
            data-testid={`tb-section-title-${s.code}`}
            className="mt-1 w-full px-3 py-2 border border-current/20 bg-white text-brand-navy font-serif text-lg"
          />
        </div>
        <div className="flex gap-1 items-start">
          <AiDraftMenu
            code={s.code}
            busy={aiBusyCode === s.code}
            onDraft={(opts) => runAiDraft(i, opts)}
          />
          <button
            onClick={() => move(i, -1)}
            data-testid={`tb-up-${s.code}`}
            className="px-2 py-1 text-xs border border-current/30 bg-white hover:bg-brand-pale"
          >
            ↑
          </button>
          <button
            onClick={() => move(i, +1)}
            data-testid={`tb-down-${s.code}`}
            className="px-2 py-1 text-xs border border-current/30 bg-white hover:bg-brand-pale"
          >
            ↓
          </button>
          <button
            onClick={() => removeSection(i)}
            data-testid={`tb-del-${s.code}`}
            className="px-2 py-1 text-xs border border-red-500 text-red-600 bg-white hover:bg-red-50"
          >
            ×
          </button>
        </div>
      </div>

      {s.hint && (
        <div className="mt-2 text-xs opacity-70 italic">{s.hint}</div>
      )}

      <RichEditor
        value={s.body || ""}
        onChange={(v) => patchSection(i, { body: v })}
        testid={`tb-section-body-${s.code}`}
        placeholder={
          s.hint ||
          `Write the ${KIND_LABEL[s.kind]?.toLowerCase() || "section"} content here…`
        }
      />

      <div className="mt-3 border-t border-current/10 pt-3 flex items-center gap-3 flex-wrap">
        <span className="text-[10px] uppercase tracking-widest opacity-60">
          Template attachment
        </span>
        {s.attachment ? (
          <a
            href={`${backendUrl}${s.attachment.url}`}
            target="_blank"
            rel="noreferrer"
            download={s.attachment.file_name}
            data-testid={`tb-attach-dl-${s.code}`}
            className="text-xs underline text-brand-navy"
          >
            📎 {s.attachment.file_name} (
            {Math.round((s.attachment.size_bytes || 0) / 1024)} KB)
          </a>
        ) : (
          <span className="text-xs opacity-60">No attachment</span>
        )}
        <label className="text-xs cursor-pointer px-2 py-1 border border-current/30 bg-white hover:bg-brand-pale">
          {s.attachment ? "Replace" : "Upload"}
          <input
            type="file"
            accept=".pdf,.doc,.docx,.xls,.xlsx"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) uploadSectionAttachment(i, f);
              e.target.value = "";
            }}
            data-testid={`tb-attach-up-${s.code}`}
            className="hidden"
          />
        </label>
        {s.attachment && (
          <button
            type="button"
            onClick={() => removeSectionAttachment(i)}
            data-testid={`tb-attach-rm-${s.code}`}
            className="text-xs text-red-600 hover:underline"
          >
            Remove
          </button>
        )}
      </div>

      <div className="mt-2 text-[11px] opacity-60">
        Code: <code className="font-mono">{s.code}</code>
        {(s.body || "").length > 0 && (
          <span className="ml-3">{(s.body || "").length} chars</span>
        )}
      </div>
    </article>
  );
}
