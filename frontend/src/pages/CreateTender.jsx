import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import DateTimePicker from "@/components/app/DateTimePicker";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { CURRENCIES, TENDER_CATEGORY_FLAT, GENERAL_CATEGORIES, COUNTRIES } from "@/data/countries";
import { Upload, X, ShieldAlert, Plus, Trash2 } from "lucide-react";

const DOC_TYPES = [
  { id: "tender", label: "Tender", body: "Standard open tender with free-form scope" },
  { id: "rfq", label: "RFQ", body: "Request for Quotation · itemised, price-focused" },
  { id: "rfp", label: "RFP", body: "Request for Proposal · weighted evaluation, technical + commercial" },
];

const empty = {
  document_type: "tender",
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
  // RFQ
  line_items: [],
  payment_terms: "",
  delivery_date: "",
  // RFP
  scope_of_work: "",
  expected_deliverables: "",
  evaluation_criteria: [],
  evaluation_committee: [],
  pre_bid_meeting_date: "",
  bid_bond_amount: "",
  two_envelope: false,
  // P1
  require_approval: false,
  emd_required: false,
  emd_amount: "",
  emd_currency: "USD",
  department_id: "",
};

export default function CreateTender() {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const initialType = ["tender", "rfp", "rfq"].includes(sp.get("type")) ? sp.get("type") : "tender";
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [kzMap, setKzMap] = useState({});
  const [kzLicenses, setKzLicenses] = useState([]);
  const [form, setForm] = useState({ ...empty, document_type: initialType });

  useEffect(() => { setForm((s) => ({ ...s, document_type: initialType })); }, [initialType]);
  // Category mode: "kz" (industry) or "general". Default to general for RFP, kz for tender/rfq.
  const [categoryMode, setCategoryMode] = useState(initialType === "rfp" ? "general" : "kz");
  useEffect(() => {
    setCategoryMode(initialType === "rfp" ? "general" : "kz");
  }, [initialType]);
  const currentCategoryList = categoryMode === "kz" ? TENDER_CATEGORY_FLAT : GENERAL_CATEGORIES;
  useEffect(() => {
    if (!currentCategoryList.includes(form.category)) {
      setForm((s) => ({ ...s, category: currentCategoryList[0] }));
    }
    // eslint-disable-next-line
  }, [categoryMode]);

  useEffect(() => {
    api.get("/reference/kz-licenses").then(({ data }) => {
      setKzMap(data.category_map || {});
      setKzLicenses(data.licenses || []);
    }).catch(() => {});
  }, []);

  // P1 — Load departments for approval workflow assignment
  const [departments, setDepartments] = useState([]);
  useEffect(() => {
    api.get("/departments").then(({ data }) => setDepartments(data)).catch(() => {});
  }, []);

  const set = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.value }));
  const suggestedKz = form.delivery_country === "KZ" ? (kzMap[form.category] || []) : [];
  const toggleLicense = (l) => setForm((s) => ({
    ...s, required_licenses: s.required_licenses.includes(l) ? s.required_licenses.filter((x) => x !== l) : [...s.required_licenses, l],
  }));

  // Line items (RFQ)
  const addLineItem = () => setForm((s) => ({ ...s, line_items: [...s.line_items, { item: "", qty: 1, unit: "unit", target_unit_price: "" }] }));
  const updateLineItem = (i, k, v) => setForm((s) => ({ ...s, line_items: s.line_items.map((li, idx) => (idx === i ? { ...li, [k]: v } : li)) }));
  const removeLineItem = (i) => setForm((s) => ({ ...s, line_items: s.line_items.filter((_, idx) => idx !== i) }));

  // Evaluation criteria (RFP)
  const addCriterion = () => setForm((s) => ({ ...s, evaluation_criteria: [...s.evaluation_criteria, { name: "", weight: 20, description: "" }] }));
  const updateCriterion = (i, k, v) => setForm((s) => ({ ...s, evaluation_criteria: s.evaluation_criteria.map((c, idx) => (idx === i ? { ...c, [k]: v } : c)) }));
  const removeCriterion = (i) => setForm((s) => ({ ...s, evaluation_criteria: s.evaluation_criteria.filter((_, idx) => idx !== i) }));
  const totalWeight = form.evaluation_criteria.reduce((sum, c) => sum + (Number(c.weight) || 0), 0);

  // Evaluation committee (RFP)
  const addCommittee = () => setForm((s) => ({ ...s, evaluation_committee: [...s.evaluation_committee, { name: "", role: "" }] }));
  const updateCommittee = (i, k, v) => setForm((s) => ({ ...s, evaluation_committee: s.evaluation_committee.map((c, idx) => (idx === i ? { ...c, [k]: v } : c)) }));
  const removeCommittee = (i) => setForm((s) => ({ ...s, evaluation_committee: s.evaluation_committee.filter((_, idx) => idx !== i) }));

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
    e.preventDefault();
    // Validate RFP weights sum to 100
    if (form.document_type === "rfp" && form.evaluation_criteria.length > 0 && totalWeight !== 100) {
      toast.error(`Evaluation criteria weights must sum to 100 (currently ${totalWeight}).`);
      return;
    }
    setBusy(true);
    try {
      if (!form.submission_deadline) {
        toast.error("Please pick a submission deadline.");
        setBusy(false);
        return;
      }
      const payload = {
        ...form,
        budget_amount: form.budget_amount ? Number(form.budget_amount) : null,
        bid_bond_amount: form.bid_bond_amount ? Number(form.bid_bond_amount) : null,
        emd_amount: form.emd_amount ? Number(form.emd_amount) : null,
        department_id: form.department_id || null,
        submission_deadline: new Date(form.submission_deadline).toISOString(),
        line_items: form.line_items.map((li) => ({ ...li, qty: Number(li.qty) || 1, target_unit_price: li.target_unit_price ? Number(li.target_unit_price) : null })),
        evaluation_criteria: form.evaluation_criteria.map((c) => ({ ...c, weight: Number(c.weight) || 0 })),
      };
      const { data } = await api.post("/tenders", payload);
      toast.success(`${form.document_type.toUpperCase()} published`);
      nav(`/tenders/${data.id}`);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const minDate = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 16);
  const isRFQ = form.document_type === "rfq";
  const isRFP = form.document_type === "rfp";

  const titleText = isRFP ? "Publish RFP" : isRFQ ? "Publish RFQ" : "Publish a tender";
  const subtitleText = isRFP
    ? "Request for Proposal · weighted evaluation of technical + commercial responses."
    : isRFQ ? "Request for Quotation · itemised, price-focused response."
    : "Define scope, budget, deadline and evaluation criteria.";

  return (
    <DashboardLayout title={titleText} subtitle={subtitleText}>
      <form onSubmit={submit} className="max-w-4xl border p-6 md:p-10 space-y-6">
        {/* Document type selector */}
        <div>
          <div className="pmc-label mb-2">Document type</div>
          <div className="grid grid-cols-3 gap-0 border">
            {DOC_TYPES.map((t) => (
              <button
                key={t.id} type="button" data-testid={`doctype-${t.id}`}
                onClick={() => setForm((s) => ({ ...s, document_type: t.id }))}
                className={`p-4 text-left border-r last:border-r-0 transition-colors ${form.document_type === t.id ? "bg-primary text-white" : "hover:bg-muted/40"}`}
              >
                <div className="font-serif text-lg">{t.label}</div>
                <div className={`text-xs mt-1 ${form.document_type === t.id ? "text-white/80" : "text-muted-foreground"}`}>{t.body}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Common fields */}
        <div>
          <label className="pmc-label block mb-2">Title</label>
          <input data-testid="ct-title" required value={form.title} onChange={set("title")}
            className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white" />
        </div>
        <div>
          <label className="pmc-label block mb-2">{isRFP ? "Executive summary" : "Description / scope of work"}</label>
          <textarea data-testid="ct-description" required value={form.description} onChange={set("description")} rows={5}
            className="w-full px-4 py-3 border border-input focus:border-primary focus:outline-none bg-white" />
        </div>

        <div className="grid md:grid-cols-2 gap-5">
          <div>
            <label className="pmc-label block mb-2">Category</label>
            <div className="grid grid-cols-2 gap-0 border mb-2 max-w-xs">
              <button type="button" data-testid="catmode-kz" onClick={() => setCategoryMode("kz")}
                className={`px-3 py-1.5 text-xs border-r transition-colors ${categoryMode === "kz" ? "bg-primary text-white" : "hover:bg-muted/40"}`}>
                KZ Industry
              </button>
              <button type="button" data-testid="catmode-general" onClick={() => setCategoryMode("general")}
                className={`px-3 py-1.5 text-xs transition-colors ${categoryMode === "general" ? "bg-primary text-white" : "hover:bg-muted/40"}`}>
                General / Consulting
              </button>
            </div>
            <select data-testid="ct-category" value={form.category} onChange={set("category")} className="w-full h-12 px-4 border border-input bg-white focus:border-primary focus:outline-none">
              {currentCategoryList.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="pmc-label block mb-2">Submission deadline</label>
            <DateTimePicker
              value={form.submission_deadline}
              onChange={(v) => setForm((s) => ({ ...s, submission_deadline: v }))}
              min={new Date(Date.now() + 24 * 3600 * 1000)}
              testid="ct-deadline"
            />
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
        </div>

        {/* RFQ block */}
        {isRFQ && (
          <div className="border p-5 border-l-4 border-primary bg-primary/5" data-testid="rfq-block">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="pmc-label text-primary">RFQ · Line items</div>
                <div className="font-serif text-xl mt-1">Itemised quotation table</div>
              </div>
              <button type="button" onClick={addLineItem} data-testid="rfq-add-item" className="text-xs inline-flex items-center gap-1 border border-foreground px-3 py-2">
                <Plus className="h-3 w-3" /> Add line item
              </button>
            </div>
            {form.line_items.length === 0 && <div className="text-sm text-muted-foreground border border-dashed p-4">No line items yet.</div>}
            {form.line_items.length > 0 && (
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b bg-white">
                    <th className="pmc-label text-left px-3 py-2">#</th>
                    <th className="pmc-label text-left px-3 py-2">Item description</th>
                    <th className="pmc-label text-left px-3 py-2">Qty</th>
                    <th className="pmc-label text-left px-3 py-2">Unit</th>
                    <th className="pmc-label text-left px-3 py-2">Target unit price</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {form.line_items.map((li, i) => (
                    <tr key={i} className="border-b bg-white" data-testid={`rfq-li-${i}`}>
                      <td className="px-3 py-2 font-mono text-xs">{String(i + 1).padStart(2, "0")}</td>
                      <td className="px-2 py-1"><input data-testid={`rfq-li-${i}-item`} value={li.item} onChange={(e) => updateLineItem(i, "item", e.target.value)} className="w-full h-9 px-2 border border-input" /></td>
                      <td className="px-2 py-1 w-20"><input data-testid={`rfq-li-${i}-qty`} type="number" min="1" value={li.qty} onChange={(e) => updateLineItem(i, "qty", e.target.value)} className="w-full h-9 px-2 border border-input" /></td>
                      <td className="px-2 py-1 w-24"><input data-testid={`rfq-li-${i}-unit`} value={li.unit} onChange={(e) => updateLineItem(i, "unit", e.target.value)} className="w-full h-9 px-2 border border-input" /></td>
                      <td className="px-2 py-1 w-36"><input data-testid={`rfq-li-${i}-price`} type="number" min="0" step="any" value={li.target_unit_price} onChange={(e) => updateLineItem(i, "target_unit_price", e.target.value)} className="w-full h-9 px-2 border border-input" /></td>
                      <td className="px-2"><button type="button" onClick={() => removeLineItem(i)}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="grid md:grid-cols-2 gap-4 mt-4">
              <div>
                <label className="pmc-label block mb-1">Payment terms</label>
                <input data-testid="rfq-payment-terms" value={form.payment_terms} onChange={set("payment_terms")} placeholder="e.g. 30 days net after delivery"
                  className="w-full h-11 px-3 border border-input bg-white focus:border-primary focus:outline-none" />
              </div>
              <div>
                <label className="pmc-label block mb-1">Required delivery date</label>
                <input data-testid="rfq-delivery-date" type="date" value={form.delivery_date} onChange={set("delivery_date")}
                  className="w-full h-11 px-3 border border-input bg-white focus:border-primary focus:outline-none" />
              </div>
            </div>
          </div>
        )}

        {/* RFP block */}
        {isRFP && (
          <div className="border p-5 border-l-4 border-primary bg-primary/5" data-testid="rfp-block">
            <div className="pmc-label text-primary mb-2">RFP · Scope, evaluation & committee</div>
            <div>
              <label className="pmc-label block mb-1">Full scope of work</label>
              <textarea data-testid="rfp-scope" rows={4} value={form.scope_of_work} onChange={set("scope_of_work")}
                className="w-full px-3 py-2 border border-input bg-white focus:border-primary focus:outline-none" />
            </div>
            <div className="mt-4">
              <label className="pmc-label block mb-1">Expected deliverables</label>
              <textarea data-testid="rfp-deliverables" rows={3} value={form.expected_deliverables} onChange={set("expected_deliverables")}
                className="w-full px-3 py-2 border border-input bg-white focus:border-primary focus:outline-none" />
            </div>

            <div className="mt-6">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="pmc-label">Evaluation criteria</div>
                  <div className="text-xs text-muted-foreground mt-1">Weights must sum to 100. Currently: <span className={totalWeight === 100 ? "text-success font-mono" : "text-warning font-mono"} data-testid="rfp-total-weight">{totalWeight}</span></div>
                </div>
                <button type="button" onClick={addCriterion} data-testid="rfp-add-criterion" className="text-xs inline-flex items-center gap-1 border border-foreground px-3 py-2"><Plus className="h-3 w-3" /> Add criterion</button>
              </div>
              {form.evaluation_criteria.length === 0 && <div className="text-sm text-muted-foreground border border-dashed p-4">No criteria yet. Typical: Technical 60%, Commercial 30%, Experience 10%.</div>}
              {form.evaluation_criteria.map((c, i) => (
                <div key={i} className="border bg-white p-3 mb-2" data-testid={`rfp-crit-${i}`}>
                  <div className="grid md:grid-cols-[1fr_100px_2fr_40px] gap-3 items-center">
                    <input data-testid={`rfp-crit-${i}-name`} placeholder="Criterion name" value={c.name} onChange={(e) => updateCriterion(i, "name", e.target.value)} className="h-10 px-3 border border-input" />
                    <input data-testid={`rfp-crit-${i}-weight`} type="number" min="0" max="100" placeholder="% weight" value={c.weight} onChange={(e) => updateCriterion(i, "weight", e.target.value)} className="h-10 px-3 border border-input" />
                    <input data-testid={`rfp-crit-${i}-desc`} placeholder="Description / what will be evaluated" value={c.description} onChange={(e) => updateCriterion(i, "description", e.target.value)} className="h-10 px-3 border border-input" />
                    <button type="button" onClick={() => removeCriterion(i)}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6">
              <div className="flex items-center justify-between mb-2">
                <div className="pmc-label">Evaluation committee</div>
                <button type="button" onClick={addCommittee} data-testid="rfp-add-committee" className="text-xs inline-flex items-center gap-1 border border-foreground px-3 py-2"><Plus className="h-3 w-3" /> Add member</button>
              </div>
              {form.evaluation_committee.map((m, i) => (
                <div key={i} className="border bg-white p-3 mb-2" data-testid={`rfp-comm-${i}`}>
                  <div className="grid md:grid-cols-[1fr_1fr_40px] gap-3 items-center">
                    <input data-testid={`rfp-comm-${i}-name`} placeholder="Name" value={m.name} onChange={(e) => updateCommittee(i, "name", e.target.value)} className="h-10 px-3 border border-input" />
                    <input data-testid={`rfp-comm-${i}-role`} placeholder="Role / department" value={m.role} onChange={(e) => updateCommittee(i, "role", e.target.value)} className="h-10 px-3 border border-input" />
                    <button type="button" onClick={() => removeCommittee(i)}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></button>
                  </div>
                </div>
              ))}
            </div>

            <div className="grid md:grid-cols-2 gap-4 mt-4">
              <div>
                <label className="pmc-label block mb-1">Pre-bid meeting date</label>
                <DateTimePicker value={form.pre_bid_meeting_date} onChange={(v) => setForm((s) => ({ ...s, pre_bid_meeting_date: v }))} testid="rfp-prebid" />
              </div>
              <div>
                <label className="pmc-label block mb-1">Bid bond amount (USD)</label>
                <input data-testid="rfp-bond" type="number" min="0" value={form.bid_bond_amount} onChange={set("bid_bond_amount")}
                  className="w-full h-11 px-3 border border-input bg-white focus:border-primary focus:outline-none" />
              </div>
            </div>

            <label className="mt-5 flex items-start gap-3 border border-dashed border-primary/40 bg-primary/[0.04] p-4 cursor-pointer hover:bg-primary/[0.07] transition-colors">
              <input
                type="checkbox"
                data-testid="rfp-two-envelope"
                checked={form.two_envelope}
                onChange={(e) => setForm((s) => ({ ...s, two_envelope: e.target.checked }))}
                className="mt-1 h-4 w-4 accent-primary"
              />
              <div>
                <div className="pmc-label text-primary">Two-envelope sealed bidding</div>
                <div className="text-sm mt-1 text-foreground/80">
                  Vendors submit technical and commercial proposals as sealed envelopes. Buyer opens technical envelopes first and scores them, then only technically-qualified bids reveal their commercial envelope for award.
                </div>
              </div>
            </label>
          </div>
        )}

        <div>
          <label className="pmc-label block mb-2">Eligibility criteria <span className="text-muted-foreground normal-case tracking-normal ml-2">(optional)</span></label>
          <textarea data-testid="ct-eligibility" value={form.eligibility_criteria} onChange={set("eligibility_criteria")} rows={3}
            className="w-full px-4 py-3 border border-input focus:border-primary focus:outline-none bg-white" />
        </div>

        {/* P1 — Governance: department + approval + EMD */}
        <div className="border p-5 space-y-4" data-testid="ct-governance">
          <div className="pmc-label">Governance</div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="pmc-label block mb-1">Department <span className="text-muted-foreground normal-case tracking-normal ml-2">(optional)</span></label>
              <select data-testid="ct-department" value={form.department_id} onChange={set("department_id")}
                className="w-full h-11 px-3 border border-input bg-white">
                <option value="">— None —</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.code})</option>)}
              </select>
              <div className="text-xs text-muted-foreground mt-1">Approval chain is inherited from the department's budget thresholds.</div>
            </div>
            <div className="flex flex-col justify-center">
              <label className="flex items-start gap-3 cursor-pointer">
                <input type="checkbox" data-testid="ct-require-approval" checked={form.require_approval}
                  onChange={(e) => setForm((s) => ({ ...s, require_approval: e.target.checked }))} className="mt-1 h-4 w-4 accent-primary" />
                <div>
                  <div className="pmc-label">Force Contracts Committee approval</div>
                  <div className="text-xs text-muted-foreground">Even if the department has no thresholds, force admin sign-off before publish.</div>
                </div>
              </label>
            </div>
          </div>

          <label className="flex items-start gap-3 cursor-pointer border-t pt-4">
            <input type="checkbox" data-testid="ct-emd-required" checked={form.emd_required}
              onChange={(e) => setForm((s) => ({ ...s, emd_required: e.target.checked }))} className="mt-1 h-4 w-4 accent-primary" />
            <div className="flex-1">
              <div className="pmc-label">Earnest Money Deposit (EMD)</div>
              <div className="text-xs text-muted-foreground">Vendors must submit an EMD before bidding. Losing bidders auto-refunded on award.</div>
            </div>
          </label>
          {form.emd_required && (
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="pmc-label block mb-1">EMD amount</label>
                <input data-testid="ct-emd-amount" type="number" min="0" value={form.emd_amount} onChange={set("emd_amount")}
                  className="w-full h-11 px-3 border border-input bg-white focus:border-primary focus:outline-none" />
              </div>
              <div>
                <label className="pmc-label block mb-1">Currency</label>
                <select data-testid="ct-emd-currency" value={form.emd_currency} onChange={set("emd_currency")} className="w-full h-11 px-3 border border-input bg-white">
                  {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
          )}
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
          <label className="pmc-label block mb-2">Attachments</label>
          <label className="block border border-dashed border-input hover:border-primary p-6 text-center cursor-pointer">
            <input data-testid="ct-file-input" type="file" multiple onChange={onUpload} className="hidden" />
            <Upload className="mx-auto h-5 w-5 text-muted-foreground mb-2" />
            <div className="text-sm">{uploading ? "Uploading..." : "Attach spec sheets, BoQ, drawings, RFP template"}</div>
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
            {busy ? "Publishing..." : `Publish ${form.document_type.toUpperCase()}`}
          </button>
        </div>
      </form>
    </DashboardLayout>
  );
}
