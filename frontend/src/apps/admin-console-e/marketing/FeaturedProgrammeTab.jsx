import { useEffect, useState } from "react";
import { toast } from "sonner";
import { siteApi, showApiError } from "@/lib/api";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm w-full";
const Field = ({ label, children }) => <label className="block text-sm space-y-1"><span className="font-semibold">{label}</span>{children}</label>;

const Highlights = ({ items, onChange }) => (
  <div className="space-y-2">
    <div className="text-sm font-semibold">Package highlights (shown as cards)</div>
    {items.map((x, i) => (
      <div key={i} className="grid grid-cols-[1fr_2fr_auto] gap-2">
        <input className={inp} placeholder="Title" value={x.title} data-testid={`prog-hl-title-${i}`}
          onChange={(e) => onChange(items.map((y, j) => (j === i ? { ...y, title: e.target.value } : y)))} />
        <input className={inp} placeholder="One line" value={x.text} data-testid={`prog-hl-text-${i}`}
          onChange={(e) => onChange(items.map((y, j) => (j === i ? { ...y, text: e.target.value } : y)))} />
        <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" data-testid={`prog-hl-remove-${i}`}
          onClick={() => onChange(items.filter((_, j) => j !== i))}>Remove</button>
      </div>))}
    {items.length < 8 && <button type="button" className="pmc-btn pmc-btn--secondary pmc-btn--sm" data-testid="prog-hl-add"
      onClick={() => onChange([...items, { title: "", text: "" }])}>Add highlight</button>}
  </div>);

export const FeaturedProgrammeTab = () => {
  const [f, setF] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { siteApi.programme().then(setF).catch(showApiError); }, []);
  if (!f) return null;
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { setF(await siteApi.saveProgramme(f)); toast.success("Featured programme saved — live on the home page now"); }
    catch (err) { showApiError(err); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={save} className="border border-brand-navy/20 bg-white p-4 space-y-4 max-w-3xl" data-testid="mkt-featured-programme">
      <div className="pmc-label">Project promoted on the home page</div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!f.enabled} data-testid="prog-enabled"
        onChange={(e) => setF({ ...f, enabled: e.target.checked })} /> Show the programme spotlight on the home page</label>
      <Field label="Small heading"><input className={inp} value={f.eyebrow} onChange={set("eyebrow")} data-testid="prog-eyebrow" /></Field>
      <Field label="Programme / project name"><input className={inp} value={f.title} onChange={set("title")} data-testid="prog-title" required /></Field>
      <Field label="Short description"><textarea className={inp} rows={3} value={f.summary} onChange={set("summary")} data-testid="prog-summary" /></Field>
      <Field label="Label under the package count in the home page numbers"><input className={inp} value={f.stat_label} onChange={set("stat_label")} data-testid="prog-stat-label" /></Field>
      <Field label="Link for 'See programme tenders' (e.g. /tenders/live?sector=…)"><input className={inp} value={f.tenders_link} onChange={set("tenders_link")} data-testid="prog-tenders-link" /></Field>
      <Field label="Brief / brochure link (optional, https://…)"><input className={inp} value={f.brief_url} onChange={set("brief_url")} data-testid="prog-brief-url" /></Field>
      <Highlights items={f.highlights || []} onChange={(highlights) => setF({ ...f, highlights })} />
      <button className="pmc-btn pmc-btn--primary" disabled={busy} data-testid="prog-save">{busy ? "Saving…" : "Save programme"}</button>
    </form>);
};
