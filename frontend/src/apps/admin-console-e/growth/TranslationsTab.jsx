import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { growthApi } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";
import { patchDict } from "@/lib/autoTranslate";
import { btn, inp, useList } from "./BuyerAppsTab";

const PAGE = 50;

const Row = ({ lang, it, onSaved }) => {
  const [out, setOut] = useState(it.out);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setOut(it.out); }, [it.out]);
  const save = () => {
    setBusy(true);
    growthApi.saveI18nPhrase({ lang, src: it.src, out }).then((r) => { patchDict(lang, r.src, r.out); toast.success("Saved. Visitors see it within 5 minutes"); onSaved(); })
      .catch(showApiError).finally(() => setBusy(false));
  };
  const key = it.src.slice(0, 40).replace(/\W+/g, "-");
  return (
    <div className="grid md:grid-cols-[1fr_1fr_auto] gap-3 py-3 border-b border-brand-navy/10" data-testid={`tr-row-${key}`}>
      <div className="text-sm text-brand-navy whitespace-pre-wrap" data-testid="tr-src">{it.src}</div>
      <textarea dir="auto" rows={Math.min(4, Math.ceil(it.src.length / 60) + 1)} value={out} onChange={(e) => setOut(e.target.value)}
        className={inp + " mt-0"} data-testid="tr-out-input" />
      <div className="flex md:flex-col gap-2 items-start">
        <button className={btn} disabled={busy || !out.trim() || (it.reviewed && out === it.out)} onClick={save} data-testid="tr-save-btn">{it.reviewed && out === it.out ? "Saved" : out === it.out ? "Approve" : "Save fix"}</button>
        {it.reviewed && <span className="text-[10px] uppercase tracking-widest text-emerald-700" data-testid="tr-reviewed-badge" title={`${it.reviewed_by || ""} ${it.reviewed_at || ""}`}>Reviewed</span>}
      </div>
    </div>);
};

export const TranslationsTab = () => {
  const [stats, loadStats] = useList(growthApi.i18nStats);
  const [lang, setLang] = useState("ar");
  const [q, setQ] = useState("");
  const [qIn, setQIn] = useState("");
  const reqId = useRef(0);
  useEffect(() => { const t = setTimeout(() => { setQ(qIn); setSkip(0); }, 350); return () => clearTimeout(t); }, [qIn]);
  const [status, setStatus] = useState("pending");
  const [skip, setSkip] = useState(0);
  const [data, setData] = useState({ total: 0, items: [] });
  const load = useCallback(() => {
    const id = ++reqId.current;
    return growthApi.i18nPhrases({ lang, q, status, skip, limit: PAGE }).then((r) => { if (id === reqId.current) setData(r); }).catch(showApiError);
  }, [lang, q, status, skip]);
  useEffect(() => { load(); }, [load]);
  const reset = (fn) => (e) => { fn(e.target.value); setSkip(0); };
  const cur = stats.find((s) => s.lang === lang);
  return (
    <div className="bg-white border border-brand-navy/15 p-4 notranslate" translate="no" data-testid="translations-tab">
      <p className="text-sm text-brand-navy/70 mb-3">Check the AI translation of each phrase. Edit and save to fix it, or press Approve if it is already right. Fixes reach every page within about 5 minutes and are never overwritten by AI. Phrases starting with a comma or full stop are pieces of a longer sentence split by a link or highlight.</p>
      <div className="grid md:grid-cols-4 gap-3 items-end mb-3">
        <label className="text-xs text-brand-navy">Language
          <select className={inp} value={lang} onChange={reset(setLang)} data-testid="tr-lang-select">
            {stats.map((s) => <option key={s.lang} value={s.lang}>{s.name} ({s.reviewed}/{s.total})</option>)}
          </select></label>
        <label className="text-xs text-brand-navy">Show
          <select className={inp} value={status} onChange={reset(setStatus)} data-testid="tr-status-select">
            <option value="pending">Not reviewed yet</option><option value="reviewed">Reviewed</option><option value="all">All</option>
          </select></label>
        <label className="text-xs text-brand-navy md:col-span-2">Search English or translation
          <input className={inp} value={qIn} onChange={(e) => setQIn(e.target.value)} placeholder="e.g. Submit bid" data-testid="tr-search-input" /></label>
      </div>
      {cur && <div className="text-xs text-brand-navy/70 mb-2" data-testid="tr-progress">{cur.reviewed} of {cur.total} phrases reviewed · {data.total} match this view</div>}
      <div>{data.items.map((it) => <Row key={it.src} lang={lang} it={it} onSaved={() => { load(); loadStats(); }} />)}</div>
      {!data.items.length && <div className="text-sm text-brand-navy/60 py-6" data-testid="tr-empty">No phrases match.</div>}
      <div className="flex gap-2 mt-3 items-center">
        <button className={btn} disabled={!skip} onClick={() => setSkip(Math.max(0, skip - PAGE))} data-testid="tr-prev-btn">Previous</button>
        <span className="text-xs text-brand-navy/70">{data.total ? `${skip + 1}–${Math.min(skip + PAGE, data.total)} of ${data.total}` : ""}</span>
        <button className={btn} disabled={skip + PAGE >= data.total} onClick={() => setSkip(skip + PAGE)} data-testid="tr-next-btn">Next</button>
      </div>
    </div>);
};
