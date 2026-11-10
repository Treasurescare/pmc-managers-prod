import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import PublicChrome from "@/apps/shared/PublicChrome";
import PasswordInput from "@/components/PasswordInput";
import { BuyerProfileFields, profileReady, profileBody } from "./BuyerProfileFields";
import { buyerApi } from "@/lib/buyerApi";
import { showApiError } from "@/lib/api";

export default function BuyerRegisterE() {
  const [f, setF] = useState({});
  const [acc, setAcc] = useState({ email: "", password: "", confirm: "", terms: false });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const ok = profileReady(f) && /\S+@\S+\.\S+/.test(acc.email) && acc.password.length >= 8 && acc.password === acc.confirm && acc.terms;
  const submit = async () => {
    setBusy(true);
    try { await buyerApi.register({ ...profileBody(f), email: acc.email, password: acc.password }); setDone(true); }
    catch (e) { showApiError(e); } finally { setBusy(false); }
  };
  return (
    <PublicChrome testid="buyer-register-page">
      <div className="pmc-wrap py-10 max-w-3xl">
        <h1 className="text-3xl font-semibold mb-1">Register as a buyer — free</h1>
        <p className="text-sm opacity-70 mb-6">Bid in auctions, make offers and buy products on the PMC marketplace. Only name, email, mobile, country and city are required. PMC verifies every buyer before bidding and buying unlock.</p>
        {done ? (
          <div className="pmc-panel p-5" data-testid="buyer-register-done">
            <h2 className="text-lg font-semibold">Check your inbox</h2>
            <p className="text-sm mt-1">We sent a confirmation link to <b>{acc.email}</b>. After you confirm, PMC reviews your account and notifies you when you can bid and buy. You can already <Link className="underline" to="/login?role=buyer">sign in</Link> after confirming.</p>
          </div>
        ) : (
          <div className="pmc-panel p-5 grid gap-4">
            <BuyerProfileFields f={f} set={setF} prefix="buyer-reg" />
            <div className="grid sm:grid-cols-3 gap-3">
              <label className="text-xs grid gap-1">Email<b className="text-red-700 inline"> *</b><input className="pmc-input" type="email" value={acc.email} onChange={(e) => setAcc({ ...acc, email: e.target.value })} data-testid="buyer-reg-email" /></label>
              <label className="text-xs grid gap-1">Password (8+ characters) *<PasswordInput value={acc.password} onChange={(e) => setAcc({ ...acc, password: e.target.value })} data-testid="buyer-reg-password" /></label>
              <label className="text-xs grid gap-1">Repeat password *<PasswordInput value={acc.confirm} onChange={(e) => setAcc({ ...acc, confirm: e.target.value })} data-testid="buyer-reg-confirm" /></label>
            </div>
            <label className="text-sm flex gap-2 items-start"><input type="checkbox" checked={acc.terms} onChange={(e) => setAcc({ ...acc, terms: e.target.checked })} data-testid="buyer-reg-terms" />I agree to the <Link className="underline" to="/privacy">terms and privacy policy</Link>.</label>
            <button className="pmc-btn pmc-btn--primary pmc-btn--lg" disabled={!ok || busy} onClick={submit} data-testid="buyer-reg-submit">{busy ? "Creating your account…" : "Create my buyer account"}</button>
            <p className="text-sm">Already registered? <Link className="underline" to="/login?role=buyer" data-testid="buyer-reg-signin">Sign in as a buyer</Link></p>
          </div>)}
      </div>
    </PublicChrome>);
}

export function BuyerVerifyEmailE() {
  const [params] = useSearchParams();
  const [st, setSt] = useState("working");
  useEffect(() => {
    buyerApi.verifyEmail(params.get("token") || "").then(() => { setSt("ok"); toast.success("Email confirmed"); }).catch(() => setSt("bad"));
  }, [params]);
  return (
    <PublicChrome testid="buyer-verify-page">
      <div className="pmc-wrap py-16 max-w-xl" data-testid={`buyer-verify-${st}`}>
        {st === "working" && <p>Confirming your email…</p>}
        {st === "ok" && <><h1 className="text-2xl font-semibold">Email confirmed</h1><p className="mt-2 text-sm">PMC will now verify your buyer account and notify you. You can sign in and browse meanwhile.</p><Link className="pmc-btn pmc-btn--primary mt-4 inline-block" to="/login?role=buyer" data-testid="buyer-verify-signin">Sign in as a buyer</Link></>}
        {st === "bad" && <><h1 className="text-2xl font-semibold">This link has expired or is invalid</h1><p className="mt-2 text-sm">Please register again or contact tenders@pmcmanagers.com.</p></>}
      </div>
    </PublicChrome>);
}
