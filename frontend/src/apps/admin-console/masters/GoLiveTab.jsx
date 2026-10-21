import { useEffect, useState } from "react";
import { toast } from "sonner";
import { settingsApi, showApiError } from "@/lib/api";

// v56s — admin Go-Live switch. OFF by default. ON makes Sector + Contract type
// mandatory on NEW notices and NEW vendor registration submissions only.
export default function GoLiveTab() {
  const [enabled, setEnabled] = useState(null);
  const [meta, setMeta] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    settingsApi.getGoLive()
      .then((d) => { setEnabled(!!d.go_live); setMeta(d); })
      .catch((e) => { showApiError(e); setEnabled(false); });
  }, []);

  const toggle = async (next) => {
    setBusy(true);
    try {
      const d = await settingsApi.setGoLive(next);
      setEnabled(!!d.go_live);
      setMeta((m) => ({ ...m, updated_at: new Date().toISOString() }));
      toast.success(next
        ? "Go-live ENABLED — Sector & Contract type now required on new notices and registrations"
        : "Go-live disabled — Sector & Contract type are optional again");
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  return (
    <div className="max-w-2xl" data-testid="go-live-tab">
      <div className="pmc-label">Portal go-live</div>
      <h3 className="font-serif text-2xl text-brand-navy mt-1 mb-2">Mandatory taxonomy switch</h3>
      <p className="text-sm text-brand-navy/70 mb-5">
        While OFF, Sector and Contract type are optional everywhere. When you switch it ON,
        the server requires a Sector and Contract type on every <strong>new</strong> notice and
        every <strong>new</strong> vendor registration submission. Existing vendors and notices
        are never changed.
      </p>
      <div className="flex items-center gap-4 border border-brand-navy/15 bg-white p-5">
        <span className={"text-xs uppercase tracking-widest px-3 py-1 font-semibold " +
          (enabled ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                   : "bg-slate-100 text-slate-600 border border-slate-300")}
          data-testid="go-live-status">
          {enabled === null ? "…" : enabled ? "Go-live ON" : "Go-live OFF"}
        </span>
        <button type="button" disabled={busy || enabled === null}
          onClick={() => toggle(!enabled)}
          data-testid="go-live-toggle"
          className={"px-5 py-2 text-[11px] uppercase tracking-widest text-white disabled:opacity-50 " +
            (enabled ? "bg-red-700 hover:bg-red-800" : "bg-brand-navy hover:bg-brand-navy-deep")}>
          {busy ? "Saving…" : enabled ? "Turn go-live OFF" : "Turn go-live ON"}
        </button>
      </div>
      {meta.updated_at && (
        <div className="text-[11px] text-brand-navy/50 mt-2" data-testid="go-live-meta">
          Last changed {String(meta.updated_at).slice(0, 19).replace("T", " ")} by {meta.updated_by || "—"}
        </div>
      )}
    </div>
  );
}
