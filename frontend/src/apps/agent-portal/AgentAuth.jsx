import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";

const inp = "mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white focus:outline-none focus:border-brand-gold";

const Shell = ({ title, children, testid }) => (
  <div className="min-h-screen bg-brand-pale flex items-center justify-center p-6" data-testid={testid}>
    <div className="bg-white border border-brand-navy/15 p-8 w-full max-w-md space-y-4">
      <div className="text-[11px] uppercase tracking-widest text-brand-navy/60">PMC Managers · Onboarding agents</div>
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
    try { await agentApi.join(token, pw); toast.success("Welcome — complete your agent profile"); nav("/agent/me"); }
    catch (e2) { showApiError(e2); } finally { setBusy(false); }
  };
  if (err) return <Shell title="Invitation not valid" testid="agent-join-invalid"><p className="text-sm">{String(err)}</p></Shell>;
  if (!info) return <Shell title="Checking your invitation…" testid="agent-join-loading" />;
  return (
    <Shell title={`Welcome, ${info.name}`} testid="agent-join">
      <p className="text-sm text-brand-navy/70">Create a password for <b>{info.email}</b>. You'll then complete your profile, banking, documents and the agent agreement.</p>
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
    try { await agentApi.login(email, pw); nav("/agent/me"); } catch (e2) { showApiError(e2); } finally { setBusy(false); }
  };
  return (
    <Shell title="Agent sign in" testid="agent-login">
      <form onSubmit={go} className="space-y-3">
        <label className="block text-sm">Email<input type="email" className={inp} required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="agent-login-email" /></label>
        <label className="block text-sm">Password<input type="password" className={inp} required value={pw} onChange={(e) => setPw(e.target.value)} data-testid="agent-login-password" /></label>
        <button className="pmc-btn pmc-btn--primary w-full" disabled={busy} data-testid="agent-login-submit">{busy ? "Signing in…" : "Sign in"}</button>
      </form>
      <p className="text-xs text-brand-navy/60">Agents join by invitation from PMC. <Link to="/" className="underline">Back to PMC Managers</Link></p>
    </Shell>
  );
}
