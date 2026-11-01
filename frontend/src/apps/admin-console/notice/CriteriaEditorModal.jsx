import { useEffect, useState } from "react";
import { toast } from "sonner";
import { criteriaApi, consortiumApi, showApiError } from "@/lib/api";

const inp = "w-full px-2 py-1.5 border border-brand-navy/20 bg-white text-sm";
const OPS = { gte: "at least", lte: "at most", eq: "exactly" };
const BLANK = { title: "", category: "other", answer_type: "number", operator: "gte", threshold: "", unit: "", period: "",
  proof: "", proof_required: true, kind: "must_pass", max_points: "", scoring: "auto", full_points_at: "", consortium_rule: "each", prefill_field: "" };

const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));

const ConsortiumOptions = ({ cons, setCons, defMax, setDefMax, admin }) => {
  const saveDef = () => consortiumApi.saveSettings({ max_members_default: Number(defMax) }).then(() => toast.success("Platform default saved")).catch(showApiError);
  return (
    <div className="border border-brand-navy/15 p-3 space-y-2" data-testid="criteria-consortium">
      <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={cons.allowed} onChange={(e) => setCons({ ...cons, allowed: e.target.checked })} data-testid="criteria-consortium-allowed" />Accept consortium bids (registered suppliers bidding together)</label>
      {cons.allowed && <div className="flex gap-3 items-end flex-wrap text-sm">
        <label>Maximum members, including the lead
          <input type="number" min={2} max={20} className={inp + " w-40"} placeholder={`Default ${defMax}`} value={cons.max} onChange={(e) => setCons({ ...cons, max: e.target.value })} data-testid="criteria-consortium-max" /></label>
        <span className="text-xs text-brand-navy/60">Leave blank to use the platform default ({defMax}). Choose lead / combined / every member on each criterion.</span>
      </div>}
      {admin && <div className="flex gap-2 items-end text-xs flex-wrap"><label>Platform default for all tenders
        <input type="number" min={2} max={20} className={inp + " w-24"} value={defMax} onChange={(e) => setDefMax(e.target.value)} data-testid="consortium-default-max" /></label>
        <button type="button" className="pmc-btn pmc-btn--secondary" onClick={saveDef} data-testid="consortium-default-save">Save default</button></div>}
    </div>);
};

const CriterionRow = ({ c, i, onChange, onRemove, prefillFields }) => {
  const set = (k, v) => onChange({ ...c, [k]: v });
  const isNum = c.answer_type === "number";
  return (
    <div className={`border p-3 space-y-2 bg-white ${c.needs_review ? "border-amber-400" : "border-brand-navy/15"}`} data-testid={`crit-row-${i}`}>
      {c.needs_review && <div className="text-[11px] text-amber-800" data-testid={`crit-review-${i}`}>Read by AI — the figure or unit wasn't clear in the document. Please fill it in.</div>}
      <div className="grid grid-cols-12 gap-2">
        <input className={`${inp} col-span-12 md:col-span-6`} placeholder="What is measured, e.g. Average annual turnover" value={c.title} onChange={(e) => set("title", e.target.value)} data-testid={`crit-title-${i}`} />
        <select className={`${inp} col-span-6 md:col-span-3`} value={c.kind} onChange={(e) => set("kind", e.target.value)} data-testid={`crit-kind-${i}`}>
          <option value="must_pass">Must pass</option><option value="scored">Scored</option>
        </select>
        <select className={`${inp} col-span-6 md:col-span-3`} value={c.answer_type} onChange={(e) => set("answer_type", e.target.value)} data-testid={`crit-type-${i}`}>
          <option value="number">Number</option><option value="yes_no">Yes / No</option><option value="text">Written answer</option>
        </select>
      </div>
      {isNum && <div className="grid grid-cols-12 gap-2">
        <select className={`${inp} col-span-4 md:col-span-2`} value={c.operator || "gte"} onChange={(e) => set("operator", e.target.value)} data-testid={`crit-op-${i}`}>
          {Object.entries(OPS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <input className={`${inp} col-span-4 md:col-span-3`} type="number" placeholder="Value" value={c.threshold ?? ""} onChange={(e) => set("threshold", e.target.value)} data-testid={`crit-threshold-${i}`} />
        <input className={`${inp} col-span-4 md:col-span-2`} placeholder="Unit / currency" value={c.unit || ""} onChange={(e) => set("unit", e.target.value)} data-testid={`crit-unit-${i}`} />
        <input className={`${inp} col-span-12 md:col-span-5`} placeholder="Period, e.g. Last 3 financial years" value={c.period || ""} onChange={(e) => set("period", e.target.value)} data-testid={`crit-period-${i}`} />
      </div>}
      {c.kind === "scored" && <div className="grid grid-cols-12 gap-2 items-center">
        <input className={`${inp} col-span-4 md:col-span-2`} type="number" placeholder="Max points" value={c.max_points ?? ""} onChange={(e) => set("max_points", e.target.value)} data-testid={`crit-points-${i}`} />
        <select className={`${inp} col-span-8 md:col-span-4`} value={c.answer_type === "text" ? "evaluator" : c.scoring || "auto"} disabled={c.answer_type === "text"} onChange={(e) => set("scoring", e.target.value)} data-testid={`crit-scoring-${i}`}>
          <option value="auto">Points worked out by the system</option><option value="evaluator">Marked by evaluators</option>
        </select>
        {isNum && (c.scoring || "auto") === "auto" && <input className={`${inp} col-span-12 md:col-span-6`} type="number" placeholder="Value that earns full points" value={c.full_points_at ?? ""} onChange={(e) => set("full_points_at", e.target.value)} data-testid={`crit-full-${i}`} />}
      </div>}
      <div className="grid grid-cols-12 gap-2 items-center">
        <input className={`${inp} col-span-12 md:col-span-5`} placeholder="Proof required, e.g. Audited accounts for 3 years" value={c.proof || ""} onChange={(e) => set("proof", e.target.value)} data-testid={`crit-proof-${i}`} />
        <label className="col-span-6 md:col-span-2 text-xs flex gap-1 items-center"><input type="checkbox" checked={!!c.proof_required} onChange={(e) => set("proof_required", e.target.checked)} data-testid={`crit-proof-req-${i}`} />Proof mandatory</label>
        <select className={`${inp} col-span-6 md:col-span-2`} value={c.consortium_rule || "each"} onChange={(e) => set("consortium_rule", e.target.value)} title="For consortium bids" data-testid={`crit-consortium-${i}`}>
          <option value="lead">Consortium: lead alone</option><option value="combined">Consortium: members together</option><option value="each">Consortium: every member</option>
        </select>
        <select className={`${inp} col-span-10 md:col-span-2`} value={c.prefill_field || ""} onChange={(e) => set("prefill_field", e.target.value)} title="Fill from supplier's PMC profile" data-testid={`crit-prefill-${i}`}>
          <option value="">No auto-fill</option>{Object.entries(prefillFields).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <button type="button" className="col-span-2 md:col-span-1 text-xs text-red-700" onClick={onRemove} data-testid={`crit-remove-${i}`}>Remove</button>
      </div>
    </div>
  );
};

const CriterionLine = ({ c }) => (
  <li className="text-sm border-b border-brand-navy/10 py-2">
    <b>{c.title}</b> · {c.kind === "must_pass" ? "must pass" : `scored, up to ${c.max_points} pts`}
    {c.answer_type === "number" && <> · {OPS[c.operator]} {Number(c.threshold).toLocaleString()} {c.unit}{c.period ? ` (${c.period})` : ""}</>}
    {c.answer_type === "yes_no" && " · yes required"}
    {c.proof && <span className="text-brand-navy/60"> · proof: {c.proof}{c.proof_required ? "" : " (optional)"}</span>}
  </li>
);

export default function CriteriaEditorModal({ noticeRef, title, onClose, onSaved, mode = "admin" }) {
  const vendor = mode !== "admin";
  const API = mode === "template" ? { get: criteriaApi.tplGet, save: criteriaApi.tplSave, ai: criteriaApi.tplAiSuggest }
    : vendor ? { get: criteriaApi.mineGet, save: criteriaApi.mineSave, ai: criteriaApi.mineAiSuggest }
      : { get: criteriaApi.adminGet, save: criteriaApi.save, ai: criteriaApi.aiSuggest };
  const [check, setCheck] = useState(null);
  const [data, setData] = useState(null);
  const [rows, setRows] = useState([]);
  const [tpl, setTpl] = useState({ templates: [], prefill_fields: {} });
  const [fx, setFx] = useState("");
  const [cons, setCons] = useState({ allowed: false, max: "" });
  const [defMax, setDefMax] = useState(5);
  const [busy, setBusy] = useState("");
  useEffect(() => {
    API.get(noticeRef).then((d) => { setData(d); setRows(d.criteria); setFx(d.fx_rule || ""); setCheck(d.ai_check || null); setCons({ allowed: !!d.consortium_allowed, max: d.consortium_max_members || "" }); }).catch(showApiError);
    criteriaApi.templates().then(setTpl).catch(() => {});
    consortiumApi.settings().then((s) => setDefMax(s.max_members_default)).catch(() => {});
  }, [noticeRef, mode]); // eslint-disable-line react-hooks/exhaustive-deps
  const upd = (i, c) => setRows((r) => r.map((x, j) => (j === i ? c : x)));
  const ai = async () => {
    setBusy("ai");
    try {
      const r = await API.ai(noticeRef);
      if (r.criteria.length) {
        const norm = (s) => (s || "").trim().toLowerCase();
        const have = rows.map((x) => norm(x.title)).filter(Boolean);
        const fresh = r.criteria.filter((x) => { const t = norm(x.title); return t && !have.some((h) => h.includes(t) || t.includes(h)); });
        setRows((x) => [...x, ...fresh]);
        toast.success(`${fresh.length} new criteria read from the tender — check each one before saving`);
      }
      else toast.info(r.note);
    } catch (e) { showApiError(e); } finally { setBusy(""); }
  };
  const save = async () => {
    setBusy("save");
    try {
      const criteria = rows.map(({ needs_review, ...c }) => ({ ...c, threshold: num(c.threshold), max_points: num(c.max_points), // eslint-disable-line no-unused-vars
        full_points_at: num(c.full_points_at), prefill_field: c.prefill_field || null, operator: c.answer_type === "number" ? c.operator || "gte" : null }));
      const d = await API.save(noticeRef, { criteria, fx_rule: fx || null, consortium_allowed: cons.allowed, consortium_max_members: cons.allowed && cons.max ? Number(cons.max) : null });
      setCheck(null);
      setRows(d.criteria); toast.success("Criteria saved"); onSaved?.(d);
    } catch (e) { showApiError(e); } finally { setBusy(""); }
  };
  const runCheck = async () => {
    setBusy("check");
    try { setCheck(await criteriaApi.aiCheck(noticeRef)); } catch (e) { showApiError(e); } finally { setBusy(""); }
  };
  const mustPass = rows.filter((c) => c.kind === "must_pass").length;
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-4 overflow-y-auto" data-testid="criteria-modal">
      <div className="bg-brand-pale w-full max-w-5xl p-5 space-y-4 my-6">
        <div className="flex justify-between items-start gap-3">
          <div><div className="text-[11px] uppercase tracking-widest text-brand-navy/60">Tender criteria{mode === "template" ? (title ? ` · ${title}` : "") : ` · ${noticeRef}`}</div>
            <h2 className="font-serif text-2xl text-brand-navy">What bidders must meet</h2>
            <p className="text-xs text-brand-navy/70">Must-pass items are checked by the system at opening. Scored items add points. At least one must-pass item is needed to publish.</p></div>
          <button type="button" className="pmc-btn pmc-btn--secondary" onClick={onClose} data-testid="criteria-close">Close</button>
        </div>
        {!vendor && data && rows.length > 0 && (
          <div className="bg-white border border-brand-navy/15 p-3 space-y-2" data-testid="criteria-ai-check">
            <div className="flex justify-between items-center gap-2 flex-wrap">
              <b className="text-sm">Do these criteria match the tender document?</b>
              <button type="button" className="pmc-btn pmc-btn--secondary" disabled={!!busy} onClick={runCheck} data-testid="criteria-ai-check-run">{busy === "check" ? "Checking…" : "Check against tender document (AI)"}</button>
            </div>
            {!check && <p className="text-xs text-brand-navy/60">Run the check before publishing. Save any changes first.</p>}
            {check && check.verdict === "match" && <p className="text-sm text-emerald-800" data-testid="criteria-ai-check-ok">No differences found ({check.checked_at?.slice(0, 16).replace("T", " ")} UTC).</p>}
            {check && check.verdict === "issues" && (
              <ul className="text-sm text-amber-900 list-disc pl-5" data-testid="criteria-ai-check-issues">
                {check.issues.map((x, i) => <li key={`iss-${i}`}>{x.criterion ? <b>{x.criterion}: </b> : null}{x.problem}{x.document_says ? <i> — document says: {x.document_says}</i> : null}</li>)}
                {check.missing_from_criteria.map((x) => <li key={x}>In the document but not in the criteria: {x}</li>)}
              </ul>)}
          </div>)}
        {!data ? <div className="text-sm">Loading…</div> : data.locked ? (
          <div data-testid="criteria-locked">
            <div className="bg-amber-50 border border-amber-300 p-3 text-sm mb-3">This tender is live. Criteria can only change through a corrigendum sent to all suppliers.</div>
            {rows.length ? <ul>{rows.map((c) => <CriterionLine key={c.id} c={c} />)}</ul> : <p className="text-sm">No criteria were set for this tender.</p>}
          </div>
        ) : <>
          <div className="flex gap-2 flex-wrap items-center">
            <button type="button" className="pmc-btn pmc-btn--secondary" disabled={!!busy} onClick={ai} data-testid="criteria-ai">{busy === "ai" ? "Reading tender…" : "Read from tender document (AI)"}</button>
            <select className={`${inp} w-auto`} value="" onChange={(e) => { const t = tpl.templates[Number(e.target.value)]; if (t) setRows((r) => [...r, { ...BLANK, ...t, id: undefined }]); }} data-testid="criteria-template">
              <option value="">+ Add from template…</option>{tpl.templates.map((t, i) => <option key={t.title} value={i}>{t.title}</option>)}
            </select>
            <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => setRows((r) => [...r, { ...BLANK }])} data-testid="criteria-add">+ Blank criterion</button>
          </div>
          <div className="space-y-2">{rows.map((c, i) => <CriterionRow key={c.id || `new-${i}`} c={c} i={i} prefillFields={tpl.prefill_fields} onChange={(x) => upd(i, x)} onRemove={() => setRows((r) => r.filter((_, j) => j !== i))} />)}</div>
          {!rows.length && <p className="text-sm text-brand-navy/60" data-testid="criteria-empty">No criteria yet. Read them from the tender document, pick a template or add one.</p>}
          <label className="block text-sm">Currency conversion rule (for amounts in other currencies)
            <input className={inp} placeholder="e.g. Central bank rate on the closing date" value={fx} onChange={(e) => setFx(e.target.value)} data-testid="criteria-fx" /></label>
          <ConsortiumOptions cons={cons} setCons={setCons} defMax={defMax} setDefMax={setDefMax} admin={!vendor} />
          <div className="flex justify-between items-center gap-2 flex-wrap">
            <span className={`text-sm ${mustPass ? "text-emerald-800" : "text-amber-800"}`} data-testid="criteria-summary">{rows.length} criteria · {mustPass} must-pass{mustPass ? "" : " — add at least one to publish"}</span>
            <button type="button" className="pmc-btn pmc-btn--primary" disabled={!!busy} onClick={save} data-testid="criteria-save">{busy === "save" ? "Saving…" : "Save criteria"}</button>
          </div>
        </>}
      </div>
    </div>
  );
}
