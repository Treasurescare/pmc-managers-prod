import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { CURRENCIES, TENDER_CATEGORY_FLAT, COUNTRIES } from "@/data/countries";
import { Upload, X, ShieldAlert } from "lucide-react";

export default function CreateTender() {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    category: TENDER_CATEGORY_FLAT[0],
    budget_currency: "USD",
    budget_amount: "",
    submission_deadline: "",
    delivery_location: "",
    delivery_country: "",
    required_licenses: [],
    eligibility_criteria: "",
    attachments: [],
  });
  const [uploading, setUploading] = useState(false);
  const [kzMap, setKzMap] = useState({});
  const [kzLicenses, setKzLicenses] = useState([]);
  useEffect(() => {
    api.get("/reference/kz-licenses").then(({ data }) => {
      setKzMap(data.category_map || {});
      setKzLicenses(data.licenses || []);
    }).catch(() => {});
  }, []);
  const set = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.value }));

  const suggestedKz = (form.delivery_country === "KZ") ? (kzMap[form.category] || []) : [];

  const toggleLicense = (l) => setForm((s) => ({
    ...s, required_licenses: s.required_licenses.includes(l) ? s.required_licenses.filter((x) => x !== l) : [...s.required_licenses, l],
  }));

  const onUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    try {
      const uploaded = [];
      for (const f of files) {
        const fd = new FormData(); fd.append("file", f);
        const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
        uploaded.push(data);
      }
      setForm((s) => ({ ...s, attachments: [...s.attachments, ...uploaded] }));
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setUploading(false); e.target.value = ""; }
  };

  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      const payload = {
        ...form,
        budget_amount: form.budget_amount ? Number(form.budget_amount) : null,
        submission_deadline: new Date(form.submission_deadline).toISOString(),
      };
      const { data } = await api.post("/tenders", payload);
      toast.success("Tender published");
      nav(`/tenders/${data.id}`);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const minDate = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 16);

  return (
    <DashboardLayout title="Publish a tender" subtitle="Define scope, budget, deadline and evaluation criteria.">
      <form onSubmit={submit} className="max-w-3xl border p-6 md:p-10 space-y-6">
        <div>
          <label className="pmc-label block mb-2">Title</label>
          <input data-testid="ct-title" required value={form.title} onChange={set("title")}
            className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white" />
        </div>
        <div>
          <label className="pmc-label block mb-2">Description / scope of work</label>
          <textarea data-testid="ct-description" required value={form.description} onChange={set("description")}
            rows={5} className="w-full px-4 py-3 border border-input focus:border-primary focus:outline-none bg-white" />
        </div>
        <div className="grid md:grid-cols-2 gap-5">
          <div>
            <label className="pmc-label block mb-2">Category</label>
            <select data-testid="ct-category" value={form.category} onChange={set("category")} className="w-full h-12 px-4 border border-input bg-white focus:border-primary focus:outline-none">
              {TENDER_CATEGORY_FLAT.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="pmc-label block mb-2">Submission deadline</label>
            <input data-testid="ct-deadline" type="datetime-local" required min={minDate} value={form.submission_deadline} onChange={set("submission_deadline")}
              className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white" />
          </div>
          <div>
            <label className="pmc-label block mb-2">Budget currency</label>
            <select data-testid="ct-currency" value={form.budget_currency} onChange={set("budget_currency")} className="w-full h-12 px-4 border border-input bg-white focus:border-primary focus:outline-none">
              {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="pmc-label block mb-2">Budget amount <span className="text-muted-foreground normal-case tracking-normal ml-2">(optional)</span></label>
            <input data-testid="ct-budget" type="number" min="0" value={form.budget_amount} onChange={set("budget_amount")}
              className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white" />
          </div>
        </div>
        <div>
          <label className="pmc-label block mb-2">Delivery location <span className="text-muted-foreground normal-case tracking-normal ml-2">(optional)</span></label>
          <input data-testid="ct-location" value={form.delivery_location} onChange={set("delivery_location")}
            className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white" />
        </div>
        <div>
          <label className="pmc-label block mb-2">Delivery country</label>
          <select data-testid="ct-delivery-country" value={form.delivery_country} onChange={set("delivery_country")}
            className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white">
            <option value="">Any / not specified</option>
            {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
        </div>

        {form.delivery_country === "KZ" && (
          <div className="border border-l-4 border-primary bg-primary/5 p-5" data-testid="ct-kz-licenses">
            <div className="flex items-center gap-2 pmc-label text-primary">
              <ShieldAlert className="h-4 w-4" /> Kazakhstan license gate
            </div>
            <div className="text-sm mt-2 mb-4">Only vendors holding these Kazakhstani licenses will be able to bid.</div>
            {suggestedKz.length > 0 && (
              <div className="text-xs mb-3 text-muted-foreground">Recommended for <span className="font-mono">{form.category}</span>: {suggestedKz.join(", ")}</div>
            )}
            <div className="flex flex-wrap gap-2">
              {kzLicenses.map((l) => {
                const on = form.required_licenses.includes(l);
                return (
                  <button key={l} type="button" onClick={() => toggleLicense(l)}
                    data-testid={`ct-lic-${l.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`}
                    className={`px-3 py-2 text-xs border transition-colors ${on ? "bg-primary text-white border-primary" : "border-input hover:border-foreground"}`}>
                    {l}
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <div>
          <label className="pmc-label block mb-2">Eligibility criteria <span className="text-muted-foreground normal-case tracking-normal ml-2">(optional)</span></label>
          <textarea data-testid="ct-eligibility" value={form.eligibility_criteria} onChange={set("eligibility_criteria")}
            rows={3} className="w-full px-4 py-3 border border-input focus:border-primary focus:outline-none bg-white" />
        </div>

        <div>
          <label className="pmc-label block mb-2">Attachments</label>
          <label className="block border border-dashed border-input hover:border-primary p-6 text-center cursor-pointer">
            <input data-testid="ct-file-input" type="file" multiple onChange={onUpload} className="hidden" />
            <Upload className="mx-auto h-5 w-5 text-muted-foreground mb-2" />
            <div className="text-sm">{uploading ? "Uploading..." : "Attach spec sheets, BoQ, drawings"}</div>
          </label>
          {form.attachments.length > 0 && (
            <ul className="border mt-3">
              {form.attachments.map((d, i) => (
                <li key={i} className="flex justify-between items-center px-4 py-2 border-b last:border-b-0 text-sm">
                  <span>{d.name} <span className="font-mono text-xs text-muted-foreground">· {(d.size / 1024).toFixed(1)} KB</span></span>
                  <button type="button" onClick={() => setForm((s) => ({ ...s, attachments: s.attachments.filter((_, idx) => idx !== i) }))}>
                    <X className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex justify-end pt-4 border-t">
          <button data-testid="ct-submit" type="submit" disabled={busy} className="bg-primary text-white px-6 py-3 text-sm hover:-translate-y-0.5 transition-transform disabled:opacity-60">
            {busy ? "Publishing..." : "Publish tender"}
          </button>
        </div>
      </form>
    </DashboardLayout>
  );
}
