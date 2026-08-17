import { useState } from "react";
import { toast } from "sonner";
import { authApi, formatApiError } from "@/lib/api";

/**
 * ForgotUsernameModal — helps a user recover their sign-in email.
 * Two modes:
 *  - "lookup"  : type phone or company name → masked email hint(s)
 *  - "request" : ask an admin to help; submits a help ticket
 */
export default function ForgotUsernameModal({ open, onClose }) {
  const [mode, setMode] = useState("lookup");
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         data-testid="forgot-username-modal">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white border border-brand-navy/10 shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-brand-navy/10">
          <div>
            <div className="pmc-label">Recover access</div>
            <div className="font-display text-brand-navy text-lg leading-tight">
              Find my username
            </div>
          </div>
          <button onClick={onClose} data-testid="forgot-close"
                  className="w-9 h-9 border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
            ✕
          </button>
        </div>

        <div className="flex border-b border-brand-navy/10 text-[11px] font-semibold uppercase tracking-widest">
          {[["lookup", "Look me up"], ["request", "Ask an admin"]].map(([k, l]) => (
            <button key={k} onClick={() => setMode(k)}
                    data-testid={`forgot-tab-${k}`}
                    className={"px-6 py-3 " +
                      (mode === k ? "bg-brand-navy text-white"
                                  : "text-brand-navy/60 hover:bg-brand-navy/5")}>
              {l}
            </button>
          ))}
        </div>

        {mode === "lookup" ? <Lookup /> : <RequestHelp onClose={onClose} />}
      </div>
    </div>
  );
}

function Lookup() {
  const [phone, setPhone] = useState("");
  const [company, setCompany] = useState("");
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (!phone && !company) return toast.error("Enter phone or company name.");
    setBusy(true); setResults(null);
    try {
      const r = await authApi.usernameLookup({ phone: phone || null, company_name: company || null });
      setResults(r.matches || []);
      if ((r.matches || []).length === 0) {
        toast.message("No match found. Try the “Ask an admin” tab.");
      }
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="p-6 space-y-4" data-testid="forgot-lookup-form">
      <p className="text-sm text-brand-navy/70">
        Enter either your phone or your company name. We'll show a masked
        version of the email you registered with, so you can recognise it.
      </p>
      <Field label="Phone" value={phone} onChange={setPhone} testId="forgot-phone" />
      <Field label="Company name" value={company} onChange={setCompany} testId="forgot-company" />
      <button type="submit" disabled={busy} data-testid="forgot-lookup-submit"
              className="w-full px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
        {busy ? "Searching…" : "Find my username"}
      </button>
      {results && results.length > 0 && (
        <div className="border-t border-brand-navy/10 pt-4 space-y-2"
             data-testid="forgot-lookup-results">
          <div className="pmc-label">Matches</div>
          {results.map((r, i) => (
            <div key={i} className="flex items-center justify-between text-sm">
              <div>
                <div className="font-semibold text-brand-navy">{r.hint}</div>
                <div className="text-xs text-brand-navy/60">{r.role} · {r.label}</div>
              </div>
            </div>
          ))}
          <p className="text-xs text-brand-navy/60 pt-2">
            If this looks right, use your full email to sign in. If it doesn't,
            switch to “Ask an admin”.
          </p>
        </div>
      )}
    </form>
  );
}

function RequestHelp({ onClose }) {
  const [full_name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [company_name, setCompany] = useState("");
  const [message, setMessage] = useState("");
  const [kind, setKind] = useState("forgot-username");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!full_name || message.length < 5) return toast.error("Name and message are required.");
    setBusy(true);
    try {
      await authApi.helpRequest({ full_name, email: email || null, phone: phone || null,
                                  company_name: company_name || null, message, kind });
      toast.success("Request sent. An admin will reach out shortly.");
      onClose && onClose();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="p-6 space-y-3" data-testid="forgot-request-form">
      <p className="text-sm text-brand-navy/70">
        Send a message to the PMC admin team. Fill in as much as you can
        remember — they'll get back to you with your username and can reset
        your password if needed.
      </p>
      <Field label="Full name" value={full_name} onChange={setName} testId="forgot-req-name" required />
      <Field label="Recovery email (optional)" value={email} onChange={setEmail} testId="forgot-req-email" type="email" />
      <Field label="Phone (optional)" value={phone} onChange={setPhone} testId="forgot-req-phone" />
      <Field label="Company (optional)" value={company_name} onChange={setCompany} testId="forgot-req-company" />
      <label className="block text-sm">
        <span className="pmc-label">What do you need help with?</span>
        <select value={kind} onChange={(e) => setKind(e.target.value)}
                data-testid="forgot-req-kind"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 text-brand-navy bg-white">
          <option value="forgot-username">Forgot my username / email</option>
          <option value="forgot-password">Forgot my password</option>
          <option value="other">Something else</option>
        </select>
      </label>
      <label className="block text-sm">
        <span className="pmc-label">Message</span>
        <textarea rows={4} required value={message} onChange={(e) => setMessage(e.target.value)}
                  data-testid="forgot-req-message"
                  className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
      </label>
      <button type="submit" disabled={busy} data-testid="forgot-request-submit"
              className="w-full px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
        {busy ? "Sending…" : "Send request to admin"}
      </button>
    </form>
  );
}

function Field({ label, value, onChange, testId, type = "text", required = false }) {
  return (
    <label className="block text-sm">
      <span className="pmc-label">{label}</span>
      <input type={type} required={required} value={value}
             onChange={(e) => onChange(e.target.value)}
             data-testid={testId}
             className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
    </label>
  );
}
