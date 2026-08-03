import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, vendorInviteApi, formatApiError } from "@/lib/api";
import TopBar from "@/apps/shared/TopBar";
import SectionA from "@/apps/registration-portal/sections/SectionA";
import SectionB from "@/apps/registration-portal/sections/SectionB";
import SectionC from "@/apps/registration-portal/sections/SectionC";
import SectionD from "@/apps/registration-portal/sections/SectionD";
import SectionE from "@/apps/registration-portal/sections/SectionE";

/**
 * Admin creates a vendor + fills the FULL Sections A–E form on their behalf.
 * Two modes:
 *   - activate  : admin sets a password, vendor is instantly active
 *   - verify    : magic-link email; vendor sets their own password
 *
 * Note on document uploads: to keep the flow single-page, the admin creates the
 * vendor first (mode=verify without a token). If they want to attach documents
 * they can share the resume link with the vendor OR run this in verify mode and
 * the vendor uploads documents themselves. This keeps the schema simple —
 * documents are attached to a registration id which needs the vendor's magic
 * token to authenticate uploads.
 */
export default function AdminVendorCreate() {
  const nav = useNavigate();
  const [step, setStep] = useState("a");
  const [reg, setReg] = useState({ country: "KZ", document_slots: {} });
  const [mode, setMode] = useState("activate");
  const [password, setPassword] = useState("");
  const [countries, setCountries] = useState([{ code: "KZ", name: "Kazakhstan" }]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    document.title = "New vendor · Admin";
    publicApi.countries().then(setCountries).catch(() => {});
  }, []);

  const update = (patch) => setReg((prev) => ({ ...prev, ...patch }));

  const submit = async () => {
    if (!reg.email) return toast.error("Vendor email is required (Section A → Contact email)");
    if (!reg.company_name) return toast.error("Company name is required");
    if (mode === "activate" && password.length < 8) return toast.error("Password must be at least 8 characters when activating immediately");
    setSaving(true);
    try {
      const r = await vendorInviteApi.adminCreate({
        email: reg.email,
        mode,
        password: mode === "activate" ? password : undefined,
        registration: reg,
      });
      toast.success(`Vendor created · ${r.vendor_ref} · ${mode === "activate" ? "activated" : "verify email sent"}`);
      nav("/admin");
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSaving(false); }
  };

  const STEPS = [
    ["a", "Section A · Identity"],
    ["b", "Section B · Contacts"],
    ["c", "Section C · Financials"],
    ["d", "Section D · Compliance"],
    ["e", "Section E · Declarations"],
    ["final", "Activation"],
  ];

  // Section components need regId + token to upload documents — since this is
  // a fresh vendor being created by admin, we defer document uploads to the
  // magic-link flow (or the admin can hand-off the token afterwards). The
  // DocSlotsBlock will hide its uploaders when regId is missing.
  const sectionProps = { reg, update, regId: null, token: null,
                          onDocChange: () => toast.info("Documents are uploaded by the vendor after they receive the verify link."),
                          countries };

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="admin-vendor-create">
      <TopBar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 lg:px-10 py-10">
        <div className="flex items-baseline justify-between flex-wrap gap-4">
          <div>
            <div className="pmc-label">Vendors · Add</div>
            <h1 className="font-display text-3xl text-brand-navy mt-1">Register a vendor on their behalf</h1>
          </div>
          <button onClick={() => nav("/admin")} className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5"
                  data-testid="admin-vendor-back">Back to admin</button>
        </div>

        <nav className="mt-6 flex flex-wrap gap-2" data-testid="admin-vendor-stepper">
          {STEPS.map(([code, label]) => (
            <button key={code} onClick={() => setStep(code)} data-testid={`admin-vendor-step-${code}`}
              className={"px-4 py-2 text-[11px] uppercase tracking-widest border " +
                (step === code ? "bg-brand-navy text-white border-brand-navy" : "bg-white text-brand-navy/70 border-brand-navy/20")}>{label}</button>
          ))}
        </nav>

        <div className="mt-6 bg-white border border-brand-navy/10 p-8 lg:p-10 space-y-4">
          {step === "a" && (
            <>
              <label className="block text-sm">
                <span className="pmc-label">Vendor login email (Section A must include this)</span>
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
            <div className="space-y-6" data-testid="admin-vendor-final">
              <div>
                <div className="pmc-label">Activation mode</div>
                <div className="mt-2 grid gap-3 md:grid-cols-2">
                  <label className={"border p-4 cursor-pointer " + (mode === "activate" ? "border-brand-navy bg-brand-navy/5" : "border-brand-navy/20 bg-white")}>
                    <input type="radio" checked={mode === "activate"} onChange={() => setMode("activate")}
                           data-testid="admin-vendor-mode-activate" className="mr-2" />
                    <strong>Activate immediately</strong>
                    <div className="text-xs text-brand-navy/60 mt-1">
                      You set the password; vendor logs in right away and is asked to change it on first sign-in.
                    </div>
                  </label>
                  <label className={"border p-4 cursor-pointer " + (mode === "verify" ? "border-brand-navy bg-brand-navy/5" : "border-brand-navy/20 bg-white")}>
                    <input type="radio" checked={mode === "verify"} onChange={() => setMode("verify")}
                           data-testid="admin-vendor-mode-verify" className="mr-2" />
                    <strong>Send verify-email</strong>
                    <div className="text-xs text-brand-navy/60 mt-1">
                      Vendor receives a magic link, verifies their email and sets their own password.
                    </div>
                  </label>
                </div>
              </div>
              {mode === "activate" && (
                <label className="block text-sm">
                  <span className="pmc-label">Initial password (min 8 chars — vendor will be prompted to change)</span>
                  <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                         data-testid="admin-vendor-password"
                         className="mt-1 w-full px-4 py-3 border border-brand-navy/20" />
                </label>
              )}
              <div className="flex justify-end gap-2">
                <button type="button" onClick={submit} disabled={saving}
                        data-testid="admin-vendor-submit"
                        className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
                  {saving ? "Saving…" : (mode === "activate" ? "Create & activate vendor" : "Create & send verify email")}
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
