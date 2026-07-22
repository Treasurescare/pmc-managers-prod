import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import PmcLogo from "@/components/app/PmcLogo";
import { toast } from "sonner";
import { ArrowRight } from "lucide-react";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "vendor" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const update = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const user = await register(form);
      toast.success("Account created");
      if (user.role === "vendor") navigate("/vendor/profile");
      else if (user.role === "buyer") navigate("/buyer");
      else navigate("/");
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
            <div className="pmc-label text-white/60 mb-4">Vendor & Buyer onboarding</div>
            <h2 className="font-serif text-4xl leading-tight tracking-tight">Register your entity in minutes.</h2>
            <p className="text-white/60 mt-6 text-sm leading-relaxed">
              After signup, vendors complete a jurisdiction-aware KYC profile. Buyers can immediately post tenders.
            </p>
            <div className="mt-10 grid grid-cols-3 gap-6 border-t border-white/20 pt-6">
              <StepMini n="01" label="Create account" />
              <StepMini n="02" label="Company profile" />
              <StepMini n="03" label="Bid or publish" />
            </div>
          </div>
        </div>
      </aside>

      <div className="flex flex-col justify-center px-6 md:px-16 py-14">
        <div className="max-w-lg w-full">
          <div className="lg:hidden mb-10"><PmcLogo /></div>
          <div className="pmc-label mb-4">Register</div>
          <h1 className="font-serif text-4xl tracking-tight">Create an account</h1>
          <p className="text-sm text-muted-foreground mt-3">Choose whether you're joining as a vendor (bidder) or buyer (issuer).</p>

          <form className="mt-8 space-y-5" onSubmit={submit}>
            <div className="grid grid-cols-2 gap-0 border">
              {[{ id: "vendor", label: "Vendor" }, { id: "buyer", label: "Buyer" }].map((r) => (
                <button
                  type="button"
                  key={r.id}
                  data-testid={`register-role-${r.id}`}
                  onClick={() => setForm((s) => ({ ...s, role: r.id }))}
                  className={`h-12 text-sm font-medium border-r last:border-r-0 transition-colors ${
                    form.role === r.id ? "bg-primary text-white" : "bg-white text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>

            <div>
              <label className="pmc-label block mb-2">{form.role === "vendor" ? "Company / Contact name" : "Full name"}</label>
              <input
                data-testid="register-name"
                type="text" required value={form.name} onChange={update("name")}
                className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white"
              />
            </div>
            <div>
              <label className="pmc-label block mb-2">Work email</label>
              <input
                data-testid="register-email"
                type="email" required value={form.email} onChange={update("email")}
                className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white"
              />
            </div>
            <div>
              <label className="pmc-label block mb-2">Password</label>
              <input
                data-testid="register-password"
                type="password" required minLength={6} value={form.password} onChange={update("password")}
                className="w-full h-12 px-4 border border-input focus:border-primary focus:outline-none bg-white"
              />
              <p className="text-xs text-muted-foreground mt-2">Minimum 6 characters.</p>
            </div>

            {err && <div data-testid="register-error" className="border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">{err}</div>}

            <button
              data-testid="register-submit"
              type="submit" disabled={busy}
              className="w-full h-12 bg-primary text-white text-sm font-medium hover:-translate-y-0.5 transition-transform inline-flex items-center justify-center gap-2 disabled:opacity-60 disabled:translate-y-0"
            >
              {busy ? "Creating..." : "Continue"}
              {!busy && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-8 text-sm text-muted-foreground">
            Already registered? <Link data-testid="register-login-link" className="text-primary underline underline-offset-4" to="/login">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function StepMini({ n, label }) {
  return (
    <div>
      <div className="font-mono text-xs text-white/50">{n}</div>
      <div className="text-sm text-white mt-1">{label}</div>
    </div>
  );
}
