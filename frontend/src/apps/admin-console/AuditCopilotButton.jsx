import { useEffect, useState } from "react";
import { toast } from "sonner";
import { bidApi, analyticsApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

/**
 * AI Audit Copilot — floats in the Admin header. Opens a modal listing
 * pipeline-visible bids (post-EMD). Admin picks one and the copilot runs an
 * LLM-assisted review of the workflow_history and returns a verdict + flags.
 */
export default function AuditCopilotButton() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [bids, setBids] = useState([]);
  const [selected, setSelected] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!open) return;
    bidApi.list({})
      .then((rows) =>
        setBids(rows.filter((b) => !["emd_pending", "submitted"].includes(b.status))))
      .catch((e) => toast.error(formatApiError(e)));
  }, [open]);

  const run = async () => {
    if (!selected) return toast.error("Pick a bid first");
    setRunning(true); setResult(null);
    try {
      const r = await analyticsApi.auditCopilot(selected);
      setResult(r);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setRunning(false); }
  };

  const close = () => { setOpen(false); setResult(null); setSelected(""); };

  const verdictColor = (v) => v === "ok"
    ? "bg-emerald-100 text-emerald-800"
    : v === "review" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-800";

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} data-testid="admin-copilot-open"
        className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
        {t("admin.header_copilot")}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
             data-testid="copilot-modal" onClick={close}>
          <div className="bg-white max-w-2xl w-full p-6 rounded-lg space-y-4"
               onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between">
              <div>
                <div className="pmc-label">AI Audit Copilot</div>
                <h3 className="font-serif text-xl mt-1">Review a bid decision</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Runs deterministic checks (KYC coverage, escrow timing) plus an LLM narrative.
                </p>
              </div>
              <button onClick={close} className="text-slate-400 hover:text-slate-600 text-2xl leading-none"
                      data-testid="copilot-close" aria-label="Close">×</button>
            </div>

            <label className="block text-sm">
              <span className="pmc-label">Bid</span>
              <select value={selected} onChange={(e) => setSelected(e.target.value)}
                      data-testid="copilot-bid-select"
                      className="mt-1 w-full px-3 py-2 border border-brand-navy/20 rounded text-sm">
                <option value="">Select a bid…</option>
                {bids.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.bid_ref} · {b.company_name || b.vendor_email} · {b.status}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex gap-2 justify-end">
              <button onClick={run} disabled={running || !selected}
                      data-testid="copilot-run"
                      className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
                {running ? "Analysing…" : "Run copilot"}
              </button>
            </div>

            {result && (
              <div className="border-t pt-4 space-y-3" data-testid="copilot-result">
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 text-xs font-semibold uppercase rounded ${verdictColor(result.verdict)}`}
                        data-testid="copilot-verdict">
                    {result.verdict}
                  </span>
                  <span className="text-xs text-slate-500">
                    {result.history_length} history entries · generated {new Date(result.generated_at).toLocaleTimeString()}
                  </span>
                </div>
                {(result.flags?.length || 0) > 0 ? (
                  <ul className="text-sm space-y-1 list-disc pl-5" data-testid="copilot-flags">
                    {result.flags.map((f, i) => (
                      <li key={`flag-${f}-${i}`} className="text-amber-800">{f}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-sm text-emerald-700">No deterministic flags raised.</div>
                )}
                {result.narrative && (
                  <div className="bg-slate-50 border-l-4 border-brand-navy/40 p-3 text-sm text-slate-700 whitespace-pre-line"
                       data-testid="copilot-narrative">
                    {result.narrative}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
