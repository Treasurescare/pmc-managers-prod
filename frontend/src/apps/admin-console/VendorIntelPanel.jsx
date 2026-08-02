import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { vendorIntelApi, formatApiError } from "@/lib/api";

const BANDS = ["excellent", "good", "fair", "poor", "blacklisted"];

export default function VendorIntelPanel() {
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rating, setRating] = useState({ score: 70, band: "good" });
  const [blacklistReason, setBlacklistReason] = useState("");

  const load = useCallback(async () => {
    try { setRows(await vendorIntelApi.summary()); }
    catch (e) { toast.error(formatApiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const saveRating = async (v) => {
    try {
      await vendorIntelApi.rate({ vendor_ref: v.vendor_ref, ...rating });
      toast.success("Rating saved");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const blacklist = async (v) => {
    if (!blacklistReason) return toast.error("Reason required");
    try {
      await vendorIntelApi.blacklist({ vendor_ref: v.vendor_ref, reason: blacklistReason });
      toast.success("Blacklisted");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const unblacklist = async (v) => {
    try { await vendorIntelApi.unblacklist(v.vendor_ref); toast.success("Removed"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="admin-vendor-intel-panel" className="bg-white border">
      <table className="w-full text-sm">
        <thead className="text-xs text-brand-navy/60 border-b">
          <tr><th className="text-left px-3 py-2">Vendor</th>
            <th className="text-left px-3 py-2">Ref</th>
            <th className="px-3 py-2">Rating</th>
            <th className="px-3 py-2">Band</th>
            <th className="px-3 py-2">Flags</th>
            <th className="px-3 py-2">Actions</th></tr>
        </thead>
        <tbody>
          {rows.map((v) => (
            <tr key={v.id} className="border-t" data-testid={`vintel-row-${v.vendor_ref}`}>
              <td className="px-3 py-2">{v.company_name || v.email}</td>
              <td className="px-3 py-2 font-mono text-xs">{v.vendor_ref}</td>
              <td className="px-3 py-2 text-center">{v.rating ?? "—"}</td>
              <td className="px-3 py-2 text-center">{v.band ?? "—"}</td>
              <td className="px-3 py-2 text-center">
                {v.blacklisted && <span className="text-red-600 text-xs mr-1">BL</span>}
                {v.watchlisted && <span className="text-amber-600 text-xs">WL</span>}
              </td>
              <td className="px-3 py-2">
                <button onClick={() => setSelected(v)} data-testid={`vintel-select-${v.vendor_ref}`}
                  className="text-xs border px-2 py-1">Manage</button>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (<tr><td colSpan={6} className="p-6 text-center text-slate-500">No vendors yet.</td></tr>)}
        </tbody>
      </table>

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full space-y-3" data-testid="vintel-modal">
            <div className="text-lg font-serif">{selected.company_name}</div>
            <div className="text-xs text-slate-500">{selected.vendor_ref}</div>
            <label className="block text-sm">
              <span>Score (0-100)</span>
              <input type="number" min="0" max="100" value={rating.score}
                onChange={(e) => setRating({ ...rating, score: Number(e.target.value) })}
                className="mt-1 w-full border px-3 py-2" data-testid="vintel-score" />
            </label>
            <label className="block text-sm">
              <span>Band</span>
              <select value={rating.band} onChange={(e) => setRating({ ...rating, band: e.target.value })}
                className="mt-1 w-full border px-3 py-2" data-testid="vintel-band">
                {BANDS.map((b) => <option key={b}>{b}</option>)}
              </select>
            </label>
            <button onClick={() => saveRating(selected)} data-testid="vintel-save-rating"
              className="w-full bg-slate-900 text-white py-2 text-sm">Save rating</button>
            <div className="border-t pt-3">
              <label className="block text-sm">
                <span>Blacklist reason</span>
                <input value={blacklistReason} onChange={(e) => setBlacklistReason(e.target.value)}
                  className="mt-1 w-full border px-3 py-2" data-testid="vintel-bl-reason" />
              </label>
              <div className="flex gap-2 mt-2">
                {!selected.blacklisted ? (
                  <button onClick={() => blacklist(selected)} data-testid="vintel-blacklist"
                    className="flex-1 bg-red-600 text-white py-2 text-sm">Blacklist</button>
                ) : (
                  <button onClick={() => unblacklist(selected)} data-testid="vintel-unblacklist"
                    className="flex-1 bg-slate-200 text-slate-900 py-2 text-sm">Remove from blacklist</button>
                )}
              </div>
            </div>
            <button onClick={() => setSelected(null)} className="text-xs text-slate-500 hover:underline">
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
