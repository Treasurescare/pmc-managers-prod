const DOT = { done: "bg-emerald-600 border-emerald-600", skipped: "bg-brand-navy/20 border-brand-navy/20", current: "bg-brand-gold border-brand-gold animate-pulse", todo: "bg-white border-brand-navy/25" };
const TXT = { done: "text-emerald-800", skipped: "text-brand-navy/40 line-through", current: "text-brand-navy font-semibold", todo: "text-brand-navy/40" };

export const TenderTracker = ({ refKey, t }) => {
  if (!t) return null;
  return (
    <div className="mt-2 flex items-start gap-0 overflow-x-auto pb-1" data-testid={`tracker-${refKey}`}>
      {t.stages.map((s, i) => (
        <div key={s.key} className="flex items-start shrink-0" title={s.detail} data-testid={`tracker-${refKey}-${s.key}`} data-state={s.state}>
          <div className="flex flex-col items-center w-[74px]">
            <span className={`w-3 h-3 rounded-full border-2 transition-colors ${DOT[s.state]}`} />
            <span className={`mt-1 text-[10px] text-center leading-tight ${TXT[s.state]}`}>{s.label}</span>
            {s.state === "current" && <span className="text-[9px] text-brand-navy/60 text-center leading-tight" data-testid={`tracker-${refKey}-detail`}>{s.detail}</span>}
          </div>
          {i < t.stages.length - 1 && <span className={`mt-[5px] h-0.5 w-5 -mx-3 ${["done", "skipped"].includes(s.state) ? "bg-emerald-600" : "bg-brand-navy/15"}`} />}
        </div>))}
    </div>);
};
