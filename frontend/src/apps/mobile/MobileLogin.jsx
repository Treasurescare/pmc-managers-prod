import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { adminApi, staffApi, vendorApi, formatApiError } from "@/lib/api";
import { biometricAvailable, biometricAuthenticate, saveSecure, loadSecure, platform, registerPush } from "@/lib/mobileBridge";

/**
 * Unified mobile login. Tries staff → admin → vendor in that order.
 * On success routes to the matching dashboard.
 * Also offers biometric quick-login when a previous session token was stored.
 */
export default function MobileLogin() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("admin");
  const [busy, setBusy] = useState(false);
  const [bioReady, setBioReady] = useState(false);
  const [savedEmail, setSavedEmail] = useState(null);

  useEffect(() => {
    (async () => {
      setBioReady(await biometricAvailable());
      setSavedEmail(await loadSecure("pmc.lastEmail"));
    })();
    // Web/native push registration (best-effort)
    registerPush(
      (token) => saveSecure("pmc.pushToken", token),
      (n) => toast(n?.title || "PMC", { description: n?.body }),
    ).catch(() => {});
  }, []);

  const tryDetect = async (email, password) => {
    // 1. Staff / admin unified endpoint (backend picks the right table)
    try {
      const r = await staffApi.login(email, password, role, undefined);
      if (r && !r.mfa_required) return { kind: "staff", role: r.active_role };
    } catch { /* try next */ }
    // 2. Admin-only fallback
    try {
      await adminApi.login(email, password);
      return { kind: "admin", role: "admin" };
    } catch { /* try next */ }
    // 3. Vendor
    try {
      await vendorApi.login(email, password);
      return { kind: "vendor", role: "vendor" };
    } catch { /* fail */ }
    throw new Error("No matching account for that email + password");
  };

  const submit = async (e) => {
    e?.preventDefault?.();
    if (!email || !password) return toast.error("Email + password required");
    setBusy(true);
    try {
      const who = await tryDetect(email, password);
      await saveSecure("pmc.lastEmail", email);
      toast.success(`Signed in as ${who.role}`);
      if (who.kind === "vendor") return nav("/vendor");
      if (who.kind === "admin" || ["admin", "reviewer"].includes(who.role)) return nav("/admin");
      return nav("/staff");
    } catch (err) {
      toast.error(formatApiError(err) || err.message || "Sign-in failed");
    } finally { setBusy(false); }
  };

  const quickBiometric = async () => {
    if (!savedEmail) return toast.error("No previous session to unlock");
    const r = await biometricAuthenticate("Unlock PMC Managers");
    if (!r.ok) return toast.error(`Biometric: ${r.reason}`);
    // Biometric only proves device presence — we still need the session cookie.
    // In production, exchange a device-bound refresh token here.
    toast.success("Biometric verified — please enter your password to complete sign-in");
    setEmail(savedEmail);
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#0b1e3f" }}
         data-testid="mobile-login-page">
      <div className="flex-1 flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm bg-white rounded-2xl p-6 space-y-4 shadow-lg">
          <div className="text-center">
            <div className="text-[10px] tracking-[0.35em] uppercase text-amber-600">PMC Managers</div>
            <h1 className="font-serif text-3xl mt-1">Global Tender Board</h1>
            <p className="text-xs text-slate-500 mt-2">Platform · {platform()}</p>
          </div>
          <label className="block text-sm">
            <span>Email</span>
            <input type="email" required value={email}
                   onChange={(e) => setEmail(e.target.value)}
                   data-testid="mobile-login-email"
                   autoComplete="email"
                   className="mt-1 w-full border rounded-lg px-3 py-3 text-base" />
          </label>
          <label className="block text-sm">
            <span>Password</span>
            <input type="password" required value={password}
                   onChange={(e) => setPassword(e.target.value)}
                   data-testid="mobile-login-password"
                   autoComplete="current-password"
                   className="mt-1 w-full border rounded-lg px-3 py-3 text-base" />
          </label>
          <label className="block text-sm">
            <span>Sign in as</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}
                    data-testid="mobile-login-role"
                    className="mt-1 w-full border rounded-lg px-3 py-3 text-base bg-white">
              <option value="admin">Admin</option>
              <option value="escrow_agent">Escrow Agent</option>
              <option value="certifier">Site Certifier</option>
              <option value="legal_counsel">Legal Counsel</option>
              <option value="accounting">Accounting</option>
              <option value="committee_member">Bid Committee</option>
              <option value="reviewer">Reviewer</option>
              <option value="auditor">Auditor</option>
              <option value="support">Support</option>
              <option value="vendor">Vendor</option>
            </select>
          </label>
          <button type="submit" disabled={busy}
                  data-testid="mobile-login-submit"
                  className="w-full bg-slate-900 text-white rounded-lg py-3 text-sm font-semibold disabled:opacity-50">
            {busy ? "Signing in…" : "Sign in"}
          </button>
          {bioReady && savedEmail && (
            <button type="button" onClick={quickBiometric}
                    data-testid="mobile-login-biometric"
                    className="w-full border rounded-lg py-3 text-sm">
              🔒 Unlock with biometrics
            </button>
          )}
          <div className="text-[11px] text-slate-500 text-center">
            Vendors: <a href="/register" className="underline">register</a> · Public: <a href="/" className="underline">notices</a>
          </div>
        </form>
      </div>
    </div>
  );
}
