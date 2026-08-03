import { useEffect, useRef, useState } from "react";

/**
 * AiDraftMenu — small popover attached to the section ✨ button.
 * Lets the admin pick tone (formal / plain / strict) × length (short / medium
 * / long) before firing the LLM call. Escapes on outside click / Esc.
 */
const TONES = [
  { id: "formal", label: "Formal", hint: "CPPP / GFR 2017 style" },
  { id: "plain",  label: "Plain",  hint: "Readable, SME-friendly" },
  { id: "strict", label: "Strict", hint: "Contractual, unambiguous" },
];
const LENGTHS = [
  { id: "short",  label: "Short",  hint: "~120 words" },
  { id: "medium", label: "Medium", hint: "~240 words" },
  { id: "long",   label: "Long",   hint: "~420 words" },
];

export default function AiDraftMenu({ code, disabled, busy, onDraft }) {
  const [open, setOpen] = useState(false);
  const [tone, setTone] = useState("formal");
  const [length, setLength] = useState("medium");
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onEsc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button type="button"
        onClick={() => !disabled && setOpen((v) => !v)}
        disabled={disabled || busy}
        data-testid={`tb-ai-draft-${code}`}
        title="Draft this section body with AI"
        className="px-2 py-1 text-xs border border-purple-500 text-purple-700 bg-white hover:bg-purple-50 disabled:opacity-40">
        {busy ? "…" : "✨ AI"}
      </button>
      {open && (
        <div className="absolute right-0 mt-1 z-30 w-64 bg-white border border-purple-200 shadow-xl p-3 text-xs"
             data-testid={`tb-ai-menu-${code}`}>
          <div className="pmc-label mb-1">Tone</div>
          <div className="grid grid-cols-3 gap-1 mb-3">
            {TONES.map((o) => (
              <button key={o.id} type="button" onClick={() => setTone(o.id)}
                data-testid={`tb-ai-tone-${o.id}-${code}`}
                title={o.hint}
                className={`px-2 py-1.5 border text-[11px] ${tone === o.id
                  ? "bg-purple-600 text-white border-purple-600"
                  : "bg-white text-brand-navy border-brand-navy/20 hover:bg-brand-pale"}`}>
                {o.label}
              </button>
            ))}
          </div>
          <div className="pmc-label mb-1">Length</div>
          <div className="grid grid-cols-3 gap-1 mb-3">
            {LENGTHS.map((o) => (
              <button key={o.id} type="button" onClick={() => setLength(o.id)}
                data-testid={`tb-ai-length-${o.id}-${code}`}
                title={o.hint}
                className={`px-2 py-1.5 border text-[11px] ${length === o.id
                  ? "bg-purple-600 text-white border-purple-600"
                  : "bg-white text-brand-navy border-brand-navy/20 hover:bg-brand-pale"}`}>
                {o.label}
              </button>
            ))}
          </div>
          <button type="button"
            onClick={() => { setOpen(false); onDraft({ tone, length }); }}
            data-testid={`tb-ai-go-${code}`}
            className="w-full bg-purple-600 text-white text-[11px] uppercase tracking-widest py-2 hover:bg-purple-700">
            Draft with AI
          </button>
        </div>
      )}
    </div>
  );
}
