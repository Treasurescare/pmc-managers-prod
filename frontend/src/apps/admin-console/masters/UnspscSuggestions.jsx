import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";
import UnspscPicker from "@/components/UnspscPicker";

const Row = ({ c, onDone }) => {
  const [manual, setManual] = useState(null);
  const approve = (code) => mastersApi.approveCategoryUnspsc(c.id, code)
    .then(() => { toast.success(`${c.name} linked to UNSPSC ${code}`); onDone(); }).catch(showApiError);
  return (
    <div className="border-t border-amber-200 py-2 space-y-1" data-testid={`unspsc-suggest-${c.code}`}>
      <div className="text-sm font-semibold">{c.name}</div>
      <div className="flex flex-wrap gap-2">
        {c.suggestions.map((s) => (
          <button key={s.code} type="button" onClick={() => approve(s.code)} data-testid={`unspsc-approve-${c.code}-${s.code}`}
            className="text-xs px-2 py-1 border border-emerald-600 text-emerald-800 hover:bg-emerald-50">
            Approve {s.code} · {s.title}</button>))}
        {!c.suggestions.length && <span className="text-xs text-brand-navy/60">No close match found — search below.</span>}
      </div>
      <div className="flex gap-2 items-start">
        <div className="flex-1"><UnspscPicker testidPrefix={`unspsc-manual-${c.code}`} value={manual?.code} title={manual?.title} onChange={setManual} /></div>
        {manual?.code && <button type="button" className="text-xs px-2 py-2 border border-brand-navy" onClick={() => approve(manual.code)}
          data-testid={`unspsc-approve-manual-${c.code}`}>Approve this code</button>}
      </div>
    </div>);
};

export default function UnspscSuggestions({ onChanged }) {
  const [rows, setRows] = useState(null);
  const load = useCallback(() => mastersApi.categoryUnspscSuggestions().then(setRows).catch(() => setRows([])), []);
  useEffect(() => { load(); }, [load]);
  if (!rows || !rows.length) return null;
  const done = () => { load(); onChanged?.(); };
  return (
    <details className="bg-amber-50 border border-amber-300 p-3 mb-4" data-testid="unspsc-suggestions">
      <summary className="text-sm cursor-pointer"><b>{rows.length} categories have no UNSPSC code.</b> Suggested codes are ready for your approval — nothing changes until you approve.</summary>
      <div className="mt-2">{rows.map((c) => <Row key={c.id} c={c} onDone={done} />)}</div>
    </details>);
}
