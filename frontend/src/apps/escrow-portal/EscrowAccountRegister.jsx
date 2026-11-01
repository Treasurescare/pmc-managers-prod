/**
 * EscrowAccountRegister — v52d gate screen.
 *
 * Account-first replacement for the old magic-link draft. Captures just
 * {email, legal entity name, primary contact phone, password} and emails
 * a verify link. The 5-section wizard is only reachable once the account
 * exists and the user is signed in.
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, showApiError, mastersApi } from "@/lib/api";
import PhonePrefixInput from "./PhonePrefixInput";
import PasswordInput from "@/components/PasswordInput";

export default function EscrowAccountRegister() {
  const [form, setForm] = useState({
    email: "", legal_name: "",
    primary_contact_phone: "", password: "", confirm: "",
  });
  const [saving, setSaving] = useState(false);
  const [sent, setSent] = useState(false);
  const [countries, setCountries] = useState([]);
  useMemo(() => {
    mastersApi.listCountriesPublic()
      .then(setCountries).catch(() => setCountries([]));
  }, []);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 8) return toast.error("Password must be at least 8 characters");
    if (form.password !== form.confirm) return toast.error("Passwords don't match");
    setSaving(true);
    try {
      await api.post("/api/v1/escrow-accounts/register", {
        email: form.email.trim(),
        legal_name: form.legal_name.trim(),
        primary_contact_phone: form.primary_contact_phone.trim(),
        password: form.password,
      });
      setSent(true);
    } catch (err) {
      showApiError(err);
    } finally { setSaving(false); }
  };

  const resend = async () => {
    try {
      await api.post("/api/v1/escrow-accounts/auth/resend-verify",
                      { email: form.email.trim() });
      toast.success("Verification email re-sent");
    } catch (err) { showApiError(err); }
  };

  if (sent) {
    return (
      <div className="max-w-xl mx-auto px-6 py-16 text-center" data-testid="escrow-reg-sent">
        <div className="inline-block text-5xl mb-4">✉</div>
        <h1 className="font-serif text-3xl text-brand-navy">Check your inbox</h1>
        <p className="mt-3 text-sm text-brand-navy/70">
          We've sent a verification link to <strong>{form.email}</strong>.
          Click it to activate your account, then sign in to complete the
          five registration sections at your own pace.
        </p>
        <p className="mt-2 text-xs text-brand-navy/50">
          The link expires in 24 hours. Didn't get it? Check spam, or
          <button type="button" onClick={resend} data-testid="escrow-reg-resend"
                  className="ml-1 underline text-brand-navy">resend it</button>.
        </p>
        <div className="mt-8">
          <Link to="/escrow/login" data-testid="escrow-reg-to-login"
                className="text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white px-5 py-2">
            Go to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto px-6 py-12" data-testid="escrow-register-gate">
      <h1 className="font-serif text-3xl text-brand-navy">Register as an escrow institution</h1>
      <p className="mt-2 text-sm text-brand-navy/70">
        PMC Managers partners with licensed banks and trustee companies to
        hold EMD and milestone funds under dual-signature control.
        Start by creating a primary-contact account — we'll email a link
        to verify your address. Signatories claim their logins after
        approval.
      </p>

      <form onSubmit={submit} className="mt-8 space-y-5">
        <Field label="Primary contact email">
          <input type="email" required value={form.email}
                 data-testid="escrow-reg-email"
                 onChange={(e) => set("email", e.target.value)}
                 className="w-full px-3 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-gold" />
        </Field>
        <Field label="Legal entity name">
          <input required value={form.legal_name}
                 data-testid="escrow-reg-name"
                 onChange={(e) => set("legal_name", e.target.value)}
                 className="w-full px-3 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-gold" />
        </Field>
        <Field label="Primary contact phone">
          <PhonePrefixInput testId="escrow-reg-phone"
                            value={form.primary_contact_phone}
                            onChange={(v) => set("primary_contact_phone", v)}
                            countries={countries} />
        </Field>
        <Field label="Password (min 8 characters)">
          <PasswordInput type="password" required minLength={8}
                 data-testid="escrow-reg-password"
                 value={form.password}
                 onChange={(e) => set("password", e.target.value)}
                 className="w-full px-3 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-gold" />
        </Field>
        <Field label="Confirm password">
          <PasswordInput type="password" required minLength={8}
                 data-testid="escrow-reg-confirm"
                 value={form.confirm}
                 onChange={(e) => set("confirm", e.target.value)}
                 className="w-full px-3 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-gold" />
        </Field>

        <div className="flex items-center justify-between pt-2">
          <Link to="/escrow/login" className="text-xs text-brand-navy/60 hover:text-brand-navy underline"
                data-testid="escrow-reg-have-account">
            Already have an account? Sign in
          </Link>
          <button type="submit" disabled={saving}
                  data-testid="escrow-reg-submit"
                  className="px-6 py-3 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
            {saving ? "Sending…" : "Send verify email"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[11px] uppercase tracking-widest text-brand-navy/70 mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
