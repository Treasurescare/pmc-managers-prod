import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, vendorInviteApi, registrationApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import SectionA from "@/apps/registration-portal/sections/SectionA";
import SectionB from "@/apps/registration-portal/sections/SectionB";
import SectionC from "@/apps/registration-portal/sections/SectionC";
import SectionD from "@/apps/registration-portal/sections/SectionD";
import SectionE from "@/apps/registration-portal/sections/SectionE";
import VendorStepperNav from "./vendor/VendorStepperNav";
import VendorActivationStep from "./vendor/VendorActivationStep";

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

  useEffect(() => {
    document.title = "New vendor · Admin";
    publicApi.countries().then(setCountries).catch(() => {});
  }, []);

  const update = (patch) => setReg((prev) => ({ ...prev, ...patch }));

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
      toast.error(formatApiError(e));
      return null;
    } finally { setCreatingDraft(false); }
  };

  const createDraft = async () => {
    const r = await ensureDraft();
    if (r) toast.success("Draft created — uploads enabled");
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
    if (!reg.company_name) return toast.error(t("admin_vendor.company_required"));
    if (mode === "activate" && password.length < 8) return toast.error(t("admin_vendor.pwd_short"));
    setSaving(true);
    try {
      const r = await vendorInviteApi.adminCreate({
        email: reg.email,
        mode,
        password: mode === "activate" ? password : undefined,
        registration: reg,
        draft_registration_id: draftId || undefined,
      });
      const modeMsg = mode === "activate" ? t("admin_vendor.ok_activated") : t("admin_vendor.ok_verify_sent");
      toast.success(`${t("admin_vendor.ok_created")} · ${r.vendor_ref} · ${modeMsg}`);
      nav("/admin");
    } catch (e) { toast.error(formatApiError(e)); }
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
          <button onClick={() => nav("/admin")} className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5"
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
            <div className="bg-brand-navy/5 border border-brand-navy/20 text-brand-navy px-4 py-2 text-sm flex items-center justify-between gap-3"
                 data-testid="admin-vendor-nodraft-banner">
              <span>Enter the vendor email first — the draft is auto-saved the moment you pick a document to upload.</span>
              <button onClick={createDraft} disabled={creatingDraft || !reg.email}
                      data-testid="admin-vendor-create-draft"
                      className="px-4 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-40">
                {creatingDraft ? "Saving…" : "Save now (optional)"}
              </button>
            </div>
          )}
        </div>

        <div className="mt-4 bg-white border border-brand-navy/10 p-8 lg:p-10 space-y-4">
          {step === "a" && (
            <>
              <label className="block text-sm">
                <span className="pmc-label">{t("admin_vendor.email_label")}</span>
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
