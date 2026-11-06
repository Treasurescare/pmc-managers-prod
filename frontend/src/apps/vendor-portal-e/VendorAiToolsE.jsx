import { useEffect, useState } from "react";
import { toast } from "sonner";
import VendorPortalChrome from "./VendorPortalChrome";
import { growthApi, payNeeded } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";

const List = ({ title, items }) => (items && items.length ? (
  <div className="mt-3"><div className="pmc-eyebrow">{title}</div>
    <ul className="list-disc pl-5 text-sm mt-1">{items.map((x, i) => <li key={i}>{typeof x === "string" ? x : x.label ? `${x.label}: ${x.date}` : `${x.item} — ${x.severity}${x.fix ? ` · Fix: ${x.fix}` : ""}`}</li>)}</ul>
  </div>) : null);

const Field = ({ k, v }) => (v ? <div className="text-sm mt-2"><b>{k}:</b> {v}</div> : null);

export const SummaryView = ({ r }) => (
  <div className="pmc-panel p-4 mt-4" data-testid="ai-summary-result">
    <h3 className="font-semibold">{r.title}</h3>
    <p className="text-sm mt-2">{r.result.summary}</p>
    <Field k="Buyer" v={r.result.buyer} /><Field k="Turnover" v={r.result.turnover} /><Field k="Experience" v={r.result.experience} />
    <Field k="EMD" v={r.result.emd} /><Field k="Evaluation" v={r.result.evaluation} />
    <List title="Scope" items={r.result.scope} /><List title="Eligibility" items={r.result.eligibility} />
    <List title="Fees" items={r.result.fees} /><List title="Key dates" items={r.result.key_dates} />
    <List title="Documents required" items={r.result.documents_required} /><List title="Risks" items={r.result.risks} />
  </div>);

const ReadyView = ({ r }) => (
  <div className="pmc-panel p-4 mt-4" data-testid="ai-readiness-result">
    <div className="flex items-center gap-3"><span className="text-3xl font-semibold" data-testid="ai-readiness-score">{r.result.score ?? "—"}</span>
      <span className="pmc-eyebrow">{({ ready: "Ready to bid", gaps: "Gaps to close", high_risk: "High disqualification risk" })[r.result.verdict] || r.result.verdict}</span></div>
    <List title="Already met" items={r.result.met} /><List title="Missing" items={r.result.missing} /><List title="Risks" items={r.result.risks} />
  </div>);

const usePay = () => (e) => {
  const pay = payNeeded(e);
  if (!pay) return showApiError(e);
  toast(pay.message, { duration: 15000, action: { label: "Pay now", onClick: () => { window.location.href = pay.checkout_url; } } });
};

export default function VendorAiToolsE() {
  const [file, setFile] = useState(null);
  const [ref, setRef] = useState("");
  const [lang, setLang] = useState("English");
  const [busy, setBusy] = useState("");
  const [sum, setSum] = useState(null);
  const [ready, setReady] = useState(null);
  const [prices, setPrices] = useState({});
  const [hist, setHist] = useState([]);
  const onErr = usePay();
  const loadHist = () => growthApi.aiReports().then((r) => setHist(r.items)).catch(() => {});
  useEffect(() => { growthApi.aiPrices().then(setPrices).catch(() => {}); loadHist(); }, []);
  const price = (c) => (prices[c]?.amount ? `${prices[c].currency} ${prices[c].amount}` : "Free");
  const summarise = async () => {
    const f = new FormData();
    if (file) f.append("file", file); else if (ref.trim()) f.append("notice_ref", ref.trim()); else return toast.error("Upload a document or enter a tender reference");
    f.append("lang", lang);
    setBusy("sum");
    try { setSum(await growthApi.aiSummary(f)); setReady(null); loadHist(); } catch (e) { onErr(e); } finally { setBusy(""); }
  };
  const check = async () => {
    setBusy("ready");
    try { setReady(await growthApi.aiReadiness(sum?.notice_ref || ref.trim() ? { notice_ref: sum?.notice_ref || ref.trim() } : { report_id: sum?.id })); loadHist(); }
    catch (e) { onErr(e); } finally { setBusy(""); }
  };
  return (
    <VendorPortalChrome active="/vendor/ai-tools">
      <div className="sp-head"><div><div className="pmc-eyebrow">AI tools</div><h1>Tender summary &amp; bid readiness</h1></div></div>
      <section className="pmc-panel p-4" data-testid="ai-tools-form">
        <p className="text-sm">Upload a tender document (PDF, DOCX or TXT) or enter a PMC tender reference. The AI pulls out eligibility, turnover, experience, EMD, fees and key dates, then checks your company profile for missing documents and disqualification risks.</p>
        <div className="grid md:grid-cols-3 gap-3 mt-3">
          <label className="text-sm">Tender document<input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} className="pmc-input mt-1 w-full" data-testid="ai-file-input" /></label>
          <label className="text-sm">…or PMC tender reference<input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="PMC-NOT-2026-0001" className="pmc-input mt-1 w-full" data-testid="ai-ref-input" /></label>
          <label className="text-sm">Answer language<select value={lang} onChange={(e) => setLang(e.target.value)} className="pmc-input mt-1 w-full" data-testid="ai-lang-select">
            {["English", "Español", "Français", "Deutsch", "हिन्दी", "Bahasa Melayu", "Bahasa Indonesia", "简体中文", "繁體中文", "한국어", "日本語", "Русский"].map((l) => <option key={l}>{l}</option>)}</select></label>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          <button className="pmc-btn pmc-btn--primary" disabled={!!busy} onClick={summarise} data-testid="ai-summary-btn">{busy === "sum" ? "Reading…" : `Summarise (${price("ai_tender_summary")})`}</button>
          <button className="pmc-btn pmc-btn--secondary" disabled={!!busy || (!sum && !ref.trim())} onClick={check} data-testid="ai-readiness-btn">{busy === "ready" ? "Checking…" : `Check my bid readiness (${price("ai_bid_readiness")})`}</button>
        </div>
        <p className="text-xs mt-2 opacity-60">AI results can be wrong — always confirm against the official tender document.</p>
      </section>
      {sum && <SummaryView r={sum} />}
      {ready && <ReadyView r={ready} />}
      {!!hist.length && <section className="pmc-panel p-4 mt-4" data-testid="ai-history">
        <div className="pmc-eyebrow mb-2">Your recent reports</div>
        {hist.map((h) => <button key={h.id} className="block text-left text-sm underline py-0.5" data-testid={`ai-history-${h.id}`}
          onClick={() => (h.kind === "summary" ? (setSum(h), setReady(null)) : setReady(h))}>{h.kind === "summary" ? "Summary" : "Readiness"} · {h.title} · {String(h.created_at).slice(0, 10)}</button>)}
      </section>}
    </VendorPortalChrome>);
}
