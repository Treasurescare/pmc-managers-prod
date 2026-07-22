import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import PmcLogo from "@/components/app/PmcLogo";
import LangSwitcher from "@/components/app/LangSwitcher";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { ArrowRight } from "lucide-react";

function homeForRole(role) {
  if (role === "admin") return "/admin";
  if (role === "buyer") return "/buyer";
  return "/vendor";
}

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
function startGoogleAuth() {
  const redirect = window.location.origin + "/auth/callback";
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
}

export default function Login() {
  const { t } = useI18n();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const user = await login(email, password);
      toast.success(`Welcome back, ${user.name}`);
      navigate(homeForRole(user.role));
    } catch (e) {
      const msg = formatApiError(e);
      setErr(msg); toast.error(msg);
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2 bg-background">
      <aside className="hidden lg:block relative border-r overflow-hidden" style={{ backgroundColor: "#050505" }}>
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              'url("https://images.unsplash.com/photo-1623051786552-e46ef84e6c07?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Nzh8MHwxfHNlYXJjaHw0fHxtb2Rlcm4lMjBjb3Jwb3JhdGUlMjBvZmZpY2UlMjBnbGFzcyUyMGFyY2hpdGVjdHVyZXxlbnwwfHx8fDE3ODQ3MDc2Njd8MA&ixlib=rb-4.1.0&q=85")',
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="absolute inset-0 pmc-noise opacity-40" />
        <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(5,5,5,0.6) 0%, rgba(5,5,5,0.95) 100%)" }} />
        <div className="relative h-full flex flex-col p-12 text-white">
          <PmcLogo variant="dark" />
          <div className="mt-auto max-w-md">
            <div className="pmc-label text-white/60 mb-4">Global tender board</div>
            <h2 className="font-serif text-4xl leading-tight tracking-tight">A quieter kind of procurement.</h2>
            <p className="text-white/60 mt-6 text-sm leading-relaxed">
              Login access is restricted to registered vendors, verified buyers and PMC administrators.
            </p>
          </div>
        </div>
      </aside>

      <div className="flex flex-col justify-center px-6 md:px-16 py-14">
        <div className="max-w-md w-full">
          <div className="flex items-center justify-between mb-10">
            <div className="lg:hidden"><PmcLogo /></div>
            <div className="ml-auto"><LangSwitcher testid="login-lang" /></div>
          </div>
          <div className="pmc-label mb-4">{t("nav.login")}</div>
          <h1 className="font-serif text-4xl tracking-tight">{t("login.title")}</h1>
          <p className="text-sm text-muted-foreground mt-3">{t("login.subtitle")}</p>

          <button
            data-testid="login-google"
            type="button" onClick={startGoogleAuth}
            className="mt-8 w-full h-12 border border-foreground text-sm font-medium inline-flex items-center justify-center gap-3 hover:bg-foreground hover:text-white transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden><path fill="#EA4335" d="M24 9.5c3.54 0 6.72 1.22 9.22 3.23l6.87-6.87C36.13 2.06 30.42 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.5 13.6 17.75 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.4-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
            {t("login.google")}
          </button>

          <div className="my-6 flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex-1 border-t" /> or <div className="flex-1 border-t" />
          </div>

          <form className="space-y-5" onSubmit={submit}>
            <div>
              <label className="pmc-label block mb-2">{t("login.email")}</label>
              <input
                data-testid="login-email"
                type="email" required autoComplete="email"
                value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white"
              />
            </div>
            <div>
              <label className="pmc-label block mb-2">{t("login.password")}</label>
              <input
                data-testid="login-password"
                type="password" required autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white"
              />
            </div>
            {err && <div data-testid="login-error" className="border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">{err}</div>}
            <button
              data-testid="login-submit"
              type="submit" disabled={busy}
              className="w-full h-12 bg-primary text-white text-sm font-medium hover:-translate-y-0.5 transition-transform inline-flex items-center justify-center gap-2 disabled:opacity-60 disabled:translate-y-0"
            >
              {busy ? t("login.submitting") : t("login.submit")}
              {!busy && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-8 text-sm text-muted-foreground">
            {t("login.no_account")} <Link data-testid="login-register-link" className="text-primary underline underline-offset-4" to="/register">{t("login.register_link")}</Link>
          </div>

          <div className="mt-12 border-t pt-6 text-xs text-muted-foreground">
            <div className="pmc-label mb-2">Demo</div>
            <div>Admin: <span className="font-mono">admin@pmcmanagers.com / Admin@123</span></div>
            <div>Buyer: <span className="font-mono">buyer@pmcmanagers.com / Buyer@123</span></div>
            <div>Vendor: <span className="font-mono">vendor@example.com / Vendor@123</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
