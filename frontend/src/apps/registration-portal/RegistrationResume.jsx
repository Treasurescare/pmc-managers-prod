import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { adminApi, publicApi, registrationApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";
import SectionA from "./sections/SectionA";
import SectionB from "./sections/SectionB";
import SectionC from "./sections/SectionC";
import SectionD from "./sections/SectionD";
import SectionDirectors from "./sections/SectionDirectors";
import SectionE from "./sections/SectionE";

// v44 — Directors & Beneficial Owners inserted between D (KZ Business Profile)
// and E (Declarations & Signature). Legacy keys a/b/c/d/e untouched.
const STEPS = ["a", "b", "c", "d", "directors", "e"];
const DECL_KEYS = [
  "decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
  "decl_data_consent", "decl_fee", "decl_notification",
];

// Section A required fields — vendor cannot advance until Identity & Basic
// Info is complete. Anything else per section is optional/progressive.
// v54e — incorporation_date is mandatory and capped at today.
const SECTION_A_REQUIRED = [
  "company_name", "registered_address", "country",
  "registration_number", "legal_entity_type", "incorporation_date",
];
const missingSectionA = (reg) =>
  SECTION_A_REQUIRED.filter((k) => !reg?.[k] || String(reg[k]).trim() === "");

export default function RegistrationResume() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token");
  const fromAdmin = params.get("from") === "admin";
  const ridParam = params.get("rid");
  const [reg, setReg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stepIdx, setStepIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [countries, setCountries] = useState([]);
  const [kzMeta, setKzMeta] = useState({ licenses: [], category_map: {} });
  // v54e — Section A reports live format problems (reg-number / tax-id
  // regex mismatch, future incorporation date) so the Next gate blocks
  // until they're fixed, not just until fields are non-empty.
  const [aFormatIssue, setAFormatIssue] = useState(false);

  useEffect(() => {
    if (!token || token === "undefined" || token === "null") {
      // v54f — a broken resume link (token=undefined/null) used to fetch a
      // 404 and bounce with a confusing generic error. Say what happened
      // and send the vendor back to the start page to request a fresh link.
      toast.error("That resume link is invalid or expired. Enter your email again and we'll send a fresh one.", { duration: 9000 });
      navigate("/register");
      return;
    }
    setLoading(true);
    Promise.all([
      registrationApi.resume(token),
      publicApi.countries().catch(() => []),
      publicApi.kzMeta().catch(() => ({ licenses: [], category_map: {} })),
    ])
      .then(([r, cs, kz]) => { setReg(r); setCountries(cs); setKzMeta(kz); })
      .catch((e) => { showApiError(e); setTimeout(() => navigate("/register"), 1200); })
      .finally(() => setLoading(false));
  }, [token, navigate]);

  const update = useCallback((patch) => setReg((prev) => ({ ...prev, ...patch })), []);

  const saveDraft = useCallback(async () => {
    if (!reg?.id) return;
    setBusy(true);
    try {
      // v54a — only send fields the backend PATCH model accepts.
      // RegistrationUpdateIn is extra="forbid", so any server-managed /
      // consent-captured-on-draft-creation field smuggled back in a PATCH
      // triggers 422 "Extra inputs are not permitted" and the signature
      // block never reaches the DB → submit later fails with "Missing
      // signature field". Strip everything that isn't a form field.
      const payload = { ...reg };
      for (const k of [
        "id", "status", "tenant_id", "created_at", "updated_at",
        "submitted_at", "vendor_ref", "reviewed_at", "reviewer_notes",
        "reviewed_by", "approved_at", "rejected_at", "magic_token",
        "email", "data_processing_consent", "marketing_consent",
        "consent_at", "document_slots",
      ]) delete payload[k];
      const fresh = fromAdmin && ridParam
        ? await adminApi.registrationAdminUpdate(ridParam, payload)
        : await registrationApi.update(reg.id, token, payload);
      setReg(fresh);
      toast.success(t("register.saved"));
      return fresh;
    } catch (err) {
      showApiError(err);
      // v54a — rethrow so submitFinal halts instead of silently calling
      // submit on an unsaved draft and surfacing a confusing 400.
      throw err;
    } finally {
      setBusy(false);
    }
  }, [reg, token, t, fromAdmin, ridParam]);

  const submitFinal = useCallback(async () => {
    setBusy(true);
    try {
      // v54a — saveDraft now throws on PATCH failure, so a 422 on save
      // short-circuits the submit instead of 400ing on an unsaved draft.
      await saveDraft();
      await registrationApi.submit(reg.id, token);
      toast.success(t("register.submitted_ok"));
      navigate(`/register/status?token=${token}`);
    } catch (err) {
      // saveDraft already surfaced the real error via showApiError;
      // only show submit-time errors here.
      if (!err?._handledBySaveDraft) showApiError(err);
    } finally {
      setBusy(false);
    }
  }, [reg, token, saveDraft, navigate, t]);

  const allDeclarationsChecked = useMemo(
    () => (reg ? DECL_KEYS.every((k) => reg[k]) : false),
    [reg]
  );

  // v44 — Directors gate: require at least one director row with a non-empty
  // full name before allowing final submit.
  const directorsOk = useMemo(() => {
    const arr = Array.isArray(reg?.directors) ? reg.directors : [];
    return arr.some((d) => (d?.full_name || "").trim().length > 0);
  }, [reg]);

  // Registration Guard — block Next if Section A is incomplete. Only enforced
  // when the current step is A; later steps can move freely once A is done.
  const sectionAGaps = useMemo(() => missingSectionA(reg), [reg]);
  const step = STEPS[stepIdx];
  const stepLabel = t(`register.section_${step}`);
  const sectionABlocked = sectionAGaps.length > 0 || aFormatIssue;
  const sectionAReason = sectionAGaps.length > 0
    ? `Please fill Identity & Basic Info first. Missing: ${sectionAGaps.map((k) => k.replace(/_/g, " ")).join(", ")}`
    : "Fix the highlighted format errors in Section A first (registration number / tax ID format, or a future incorporation date).";
  const nextBlocked = step === "a" && sectionABlocked;

  if (loading || !reg) {
    return (
      <div className="min-h-screen bg-brand-pale flex flex-col">
        <TopBar />
        <div className="flex-1 flex items-center justify-center text-brand-navy/60">{t("common.loading")}</div>
        <Footer />
      </div>
    );
  }

  // Admins opening via RegistrationsPanel's "Edit sections" (?from=admin) get
  // the editable stepper for any non-approved/non-rejected status; vendors
  // keep the read-only status screen once submitted.
  const adminEditable = fromAdmin && !["approved", "rejected"].includes(reg.status);
  if (reg.status && !["draft", "needs_clarification"].includes(reg.status) && !adminEditable) {
    return (
      <div className="min-h-screen bg-brand-pale flex flex-col">
        <TopBar />
        <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-16">
          <div className="border border-brand-navy/10 bg-white p-10">
            <div className="pmc-label">{t("register.status_heading")}</div>
            <h1 className="font-display text-3xl mt-2 text-brand-navy">
              {reg.status === "submitted" ? t("register.status_submitted") : `${t("register.status_generic")}: ${reg.status}`}
            </h1>
            <p className="text-brand-navy/70 mt-3">
              {reg.reviewer_notes || t("register.status_reviewer_default")}
            </p>
            {reg.vendor_ref && (
              <div className="mt-6 font-mono text-lg text-brand-navy-soft">{t("register.supplier_ref")}: {reg.vendor_ref}</div>
            )}
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  // v52cb — when an admin opened this via "Edit sections" the resume page
  // launches in a NEW TAB. The TopBar's public "Back" chip used to walk the
  // browser history, which in a fresh tab lands on the public home page.
  // Give admins an explicit "Back to Registrations" control that closes
  // the just-opened tab (and falls back to navigating in-tab).
  const closeBackToAdmin = () => {
    try { window.close(); } catch { /* no-op */ }
    // If window.close() was blocked (tab was not opened by script in a way
    // the browser trusts), navigate to the admin registrations page as a
    // safety net so the admin never ends up on the public homepage.
    setTimeout(() => {
      if (!window.closed) window.location.href = "/admin/e/registrations";
    }, 120);
  };

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 lg:px-10 py-12">
        {fromAdmin && (
          <button type="button" onClick={closeBackToAdmin}
                  data-testid="reg-resume-back-admin"
                  className="mb-6 inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-widest text-brand-navy border border-brand-navy/30 px-4 py-2 hover:bg-brand-navy hover:text-white">
            ← Back to Registrations
          </button>
        )}
        <div className="pmc-label">{t("register.title")}</div>
        <h1 className="font-display text-3xl lg:text-4xl mt-2 text-brand-navy">{stepLabel}</h1>
        {/* v54f — anchor the vendor's identity: the resume page never showed
            which email the draft belongs to, so vendors bounced from a broken
            link couldn't tell the form knew them at all. */}
        <div className="mt-2 text-sm text-brand-navy/70" data-testid="reg-resume-email">
          Registering as <span className="font-mono font-semibold text-brand-navy">{reg.email}</span>
          {" · "}private draft link — do not share
        </div>

        <ol className="mt-6 flex items-center gap-2 flex-wrap" data-testid="stepper">
          {STEPS.map((s, i) => {
            const active = i === stepIdx;
            const passed = i < stepIdx;
            // Bug-blitz (a) — Registration step gate. Jumping past Section A
            // via the stepper used to bypass the required-field check; block
            // it here so the only way past Section A is completing it.
            const jumpBlocked = i > 0 && sectionABlocked;
            return (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => {
                    if (jumpBlocked) {
                      toast.error(sectionAReason);
                      return;
                    }
                    setStepIdx(i);
                  }}
                  data-testid={`step-${s}`}
                  aria-disabled={jumpBlocked}
                  title={jumpBlocked ? `Complete Section A first (${sectionAGaps.length} field(s) missing)` : ""}
                  className={
                    "px-3 py-2 text-[11px] font-semibold uppercase tracking-widest border whitespace-nowrap aria-disabled:opacity-40 aria-disabled:cursor-not-allowed " +
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
          {(() => {
            const docProps = {
              regId: reg.id,
              token: token,
              onDocChange: (slot, meta) => {
                setReg((prev) => {
                  const slots = { ...(prev.document_slots || {}) };
                  if (meta) slots[slot] = meta; else delete slots[slot];
                  return { ...prev, document_slots: slots };
                });
              },
            };
            if (step === "a") return <SectionA reg={reg} update={update} countries={countries} onFormatIssue={setAFormatIssue} {...docProps} />;
            if (step === "b") return <SectionB reg={reg} update={update} countries={countries} {...docProps} />;
            if (step === "c") return <SectionC reg={reg} update={update} {...docProps} />;
            if (step === "d") return <SectionD reg={reg} update={update} kzMeta={kzMeta} {...docProps} />;
            if (step === "directors") return <SectionDirectors reg={reg} update={update} />;
            if (step === "e") return <SectionE reg={reg} update={update} />;
            return null;
          })()}
        </div>

        <div className="mt-6 flex items-center justify-between flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setStepIdx(Math.max(0, stepIdx - 1))}
            disabled={stepIdx === 0}
            data-testid="btn-prev"
            className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5 disabled:opacity-40"
          >
            ← {t("register.prev")}
          </button>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={saveDraft}
              disabled={busy}
              data-testid="btn-save-draft"
              className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5 disabled:opacity-40"
            >
              {t("register.save_draft")}
            </button>

            {stepIdx < STEPS.length - 1 ? (
              <div className="flex flex-col items-end gap-1">
                <button
                  type="button"
                  onClick={async () => {
                    if (nextBlocked) {
                      toast.error(sectionAReason);
                      return;
                    }
                    await saveDraft();
                    setStepIdx(stepIdx + 1);
                  }}
                  disabled={busy || nextBlocked}
                  data-testid="btn-next"
                  title={nextBlocked ? `Complete Section A first (${sectionAGaps.length} field(s) missing)` : ""}
                  className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40"
                >
                  {t("register.next")} →
                </button>
                {nextBlocked && (
                  <span className="text-[11px] text-red-600" data-testid="section-a-gaps">
                    {sectionAGaps.length} required field(s) missing in Section A
                  </span>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-end gap-1">
                <button
                  type="button"
                  onClick={() => {
                    if (!directorsOk) {
                      toast.error(t("register.directors_required"));
                      return;
                    }
                    submitFinal();
                  }}
                  disabled={busy || !allDeclarationsChecked || !directorsOk}
                  data-testid="btn-submit-final"
                  title={!directorsOk ? t("register.directors_required") : ""}
                  className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90 disabled:opacity-40"
                >
                  {t("register.submit_final")}
                </button>
                {!directorsOk && (
                  <span className="text-[11px] text-red-600" data-testid="directors-gap">
                    {t("register.directors_required")}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
