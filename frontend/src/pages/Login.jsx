import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import PmcLogo from "@/components/app/PmcLogo";
import { toast } from "sonner";
import { ArrowRight } from "lucide-react";

function homeForRole(role) {
  if (role === "admin") return "/admin";
  if (role === "buyer") return "/buyer";
  return "/vendor";
}

export default function Login() {
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
          <div className="lg:hidden mb-10"><PmcLogo /></div>
          <div className="pmc-label mb-4">Login</div>
          <h1 className="font-serif text-4xl tracking-tight">Access the board</h1>
          <p className="text-sm text-muted-foreground mt-3">Use your registered credentials to continue.</p>

          <form className="mt-10 space-y-5" onSubmit={submit}>
            <div>
              <label className="pmc-label block mb-2">Email</label>
              <input
                data-testid="login-email"
                type="email" required autoComplete="email"
                value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white"
              />
            </div>
            <div>
              <label className="pmc-label block mb-2">Password</label>
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
              {busy ? "Signing in..." : "Sign in"}
              {!busy && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-8 text-sm text-muted-foreground">
            No account? <Link data-testid="login-register-link" className="text-primary underline underline-offset-4" to="/register">Register a new entity</Link>
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
