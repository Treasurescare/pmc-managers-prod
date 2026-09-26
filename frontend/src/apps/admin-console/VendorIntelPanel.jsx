import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { vendorIntelApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import ReviewModerationSection, { AdminBadgePreview } from "@/apps/admin-console/vendor/ReviewModerationSection";
import { useListPager } from "@/components/ListPager";

const BANDS = ["excellent", "good", "fair", "poor", "blacklisted"];

export default function VendorIntelPanel() {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rating, setRating] = useState({ score: 70, band: "good" });
  const [blacklistReason, setBlacklistReason] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    try { setRows(await vendorIntelApi.summary()); }
    catch (e) { showApiError(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const q = search.trim().toLowerCase();
  const filtered = q
    ? rows.filter((v) => (v.company_name || "").toLowerCase().includes(q)
        || (v.email || "").toLowerCase().includes(q)
        || (v.vendor_ref || "").toLowerCase().includes(q))
    : rows;
  const { paged, controls } = useListPager(filtered, { testid: "vintel-pager" });

  const saveRating = async (v) => {
    try {
      await vendorIntelApi.rate({ vendor_ref: v.vendor_ref, ...rating });
      toast.success(t("panels.vendor_intel.rating_saved"));
      load();
    } catch (e) { showApiError(e); }
  };
  const blacklist = async (v) => {
    if (!blacklistReason) return toast.error(t("panels.vendor_intel.reason_required"));
    try {
      await vendorIntelApi.blacklist({ vendor_ref: v.vendor_ref, reason: blacklistReason });
      toast.success(t("panels.vendor_intel.blacklisted_toast"));
      load();
    } catch (e) { showApiError(e); }
  };
  const unblacklist = async (v) => {
    try { await vendorIntelApi.unblacklist(v.vendor_ref); toast.success(t("panels.vendor_intel.removed_toast")); load(); }
    catch (e) { showApiError(e); }
  };

  return (
    <div data-testid="admin-vendor-intel-panel" className="bg-white border">
      <div className="px-3 py-2 border-b bg-brand-pale text-[11px] text-brand-navy/70 flex flex-wrap gap-x-4 gap-y-1">
        <span className="pmc-label">Flag legend</span>
        <span><span className="text-red-600 font-bold">BL</span> = Blacklisted</span>
        <span><span className="text-amber-600 font-bold">WL</span> = Watch-list (elevated scrutiny)</span>
        <span className="text-brand-navy/50">· Anonymised entries appear as "—"</span>
      </div>
      {/* Bug #84 — horizontal scroll wrapper so long vendor rows don't blow
          out the mobile viewport (was overflowing on iPhone SE / narrow
          Android). min-w-[640px] keeps columns readable while allowing swipe. */}
      <div className="px-3 py-2 border-b">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by company or vendor reference…"
          data-testid="vintel-search"
          className="w-full px-3 py-2 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white text-sm"
        />
      </div>
      <div className="w-full overflow-x-auto">
      <table className="w-full text-sm min-w-[640px]">
        <thead className="text-xs text-brand-navy/60 border-b">
          <tr><th className="text-left px-3 py-2">{t("panels.vendor_intel.col_vendor")}</th>
            <th className="text-left px-3 py-2">{t("panels.vendor_intel.col_ref")}</th>
            <th className="px-3 py-2">{t("panels.vendor_intel.col_rating")}</th>
            <th className="px-3 py-2">{t("panels.vendor_intel.col_band")}</th>
            <th className="px-3 py-2">Trust badge</th>
            <th className="px-3 py-2">{t("panels.vendor_intel.col_flags")}</th>
            <th className="px-3 py-2">{t("panels.vendor_intel.col_actions")}</th></tr>
        </thead>
        <tbody>
          {filtered.length === 0 ? (
            <tr><td colSpan={7} className="p-6 text-center text-slate-500">
              {q ? "No matches" : t("panels.vendor_intel.empty")}
            </td></tr>
          ) : paged.map((v) => (
            <tr key={v.id} className="border-t" data-testid={`vintel-row-${v.vendor_ref}`}>
              <td className="px-3 py-2">{v.company_name || v.email}</td>
              <td className="px-3 py-2 font-mono text-xs">{v.vendor_ref}</td>
              <td className="px-3 py-2 text-center">{v.rating ?? "—"}</td>
              <td className="px-3 py-2 text-center">{v.band ?? "—"}</td>
              <td className="px-3 py-2 text-center"><AdminBadgePreview vendorRef={v.vendor_ref} /></td>
              <td className="px-3 py-2 text-center">
                {v.blacklisted && <span className="text-red-600 text-xs mr-1">BL</span>}
                {v.watchlisted && <span className="text-amber-600 text-xs">WL</span>}
              </td>
              <td className="px-3 py-2">
                <button onClick={() => setSelected(v)} data-testid={`vintel-select-${v.vendor_ref}`}
                  className="text-xs border px-2 py-1">{t("panels.vendor_intel.manage")}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {controls}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full space-y-3" data-testid="vintel-modal">
            <div className="text-lg font-serif">{selected.company_name}</div>
            <div className="text-xs text-slate-500">{selected.vendor_ref}</div>
            <label className="block text-sm">
              <span>{t("panels.vendor_intel.score_label")}<InfoDot tip="Numeric score 0-100. Reflects the vendor's overall reliability across past contracts. Used to compute the Band." /></span>
              <input type="number" min="0" max="100" value={rating.score}
                onChange={(e) => setRating({ ...rating, score: Number(e.target.value) })}
                className="mt-1 w-full border px-3 py-2" data-testid="vintel-score" />
            </label>
            <label className="block text-sm">
              <span>{t("panels.vendor_intel.band_label")}<InfoDot tip="Coarse tier used by matrix routing rules — 'blacklisted' auto-rejects future bids from this vendor." /></span>
              <select value={rating.band} onChange={(e) => setRating({ ...rating, band: e.target.value })}
                className="mt-1 w-full border px-3 py-2" data-testid="vintel-band">
                {BANDS.map((b) => <option key={b}>{b}</option>)}
              </select>
            </label>
            <button onClick={() => saveRating(selected)} data-testid="vintel-save-rating"
              className="w-full bg-slate-900 text-white py-2 text-sm">
              {t("panels.vendor_intel.save_rating")}
              <InfoDot tip="Persists the score and band. Every change is written to the audit log with the acting admin's identity." />
            </button>
            <div className="border-t pt-3">
              <label className="block text-sm">
                <span>{t("panels.vendor_intel.bl_reason")}<InfoDot tip="Required when blacklisting. Rendered in the vendor's dossier and legal exports. Minimum 8 characters recommended." /></span>
                <input value={blacklistReason} onChange={(e) => setBlacklistReason(e.target.value)}
                  className="mt-1 w-full border px-3 py-2" data-testid="vintel-bl-reason" />
              </label>
              <div className="flex gap-2 mt-2">
                {!selected.blacklisted ? (
                  <button onClick={() => blacklist(selected)} data-testid="vintel-blacklist"
                    className="flex-1 bg-red-600 text-white py-2 text-sm">{t("panels.vendor_intel.blacklist")}</button>
                ) : (
                  <button onClick={() => unblacklist(selected)} data-testid="vintel-unblacklist"
                    className="flex-1 bg-slate-200 text-slate-900 py-2 text-sm">{t("panels.vendor_intel.unblacklist")}</button>
                )}
              </div>
            </div>
            <button onClick={() => setSelected(null)} className="text-xs text-slate-500 hover:underline">
              {t("panels.vendor_intel.close")}
            </button>
          </div>
        </div>
      )}
      <ReviewModerationSection />
    </div>
  );
}
