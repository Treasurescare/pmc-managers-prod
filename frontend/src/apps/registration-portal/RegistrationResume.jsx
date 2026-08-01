import { useEffect, useMemo, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, registrationApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";

const STEPS = ["a", "b", "c", "d", "e"];

function Field({ label, children, hint }) {
  return (
    <label className="block">
      <span className="pmc-label">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-brand-navy/50 mt-1">{hint}</span>}
    </label>
  );
}

function Input({ testId, ...rest }) {
  return (
    <input
      data-testid={testId}
      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white"
      {...rest}
    />
  );
}

export default function RegistrationResume() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token");
  const [reg, setReg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stepIdx, setStepIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [countries, setCountries] = useState([]);
  const [kzMeta, setKzMeta] = useState({ licenses: [], category_map: {} });

  useEffect(() => {
    if (!token) { navigate("/register"); return; }
    setLoading(true);
    Promise.all([
      registrationApi.resume(token),
      publicApi.countries().catch(() => []),
      publicApi.kzMeta().catch(() => ({ licenses: [], category_map: {} })),
    ])
      .then(([r, cs, kz]) => { setReg(r); setCountries(cs); setKzMeta(kz); })
      .catch((e) => { toast.error(formatApiError(e)); setTimeout(() => navigate("/register"), 1200); })
      .finally(() => setLoading(false));
  }, [token, navigate]);

  const update = (patch) => setReg((prev) => ({ ...prev, ...patch }));

  const saveDraft = async () => {
    if (!reg?.id) return;
    setBusy(true);
    try {
      const payload = { ...reg };
      delete payload.id; delete payload.status; delete payload.tenant_id;
      delete payload.created_at; delete payload.updated_at; delete payload.submitted_at;
      delete payload.vendor_ref; delete payload.reviewed_at; delete payload.reviewer_notes; delete payload.magic_token;
      const fresh = await registrationApi.update(reg.id, token, payload);
      setReg(fresh);
      toast.success("Saved");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const submitFinal = async () => {
    setBusy(true);
    try {
      await saveDraft();
      await registrationApi.submit(reg.id, token);
      toast.success("Registration submitted for review");
      navigate(`/register/status?token=${token}`);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const allDeclarationsChecked = useMemo(() => {
    if (!reg) return false;
    return ["decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
            "decl_data_consent", "decl_fee", "decl_notification"].every((k) => reg[k]);
  }, [reg]);

  const step = STEPS[stepIdx];
  const stepLabel = t(`register.section_${step}`);

  if (loading || !reg) {
    return (
      <div className="min-h-screen bg-brand-pale flex flex-col">
        <TopBar />
        <div className="flex-1 flex items-center justify-center text-brand-navy/60">{t("common.loading")}</div>
        <Footer />
      </div>
    );
  }

  if (reg.status && !["draft", "needs_clarification"].includes(reg.status)) {
    return (
      <div className="min-h-screen bg-brand-pale flex flex-col">
        <TopBar />
        <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-16">
          <div className="border border-brand-navy/10 bg-white p-10">
            <div className="pmc-label">Registration status</div>
            <h1 className="font-display text-3xl mt-2 text-brand-navy">
              {reg.status === "submitted" ? "Submitted — under review" : `Status: ${reg.status}`}
            </h1>
            <p className="text-brand-navy/70 mt-3">
              {reg.reviewer_notes || "Our team will get back to you by email once the review is complete."}
            </p>
            {reg.vendor_ref && (
              <div className="mt-6 font-mono text-lg text-brand-navy-soft">Supplier ref: {reg.vendor_ref}</div>
            )}
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 lg:px-10 py-12">
        <div className="pmc-label">Pre-Tender Registration</div>
        <h1 className="font-display text-3xl lg:text-4xl mt-2 text-brand-navy">{stepLabel}</h1>

        {/* Stepper */}
        <ol className="mt-6 flex items-center gap-3 flex-wrap" data-testid="stepper">
          {STEPS.map((s, i) => {
            const active = i === stepIdx;
            const passed = i < stepIdx;
            return (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => setStepIdx(i)}
                  data-testid={`step-${s}`}
                  className={
                    "px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border " +
                    (active
                      ? "bg-brand-navy text-white border-brand-navy"
                      : passed
                        ? "bg-brand-navy-soft/10 text-brand-navy border-brand-navy-soft/40"
                        : "bg-white text-brand-navy/50 border-brand-navy/20")
                  }
                >
                  {s.toUpperCase()} · {t(`register.section_${s}`).split("·")[1]?.trim() || s}
                </button>
              </li>
            );
          })}
        </ol>

        <div className="mt-8 bg-white border border-brand-navy/10 p-8 lg:p-10 grid gap-5" data-testid={`section-${step}`}>
          {step === "a" && (
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Company name">
                <Input testId="f-company-name" value={reg.company_name || ""} onChange={(e) => update({ company_name: e.target.value })} />
              </Field>
              <Field label="Trade name">
                <Input testId="f-trade-name" value={reg.trade_name || ""} onChange={(e) => update({ trade_name: e.target.value })} />
              </Field>
              <Field label="Registered address">
                <Input testId="f-registered-address" value={reg.registered_address || ""} onChange={(e) => update({ registered_address: e.target.value })} />
              </Field>
              <Field label="Mailing address">
                <Input testId="f-mailing-address" value={reg.mailing_address || ""} onChange={(e) => update({ mailing_address: e.target.value })} />
              </Field>
              <Field label="Country">
                <select data-testid="f-country" value={reg.country || "KZ"} onChange={(e) => update({ country: e.target.value })}
                  className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
                  {countries.map((c) => (<option key={c.code} value={c.code}>{c.name}</option>))}
                </select>
              </Field>
              <Field label="Registration number">
                <Input testId="f-reg-number" value={reg.registration_number || ""} onChange={(e) => update({ registration_number: e.target.value })} />
              </Field>
              <Field label="Incorporation date"><Input testId="f-incorp-date" type="date" value={reg.incorporation_date || ""} onChange={(e) => update({ incorporation_date: e.target.value })} /></Field>
              <Field label="Tax ID"><Input testId="f-tax-id" value={reg.tax_id || ""} onChange={(e) => update({ tax_id: e.target.value })} /></Field>
              <Field label="Legal entity type">
                <select data-testid="f-legal-type" value={reg.legal_entity_type || ""} onChange={(e) => update({ legal_entity_type: e.target.value })}
                  className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
                  <option value="">—</option>
                  <option>LLC</option><option>JSC</option><option>Sole Proprietorship</option><option>Partnership</option><option>Branch</option><option>Other</option>
                </select>
              </Field>
              <Field label="Website"><Input testId="f-website" value={reg.website || ""} onChange={(e) => update({ website: e.target.value })} /></Field>
              <Field label="Employees count"><Input testId="f-employees" type="number" value={reg.employees_count || ""} onChange={(e) => update({ employees_count: parseInt(e.target.value || "0", 10) || null })} /></Field>
            </div>
          )}

          {step === "b" && (
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Contact name"><Input testId="f-contact-name" value={reg.contact_name || ""} onChange={(e) => update({ contact_name: e.target.value })} /></Field>
              <Field label="Contact title"><Input testId="f-contact-title" value={reg.contact_title || ""} onChange={(e) => update({ contact_title: e.target.value })} /></Field>
              <Field label="Office phone"><Input testId="f-contact-phone" value={reg.contact_office_phone || ""} onChange={(e) => update({ contact_office_phone: e.target.value })} /></Field>
              <Field label="Mobile"><Input testId="f-contact-mobile" value={reg.contact_mobile || ""} onChange={(e) => update({ contact_mobile: e.target.value })} /></Field>
              <Field label="Contact email"><Input testId="f-contact-email" type="email" value={reg.contact_email || ""} onChange={(e) => update({ contact_email: e.target.value })} /></Field>
              <div />
              <Field label="Authorized signatory name"><Input testId="f-sig-name" value={reg.signatory_name || ""} onChange={(e) => update({ signatory_name: e.target.value })} /></Field>
              <Field label="Signatory title"><Input testId="f-sig-title" value={reg.signatory_title || ""} onChange={(e) => update({ signatory_title: e.target.value })} /></Field>
              <Field label="Signatory contact"><Input testId="f-sig-contact" value={reg.signatory_contact || ""} onChange={(e) => update({ signatory_contact: e.target.value })} /></Field>
            </div>
          )}

          {step === "c" && (
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Bank name"><Input testId="f-bank-name" value={reg.bank_name || ""} onChange={(e) => update({ bank_name: e.target.value })} /></Field>
              <Field label="Branch"><Input testId="f-bank-branch" value={reg.bank_branch || ""} onChange={(e) => update({ bank_branch: e.target.value })} /></Field>
              <Field label="Account number"><Input testId="f-bank-acct" value={reg.bank_account_number || ""} onChange={(e) => update({ bank_account_number: e.target.value })} /></Field>
              <Field label="SWIFT"><Input testId="f-bank-swift" value={reg.bank_swift || ""} onChange={(e) => update({ bank_swift: e.target.value })} /></Field>
              <Field label="Bank address"><Input testId="f-bank-address" value={reg.bank_address || ""} onChange={(e) => update({ bank_address: e.target.value })} /></Field>
              <Field label="Turnover currency">
                <select data-testid="f-turnover-currency" value={reg.turnover_currency || "USD"} onChange={(e) => update({ turnover_currency: e.target.value })}
                  className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
                  <option>USD</option><option>EUR</option><option>KZT</option><option>RUB</option><option>GBP</option>
                </select>
              </Field>
              <Field label="Turnover Year 1"><Input testId="f-turnover-1" type="number" step="0.01" value={reg.turnover_year1 || ""} onChange={(e) => update({ turnover_year1: parseFloat(e.target.value || "0") || null })} /></Field>
              <Field label="Turnover Year 2"><Input testId="f-turnover-2" type="number" step="0.01" value={reg.turnover_year2 || ""} onChange={(e) => update({ turnover_year2: parseFloat(e.target.value || "0") || null })} /></Field>
              <Field label="Turnover Year 3"><Input testId="f-turnover-3" type="number" step="0.01" value={reg.turnover_year3 || ""} onChange={(e) => update({ turnover_year3: parseFloat(e.target.value || "0") || null })} /></Field>
            </div>
          )}

          {step === "d" && (
            <div className="grid gap-5">
              <Field label="Primary sector"><Input testId="f-primary-sector" value={reg.primary_sector || ""} onChange={(e) => update({ primary_sector: e.target.value })} /></Field>
              <Field label="Business description">
                <textarea data-testid="f-business-desc" value={reg.business_description || ""} onChange={(e) => update({ business_description: e.target.value })} rows={4}
                  className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
              </Field>
              <Field label="Operating regions (comma separated)">
                <Input testId="f-op-regions" value={(reg.operating_regions || []).join(", ")} onChange={(e) => update({ operating_regions: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
              </Field>
              <Field label="Business categories (comma separated)">
                <Input testId="f-categories" value={(reg.business_categories || []).join(", ")} onChange={(e) => update({ business_categories: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
              </Field>
              <Field label="Kazakhstan licenses held" hint="Only select licenses your company currently holds. These gate access to KZ tenders that require them.">
                <div className="grid md:grid-cols-2 gap-2 mt-2">
                  {kzMeta.licenses?.map((lic) => {
                    const held = (reg.kz_licenses || []).includes(lic);
                    return (
                      <label key={lic} className="flex items-center gap-2 border border-brand-navy/10 px-3 py-2 bg-white cursor-pointer hover:border-brand-navy-soft/60">
                        <input
                          type="checkbox"
                          data-testid={`f-kz-license-${lic.split(" ")[0].toLowerCase()}`}
                          checked={held}
                          onChange={() => {
                            const cur = new Set(reg.kz_licenses || []);
                            if (held) cur.delete(lic); else cur.add(lic);
                            update({ kz_licenses: Array.from(cur) });
                          }}
                        />
                        <span className="text-sm text-brand-navy">{lic}</span>
                      </label>
                    );
                  })}
                </div>
              </Field>
              <Field label="ISO certifications"><Input testId="f-iso" value={reg.iso_certifications || ""} onChange={(e) => update({ iso_certifications: e.target.value })} /></Field>
              <Field label="Insurance details"><Input testId="f-insurance" value={reg.insurance_details || ""} onChange={(e) => update({ insurance_details: e.target.value })} /></Field>
              <Field label="Litigation history">
                <textarea data-testid="f-litigation" rows={2} value={reg.litigation_history || ""} onChange={(e) => update({ litigation_history: e.target.value })}
                  className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
              </Field>
            </div>
          )}

          {step === "e" && (
            <div className="grid gap-5">
              <div>
                <div className="pmc-label mb-3">Declarations · all six required</div>
                <div className="grid gap-2">
                  {[
                    ["decl_conflict_of_interest", "No conflict of interest with PMC Managers, Emerald Corporates or Big B Corporation"],
                    ["decl_integrity", "Company is not under sanctions, blacklisting or debarment"],
                    ["decl_accuracy", "All information provided is accurate to the best of our knowledge"],
                    ["decl_data_consent", "Consent to PMC storing and processing this data in line with applicable data-protection law"],
                    ["decl_fee", "Understand that any registration fee (if applicable) is non-refundable"],
                    ["decl_notification", "Accept email notifications on tender activity"],
                  ].map(([k, label]) => (
                    <label key={k} className="flex items-start gap-3 border border-brand-navy/10 px-4 py-3 bg-white cursor-pointer hover:border-brand-navy-soft/60">
                      <input
                        type="checkbox"
                        data-testid={`f-${k}`}
                        checked={!!reg[k]}
                        onChange={() => update({ [k]: !reg[k] })}
                        className="mt-1"
                      />
                      <span className="text-sm text-brand-navy">{label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="grid gap-5 md:grid-cols-3">
                <Field label="Signature — full name"><Input testId="f-sign-name" value={reg.signature_name || ""} onChange={(e) => update({ signature_name: e.target.value })} /></Field>
                <Field label="Signature — title"><Input testId="f-sign-title" value={reg.signature_title || ""} onChange={(e) => update({ signature_title: e.target.value })} /></Field>
                <Field label="Signature — date"><Input testId="f-sign-date" type="date" value={reg.signature_date || ""} onChange={(e) => update({ signature_date: e.target.value })} /></Field>
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 flex items-center justify-between flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setStepIdx(Math.max(0, stepIdx - 1))}
            disabled={stepIdx === 0}
            data-testid="btn-prev"
            className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5 disabled:opacity-40"
          >
            ← Previous
          </button>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={saveDraft}
              disabled={busy}
              data-testid="btn-save-draft"
              className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5 disabled:opacity-40"
            >
              Save draft
            </button>

            {stepIdx < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={async () => { await saveDraft(); setStepIdx(stepIdx + 1); }}
                disabled={busy}
                data-testid="btn-next"
                className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40"
              >
                Next →
              </button>
            ) : (
              <button
                type="button"
                onClick={submitFinal}
                disabled={busy || !allDeclarationsChecked}
                data-testid="btn-submit-final"
                className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90 disabled:opacity-40"
              >
                Submit for review
              </button>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
