import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Bell } from "lucide-react";
import { api, showApiError } from "@/lib/api";
import { marketApi } from "@/lib/marketApi";

// Verified buyer organisations choose categories; PMC emails them when a new product in one goes live.
export function CategoryAlerts() {
  const [cats, setCats] = useState([]);
  const [mine, setMine] = useState(null);
  const [email, setEmail] = useState("");
  const [q, setQ] = useState("");
  useEffect(() => {
    marketApi.alerts().then((r) => { setMine(r.categories); setEmail(r.email); }).catch(() => setMine(false));
    api.get("/api/v1/masters/categories/public").then((r) => setCats(r.data || [])).catch(() => {});
  }, []);
  if (mine === false || mine === null) return null;
  const toggle = (n) => setMine((m) => (m.includes(n) ? m.filter((x) => x !== n) : [...m, n].slice(0, 30)));
  const save = () => marketApi.saveAlerts(mine).then((r) => { setMine(r.categories); toast.success(r.categories.length ? `Alerts on for ${r.categories.length} categor${r.categories.length === 1 ? "y" : "ies"}` : "Category alerts turned off"); }).catch(showApiError);
  const shown = cats.filter((c) => !q || c.name.toLowerCase().includes(q.toLowerCase())).slice(0, 80);
  return (
    <section className="pmc-panel p-4 mt-6" data-testid="market-category-alerts">
      <div className="flex items-center gap-2 font-semibold"><Bell size={16} /> Category alerts</div>
      <p className="text-sm opacity-80 mt-1">Choose the categories you buy. We email <b>{email}</b> as soon as a new product in one of them is approved.</p>
      {mine.length > 0 && <div className="flex flex-wrap gap-2 mt-2" data-testid="alerts-selected">{mine.map((n) => (
        <button key={n} type="button" className="pmc-tag" style={{ textTransform: "none" }} onClick={() => toggle(n)} data-testid={`alerts-remove-${n}`}>{n} ×</button>))}</div>}
      <input className="pmc-input w-full max-w-md mt-3" placeholder="Search categories" value={q} onChange={(e) => setQ(e.target.value)} data-testid="alerts-search" />
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-1 mt-2 max-h-64 overflow-auto text-sm">
        {shown.map((c) => (
          <label key={c.id || c.name} className="flex items-center gap-2"><input type="checkbox" checked={mine.includes(c.name)} onChange={() => toggle(c.name)} data-testid={`alerts-cat-${c.id}`} />{c.name}</label>))}
      </div>
      <button className="pmc-btn pmc-btn--primary pmc-btn--sm mt-3" onClick={save} data-testid="alerts-save">Save alerts</button>
    </section>);
}
