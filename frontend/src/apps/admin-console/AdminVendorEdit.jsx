import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, vendorInviteApi, mastersGeoApi, showApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import SectionA from "@/apps/registration-portal/sections/SectionA";
import SectionB from "@/apps/registration-portal/sections/SectionB";
import SectionC from "@/apps/registration-portal/sections/SectionC";
import SectionD from "@/apps/registration-portal/sections/SectionD";
import SectionE from "@/apps/registration-portal/sections/SectionE";
import VendorStepperNav from "./vendor/VendorStepperNav";
import { InfoDot } from "@/components/InfoDot";

/**
 * AdminVendorEdit — v51aa.
 * Lets an admin open ANY vendor record (invited / pending-verify / active /
 * not-yet-approved) and edit the entire Sections A–E profile on the vendor's
 * behalf. Used both as a resolution path for the 409 "already active" invite
 * error and as a general bulk-edit facility for every unpublished vendor.
 *
 * Routes to:  /admin/vendors/:vendor_ref/edit
 * Backend  :  GET /api/v1/vendors/admin/:ref/full  +  PATCH …/full
 */
export default function AdminVendorEdit() {
  const { t } = useI18n();
  const nav = useNavigate();
  const { vendor_ref } = useParams();
  const [vendor, setVendor] = useState(null);
  const [reg, setReg] = useState(null);
  const [step, setStep] = useState("a");
  const [countries, setCountries] = useState([{ code: "KZ", name: "Kazakhstan" }]);
  const [saving, setSaving] = useState(false);
  const [savingSection, setSavingSection] = useState(false);
  const [lastSavedStep, setLastSavedStep] = useState(null);

  useEffect(() => {
    document.title = `Edit vendor · ${vendor_ref}`;
    // v52cn — prefer the full 250-country master; fall back to meta if empty.
    mastersGeoApi.countries()
      .then((rows) => {
        if (Array.isArray(rows) && rows.length) { setCountries(rows); return null; }
        return publicApi.countries().catch(() => []);
      })
      .then((rows) => rows && setCountries(Array.isArray(rows) ? rows : []))
      .catch(() => {});
    vendorInviteApi.getFull(vendor_ref)
      .then((v) => {
        setVendor(v);
        setReg({
          email: v.email,
          company_name: v.company_name || v.profile?.company_name || "",
          country: v.country || v.profile?.country || "KZ",
          contact_name: v.contact_name || v.profile?.contact_name || "",
          document_slots: v.profile?.document_slots || {},
          ...(v.profile || {}),
        });
      })
      .catch((e) => { showApiError(e); nav("/admin?tab=vendors"); });
  }, [vendor_ref, nav]);

  const update = (patch) => setReg((prev) => ({ ...prev, ...patch }));

  // Document upload is read-only from this screen (uploads happen through
  // the vendor's own registration-draft or the Admin → New Vendor flow).
  // Pass a no-op so the SectionX components still render their doc blocks.
  const onDocChange = () => {};
  const ensureDraft = async () => null;

  const saveSection = async (which) => {
    if (savingSection) return;
    setSavingSection(true);
    try {
      const { email, document_slots, ...profileFields } = reg;
      await vendorInviteApi.updateFull(vendor_ref, {
        company_name: profileFields.company_name || null,
        country: profileFields.country || null,
        contact_name: profileFields.contact_name || null,
        profile: profileFields,
      });
      setLastSavedStep(which);
      toast.success(`Section ${which.toUpperCase()} saved`, {
        description: "Changes applied to the vendor record immediately.",
      });
      setTimeout(() => setLastSavedStep((cur) => (cur === which ? null : cur)), 4000);
    } catch (e) { showApiError(e); } finally { setSavingSection(false); }
  };

  const saveAllAndClose = async () => {
    if (saving) return;
    setSaving(true);
    try {
      const { email, document_slots, ...profileFields } = reg;
      await vendorInviteApi.updateFull(vendor_ref, {
        company_name: profileFields.company_name || null,
        country: profileFields.country || null,
        contact_name: profileFields.contact_name || null,
        profile: profileFields,
      });
      toast.success(`Vendor ${vendor_ref} updated`);
      nav("/admin?tab=vendors");
    } catch (e) { showApiError(e); } finally { setSaving(false); }
  };

  if (!reg || !vendor) {
    return (
      <div className="min-h-screen bg-brand-pale">
        <TopBar />
        <div className="p-10 text-center text-brand-navy/50" data-testid="admin-vendor-edit-loading">Loading vendor…</div>
      </div>
    );
  }

  const STEPS = [
    ["a", t("admin_vendor.step_a")],
    ["b", t("admin_vendor.step_b")],
    ["c", t("admin_vendor.step_c")],
    ["d", t("admin_vendor.step_d")],
    ["e", t("admin_vendor.step_e")],
  ];

  const sectionProps = { reg, update, regId: null, token: null,
                          onDocChange, ensureDraft, countries };

  const statusBadge = () => {
    if (vendor.is_active && vendor.email_verified) return <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest bg-emerald-100 text-emerald-800 border border-emerald-300">Active</span>;
    if (vendor.email_verified === false) return <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest bg-amber-100 text-amber-800 border border-amber-300">Pending verify</span>;
    return <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest bg-slate-100 text-slate-700 border border-slate-300">Inactive</span>;
  };

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="admin-vendor-edit">
      <TopBar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 lg:px-10 py-10">
        <div className="flex items-baseline justify-between flex-wrap gap-4">
          <div>
            <div className="pmc-label">Edit vendor profile</div>
            <h1 className="font-display text-3xl text-brand-navy mt-1">
              {vendor.company_name || vendor.email}
            </h1>
            <div className="mt-1 text-xs font-mono text-brand-navy-soft flex items-center gap-2">
              <span>{vendor_ref}</span>
              <span>·</span>
              <span>{vendor.email}</span>
              {statusBadge()}
            </div>
          </div>
          <button onClick={() => nav("/admin?tab=vendors")} data-testid="admin-vendor-edit-back"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
            Back to vendors
          </button>
        </div>

        <div className="mt-4 bg-emerald-50 border border-emerald-200 text-emerald-900 px-4 py-2 text-xs"
             data-testid="admin-vendor-edit-hint">
          You can edit the entire Sections A–E profile on the vendor's behalf.
          Each tab has its own Save button; changes apply immediately to the vendor record.
        </div>

        <VendorStepperNav steps={STEPS} step={step} setStep={setStep} />

        <div className="mt-4 bg-white border border-brand-navy/10 p-8 lg:p-10 space-y-4">
          {step === "a" && (
            <>
              <label className="block text-sm">
                <span className="pmc-label">Vendor email<InfoDot tip="Vendor's login email. Not editable here — if the email is wrong, invite the vendor again with the right address." /></span>
                <input type="email" value={reg.email || ""} disabled
                       data-testid="admin-vendor-edit-email"
                       className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-brand-pale/40 text-brand-navy/70" />
              </label>
              <SectionA {...sectionProps} />
            </>
          )}
          {step === "b" && <SectionB {...sectionProps} />}
          {step === "c" && <SectionC {...sectionProps} />}
          {step === "d" && <SectionD {...sectionProps} />}
          {step === "e" && <SectionE {...sectionProps} />}

          <div className="pt-4 mt-4 border-t border-brand-navy/10 flex items-center justify-between gap-3 flex-wrap"
               data-testid={`admin-vendor-edit-save-bar-${step}`}>
            <div className="text-xs text-brand-navy/60">
              {lastSavedStep === step
                ? <span className="text-emerald-700">✓ Section {step.toUpperCase()} saved just now</span>
                : "Save this section, or hit Save & close to persist and return to the vendors list."}
            </div>
            <div className="flex gap-2 flex-wrap">
              <button type="button" onClick={() => saveSection(step)} disabled={savingSection}
                      data-testid={`admin-vendor-edit-save-section-${step}`}
                      className="px-6 py-2.5 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-40">
                {savingSection ? "Saving…" : `Save section ${step.toUpperCase()}`}
              </button>
              <button type="button" onClick={saveAllAndClose} disabled={saving}
                      data-testid="admin-vendor-edit-save-close"
                      className="px-6 py-2.5 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                {saving ? "Saving…" : "Save & close"}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
