import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, registrationApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";
import SectionA from "./sections/SectionA";
import SectionB from "./sections/SectionB";
import SectionC from "./sections/SectionC";
import SectionD from "./sections/SectionD";
import SectionE from "./sections/SectionE";

const STEPS = ["a", "b", "c", "d", "e"];
const DECL_KEYS = [
  "decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
  "decl_data_consent", "decl_fee", "decl_notification",
];

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

  const update = useCallback((patch) => setReg((prev) => ({ ...prev, ...patch })), []);

  const saveDraft = useCallback(async () => {
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
  }, [reg, token]);

  const submitFinal = useCallback(async () => {
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
  }, [reg, token, saveDraft, navigate]);

  const allDeclarationsChecked = useMemo(
    () => (reg ? DECL_KEYS.every((k) => reg[k]) : false),
    [reg]
  );

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
          {step === "a" && <SectionA reg={reg} update={update} countries={countries} />}
          {step === "b" && <SectionB reg={reg} update={update} />}
          {step === "c" && <SectionC reg={reg} update={update} />}
          {step === "d" && <SectionD reg={reg} update={update} kzMeta={kzMeta} />}
          {step === "e" && <SectionE reg={reg} update={update} />}
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
