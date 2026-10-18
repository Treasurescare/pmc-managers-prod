import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { mastersApi, mastersGeoApi, uploadsApi, showApiError } from "@/lib/api";
import { useListPager } from "@/components/ListPager";
import { InfoDot } from "@/components/InfoDot";

/**
 * v56 — full Company Master. Create/edit company profile
 * (country→state→city→ZIP + incorporation details) and manage company
 * documents: single-slot Incorporation Certificate / MOA / AOA, plus a
 * repeatable Licenses list. Uploads reuse the shared /uploads flow
 * (scope="company-docs"); view/download via the authenticated blob fetch.
 */

const DOC_SLOTS = [
  ["incorporation_certificate", "Incorporation Certificate"],
  ["moa", "Memorandum of Association (MOA)"],
  ["aoa", "Articles of Association (AOA)"],
];

const emptyDraft = () => ({
  name: "", code: "", country: "", state_code: "", state_name: "",
  city: "", postal_code: "", address: "", reg_number: "",
  incorporation_date: "", tax_id: "", is_active: true,
});

export default function CompaniesTab({ companies, onChange }) {
  const [countries, setCountries] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState(emptyDraft());
  const [editingId, setEditingId] = useState(null);
  const { paged, controls } = useListPager(companies || [], { testid: "company-pager" });

  useEffect(() => {
    mastersGeoApi.countries()
      .then((r) => setCountries(Array.isArray(r) ? r : []))
      .catch(() => setCountries([]));
  }, []);

  const startNew = () => { setDraft(emptyDraft()); setEditingId(null); setShowNew(true); };
  const startEdit = (c) => {
    setEditingId(c.id);
    setShowNew(false);
    setDraft({
      name: c.name || "", code: c.code || "", country: c.country || "",
      state_code: c.state_code || "", state_name: c.state_name || "",
      city: c.city || "", postal_code: c.postal_code || "", address: c.address || "",
      reg_number: c.reg_number || "", incorporation_date: (c.incorporation_date || "").slice(0, 10),
      tax_id: c.tax_id || "", is_active: c.is_active !== false,
    });
  };
  const cancel = () => { setShowNew(false); setEditingId(null); setDraft(emptyDraft()); };

  const save = async () => {
    if (!draft.name || !draft.code) return toast.error("Name and code are required");
    try {
      if (editingId) {
        await mastersApi.updateCompany(editingId, draft);
        toast.success("Company updated");
        onChange?.();
      } else {
        const created = await mastersApi.createCompany(draft);
        toast.success("Company created — scroll down to upload documents");
        setShowNew(false);
        setEditingId(created.id);
        onChange?.();
      }
    } catch (e) { showApiError(e); }
  };

  const editingCompany = (companies || []).find((c) => c.id === editingId);

  return (
    <div data-testid="companies-tab">
      <div className="flex justify-between mb-4">
        <div className="text-sm text-brand-navy/70">{(companies || []).length} companies</div>
        {!editingId && (
          <button onClick={() => (showNew ? cancel() : startNew())} data-testid="company-new-toggle"
            className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
            {showNew ? "Cancel" : "New Company"}
          </button>
        )}
      </div>

      {(showNew || editingId) && (
        <CompanyForm
          draft={draft} setDraft={setDraft} countries={countries}
          onSave={save} onCancel={cancel} isEdit={!!editingId}
        />
      )}

      {editingCompany && (
        <CompanyDocuments company={editingCompany} onChange={onChange} />
      )}

      <div className="bg-white border mt-4">
        {(companies || []).length === 0 ? (
          <div className="p-6 text-sm text-slate-500">No companies yet.</div>
        ) : paged.map((c) => (
          <div key={c.id} className="border-b p-3 text-sm flex items-center justify-between gap-3"
            data-testid={`company-row-${c.code}`}>
            <div>
              <span className="font-mono text-xs mr-3">{c.code}</span>
              <strong>{c.name}</strong>
              <span className="ml-3 text-xs text-slate-500">
                {[c.city, c.state_name, c.country].filter(Boolean).join(", ") || c.country}
              </span>
              {c.is_active === false && <span className="ml-2 text-[10px] text-red-600">inactive</span>}
            </div>
            <button onClick={() => startEdit(c)} data-testid={`company-edit-${c.code}`}
              className="text-[10px] uppercase tracking-widest px-3 py-1 bg-brand-navy text-white">
              Edit
            </button>
          </div>
        ))}
        {controls}
      </div>
    </div>
  );
}

function CompanyForm({ draft, setDraft, countries, onSave, onCancel, isEdit }) {
  const [states, setStates] = useState([]);
  const [cities, setCities] = useState([]);
  const countryObj = (countries || []).find((c) => c.code === draft.country);

  useEffect(() => {
    if (!draft.country) { setStates([]); return; }
    mastersGeoApi.states(draft.country)
      .then((r) => setStates(Array.isArray(r) ? r : []))
      .catch(() => setStates([]));
  }, [draft.country]);

  useEffect(() => {
    if (!draft.country || !draft.state_code) { setCities([]); return; }
    mastersGeoApi.cities(draft.country, draft.state_code, draft.city, 200)
      .then((r) => setCities(Array.isArray(r) ? r : []))
      .catch(() => setCities([]));
  }, [draft.country, draft.state_code, draft.city]);

  const zipPattern = countryObj?.postal_code_regex || null;
  const zipFormat = countryObj?.postal_code_format || null;
  let zipValid = true;
  if (draft.postal_code && zipPattern) {
    try { zipValid = new RegExp(zipPattern).test(draft.postal_code); } catch { zipValid = true; }
  }

  const set = (k, v) => setDraft((d) => ({ ...d, [k]: v }));

  return (
    <div className="bg-white border p-4 mb-4 grid gap-3 md:grid-cols-3" data-testid="company-form">
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        Name
        <input value={draft.name} onChange={(e) => set("name", e.target.value)}
          className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="company-name" />
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        Code<InfoDot tip="Short unique code (e.g. PMC-KZ)." />
        <input value={draft.code} onChange={(e) => set("code", e.target.value)}
          disabled={isEdit}
          className="mt-1 w-full px-3 py-2 border normal-case tracking-normal disabled:bg-slate-100"
          data-testid="company-code" />
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        Country
        <select value={draft.country}
          onChange={(e) => setDraft((d) => ({ ...d, country: e.target.value, state_code: "", state_name: "", city: "", postal_code: "" }))}
          className="mt-1 w-full px-3 py-2 border bg-white normal-case tracking-normal"
          data-testid="company-country">
          <option value="">Select…</option>
          {countries.map((c) => (
            <option key={c.code} value={c.code}>{c.code} — {c.name}</option>
          ))}
        </select>
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        State / Province
        {states.length > 0 ? (
          <select value={draft.state_code}
            onChange={(e) => {
              const st = states.find((s) => s.state_code === e.target.value);
              setDraft((d) => ({ ...d, state_code: e.target.value, state_name: st?.name || "" }));
            }}
            className="mt-1 w-full px-3 py-2 border bg-white normal-case tracking-normal"
            data-testid="company-state">
            <option value="">Select…</option>
            {states.map((s) => <option key={s.state_code} value={s.state_code}>{s.name}</option>)}
          </select>
        ) : (
          <input value={draft.state_name} onChange={(e) => set("state_name", e.target.value)}
            placeholder="State / province"
            className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="company-state-free" />
        )}
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        City
        <input list="company-city-dl" value={draft.city} onChange={(e) => set("city", e.target.value)}
          disabled={states.length > 0 && !draft.state_code}
          autoComplete="off"
          placeholder={draft.country ? (states.length === 0 || draft.state_code ? "Select or type city…" : "Pick a state first") : "Pick a country first"}
          className="mt-1 w-full px-3 py-2 border normal-case tracking-normal disabled:bg-slate-100" data-testid="company-city" />
        <datalist id="company-city-dl">
          {cities.map((c, i) => <option key={i} value={c.name} />)}
        </datalist>
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        ZIP / Postal code{zipFormat ? <span className="normal-case tracking-normal text-brand-navy/40"> ({zipFormat})</span> : null}
        <input value={draft.postal_code} onChange={(e) => set("postal_code", e.target.value)}
          className={`mt-1 w-full px-3 py-2 border normal-case tracking-normal ${!zipValid ? "border-red-400" : ""}`} data-testid="company-zip" />
        {!zipValid && (
          <span className="normal-case tracking-normal text-[10px] text-red-700" data-testid="company-zip-error">
            Doesn't match {draft.country} postal format{zipFormat ? ` (${zipFormat})` : ""}.
          </span>
        )}
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-3">
        Registered address
        <input value={draft.address} onChange={(e) => set("address", e.target.value)}
          className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="company-address" />
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        Registration / Incorporation no.
        <input value={draft.reg_number} onChange={(e) => set("reg_number", e.target.value)}
          className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="company-reg-number" />
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        Incorporation date
        <input type="date" value={draft.incorporation_date} max={new Date().toISOString().slice(0, 10)}
          onChange={(e) => set("incorporation_date", e.target.value)}
          className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="company-incorp-date" />
      </label>
      <label className="text-xs uppercase tracking-widest text-brand-navy/60">
        Tax ID
        <input value={draft.tax_id} onChange={(e) => set("tax_id", e.target.value)}
          className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="company-tax-id" />
      </label>
      <label className="text-sm flex items-center gap-2 md:col-span-3">
        <input type="checkbox" checked={draft.is_active}
          onChange={(e) => set("is_active", e.target.checked)} data-testid="company-active" />
        <span>Active</span>
      </label>
      <div className="md:col-span-3 flex gap-2">
        <button onClick={onSave} disabled={!zipValid} data-testid="company-save"
          className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white disabled:opacity-50">
          {isEdit ? "Save company" : "Create company"}
        </button>
        <button onClick={onCancel}
          className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy">
          Cancel
        </button>
      </div>
    </div>
  );
}

function CompanyDocuments({ company, onChange }) {
  const [busy, setBusy] = useState("");
  const fileRefs = useRef({});
  const licRef = useRef(null);

  const uploadDoc = async (slot, file) => {
    if (!file) return;
    setBusy(slot);
    try {
      const up = await uploadsApi.uploadFile(file, { scope: "company-docs" });
      await mastersApi.setCompanyDocument(company.id, slot, {
        key: up.key, filename: up.filename, content_type: up.content_type,
      });
      toast.success("Document uploaded");
      onChange?.();
    } catch (e) { showApiError(e); }
    finally { setBusy(""); }
  };
  const removeDoc = async (slot) => {
    setBusy(slot);
    try {
      await mastersApi.deleteCompanyDocument(company.id, slot);
      toast.success("Document removed");
      onChange?.();
    } catch (e) { showApiError(e); }
    finally { setBusy(""); }
  };
  const addLicense = async (file) => {
    if (!file) return;
    setBusy("license");
    try {
      const up = await uploadsApi.uploadFile(file, { scope: "company-docs" });
      await mastersApi.addCompanyLicense(company.id, {
        key: up.key, filename: up.filename, content_type: up.content_type, label: file.name,
      });
      toast.success("License added");
      onChange?.();
    } catch (e) { showApiError(e); }
    finally { setBusy(""); if (licRef.current) licRef.current.value = ""; }
  };
  const removeLicense = async (index) => {
    setBusy(`license-${index}`);
    try {
      await mastersApi.deleteCompanyLicense(company.id, index);
      toast.success("License removed");
      onChange?.();
    } catch (e) { showApiError(e); }
    finally { setBusy(""); }
  };

  const docs = company.documents || {};
  const licenses = company.licenses || [];

  return (
    <div className="bg-brand-pale/40 border border-brand-navy/15 p-4 mb-4 space-y-4"
      data-testid="company-documents">
      <div className="pmc-label">Company documents — {company.name}</div>

      <div className="grid gap-2 md:grid-cols-3">
        {DOC_SLOTS.map(([slot, label]) => {
          const d = docs[slot];
          return (
            <div key={slot} className="bg-white border border-brand-navy/10 p-3 text-sm"
              data-testid={`company-doc-${slot}`}>
              <div className="text-xs font-semibold text-brand-navy mb-1">{label}</div>
              {d?.key ? (
                <div className="space-y-1">
                  <div className="text-xs text-brand-navy/60 truncate" title={d.filename}>{d.filename}</div>
                  <div className="flex gap-2">
                    <button onClick={() => uploadsApi.openFile(d.key).catch(showApiError)}
                      data-testid={`company-doc-view-${slot}`}
                      className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20">View</button>
                    <button onClick={() => uploadsApi.openInNewTab(d.key, { download: true, filename: d.filename }).catch(showApiError)}
                      data-testid={`company-doc-download-${slot}`}
                      className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20">Download</button>
                    <button onClick={() => removeDoc(slot)} disabled={busy === slot}
                      data-testid={`company-doc-remove-${slot}`}
                      className="text-[10px] uppercase tracking-widest px-2 py-1 text-red-700 border border-red-200">Remove</button>
                  </div>
                </div>
              ) : (
                <>
                  <input type="file" ref={(el) => (fileRefs.current[slot] = el)}
                    onChange={(e) => uploadDoc(slot, e.target.files?.[0])}
                    className="hidden" data-testid={`company-doc-input-${slot}`} />
                  <button onClick={() => fileRefs.current[slot]?.click()} disabled={busy === slot}
                    data-testid={`company-doc-upload-${slot}`}
                    className="text-[10px] uppercase tracking-widest px-3 py-1 bg-brand-navy text-white disabled:opacity-50">
                    {busy === slot ? "Uploading…" : "Upload"}
                  </button>
                </>
              )}
            </div>
          );
        })}
      </div>

      <div className="bg-white border border-brand-navy/10 p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs font-semibold text-brand-navy">Licenses ({licenses.length})</div>
          <input type="file" ref={licRef} onChange={(e) => addLicense(e.target.files?.[0])}
            className="hidden" data-testid="company-license-input" />
          <button onClick={() => licRef.current?.click()} disabled={busy === "license"}
            data-testid="company-license-add"
            className="text-[10px] uppercase tracking-widest px-3 py-1 bg-brand-navy text-white disabled:opacity-50">
            {busy === "license" ? "Uploading…" : "Add license"}
          </button>
        </div>
        {licenses.length === 0 ? (
          <div className="text-xs text-brand-navy/50">No licenses uploaded.</div>
        ) : licenses.map((l, i) => (
          <div key={i} className="flex items-center justify-between gap-2 text-sm py-1 border-b border-brand-navy/5"
            data-testid={`company-license-row-${i}`}>
            <span className="truncate" title={l.filename}>{l.label || l.filename}</span>
            <div className="flex gap-2 shrink-0">
              <button onClick={() => uploadsApi.openFile(l.key).catch(showApiError)}
                data-testid={`company-license-view-${i}`}
                className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20">View</button>
              <button onClick={() => uploadsApi.openInNewTab(l.key, { download: true, filename: l.filename }).catch(showApiError)}
                className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20">Download</button>
              <button onClick={() => removeLicense(i)} disabled={busy === `license-${i}`}
                data-testid={`company-license-remove-${i}`}
                className="text-[10px] uppercase tracking-widest px-2 py-1 text-red-700 border border-red-200">Remove</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
