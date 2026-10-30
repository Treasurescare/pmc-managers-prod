import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { marketingApi, showApiError } from "@/lib/api";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm";
const TEMPLATE = "email,name,company,audience,country,categories,consent\nbuyer@example.org,Jane Doe,City Works Dept,buyer,GB,Construction;Roofing,yes\n";

function ImportBox({ onDone }) {
  const [text, setText] = useState("");
  const [aud, setAud] = useState("vendor");
  const [ok, setOk] = useState(false);
  const pick = (e) => { const f = e.target.files?.[0]; if (f) f.text().then(setText); };
  const run = async () => {
    try {
      const r = await marketingApi.importCsv({ csv_text: text, audience: aud, lawful_basis_confirmed: ok });
      toast.success(`Imported: ${r.created} new, ${r.updated} updated, ${r.skipped} skipped`);
      setText(""); onDone();
    } catch (e) { showApiError(e); }
  };
  const tpl = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([TEMPLATE], { type: "text/csv" }));
    a.download = "pmc-contacts-template.csv"; a.click();
  };
  return (
    <div className="border border-brand-navy/20 bg-white p-4 space-y-3" data-testid="mkt-import">
      <div className="pmc-label">Upload a contact list (CSV)</div>
      <div className="flex flex-wrap gap-3 items-center text-sm">
        <input type="file" accept=".csv,text/csv" onChange={pick} data-testid="mkt-import-file" />
        <select className={inp} value={aud} onChange={(e) => setAud(e.target.value)} data-testid="mkt-import-audience">
          <option value="vendor">Default: vendors</option><option value="buyer">Default: buyers</option></select>
        <button type="button" className="underline text-brand-navy" onClick={tpl} data-testid="mkt-import-template">Download template</button>
      </div>
      {text && <div className="text-xs text-brand-navy/60">{text.split("\n").filter(Boolean).length - 1} rows ready</div>}
      <label className="flex gap-2 text-xs items-start">
        <input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} data-testid="mkt-import-consent" />
        I confirm these people agreed to hear from PMC Managers, or are business contacts we may lawfully email. Each email will include an unsubscribe link.
      </label>
      <button className="pmc-btn pmc-btn--primary" disabled={!text || !ok} onClick={run} data-testid="mkt-import-submit">Import contacts</button>
    </div>
  );
}

export const ContactsTab = () => {
  const [f, setF] = useState({ audience: "", country: "", q: "" });
  const [data, setData] = useState({ total: 0, items: [] });
  const load = useCallback(() => marketingApi.contacts(Object.fromEntries(Object.entries(f).filter(([, v]) => v)))
    .then(setData).catch(showApiError), [f]);
  useEffect(() => { load(); }, [load]);
  const sync = async () => { try { const r = await marketingApi.syncPlatform(); toast.success(`${r.created} platform contacts added`); load(); } catch (e) { showApiError(e); } };
  const del = async (id) => { if (!window.confirm("Remove this contact permanently?")) return; try { await marketingApi.deleteContact(id); load(); } catch (e) { showApiError(e); } };
  return (
    <div className="space-y-4" data-testid="mkt-contacts">
      <div className="flex flex-wrap gap-2 items-center">
        <select className={inp} value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })} data-testid="mkt-filter-audience">
          <option value="">Everyone</option><option value="vendor">Vendors</option><option value="buyer">Buyers</option></select>
        <input className={inp} placeholder="Country (GB)" maxLength={2} value={f.country} onChange={(e) => setF({ ...f, country: e.target.value.toUpperCase() })} data-testid="mkt-filter-country" />
        <input className={inp} placeholder="Search email or company" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} data-testid="mkt-filter-q" />
        <button className="pmc-btn" onClick={sync} data-testid="mkt-sync">Add platform vendors &amp; buyers</button>
        <span className="text-sm text-brand-navy/70 ml-auto" data-testid="mkt-contacts-total">{data.total} contacts</span>
      </div>
      <ImportBox onDone={load} />
      <div className="overflow-x-auto border border-brand-navy/15 bg-white">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs uppercase tracking-widest text-brand-navy/60">
            {["Email", "Company", "Type", "Country", "Categories", "Source", "Status", ""].map((h) => <th key={h} className="p-2">{h}</th>)}</tr></thead>
          <tbody>{data.items.map((c) => (
            <tr key={c.id} className="border-t border-brand-navy/10" data-testid={`mkt-contact-${c.id}`}>
              <td className="p-2">{c.email}</td><td className="p-2">{c.company || "—"}</td><td className="p-2">{c.audience}</td>
              <td className="p-2">{c.country || "—"}</td><td className="p-2">{(c.categories || []).join(", ") || "—"}</td>
              <td className="p-2">{c.source}</td>
              <td className="p-2">{c.unsubscribed ? <span className="text-red-700">Unsubscribed</span> : c.consent ? "Can email" : <span className="text-amber-700">No consent</span>}</td>
              <td className="p-2"><button className="text-red-700 text-xs underline" onClick={() => del(c.id)} data-testid={`mkt-contact-del-${c.id}`}>Remove</button></td>
            </tr>))}
            {!data.items.length && <tr><td colSpan={8} className="p-6 text-center text-brand-navy/60">No contacts yet — add platform users or upload a CSV.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
};
