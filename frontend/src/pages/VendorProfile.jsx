import { useEffect, useState } from "react";
import { COUNTRIES, BUSINESS_CATEGORIES, CURRENCIES, LEGAL_ENTITY_TYPES, DECLARATIONS, REQUIRED_DOCUMENTS } from "@/data/countries";
import DashboardLayout from "@/components/app/DashboardLayout";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Upload, X, Check, Plus, Trash2 } from "lucide-react";
import StatusBadge from "@/components/app/StatusBadge";

const STEPS = [
  { id: 1, label: "Identity & Basics", section: "A" },
  { id: 2, label: "Contact & Signatory", section: "A" },
  { id: 3, label: "Bank & Financials", section: "A" },
  { id: 4, label: "Business Capability", section: "B" },
  { id: 5, label: "KYC Documents", section: "C" },
  { id: 6, label: "Declarations & Sign", section: "D/E" },
];

const empty = {
  company_name: "",
  trade_name: "",
  registered_address: "",
  mailing_address: "",
  country: "",
  country_id_label: "",
  registration_number: "",
  incorporation_date: "",
  tax_id: "",
  legal_entity_type: "LLP / LLC",
  website: "",
  employees_count: "",
  contact_name: "",
  contact_title: "",
  contact_office_phone: "",
  contact_mobile: "",
  contact_email: "",
  signatory_name: "",
  signatory_title: "",
  signatory_contact: "",
  bank_name: "",
  bank_branch: "",
  bank_account_number: "",
  bank_swift: "",
  bank_address: "",
  primary_sector: "",
  business_description: "",
  operating_regions: [],
  business_categories: [],
  turnover_year1: "",
  turnover_year2: "",
  turnover_year3: "",
  turnover_currency: "USD",
  previous_projects: [],
  references: [],
  iso_certifications: "",
  licenses_permits: "",
  insurance_details: "",
  litigation_history: "",
  kz_licenses: [],
  documents: [],
  decl_conflict_of_interest: false,
  decl_integrity: false,
  decl_accuracy: false,
  decl_data_consent: false,
  decl_fee: false,
  decl_notification: false,
  signature_name: "",
  signature_title: "",
  signature_date: "",
};

const KZ_LICENSE_TYPES = [
  "Construction (1st category)",
  "Electrical installation",
  "Mechanical works",
  "Plumbing & firefighting",
  "Medical gas installation",
  "HSE compliance",
];

export default function VendorProfile() {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(empty);
  const [status, setStatus] = useState("pending");
  const [feePaid, setFeePaid] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [regionInput, setRegionInput] = useState("");

  useEffect(() => {
    api.get("/vendor/profile").then(({ data }) => {
      setStatus(data.vendor_status || "pending");
      setFeePaid(!!data.registration_fee_paid);
      if (data.vendor_profile) setForm({ ...empty, ...data.vendor_profile });
    }).catch((e) => console.warn("Failed to load vendor profile", e));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleKzLicense = (l) => setForm((s) => ({
    ...s, kz_licenses: s.kz_licenses.includes(l) ? s.kz_licenses.filter((x) => x !== l) : [...s.kz_licenses, l],
  }));

  const set = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target?.value ?? e }));
  const setBool = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.checked }));

  const onCountryChange = (e) => {
    const c = COUNTRIES.find((x) => x.code === e.target.value);
    setForm((s) => ({ ...s, country: c?.code || "", country_id_label: c?.idLabel || "" }));
  };

  const toggleCategory = (cat) =>
    setForm((s) => ({ ...s, business_categories: s.business_categories.includes(cat) ? s.business_categories.filter((c) => c !== cat) : [...s.business_categories, cat] }));

  const addRegion = () => {
    const v = regionInput.trim();
    if (!v) return;
    setForm((s) => ({ ...s, operating_regions: [...s.operating_regions, v] }));
    setRegionInput("");
  };
  const removeRegion = (i) => setForm((s) => ({ ...s, operating_regions: s.operating_regions.filter((_, idx) => idx !== i) }));

  const addProject = () => setForm((s) => ({ ...s, previous_projects: [...s.previous_projects, { name: "", client: "", value: "", currency: "USD", period: "" }] }));
  const updateProject = (i, k, v) => setForm((s) => ({ ...s, previous_projects: s.previous_projects.map((p, idx) => (idx === i ? { ...p, [k]: v } : p)) }));
  const removeProject = (i) => setForm((s) => ({ ...s, previous_projects: s.previous_projects.filter((_, idx) => idx !== i) }));

  const addReference = () => setForm((s) => ({ ...s, references: [...s.references, { name: "", position: "", company: "", phone: "", email: "" }] }));
  const updateReference = (i, k, v) => setForm((s) => ({ ...s, references: s.references.map((p, idx) => (idx === i ? { ...p, [k]: v } : p)) }));
  const removeReference = (i) => setForm((s) => ({ ...s, references: s.references.filter((_, idx) => idx !== i) }));

  const onUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    try {
      const uploaded = [];
      for (const f of files) {
        const fd = new FormData(); fd.append("file", f);
        const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
        uploaded.push({ ...data, category: "" });
      }
      setForm((s) => ({ ...s, documents: [...s.documents, ...uploaded] }));
      toast.success(`${uploaded.length} file(s) uploaded`);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setUploading(false); e.target.value = ""; }
  };
  const setDocCategory = (i, cat) => setForm((s) => ({ ...s, documents: s.documents.map((d, idx) => (idx === i ? { ...d, category: cat } : d)) }));
  const removeDoc = (i) => setForm((s) => ({ ...s, documents: s.documents.filter((_, idx) => idx !== i) }));

  const allDeclarations = DECLARATIONS.every((d) => form[d.key]);

  const submit = async () => {
    if (!allDeclarations) { toast.error("Please accept all declarations before submitting."); return; }
    if (!form.signature_name || !form.signature_title || !form.signature_date) { toast.error("Please complete the signature block."); return; }
    setBusy(true);
    try {
      const payload = {
        ...form,
        employees_count: form.employees_count ? Number(form.employees_count) : null,
        turnover_year1: form.turnover_year1 ? Number(form.turnover_year1) : null,
        turnover_year2: form.turnover_year2 ? Number(form.turnover_year2) : null,
        turnover_year3: form.turnover_year3 ? Number(form.turnover_year3) : null,
      };
      await api.post("/vendor/profile", payload);
      toast.success("Profile submitted for review");
      setStatus("pending");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <DashboardLayout
      title="Pre-Tender Registration Form"
      subtitle="Expression of interest only · Submission does not guarantee bidding eligibility."
      actions={<StatusBadge status={status} testid="vendor-profile-status" />}
    >
      <div className="mb-6 border border-l-4 border-primary bg-primary/5 p-4 text-sm">
        <strong>Instructions to Applicants / Suppliers.</strong>{" "}
        Only fully completed registration forms (with all required attachments) are accepted.
        All information must be true, accurate, and verifiable. After approval you will receive
        access to the tendering portal. A non-refundable registration fee is payable per PMC instructions.
      </div>

      {!feePaid && (
        <div data-testid="fee-banner" className="mb-6 border border-l-4 border-warning bg-warning/10 p-4 text-sm flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="pmc-label text-warning">Fee required</div>
            <div className="mt-1">Your registration fee (USD 100, one-time) must be paid before your profile can be submitted for review.</div>
          </div>
          <a data-testid="fee-banner-cta" href="/vendor/payment" className="bg-primary text-white px-4 py-2 text-sm inline-flex items-center gap-2">Pay registration fee</a>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-8">
        <ol className="space-y-0 bg-white border border-brand-navy/10" data-testid="vendor-stepper">
          {STEPS.map((s) => {
            const isActive = step === s.id;
            const isPast = step > s.id;
            return (
              <li key={s.id}>
                <button
                  data-testid={`vp-step-${s.id}`}
                  onClick={() => setStep(s.id)}
                  className={`w-full text-left flex items-center gap-4 px-5 py-4 border-b border-brand-navy/10 last:border-b-0 transition-all relative ${
                    isActive ? "bg-brand-pale text-brand-navy" : "hover:bg-brand-pale/50 text-brand-navy/60"
                  }`}
                >
                  {isActive && <span className="absolute left-0 top-0 bottom-0 w-1 bg-brand-navy-soft" />}
                  <span className={`h-8 w-8 flex items-center justify-center border font-mono text-[0.6875rem] shrink-0 ${
                    isPast ? "bg-brand-navy-soft border-brand-navy-soft text-white"
                    : isActive ? "border-brand-navy-soft text-brand-navy-soft bg-white"
                    : "border-brand-navy/20 text-brand-navy/50"
                  }`}>
                    {isPast ? "✓" : `0${s.id}`}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm ${isActive ? "font-semibold" : "font-medium"}`}>{s.label}</div>
                    <div className="pmc-label mt-0.5">Section {s.section}</div>
                  </div>
                </button>
              </li>
            );
          })}
        </ol>

        <div className="min-w-0">
          <div className="border border-brand-navy/10 bg-white p-6 md:p-10 space-y-6">
            {step === 1 && (
              <>
                <Head n="01" title="Identity & basic information" caption="Section A" />
                <Field label="Legal / Company name (in full)" required value={form.company_name} onChange={set("company_name")} testid="vp-company_name" hint="As per company registration certificate" />
                <Field label="Trade / Doing Business As name" optional value={form.trade_name} onChange={set("trade_name")} testid="vp-trade_name" />
                <TextArea label="Registered address (legal)" required rows={2} value={form.registered_address} onChange={set("registered_address")} testid="vp-registered_address" hint="Street, city, region, postal code, country" />
                <TextArea label="Mailing / correspondence address" optional rows={2} value={form.mailing_address} onChange={set("mailing_address")} testid="vp-mailing_address" />
                <div className="grid md:grid-cols-2 gap-5">
                  <div>
                    <label className="pmc-label block mb-2">Country of incorporation / registration<Req/></label>
                    <select data-testid="vp-country" value={form.country} onChange={onCountryChange} className="w-full h-12 px-4 border border-input bg-white">
                      <option value="">Select country</option>
                      {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
                    </select>
                  </div>
                  <Field label={form.country_id_label || "Company registration number / Business ID"} required value={form.registration_number} onChange={set("registration_number")} testid="vp-registration_number" hint={form.country_id_label ? `Enter your ${form.country_id_label}` : ""} />
                  <Field label="Date of incorporation" type="date" required value={form.incorporation_date} onChange={set("incorporation_date")} testid="vp-incorporation_date" />
                  <Field label="TIN / VAT number" required value={form.tax_id} onChange={set("tax_id")} testid="vp-tax_id" />
                  <Select label="Company type / legal form" value={form.legal_entity_type} onChange={set("legal_entity_type")} testid="vp-legal_entity_type" options={LEGAL_ENTITY_TYPES} />
                  <Field label="Number of full-time employees" required type="number" value={form.employees_count} onChange={set("employees_count")} testid="vp-employees_count" />
                  <Field label="Website / URL" optional value={form.website} onChange={set("website")} testid="vp-website" placeholder="https://" />
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <Head n="02" title="Primary contact & authorized signatory" caption="Section A" />
                <div className="pmc-label">Primary contact person</div>
                <div className="grid md:grid-cols-2 gap-5">
                  <Field label="Full name" required value={form.contact_name} onChange={set("contact_name")} testid="vp-contact_name" />
                  <Field label="Job title / position" required value={form.contact_title} onChange={set("contact_title")} testid="vp-contact_title" />
                  <Field label="Office phone" required value={form.contact_office_phone} onChange={set("contact_office_phone")} testid="vp-contact_office_phone" hint="Include country & area code" />
                  <Field label="Mobile / cell phone" optional value={form.contact_mobile} onChange={set("contact_mobile")} testid="vp-contact_mobile" />
                  <Field label="Email (for correspondence)" required type="email" value={form.contact_email} onChange={set("contact_email")} testid="vp-contact_email" />
                </div>

                <div className="pmc-label mt-6">Authorized signatory (for contracts)</div>
                <div className="grid md:grid-cols-2 gap-5">
                  <Field label="Full name" required value={form.signatory_name} onChange={set("signatory_name")} testid="vp-signatory_name" />
                  <Field label="Position / title" required value={form.signatory_title} onChange={set("signatory_title")} testid="vp-signatory_title" />
                  <Field label="Signatory contact (email / phone)" optional value={form.signatory_contact} onChange={set("signatory_contact")} testid="vp-signatory_contact" />
                </div>
              </>
            )}

            {step === 3 && (
              <>
                <Head n="03" title="Bank & financial details" caption="Section A" />
                <div className="grid md:grid-cols-2 gap-5">
                  <Field label="Bank name" required value={form.bank_name} onChange={set("bank_name")} testid="vp-bank_name" />
                  <Field label="Branch" optional value={form.bank_branch} onChange={set("bank_branch")} testid="vp-bank_branch" />
                  <Field label="Account number / IBAN" required value={form.bank_account_number} onChange={set("bank_account_number")} testid="vp-bank_account_number" />
                  <Field label="SWIFT / BIC" required value={form.bank_swift} onChange={set("bank_swift")} testid="vp-bank_swift" />
                </div>
                <TextArea label="Bank address" optional rows={2} value={form.bank_address} onChange={set("bank_address")} testid="vp-bank_address" />

                <div className="pmc-label mt-6">Yearly turnover (last 3 years)</div>
                <div className="grid md:grid-cols-4 gap-5">
                  <Select label="Currency" value={form.turnover_currency} onChange={set("turnover_currency")} testid="vp-turnover_currency" options={CURRENCIES} />
                  <Field label="Year 1" type="number" value={form.turnover_year1} onChange={set("turnover_year1")} testid="vp-turnover_year1" />
                  <Field label="Year 2" type="number" value={form.turnover_year2} onChange={set("turnover_year2")} testid="vp-turnover_year2" />
                  <Field label="Year 3" type="number" value={form.turnover_year3} onChange={set("turnover_year3")} testid="vp-turnover_year3" />
                </div>
                <p className="text-xs text-muted-foreground">Attach audited financials in Section C (Documents).</p>
              </>
            )}

            {step === 4 && (
              <>
                <Head n="04" title="Business profile & capability" caption="Section B" />
                <Field label="Primary business / sector / industry" required value={form.primary_sector} onChange={set("primary_sector")} testid="vp-primary_sector" hint="e.g. medical equipment, pharmaceuticals, construction" />
                <TextArea label="Description of goods / works / services you supply" required rows={3} value={form.business_description} onChange={set("business_description")} testid="vp-business_description" />

                <div>
                  <label className="pmc-label block mb-2">Regions / countries where you operate<Req/></label>
                  <div className="flex gap-2">
                    <input data-testid="vp-region-input" value={regionInput} onChange={(e) => setRegionInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addRegion())}
                      placeholder="Add a country/region and press Enter"
                      className="flex-1 h-11 px-3 border border-input bg-white focus:border-primary focus:outline-none" />
                    <button type="button" data-testid="vp-region-add" onClick={addRegion} className="px-4 border border-foreground text-sm hover:bg-foreground hover:text-white transition-colors">Add</button>
                  </div>
                  {form.operating_regions.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {form.operating_regions.map((r, i) => (
                        <span key={i} data-testid={`vp-region-${i}`} className="inline-flex items-center gap-2 border border-input bg-muted/50 px-3 py-1 text-xs">
                          {r}<button type="button" onClick={() => removeRegion(i)}><X className="h-3 w-3" /></button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <label className="pmc-label block mb-2">Business categories<Req/></label>
                  <div className="flex flex-wrap gap-2">
                    {BUSINESS_CATEGORIES.map((c) => {
                      const on = form.business_categories.includes(c);
                      return (
                        <button
                          key={c} type="button" onClick={() => toggleCategory(c)}
                          data-testid={`vp-cat-${c.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`}
                          className={`px-3 py-2 text-xs border transition-colors ${on ? "bg-primary text-white border-primary" : "border-input hover:border-foreground"}`}
                        >
                          {on && <Check className="inline h-3 w-3 mr-1" />} {c}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Previous projects */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="pmc-label">Previous experience — major projects (up to 5)</label>
                    <button type="button" data-testid="vp-add-project" onClick={addProject} className="text-xs inline-flex items-center gap-1 border px-3 py-1"><Plus className="h-3 w-3" /> Add</button>
                  </div>
                  {form.previous_projects.length === 0 && <div className="text-sm text-muted-foreground border border-dashed p-4">No projects added.</div>}
                  {form.previous_projects.map((p, i) => (
                    <div key={i} className="border p-4 mb-3" data-testid={`vp-project-${i}`}>
                      <div className="flex justify-between items-center mb-3">
                        <div className="pmc-label">Project #{i + 1}</div>
                        <button type="button" onClick={() => removeProject(i)}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></button>
                      </div>
                      <div className="grid md:grid-cols-2 gap-3">
                        <MiniField label="Project name" value={p.name} onChange={(v) => updateProject(i, "name", v)} testid={`vp-project-${i}-name`} />
                        <MiniField label="Client / owner" value={p.client} onChange={(v) => updateProject(i, "client", v)} testid={`vp-project-${i}-client`} />
                        <MiniField label="Contract value" value={p.value} onChange={(v) => updateProject(i, "value", v)} testid={`vp-project-${i}-value`} />
                        <MiniField label="Currency" value={p.currency} onChange={(v) => updateProject(i, "currency", v)} testid={`vp-project-${i}-currency`} />
                        <MiniField label="Period (year(s))" value={p.period} onChange={(v) => updateProject(i, "period", v)} testid={`vp-project-${i}-period`} />
                      </div>
                    </div>
                  ))}
                </div>

                {/* References */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="pmc-label">References / clients (for verification)</label>
                    <button type="button" data-testid="vp-add-reference" onClick={addReference} className="text-xs inline-flex items-center gap-1 border px-3 py-1"><Plus className="h-3 w-3" /> Add</button>
                  </div>
                  {form.references.length === 0 && <div className="text-sm text-muted-foreground border border-dashed p-4">No references added.</div>}
                  {form.references.map((r, i) => (
                    <div key={i} className="border p-4 mb-3" data-testid={`vp-reference-${i}`}>
                      <div className="flex justify-between items-center mb-3">
                        <div className="pmc-label">Reference #{i + 1}</div>
                        <button type="button" onClick={() => removeReference(i)}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></button>
                      </div>
                      <div className="grid md:grid-cols-2 gap-3">
                        <MiniField label="Contact name" value={r.name} onChange={(v) => updateReference(i, "name", v)} testid={`vp-ref-${i}-name`} />
                        <MiniField label="Position" value={r.position} onChange={(v) => updateReference(i, "position", v)} testid={`vp-ref-${i}-position`} />
                        <MiniField label="Company" value={r.company} onChange={(v) => updateReference(i, "company", v)} testid={`vp-ref-${i}-company`} />
                        <MiniField label="Phone" value={r.phone} onChange={(v) => updateReference(i, "phone", v)} testid={`vp-ref-${i}-phone`} />
                        <MiniField label="Email" value={r.email} onChange={(v) => updateReference(i, "email", v)} testid={`vp-ref-${i}-email`} />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="grid md:grid-cols-2 gap-5">
                  <TextArea label="ISO / quality certifications & standards" optional rows={2} value={form.iso_certifications} onChange={set("iso_certifications")} testid="vp-iso" hint="e.g. ISO 9001, 13485 — attach in documents" />
                  <TextArea label="Licenses / permits / regulatory authorizations" optional rows={2} value={form.licenses_permits} onChange={set("licenses_permits")} testid="vp-licenses" />
                  <TextArea label="Insurance / liability coverage" optional rows={2} value={form.insurance_details} onChange={set("insurance_details")} testid="vp-insurance" />
                  <TextArea label="Litigation / disputes / bankruptcy history (past 5 years)" required rows={2} value={form.litigation_history} onChange={set("litigation_history")} testid="vp-litigation" hint="Write 'None' if not applicable" />
                </div>

                {form.country === "KZ" && (
                  <div className="border border-l-4 border-primary bg-primary/5 p-5" data-testid="vp-kz-license-block">
                    <div className="pmc-label text-primary mb-2">Kazakhstan-specific licenses</div>
                    <h4 className="font-serif text-xl mb-2">Select all licenses you currently hold</h4>
                    <p className="text-sm text-muted-foreground mb-4">These map to specialised tender categories (medical gas, electrical, plumbing, etc.). Tenders requiring these will only accept bids from vendors holding the matching licence.</p>
                    <div className="flex flex-wrap gap-2">
                      {KZ_LICENSE_TYPES.map((l) => {
                        const on = form.kz_licenses.includes(l);
                        return (
                          <button
                            key={l} type="button" onClick={() => toggleKzLicense(l)}
                            data-testid={`vp-kzlic-${l.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`}
                            className={`px-3 py-2 text-xs border transition-colors ${on ? "bg-primary text-white border-primary" : "border-input hover:border-foreground"}`}
                          >
                            {on && <Check className="inline h-3 w-3 mr-1" />} {l}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            )}

            {step === 5 && (
              <>
                <Head n="05" title="KYC documents to attach" caption="Section C" />
                <p className="text-sm text-muted-foreground">Please attach the following documents (PDF, DOC, image). Max 5 MB each. Tag each file with its category.</p>
                <ul className="border">
                  {REQUIRED_DOCUMENTS.map((d, i) => (
                    <li key={i} className="px-4 py-2.5 border-b last:border-b-0 text-sm flex items-center gap-3">
                      <span className="font-mono text-xs text-muted-foreground">C{String(i + 1).padStart(2, "0")}</span>
                      <span>{d}</span>
                    </li>
                  ))}
                </ul>
                <label className="block border border-dashed border-input hover:border-primary transition-colors p-8 text-center cursor-pointer">
                  <input data-testid="vp-file-input" type="file" multiple onChange={onUpload} className="hidden" accept="image/*,.pdf,.doc,.docx" />
                  <Upload className="mx-auto h-6 w-6 text-muted-foreground mb-3" />
                  <div className="text-sm">{uploading ? "Uploading..." : "Click to upload documents"}</div>
                  <div className="text-xs text-muted-foreground mt-2">PDF, DOC, PNG, JPG · up to 5 MB each</div>
                </label>
                {form.documents.length > 0 && (
                  <ul data-testid="vp-doc-list" className="border">
                    {form.documents.map((d, i) => (
                      <li key={i} className="flex items-center gap-3 px-4 py-3 border-b last:border-b-0 text-sm">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{d.name}</div>
                          <div className="text-xs text-muted-foreground font-mono">{d.type} · {(d.size / 1024).toFixed(1)} KB</div>
                        </div>
                        <select data-testid={`vp-doc-cat-${i}`} value={d.category || ""} onChange={(e) => setDocCategory(i, e.target.value)} className="text-xs border border-input h-9 px-2 bg-white max-w-[240px]">
                          <option value="">— Tag category —</option>
                          {REQUIRED_DOCUMENTS.map((r) => <option key={r} value={r}>{r}</option>)}
                        </select>
                        <button onClick={() => removeDoc(i)} className="text-muted-foreground hover:text-destructive" data-testid={`vp-doc-remove-${i}`}>
                          <X className="h-4 w-4" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}

            {step === 6 && (
              <>
                <Head n="06" title="Declarations & signature" caption="Sections D & E" />
                <div className="space-y-4">
                  {DECLARATIONS.map((d) => (
                    <label key={d.key} className={`flex gap-4 border p-4 cursor-pointer transition-colors ${form[d.key] ? "border-primary bg-primary/5" : "hover:border-foreground"}`}>
                      <input data-testid={`vp-${d.key}`} type="checkbox" checked={!!form[d.key]} onChange={setBool(d.key)}
                        className="mt-1 h-4 w-4 accent-[hsl(var(--primary))]" />
                      <div>
                        <div className="font-serif text-lg">{d.heading}</div>
                        <div className="text-sm text-muted-foreground mt-1">{d.body}</div>
                      </div>
                    </label>
                  ))}
                </div>

                <div className="border-t pt-6 mt-4">
                  <div className="pmc-label mb-3">Section E — Signature</div>
                  <div className="grid md:grid-cols-3 gap-5">
                    <Field label="Name of authorized signatory" required value={form.signature_name} onChange={set("signature_name")} testid="vp-signature_name" />
                    <Field label="Position / title" required value={form.signature_title} onChange={set("signature_title")} testid="vp-signature_title" />
                    <Field label="Date" type="date" required value={form.signature_date} onChange={set("signature_date")} testid="vp-signature_date" />
                  </div>
                  <p className="text-xs text-muted-foreground mt-3">By submitting this form electronically, you consent to it being treated as your legal signature. A stamped copy may be uploaded in Section C.</p>
                </div>
              </>
            )}

            <div className="flex items-center justify-between border-t pt-6 mt-4">
              <button data-testid="vp-back" disabled={step === 1} onClick={() => setStep((s) => Math.max(1, s - 1))} className="text-sm px-4 py-2 border border-input disabled:opacity-40">Back</button>
              {step < STEPS.length ? (
                <button data-testid="vp-next" onClick={() => setStep((s) => Math.min(STEPS.length, s + 1))} className="text-sm px-5 py-2 bg-foreground text-white hover:-translate-y-0.5 transition-transform">Next step</button>
              ) : (
                <button data-testid="vp-submit" onClick={submit} disabled={busy} className="text-sm px-5 py-2 bg-primary text-white hover:-translate-y-0.5 transition-transform disabled:opacity-60">
                  {busy ? "Submitting..." : "Submit for review"}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

function Head({ n, title, caption }) {
  return (
    <div className="border-b pb-4 mb-2">
      <div className="pmc-label mb-1">{caption} · Step {n}</div>
      <h2 className="font-serif text-2xl tracking-tight">{title}</h2>
    </div>
  );
}
function Req() { return <span className="text-destructive ml-1">*</span>; }

function Field({ label, value, onChange, testid, optional, required, hint, type = "text", placeholder }) {
  return (
    <div>
      <label className="pmc-label block mb-2">
        {label}
        {required && <Req />}
        {optional && <span className="normal-case tracking-normal text-muted-foreground/70 ml-2">(optional)</span>}
      </label>
      <input data-testid={testid} type={type} value={value || ""} onChange={onChange} placeholder={placeholder}
        className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white" />
      {hint && <p className="text-xs text-muted-foreground mt-1.5">{hint}</p>}
    </div>
  );
}
function TextArea({ label, value, onChange, testid, optional, required, hint, rows = 3 }) {
  return (
    <div>
      <label className="pmc-label block mb-2">{label}{required && <Req />}{optional && <span className="normal-case tracking-normal text-muted-foreground/70 ml-2">(optional)</span>}</label>
      <textarea data-testid={testid} rows={rows} value={value || ""} onChange={onChange} className="w-full px-4 py-3 border border-input focus:border-primary focus:outline-none bg-white" />
      {hint && <p className="text-xs text-muted-foreground mt-1.5">{hint}</p>}
    </div>
  );
}
function Select({ label, value, onChange, testid, options }) {
  return (
    <div>
      <label className="pmc-label block mb-2">{label}</label>
      <select data-testid={testid} value={value} onChange={onChange} className="w-full h-12 px-4 border border-input bg-white focus:border-primary focus:outline-none">
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}
function MiniField({ label, value, onChange, testid }) {
  return (
    <div>
      <label className="text-[11px] uppercase tracking-widest text-muted-foreground block mb-1">{label}</label>
      <input data-testid={testid} value={value || ""} onChange={(e) => onChange(e.target.value)}
        className="w-full h-10 px-3 border border-input focus:border-primary focus:outline-none bg-white text-sm" />
    </div>
  );
}
