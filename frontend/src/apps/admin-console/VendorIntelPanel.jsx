import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { vendorIntelApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import ReviewModerationSection, { AdminBadgePreview } from "@/apps/admin-console/vendor/ReviewModerationSection";
import { useListPager } from "@/components/ListPager";
import EvidenceManager from "@/components/EvidenceManager";
import BlacklistDashboardPanel from "@/apps/admin-console/BlacklistDashboardPanel";

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
  const [blDetail, setBlDetail] = useState(null); // full record with evidence + appeals

  const refreshBlDetail = async (ref) => {
    try { setBlDetail(await vendorIntelApi.getBlacklist(ref)); }
    catch { setBlDetail(null); }
  };

  const blacklist = async (v) => {
    if (!blacklistReason) return toast.error(t("panels.vendor_intel.reason_required"));
    try {
      await vendorIntelApi.blacklist({ vendor_ref: v.vendor_ref, reason: blacklistReason });
      toast.success(t("panels.vendor_intel.blacklisted_toast"));
      // v51av — reflect the new state in the open modal immediately so the
      // Remove button flips side without closing + reopening (docx #17).
      setSelected({ ...v, blacklisted: true });
      refreshBlDetail(v.vendor_ref);
      load();
    } catch (e) { showApiError(e); }
  };
  const unblacklist = async (v) => {
    if (!window.confirm(`Whitelist ${v.company_name || v.vendor_ref}? They will be able to bid again. The blacklist record and all evidence will be removed.`)) return;
    try {
      await vendorIntelApi.unblacklist(v.vendor_ref);
      toast.success(t("panels.vendor_intel.removed_toast"));
      setSelected({ ...v, blacklisted: false });
      setBlacklistReason("");
      setBlDetail(null);
      load();
    } catch (e) { showApiError(e); }
  };

  const addEvidence = async (entry) => {
    try {
      const bl = await vendorIntelApi.addEvidence(selected.vendor_ref, entry);
      setBlDetail(bl);
    } catch (e) { showApiError(e); }
  };
  const deleteEvidence = async (idx) => {
    if (!window.confirm("Delete this piece of evidence? This cannot be undone.")) return;
    try {
      const bl = await vendorIntelApi.deleteEvidence(selected.vendor_ref, idx);
      setBlDetail(bl);
    } catch (e) { showApiError(e); }
  };

  // When a vendor row is opened AND they are blacklisted, pull the detail
  // record so the evidence/appeals manager is populated.
  useEffect(() => {
    if (selected?.vendor_ref && selected?.blacklisted) refreshBlDetail(selected.vendor_ref);
    else setBlDetail(null);
  }, [selected?.vendor_ref, selected?.blacklisted]);

  return (
    <div data-testid="admin-vendor-intel-panel" className="bg-white border">
      {/* v51bd — triage dashboard first, so compliance opens the most urgent
          vendor without scrolling the giant summary table. */}
      <BlacklistDashboardPanel onOpenVendor={(row) => {
        const match = rows.find((v) => v.vendor_ref === row.vendor_ref);
        setSelected(match || { ...row, blacklisted: true });
      }} />
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full space-y-3 my-10" data-testid="vintel-modal">
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
                    className="flex-1 bg-emerald-600 text-white py-2 text-sm font-semibold">
                    Whitelist / remove from blacklist
                  </button>
                )}
              </div>
            </div>

            {/* v51bd — admin evidence manager (visible only once vendor is
                blacklisted). Supports file + camera capture + view/download/
                print/delete. */}
            {selected.blacklisted && (
              <div className="border-t pt-3 space-y-3" data-testid="vintel-bl-detail">
                <div className="text-xs text-slate-600">
                  <strong>Blacklist reason:</strong> {blDetail?.reason || "—"}
                  {blDetail?.at && <span> · {(blDetail.at || "").slice(0, 19).replace("T", " ")}</span>}
                </div>
                <EvidenceManager
                  title="Admin evidence"
                  items={blDetail?.evidence || []}
                  onAdd={addEvidence}
                  onDelete={deleteEvidence}
                  scope="blacklist-evidence"
                  testIdPrefix="vintel-ev"
                />
                {(blDetail?.appeals || []).length > 0 && (
                  <div className="border border-slate-200 bg-amber-50 p-3"
                       data-testid="vintel-appeals">
                    <div className="text-[11px] uppercase tracking-widest text-amber-800 font-semibold mb-2">
                      Vendor appeals ({(blDetail?.appeals || []).length})
                    </div>
                    <ul className="space-y-3">
                      {(blDetail?.appeals || []).map((ap, ai) => (
                        <AppealRow key={ai} appeal={ap} idx={ai}
                                   vendorRef={selected.vendor_ref}
                                   onDecision={(bl) => setBlDetail(bl)}
                                   onWhitelisted={() => {
                                     setSelected({ ...selected, blacklisted: false });
                                     setBlDetail(null); setBlacklistReason("");
                                     load();
                                   }} />
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

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


// v51be — appeal row with inline approve/reject form.
function AppealRow({ appeal, idx, vendorRef, onDecision, onWhitelisted }) {
  const [note, setNote] = useState("");
  const [whitelist, setWhitelist] = useState(false);
  const [busy, setBusy] = useState(false);
  const pending = (appeal.status || "pending") === "pending";

  const decide = async (verdict) => {
    if (!window.confirm(`Mark this appeal ${verdict.toUpperCase()}?${
      verdict === "approved" && whitelist ? "\nThis will also WHITELIST the vendor." : ""}`)) return;
    setBusy(true);
    try {
      const res = await vendorIntelApi.decideAppeal(vendorRef, idx,
        { decision: verdict, note: note.trim() || null,
          whitelist: verdict === "approved" ? whitelist : false });
      toast.success(`Appeal ${verdict}${res?.whitelisted ? " · vendor whitelisted" : ""}`);
      if (res?.whitelisted) onWhitelisted?.();
      else onDecision?.(res);
    } catch (e) {
      showApiError(e, { fallbackTitle: `Could not ${verdict === "approved" ? "approve" : "reject"} appeal` });
    } finally { setBusy(false); }
  };

  return (
    <li className="border-t border-amber-200 pt-2" data-testid={`vintel-appeal-${idx}`}>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="text-xs text-slate-700">
          <strong>{appeal.by || "vendor"}</strong>
          <span className="text-slate-500"> · {(appeal.at || "").slice(0, 19).replace("T", " ")}</span>
        </div>
        <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 border ${
          pending ? "border-amber-500 text-amber-700 bg-amber-100" :
          appeal.status === "approved" ? "border-emerald-500 text-emerald-700 bg-emerald-50" :
          "border-red-500 text-red-700 bg-red-50"
        }`} data-testid={`vintel-appeal-${idx}-status`}>
          {appeal.status || "pending"}
        </span>
      </div>
      {appeal.message && (
        <div className="text-sm text-slate-800 whitespace-pre-wrap mt-1">{appeal.message}</div>
      )}
      {(appeal.evidence || []).length > 0 && (
        <div className="mt-2">
          <EvidenceManager title="Appeal evidence" items={appeal.evidence} readOnly
                            testIdPrefix={`vintel-ap-ev-${idx}`} />
        </div>
      )}
      {!pending && (
        <div className="mt-2 bg-white border border-slate-200 p-2 text-xs"
             data-testid={`vintel-appeal-${idx}-decision`}>
          <div><strong>Decided by:</strong> {appeal.decided_by || "—"}
            <span className="text-slate-500"> · {(appeal.decided_at || "").slice(0, 19).replace("T", " ")}</span>
          </div>
          {appeal.decision_note && (
            <div className="mt-1 whitespace-pre-wrap italic">“{appeal.decision_note}”</div>
          )}
        </div>
      )}
      {pending && (
        <div className="mt-3 bg-white border border-slate-200 p-3 space-y-2">
          <label className="pmc-label block">Decision note (emailed to vendor)</label>
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)}
            placeholder="Add context — this is included in the vendor's email and the audit log"
            className="w-full px-2 py-1.5 border border-slate-300 text-sm"
            data-testid={`vintel-appeal-${idx}-note`} />
          <label className="inline-flex items-center gap-2 text-xs text-slate-700">
            <input type="checkbox" checked={whitelist}
              onChange={(e) => setWhitelist(e.target.checked)}
              data-testid={`vintel-appeal-${idx}-whitelist-toggle`} />
            Also whitelist vendor on approval
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={() => decide("approved")} disabled={busy}
              className="flex-1 bg-emerald-600 text-white py-2 text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50"
              data-testid={`vintel-appeal-${idx}-approve`}>
              {busy ? "Working…" : "Approve"}
            </button>
            <button type="button" onClick={() => decide("rejected")} disabled={busy}
              className="flex-1 bg-red-600 text-white py-2 text-sm font-semibold hover:bg-red-700 disabled:opacity-50"
              data-testid={`vintel-appeal-${idx}-reject`}>
              {busy ? "Working…" : "Reject"}
            </button>
          </div>
        </div>
      )}
    </li>
  );
}
