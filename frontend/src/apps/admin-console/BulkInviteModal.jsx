import { useState } from "react";
import { toast } from "sonner";
import { vendorInviteApi, formatApiError } from "@/lib/api";

/**
 * BulkInviteModal — CSV-driven bulk vendor invite.
 * Admin pastes CSV text with a header row (email, company_name, country, contact_name)
 * and gets a per-row result table back from the backend.
 */
export default function BulkInviteModal({ open, onClose, onDone }) {
  const [csvText, setCsvText] = useState(
    "email,company_name,country,contact_name\n"
  );
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);

  if (!open) return null;

  const submit = async () => {
    if (csvText.split("\n").filter((l) => l.trim() && !l.toLowerCase().startsWith("email,")).length === 0) {
      return toast.error("Add at least one row after the header");
    }
    setRunning(true); setResults(null);
    try {
      const r = await vendorInviteApi.inviteBulk(csvText);
      setResults(r || { invited: 0, skipped: 0, total: 0, results: [] });
      toast.success(`Invited ${r?.invited ?? 0} · Skipped ${r?.skipped ?? 0}`);
      if ((r?.invited ?? 0) > 0 && onDone) onDone();
    } catch (e) {
      // Bug #28/52 — never let this handler throw uncaught; blank-screen bug.
      // Show a friendly toast and preserve the modal state so admin can retry.
      toast.error(formatApiError(e));
      setResults({ invited: 0, skipped: 0, total: 0, results: [],
                   error: e?.response?.data?.detail || e?.message || "Unknown error" });
    }
    finally { setRunning(false); }
  };

  const close = () => {
    setResults(null);
    setCsvText("email,company_name,country,contact_name\n");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
         data-testid="bulk-invite-modal" onClick={close}>
      <div className="bg-white max-w-3xl w-full p-6 rounded-lg space-y-4 max-h-[90vh] overflow-auto"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <div>
            <div className="pmc-label">Bulk vendor invite</div>
            <h3 className="font-serif text-xl mt-1">Paste CSV rows</h3>
            <p className="text-xs text-slate-500 mt-1">
              First row must be the header. `email` is required. Optional: `company_name`, `country`, `contact_name`.
            </p>
          </div>
          <button onClick={close} className="text-slate-400 hover:text-slate-600 text-2xl leading-none"
                  data-testid="bulk-invite-close" aria-label="Close">×</button>
        </div>
        <textarea
          value={csvText} onChange={(e) => setCsvText(e.target.value)} rows={10}
          data-testid="bulk-invite-csv"
          className="w-full px-3 py-2 border border-brand-navy/20 font-mono text-xs"
          placeholder="email,company_name,country,contact_name&#10;acme@example.com,Acme Ltd,KZ,Jane Doe&#10;beta@example.com,Beta Corp,US,John Smith"
        />

        {results && (
          <div className="border border-brand-navy/10 max-h-64 overflow-auto"
               data-testid="bulk-invite-results">
            <div className="p-3 bg-brand-navy/5 text-sm font-semibold">
              {results.invited} invited · {results.skipped} skipped · {results.total} total
            </div>
            <table className="w-full text-xs">
              <thead className="bg-slate-50">
                <tr className="text-left">
                  <th className="px-3 py-1">Row</th>
                  <th className="px-3 py-1">Email</th>
                  <th className="px-3 py-1">Status</th>
                  <th className="px-3 py-1">Vendor ref / reason</th>
                </tr>
              </thead>
              <tbody>
                {results.results.map((r) => (
                  <tr key={`row-${r.row}-${r.email}`}
                      className="border-t border-brand-navy/10"
                      data-testid={`bulk-invite-row-${r.row}`}>
                    <td className="px-3 py-1 font-mono">{r.row}</td>
                    <td className="px-3 py-1">{r.email}</td>
                    <td className={"px-3 py-1 font-semibold " + (r.status === "invited" ? "text-emerald-700" : "text-amber-700")}>
                      {r.status}
                    </td>
                    <td className="px-3 py-1 text-brand-navy/60 font-mono">{r.vendor_ref || r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button onClick={close}
                  className="px-4 py-2 text-sm border rounded">Close</button>
          <button onClick={submit} disabled={running}
                  data-testid="bulk-invite-submit"
                  className="px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
            {running ? "Sending…" : "Invite all"}
          </button>
        </div>
      </div>
    </div>
  );
}
