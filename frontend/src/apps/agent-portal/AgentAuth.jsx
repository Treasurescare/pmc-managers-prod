import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";

const inp = "mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white focus:outline-none focus:border-brand-gold";

const Shell = ({ title, children, testid }) => (
  <div className="min-h-screen bg-brand-pale flex items-center justify-center p-6" data-testid={testid}>
    <div className="bg-white border border-brand-navy/15 p-8 w-full max-w-md space-y-4">
      <div className="text-[11px] uppercase tracking-widest text-brand-navy/60">PMC Managers · Partners</div>
      <h1 className="font-serif text-2xl text-brand-navy">{title}</h1>
      {children}
    </div>
  </div>
);

export function AgentJoin() {
  const { token } = useParams();
  const nav = useNavigate();
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { agentApi.joinInfo(token).then(setInfo).catch((e) => setErr(e?.response?.data?.detail || "Invalid link")); }, [token]);
  const go = async (e) => {
    e.preventDefault();
    if (pw !== pw2) { toast.error("Passwords do not match"); return; }
    setBusy(true);
    try { await agentApi.join(token, pw); toast.success("Email confirmed — complete your partner profile"); nav("/partner/me"); }
    catch (e2) { showApiError(e2); } finally { setBusy(false); }
  };
  if (err) return <Shell title="Invitation not valid" testid="agent-join-invalid"><p className="text-sm">{String(err)}</p></Shell>;
  if (!info) return <Shell title="Checking your invitation…" testid="agent-join-loading" />;
  return (
    <Shell title={`Welcome, ${info.name}`} testid="agent-join">
      <p className="text-sm text-brand-navy/70">Create a password for <b>{info.email}</b>. You'll then complete your profile, banking, documents and the partner agreement.</p>
      <form onSubmit={go} className="space-y-3">
        <label className="block text-sm">Password (8+ characters)<input type="password" className={inp} minLength={8} required value={pw} onChange={(e) => setPw(e.target.value)} data-testid="agent-join-password" /></label>
        <label className="block text-sm">Confirm password<input type="password" className={inp} minLength={8} required value={pw2} onChange={(e) => setPw2(e.target.value)} data-testid="agent-join-password2" /></label>
        <button className="pmc-btn pmc-btn--primary w-full" disabled={busy} data-testid="agent-join-submit">{busy ? "Creating…" : "Create password & continue"}</button>
      </form>
    </Shell>
  );
}

export function AgentLogin() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { await agentApi.login(email, pw); nav("/partner/me"); } catch (e2) { showApiError(e2); } finally { setBusy(false); }
  };
  return (
    <Shell title="Partner sign in" testid="agent-login">
      <form onSubmit={go} className="space-y-3">
        <label className="block text-sm">Email<input type="email" className={inp} required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="agent-login-email" /></label>
        <label className="block text-sm">Password<input type="password" className={inp} required value={pw} onChange={(e) => setPw(e.target.value)} data-testid="agent-login-password" /></label>
        <button className="pmc-btn pmc-btn--primary w-full" disabled={busy} data-testid="agent-login-submit">{busy ? "Signing in…" : "Sign in"}</button>
      </form>
      <p className="text-xs text-brand-navy/60"><Link to="/forgot-password?portal=partner" className="underline" data-testid="agent-login-forgot">Forgot password?</Link> · New partner? <Link to="/partner/register" className="underline" data-testid="agent-login-register">Apply here</Link> · <Link to="/" className="underline">Back to PMC Managers</Link></p>
    </Shell>
  );
}

export function PartnerRegister() {
  const [f, setF] = useState({ name: "", email: "" });
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const go = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { await agentApi.register(f.email, f.name); setDone(true); } catch (e2) { showApiError(e2); } finally { setBusy(false); }
  };
  if (done) return <Shell title="Check your email" testid="partner-register-done"><p className="text-sm">If this email can be used, we've sent a confirmation link to <b>{f.email}</b>. Open it to set your password and build your partner profile.</p><p className="text-xs"><Link to="/partner/login" className="underline">Partner sign in</Link> · <Link to="/" className="underline">Home</Link></p></Shell>;
  return (
    <Shell title="Become a PMC partner" testid="partner-register">
      <p className="text-sm text-brand-navy/70">Introduce suppliers to PMC Managers and earn commission. Start with your email — we'll send a confirmation link.</p>
      <form onSubmit={go} className="space-y-3">
        <label className="block text-sm">Your name or company<input className={inp} required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="partner-register-name" /></label>
        <label className="block text-sm">Email<input type="email" className={inp} required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="partner-register-email" /></label>
        <button className="pmc-btn pmc-btn--primary w-full" disabled={busy} data-testid="partner-register-submit">{busy ? "Sending…" : "Send confirmation link"}</button>
      </form>
      <p className="text-xs text-brand-navy/60">Already a partner? <Link to="/partner/login" className="underline">Sign in</Link></p>
    </Shell>
  );
}
