import { useEffect, useState } from "react";
import { toast } from "sonner";
import DOMPurify from "dompurify";
import { marketingApi, showApiError } from "@/lib/api";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm w-full";
const sec = "pmc-btn border border-brand-navy/40 bg-white px-3 py-2 text-sm whitespace-nowrap";
const EMPTY = { name: "", subject: "", body_html: "", segment_id: "", cta_label: "", cta_url: "" };

function AiWriter({ onDraft }) {
  const [b, setB] = useState({ brief: "", audience: "vendor", tone: "professional" });
  const [busy, setBusy] = useState(false);
  const go = async () => {
    if (b.brief.trim().length < 10) return toast.error("Describe the email in a sentence or two");
    setBusy(true);
    try { onDraft(await marketingApi.aiCopy(b)); toast.success("Draft written — edit it as you like"); }
    catch (e) { showApiError(e); } finally { setBusy(false); }
  };
  return (
    <div className="border border-brand-gold/60 bg-amber-50/40 p-3 space-y-2" data-testid="mkt-ai">
      <div className="pmc-label">Write it with AI</div>
      <textarea className={inp} rows={3} placeholder="e.g. Invite UK roofing contractors to register free and see live council tenders" value={b.brief} onChange={(e) => setB({ ...b, brief: e.target.value })} data-testid="mkt-ai-brief" />
      <div className="flex gap-2">
        <select className={inp} value={b.audience} onChange={(e) => setB({ ...b, audience: e.target.value })} data-testid="mkt-ai-audience">
          <option value="vendor">To vendors</option><option value="buyer">To buyers</option></select>
        <select className={inp} value={b.tone} onChange={(e) => setB({ ...b, tone: e.target.value })} data-testid="mkt-ai-tone">
          <option value="professional">Professional</option><option value="friendly">Friendly</option><option value="urgent">Urgent</option></select>
        <button className={sec} onClick={go} disabled={busy} data-testid="mkt-ai-go">{busy ? "Writing…" : "Write draft"}</button>
      </div>
    </div>
  );
}

function Editor({ segments, initial, onClose }) {
  const [f, setF] = useState(initial || EMPTY);
  const [testTo, setTestTo] = useState("");
  const save = async () => {
    try {
      if (f.id) { await marketingApi.updateCampaign(f.id, f); return f.id; }
      const r = await marketingApi.createCampaign(f); setF({ ...f, id: r.id }); return r.id;
    } catch (e) { showApiError(e); return null; }
  };
  const saveClose = async () => { if (await save()) { toast.success("Draft saved"); onClose(); } };
  const test = async () => {
    const id = await save(); if (!id) return;
    try { const r = await marketingApi.testCampaign(id, testTo); r.email_sent ? toast.success(`Test sent to ${testTo}`) : toast.error("Test email could not be sent"); } catch (e) { showApiError(e); }
  };
  const send = async () => {
    const seg = segments.find((s) => s.id === f.segment_id);
    if (!window.confirm(`Send "${f.subject}" to ${seg?.size ?? 0} people now? This cannot be undone.`)) return;
    const id = await save(); if (!id) return;
    try { const r = await marketingApi.sendCampaign(id); toast.success(`Sending to ${r.queued} people`); onClose(); } catch (e) { showApiError(e); }
  };
  return (
    <div className="grid gap-6 lg:grid-cols-2" data-testid="mkt-editor">
      <div className="space-y-3">
        <AiWriter onDraft={(d) => setF((x) => ({ ...x, subject: d.subject, body_html: d.body_html }))} />
        <input className={inp} placeholder="Campaign name (internal)" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="mkt-c-name" />
        <select className={inp} value={f.segment_id} onChange={(e) => setF({ ...f, segment_id: e.target.value })} data-testid="mkt-c-segment">
          <option value="">Send to which list?</option>
          {segments.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.size})</option>)}</select>
        <input className={inp} placeholder="Subject line" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} data-testid="mkt-c-subject" />
        <textarea className={inp + " font-mono"} rows={10} placeholder="Email body (HTML: <p>, <b>, <ul>, <a href>)" value={f.body_html} onChange={(e) => setF({ ...f, body_html: e.target.value })} data-testid="mkt-c-body" />
        <div className="flex gap-2">
          <input className={inp} placeholder="Button text (optional)" value={f.cta_label} onChange={(e) => setF({ ...f, cta_label: e.target.value })} data-testid="mkt-c-cta-label" />
          <input className={inp} placeholder="Button link https://…" value={f.cta_url} onChange={(e) => setF({ ...f, cta_url: e.target.value })} data-testid="mkt-c-cta-url" />
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <button className={sec} onClick={saveClose} data-testid="mkt-c-save">Save draft</button>
          <input className={inp + " !w-56"} placeholder="your@email for a test" value={testTo} onChange={(e) => setTestTo(e.target.value)} data-testid="mkt-c-test-email" />
          <button className={sec} disabled={!testTo} onClick={test} data-testid="mkt-c-test">Send test</button>
          <button className="pmc-btn pmc-btn--primary" disabled={!f.segment_id} onClick={send} data-testid="mkt-c-send">Send campaign</button>
          <button className="text-sm underline ml-auto" onClick={onClose} data-testid="mkt-c-cancel">Close</button>
        </div>
      </div>
      <div className="border border-brand-navy/15 bg-white p-5" data-testid="mkt-c-preview">
        <div className="text-xs uppercase tracking-widest text-brand-navy/50 mb-2">Preview</div>
        <div className="font-semibold mb-3">{f.subject || "Subject line"}</div>
        <div className="max-w-none text-sm leading-relaxed [&_ul]:list-disc [&_ul]:pl-5 [&_p]:mb-3 [&_a]:underline" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(f.body_html || "<p>Your email text appears here.</p>") }} />
        {f.cta_label && <div className="mt-4"><span className="inline-block px-4 py-2 bg-brand-navy text-white text-sm">{f.cta_label}</span></div>}
        <div className="mt-6 text-[11px] text-brand-navy/50">An unsubscribe link is added automatically.</div>
      </div>
    </div>
  );
}

export const CampaignsTab = () => {
  const [rows, setRows] = useState([]);
  const [segments, setSegments] = useState([]);
  const [edit, setEdit] = useState(null);
  const load = () => {
    marketingApi.campaigns().then((r) => setRows(r.items || [])).catch(showApiError);
    marketingApi.segments().then((r) => setSegments(r.items || [])).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  const del = async (id) => { try { await marketingApi.deleteCampaign(id); load(); } catch (e) { showApiError(e); } };
  if (edit) return <Editor segments={segments} initial={edit === "new" ? null : edit} onClose={() => { setEdit(null); load(); }} />;
  const pct = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : "—");
  return (
    <div className="space-y-3" data-testid="mkt-campaigns">
      <button className="pmc-btn pmc-btn--primary" onClick={() => setEdit("new")} data-testid="mkt-new-campaign">New campaign</button>
      <div className="overflow-x-auto border border-brand-navy/15 bg-white">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs uppercase tracking-widest text-brand-navy/60">
            {["Campaign", "Subject", "Status", "Sent", "Opened", "Clicked", ""].map((h) => <th key={h} className="p-2">{h}</th>)}</tr></thead>
          <tbody>{rows.map((c) => (
            <tr key={c.id} className="border-t border-brand-navy/10" data-testid={`mkt-campaign-${c.id}`}>
              <td className="p-2 font-semibold">{c.name}</td><td className="p-2">{c.subject}</td>
              <td className="p-2" data-testid={`mkt-campaign-status-${c.id}`}>{c.status}</td>
              <td className="p-2">{c.stats.sent}{c.stats.failed ? ` (${c.stats.failed} failed)` : ""}</td>
              <td className="p-2">{c.stats.opened} · {pct(c.stats.opened, c.stats.sent)}</td>
              <td className="p-2">{c.stats.clicked} · {pct(c.stats.clicked, c.stats.sent)}</td>
              <td className="p-2 space-x-3">{c.status === "draft" && <>
                <button className="underline text-xs" onClick={() => setEdit(c)} data-testid={`mkt-campaign-edit-${c.id}`}>Edit</button>
                <button className="underline text-xs text-red-700" onClick={() => del(c.id)} data-testid={`mkt-campaign-del-${c.id}`}>Delete</button></>}</td>
            </tr>))}
            {!rows.length && <tr><td colSpan={7} className="p-6 text-center text-brand-navy/60">No campaigns yet.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="text-xs text-brand-navy/50">Opens are approximate: some email apps block the tracking image.</div>
    </div>
  );
};
