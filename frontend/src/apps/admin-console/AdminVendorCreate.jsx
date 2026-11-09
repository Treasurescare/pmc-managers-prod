import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, vendorInviteApi, registrationApi, mastersGeoApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import SectionA from "@/apps/registration-portal/sections/SectionA";
import SectionB from "@/apps/registration-portal/sections/SectionB";
import SectionC from "@/apps/registration-portal/sections/SectionC";
import SectionD from "@/apps/registration-portal/sections/SectionD";
import SectionE from "@/apps/registration-portal/sections/SectionE";
import VendorStepperNav from "./vendor/VendorStepperNav";
import VendorActivationStep from "./vendor/VendorActivationStep";
import { InfoDot } from "@/components/InfoDot";
import { missingRequired } from "@/apps/registration-portal/requiredFields";

/**
 * Admin creates a vendor + fills the FULL Sections A–E form on their behalf.
 * A "draft" registration is created on demand so that admin-side document
 * uploads can flow through the standard public upload endpoint. On final
 * activation the draft's document_slots are carried into the vendor record.
 */
export default function AdminVendorCreate() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [step, setStep] = useState("a");
  const [reg, setReg] = useState({ country: "KZ", document_slots: {} });
  const [mode, setMode] = useState("activate");
  const [password, setPassword] = useState("");
  const [countries, setCountries] = useState([{ code: "KZ", name: "Kazakhstan" }]);
  const [saving, setSaving] = useState(false);
  const [draftId, setDraftId] = useState(null);
  const [draftToken, setDraftToken] = useState(null);
  const [creatingDraft, setCreatingDraft] = useState(false);
  const [savingSection, setSavingSection] = useState(false);
  const [lastSavedStep, setLastSavedStep] = useState(null);

  useEffect(() => {
    document.title = "New vendor · Admin";
    // v52cn — pull the full 250-country master so Section A's country
    // dropdown and SectionD's cascading geo editor share one source of truth.
    // Falls back to the legacy 30-country meta shortlist only when the
    // masters endpoint returns nothing.
    (async () => {
      try {
        const rows = await mastersGeoApi.countries();
        if (Array.isArray(rows) && rows.length) { setCountries(rows); return; }
      } catch { /* fall through */ }
      try {
        const rows = await publicApi.countries();
        setCountries(Array.isArray(rows) ? rows : []);
      } catch { /* keep seed */ }
    })();
  }, []);

  const update = (patch) => setReg((prev) => {
    // Bug #78 fix (Vendor Document Crossover) — if the admin changes the
    // vendor email after having auto-created a draft, we MUST discard the
    // previous draft + any documents uploaded against it. Otherwise the
    // newly-emailed vendor inherits the previous vendor's uploaded files.
    if ("email" in patch && patch.email !== prev.email && (draftId || Object.keys(prev.document_slots || {}).length > 0)) {
      setDraftId(null);
      setDraftToken(null);
      return { ...prev, ...patch, document_slots: {} };
    }
    return { ...prev, ...patch };
  });

  // Silent auto-save the FIRST time it's needed (e.g. the admin picks a
  // document to upload before manually hitting "Save draft"). Returns the
  // fresh {regId, token} so the caller can immediately upload.
  const ensureDraft = async () => {
    if (draftId && draftToken) return { regId: draftId, token: draftToken };
    if (!reg.email) {
      toast.error(t("admin_vendor.email_required"));
      return null;
    }
    setCreatingDraft(true);
    try {
      const d = await registrationApi.createDraft({
        email: reg.email,
        company_name: reg.company_name || undefined,
        country: reg.country || "KZ",
      });
      const tok = d.magic_token || d.token;
      setDraftId(d.id);
      setDraftToken(tok);
      return { regId: d.id, token: tok };
    } catch (e) {
      showApiError(e);
      return null;
    } finally { setCreatingDraft(false); }
  };

  const createDraft = async () => {
    const r = await ensureDraft();
    if (r) toast.success("Draft created — uploads enabled");
  };

  // Bug (c) — per-section SAVE button. Persists the current Section A-E
  // fields against the draft so the admin can switch tabs / walk away
  // without losing work. Auto-creates the draft on first save. Silent
  // no-op if there's nothing to save yet.
  const saveSection = async (which) => {
    if (savingSection) return;
    if (!reg.email) {
      toast.error("Enter the vendor email first — it identifies the draft.");
      return;
    }
    setSavingSection(true);
    try {
      const d = await ensureDraft();
      if (!d) return;
      const { document_slots, ...fields } = reg;
      await registrationApi.update(d.regId, d.token, fields);
      setLastSavedStep(which);
      toast.success(`Section ${which.toUpperCase()} saved`, {
        description: "You can safely switch tabs or come back later.",
      });
      // Clear the "saved" chip after 4s so it doesn't linger.
      setTimeout(() => setLastSavedStep((cur) => (cur === which ? null : cur)), 4000);
    } catch (e) {
      showApiError(e);
    } finally {
      setSavingSection(false);
    }
  };

  const onDocChange = (slot, meta) => {
    setReg((prev) => {
      const slots = { ...(prev.document_slots || {}) };
      if (meta) slots[slot] = meta; else delete slots[slot];
      return { ...prev, document_slots: slots };
    });
  };

  const submit = async () => {
    if (!reg.email) return toast.error(t("admin_vendor.email_required"));
    const gaps = missingRequired(reg);
    if (gaps.length > 0) {
      toast.error(`${gaps.length} mandatory item(s) still missing`, {
        description: gaps.slice(0, 8).map((g) => `Section ${g.section.toUpperCase()}: ${g.label}`).join("\n") + (gaps.length > 8 ? "\n…" : ""),
        duration: 12000,
      });
      setStep(gaps[0].section);
      return;
    }
    if (mode === "activate" && password.length < 8) return toast.error(t("admin_vendor.pwd_short"));
    // v50j · bug #120 — 6 Section-E (team's "Section K") declarations must
    // all be accepted before the admin can activate / invite the vendor.
    const DECLS = ["decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
                   "decl_data_consent", "decl_fee", "decl_notification"];
    const missing = DECLS.filter((k) => !reg[k]);
    if (missing.length > 0) {
      toast.error(`Section K · ${missing.length} declaration(s) still unchecked`, {
        description: "Open the Declarations tab and tick every box before saving.",
      });
      setStep("e");
      return;
    }
    setSaving(true);
    try {
      const r = await vendorInviteApi.adminCreate({
        email: reg.email,
        mode,
        password: mode === "activate" ? password : undefined,
        registration: reg,
        draft_registration_id: draftId || undefined,
      });
      // Bug #9 fix — build the toast defensively so we never render "undefined"
      const ref = r?.vendor_ref || reg.email;
      const modeMsg = mode === "activate"
        ? t("admin_vendor.ok_activated")
        : t("admin_vendor.ok_verify_sent");
      const created = t("admin_vendor.ok_created") || "Vendor created";
      toast.success(`${created} · ${ref} · ${modeMsg}`);
      // Bug #63 — land back on the Vendors tab so the freshly-created vendor
      // is visible immediately (previously we redirected to /admin which
      // opened the "Dashboard" tab and testers thought the vendor was lost).
      nav("/admin?tab=vendors");
    } catch (e) { showApiError(e); }
    finally { setSaving(false); }
  };

  const STEPS = [
    ["a", t("admin_vendor.step_a")],
    ["b", t("admin_vendor.step_b")],
    ["c", t("admin_vendor.step_c")],
    ["d", t("admin_vendor.step_d")],
    ["e", t("admin_vendor.step_e")],
    ["final", t("admin_vendor.step_final")],
  ];

  const sectionProps = { reg, update, regId: draftId, token: draftToken,
                          onDocChange, ensureDraft, countries };

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="admin-vendor-create">
      <TopBar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 lg:px-10 py-10">
        <div className="flex items-baseline justify-between flex-wrap gap-4">
          <div>
            <div className="pmc-label">{t("admin_vendor.kicker")}</div>
            <h1 className="font-display text-3xl text-brand-navy mt-1">{t("admin_vendor.title")}</h1>
          </div>
          <button onClick={() => nav("/admin?tab=vendors")} className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5"
                  data-testid="admin-vendor-back">{t("admin_vendor.back")}</button>
        </div>

        <VendorStepperNav steps={STEPS} step={step} setStep={setStep} />

        {/* Draft banner */}
        <div className="mt-4">
          {draftId ? (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 px-4 py-2 text-sm flex items-center gap-3"
                 data-testid="admin-vendor-draft-banner">
              <span>Draft <code className="font-mono">{draftId.slice(-6)}</code> · uploads enabled</span>
              <span className="text-emerald-700/70">{Object.keys(reg.document_slots || {}).length} file(s) so far</span>
            </div>
          ) : (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 px-4 py-2 text-sm flex items-center justify-between gap-3"
                 data-testid="admin-vendor-nodraft-banner">
              <span>Enter the vendor email first — the draft is auto-saved the moment you pick a document to upload.</span>
              <button onClick={createDraft} disabled={creatingDraft || !reg.email}
                      data-testid="admin-vendor-create-draft"
                      className="px-4 py-1.5 text-[11px] uppercase tracking-widest border border-emerald-700 text-emerald-800 hover:bg-emerald-700 hover:text-white disabled:opacity-40">
                {creatingDraft ? "Saving…" : "Save now (optional)"}
              </button>
            </div>
          )}
        </div>

        <div className="mt-4 bg-white border border-brand-navy/10 p-8 lg:p-10 space-y-4">
          {step === "a" && (
            <>
              <label className="block text-sm">
                <span className="pmc-label">{t("admin_vendor.email_label")}<InfoDot tip="Vendor's login email. Must be unique. If a draft with this email already exists it will be re-used automatically." /></span>
                <input type="email" required value={reg.email || ""}
                       onChange={(e) => update({ email: e.target.value })}
                       data-testid="admin-vendor-email"
                       className="mt-1 w-full px-4 py-3 border border-brand-navy/20" />
              </label>
              <SectionA {...sectionProps} />
            </>
          )}
          {step === "b" && <SectionB {...sectionProps} />}
          {step === "c" && <SectionC {...sectionProps} />}
          {step === "d" && <SectionD {...sectionProps} />}
          {step === "e" && <SectionE {...sectionProps} />}
          {step !== "final" && (
            <div className="pt-4 mt-4 border-t border-brand-navy/10 flex items-center justify-between gap-3 flex-wrap"
                 data-testid={`admin-vendor-section-save-bar-${step}`}>
              <div className="text-xs text-brand-navy/60">
                {lastSavedStep === step
                  ? <span className="text-emerald-700">✓ Section {step.toUpperCase()} saved just now</span>
                  : "Save what you have entered so far. You can leave the tab and come back."}
              </div>
              <div className="flex gap-2 flex-wrap">
                <button type="button" onClick={() => saveSection(step)} disabled={savingSection || !reg.email}
                        data-testid={`admin-vendor-save-section-${step}`}
                        className="px-6 py-2.5 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-40 disabled:cursor-not-allowed">
                  {savingSection ? "Saving…" : `Save section ${step.toUpperCase()}`}
                </button>
                {/* v51av — explicit Next button (xlsx #6). Users were missing
                    the stepper tabs and getting stuck on Section A. Clicking
                    Next saves the current section then advances. */}
                <button type="button"
                        onClick={async () => {
                          if (reg.email) await saveSection(step);
                          const idx = STEPS.findIndex(([k]) => k === step);
                          if (idx !== -1 && idx + 1 < STEPS.length) {
                            setStep(STEPS[idx + 1][0]);
                          }
                        }}
                        disabled={savingSection}
                        data-testid={`admin-vendor-next-${step}`}
                        className="px-6 py-2.5 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40 disabled:cursor-not-allowed">
                  Save &amp; next →
                </button>
              </div>
            </div>
          )}
          {step === "final" && (
            <VendorActivationStep
              t={t}
              mode={mode} setMode={setMode}
              password={password} setPassword={setPassword}
              saving={saving} onSubmit={submit}
            />
          )}
        </div>
      </main>
    </div>
  );
}
