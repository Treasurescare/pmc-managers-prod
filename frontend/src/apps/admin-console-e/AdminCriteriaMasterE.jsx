import { useEffect, useState } from "react";
import { toast } from "sonner";
import AdminEShell from "./AdminEShell";
import { criteriaApi, criteriaLibApi, showApiError } from "@/lib/api";
import { BLANK, CriterionLine, CriterionRow, toPayload } from "@/apps/admin-console/notice/CriteriaEditorModal";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm";
const strip = ({ id, _id, status, created_at, created_by, updated_at, updated_by, ...c }) => c; // eslint-disable-line no-unused-vars

const ItemEditor = ({ item, i, prefill, onDone }) => {
  const [c, setC] = useState(() => ({ ...BLANK, ...strip(item) }));
  const save = () => (item.id ? criteriaLibApi.editItem(item.id, toPayload(c)) : criteriaLibApi.addItem(toPayload(c)))
    .then(() => { toast.success("Master criterion saved"); onDone(); }).catch(showApiError);
  const archive = () => (item.id ? (window.confirm(`Remove "${item.title}" from the master? Tenders already using it keep it.`) && criteriaLibApi.archiveItem(item.id).then(() => { toast.success("Removed from master"); onDone(); }).catch(showApiError)) : onDone());
  return (
    <div className="space-y-2" data-testid={`master-item-${i}`}>
      <CriterionRow c={c} i={i} prefillFields={prefill} onChange={setC} onRemove={archive} />
      <div className="flex justify-end"><button type="button" className="pmc-btn pmc-btn--primary" onClick={save} data-testid={`master-item-save-${i}`}>Save</button></div>
    </div>);
};

const NewSet = ({ items, onDone }) => {
  const [name, setName] = useState("");
  const [pick, setPick] = useState([]);
  const toggle = (id) => setPick((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const save = () => criteriaLibApi.addSet({ name, criteria: items.filter((x) => pick.includes(x.id)).map((x) => toPayload({ ...BLANK, ...strip(x) })) })
    .then(() => { toast.success(`Criteria set "${name}" saved`); setName(""); setPick([]); onDone(); }).catch(showApiError);
  return (
    <div className="bg-white border border-brand-navy/15 p-4 space-y-3" data-testid="master-new-set">
      <b className="text-sm">New criteria set</b>
      <input className={inp + " w-full md:w-96 block"} placeholder="Set name, e.g. Standard construction" value={name} onChange={(e) => setName(e.target.value)} data-testid="master-new-set-name" />
      <div className="grid md:grid-cols-2 gap-1 text-sm">
        {items.map((x) => <label key={x.id} className="flex gap-2 items-center"><input type="checkbox" checked={pick.includes(x.id)} onChange={() => toggle(x.id)} data-testid={`master-new-set-pick-${x.id}`} />{x.title}</label>)}
      </div>
      <button type="button" className="pmc-btn pmc-btn--primary" disabled={name.trim().length < 2 || !pick.length} onClick={save} data-testid="master-new-set-save">Save set ({pick.length})</button>
    </div>);
};

const SetCard = ({ s, onDone }) => (
  <div className="bg-white border border-brand-navy/15 p-4" data-testid={`master-set-${s.id}`}>
    <div className="flex justify-between items-center gap-2"><b>{s.name}</b><span className="text-xs text-brand-navy/60">{s.criteria.length} criteria</span>
      <button type="button" className="text-xs text-red-700 underline" onClick={() => window.confirm(`Remove the set "${s.name}"?`) && criteriaLibApi.archiveSet(s.id).then(() => { toast.success("Set removed"); onDone(); }).catch(showApiError)} data-testid={`master-set-remove-${s.id}`}>Remove</button></div>
    <ul>{s.criteria.map((c, i) => <CriterionLine key={`${s.id}-${i}`} c={c} />)}</ul>
  </div>);

export default function AdminCriteriaMasterE() {
  const [lib, setLib] = useState(null);
  const [prefill, setPrefill] = useState({});
  const [adding, setAdding] = useState(false);
  const load = () => criteriaLibApi.get().then(setLib).catch(showApiError);
  useEffect(() => { load(); criteriaApi.templates().then((t) => setPrefill(t.prefill_fields || {})).catch(() => {}); }, []);
  const done = () => { setAdding(false); load(); };
  return (
    <AdminEShell active="Criteria master" crumb={<>Procurement / <b>Criteria master</b></>}>
      <div className="p-6 space-y-6" data-testid="criteria-master-page">
        <p className="text-sm text-brand-navy/70 max-w-3xl">Build the criteria every tender picks from. Tender authors add these (or a whole set) with <b>+ Add from master</b> in the Criteria window, and can still add one-off criteria of their own. Changes here don't alter tenders that already use a criterion.</p>
        {!lib ? <div className="text-sm">Loading…</div> : <>
          <section className="space-y-3">
            <div className="flex justify-between items-center"><h2 className="font-serif text-xl text-brand-navy">Criteria sets</h2></div>
            {lib.sets.map((s) => <SetCard key={s.id} s={s} onDone={load} />)}
            {!lib.sets.length && <p className="text-sm text-brand-navy/60" data-testid="master-sets-empty">No sets yet. Build one below, or use "Save as set" in any tender's Criteria window.</p>}
            <NewSet items={lib.items} onDone={load} />
          </section>
          <section className="space-y-3">
            <div className="flex justify-between items-center"><h2 className="font-serif text-xl text-brand-navy">Master criteria ({lib.items.length})</h2>
              <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => setAdding(true)} data-testid="master-add-item">+ New criterion</button></div>
            {adding && <ItemEditor item={{}} i="new" prefill={prefill} onDone={done} />}
            {lib.items.map((x, i) => <ItemEditor key={x.id} item={x} i={i} prefill={prefill} onDone={load} />)}
          </section>
        </>}
      </div>
    </AdminEShell>
  );
}
