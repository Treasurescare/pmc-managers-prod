import { useState } from "react";
import { toast } from "sonner";
import { growthApi } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";
import { btn, inp, useList } from "./BuyerAppsTab";

const BLANK = { name: "", summary: "", price: "", currency: "USD", price_note: "", is_active: true, order: 0 };

const ServiceForm = ({ init, onDone }) => {
  const [f, setF] = useState(init);
  const up = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const save = () => {
    const b = { ...f, price: f.price === "" || f.price === null ? null : Number(f.price), order: Number(f.order || 0), price_note: f.price_note || null };
    return (f.id ? growthApi.updateService(f.id, b) : growthApi.createService(b)).then(() => { toast.success("Service saved"); onDone(); }).catch(showApiError);
  };
  return (
    <div className="bg-white border border-brand-navy/20 p-3 mb-3 grid md:grid-cols-4 gap-2 text-xs" data-testid="service-form">
      <label className="md:col-span-2">Name<input className={inp} value={f.name} onChange={up("name")} data-testid="service-form-name" /></label>
      <label>Price (blank = on request)<input type="number" className={inp} value={f.price ?? ""} onChange={up("price")} data-testid="service-form-price" /></label>
      <label>Currency<input className={inp} maxLength={3} value={f.currency} onChange={up("currency")} data-testid="service-form-currency" /></label>
      <label className="md:col-span-4">Description<textarea rows={3} className={inp} value={f.summary} onChange={up("summary")} data-testid="service-form-summary" /></label>
      <label>Price note<input className={inp} value={f.price_note || ""} onChange={up("price_note")} placeholder="From USD 500" data-testid="service-form-note" /></label>
      <label>Order<input type="number" className={inp} value={f.order} onChange={up("order")} data-testid="service-form-order" /></label>
      <label className="flex items-center gap-2 mt-4"><input type="checkbox" checked={f.is_active} onChange={up("is_active")} data-testid="service-form-active" />Shown publicly</label>
      <div className="flex gap-2 items-end"><button className={btn} onClick={save} data-testid="service-form-save">Save</button><button className={btn} onClick={onDone} data-testid="service-form-cancel">Cancel</button></div>
    </div>);
};

const STATUSES = ["new", "assigned", "in_progress", "done", "cancelled"];
const Req = ({ r, onDone }) => {
  const [f, setF] = useState({ status: r.status, assigned_to: r.assigned_to || "", notes: r.notes || "" });
  const save = () => growthApi.updateRequest(r.id, { ...f, assigned_to: f.assigned_to || null, notes: f.notes || null }).then(() => { toast.success("Updated"); onDone(); }).catch(showApiError);
  return (
    <div className="p-3 text-sm" data-testid={`consult-req-${r.id}`}>
      <div><b>{r.service_name}</b> · {r.name} &lt;{r.email}&gt; {r.company ? `· ${r.company}` : ""} · payment {r.payment} · {String(r.created_at).slice(0, 10)}</div>
      <div className="text-xs mt-1">{r.message}{r.notice_ref ? ` · tender ${r.notice_ref}` : ""}</div>
      <div className="grid md:grid-cols-4 gap-2 mt-2 text-xs items-end">
        <select className={inp} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })} data-testid={`consult-req-status-${r.id}`}>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        <input className={inp} placeholder="Assigned to" value={f.assigned_to} onChange={(e) => setF({ ...f, assigned_to: e.target.value })} data-testid={`consult-req-assign-${r.id}`} />
        <input className={inp} placeholder="Notes" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} data-testid={`consult-req-notes-${r.id}`} />
        <button className={btn} onClick={save} data-testid={`consult-req-save-${r.id}`}>Save</button>
      </div>
    </div>);
};

export const ConsultingTab = () => {
  const [svcs, loadS] = useList(growthApi.adminServices);
  const [reqs, loadR] = useList(growthApi.adminRequests);
  const [edit, setEdit] = useState(null);
  return (
    <div data-testid="consulting-tab">
      <div className="flex justify-between mb-2"><div className="pmc-label">Services (public page: /consultancy)</div>
        <button className={btn} onClick={() => setEdit(BLANK)} data-testid="service-new-btn">New service</button></div>
      {edit && <ServiceForm init={edit} onDone={() => { setEdit(null); loadS(); }} />}
      <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10 mb-5">
        {svcs.map((s) => <div key={s.id} className="p-3 text-sm flex gap-2" data-testid={`service-row-${s.id}`}><span className="flex-1"><b>{s.name}</b> · {s.price ? `${s.currency} ${s.price}` : s.price_note || "on request"} {!s.is_active && "· hidden"}</span>
          <button className={btn} onClick={() => setEdit(s)} data-testid={`service-edit-${s.id}`}>Edit</button></div>)}
        {!svcs.length && <div className="p-3 text-sm opacity-60">No services yet.</div>}
      </div>
      <div className="pmc-label mb-2">Requests</div>
      <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10">
        {reqs.map((r) => <Req key={r.id} r={r} onDone={loadR} />)}
        {!reqs.length && <div className="p-3 text-sm opacity-60" data-testid="consult-req-empty">No requests yet.</div>}
      </div>
    </div>);
};
