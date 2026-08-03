import { diffWordsWithSpace } from "diff";
import { useMemo } from "react";
import DOMPurify from "dompurify";

/**
 * AiDiffModal — shown when the admin re-runs AI on a section that already has
 * a body. Displays a word-level red/green diff (removed | added) so they can
 * accept or reject before the RichEditor is overwritten.
 *
 * Strategy: strip tags for readability (diffs on visible text), but persist
 * the sanitised HTML from the AI output on Accept.
 */
const SANITIZE_CFG = {
  ALLOWED_TAGS: ["p", "br", "b", "strong", "i", "em", "u", "h2", "h3",
                 "ul", "ol", "li", "blockquote", "code", "pre", "span", "div"],
  ALLOWED_ATTR: [],
};

function stripHtml(html) {
  if (!html) return "";
  const d = document.createElement("div");
  d.innerHTML = DOMPurify.sanitize(html, SANITIZE_CFG);
  return (d.innerText || "").replace(/\s+\n/g, "\n").trim();
}

export default function AiDiffModal({ open, sectionTitle, oldBody, newBody, onAccept, onReject }) {
  const parts = useMemo(() => {
    if (!open) return [];
    return diffWordsWithSpace(stripHtml(oldBody), stripHtml(newBody));
  }, [open, oldBody, newBody]);

  if (!open) return null;

  const stats = parts.reduce((acc, p) => {
    if (p.added) acc.added += p.value.trim().split(/\s+/).filter(Boolean).length;
    else if (p.removed) acc.removed += p.value.trim().split(/\s+/).filter(Boolean).length;
    return acc;
  }, { added: 0, removed: 0 });

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-6"
         data-testid="ai-diff-modal"
         onClick={(e) => { if (e.target === e.currentTarget) onReject(); }}>
      <div className="bg-white border border-brand-navy/10 w-full max-w-4xl max-h-[85vh] flex flex-col">
        <header className="border-b border-brand-navy/10 px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">AI redraft preview</div>
            <h3 className="font-display text-xl text-brand-navy">{sectionTitle}</h3>
          </div>
          <div className="text-xs text-brand-navy/60 tabular-nums">
            <span className="text-emerald-700">+{stats.added}</span>
            <span className="mx-2">·</span>
            <span className="text-red-600">−{stats.removed}</span>
            <span className="ml-1">words</span>
          </div>
        </header>
        <div className="overflow-auto p-6 flex-1 leading-relaxed text-sm text-brand-navy"
             data-testid="ai-diff-body">
          {parts.length === 0 && (
            <div className="text-brand-navy/50 italic">The AI draft is identical to the current body.</div>
          )}
          {parts.map((p, i) => {
            if (p.added) return <span key={i} className="bg-emerald-100 text-emerald-900" data-diff="add">{p.value}</span>;
            if (p.removed) return <span key={i} className="bg-red-100 text-red-800 line-through" data-diff="rem">{p.value}</span>;
            return <span key={i} className="text-brand-navy/80">{p.value}</span>;
          })}
        </div>
        <footer className="border-t border-brand-navy/10 px-6 py-4 flex justify-end gap-3">
          <button type="button" onClick={onReject}
                  data-testid="ai-diff-reject"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-pale">
            Keep current
          </button>
          <button type="button" onClick={onAccept}
                  data-testid="ai-diff-accept"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest bg-purple-600 text-white hover:bg-purple-700">
            Replace with AI draft
          </button>
        </footer>
      </div>
    </div>
  );
}
