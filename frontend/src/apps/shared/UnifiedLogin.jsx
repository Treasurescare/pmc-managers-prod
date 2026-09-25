import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ShieldCheck, Building2, Handshake, Briefcase, Store,
  ArrowLeft, ArrowRight, KeyRound, Mail,
} from "lucide-react";
import { adminApi, staffApi, vendorApi, showApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import ForgotUsernameModal from "@/apps/shared/ForgotUsernameModal";

/**
 * v46k — Five-Portal Sovereign Sign-in Gateway
 *
 * Replaces the old 2-card (Employee / Vendor) picker with 5 distinctive
 * credential badges. Each portal has its own colour system, badge kicker,
 * icon and descriptor. Selecting a card reveals the credential form for
 * that portal — no page transitions, no dropdown of 12 roles.
 */

const PORTALS = [
  {
    id: "admin",
    role: "admin",
    kind: "staff",
    title: "System Administrator",
    badge: "SUPERVISORY · ROOT",
    icon: ShieldCheck,
    accent: "bg-amber-500",
    ring: "ring-amber-500/60",
    border: "border-amber-500/40",
    grad: "from-slate-950 via-slate-900 to-slate-950",
    testid: "portal-card-admin",
    description: "Configure the platform, provision users, curate the master catalog, and audit every transaction.",
    goto: "/admin",
  },
  {
    id: "management",
    role: "management",
    kind: "staff",
    title: "PMC Management",
    badge: "EXECUTIVE",
    icon: Building2,
    accent: "bg-blue-500",
    ring: "ring-blue-500/60",
    border: "border-blue-500/40",
    grad: "from-slate-950 via-blue-950 to-slate-950",
    testid: "portal-card-management",
    description: "Executive oversight of tender awards, committee outcomes, and escrow-level financials.",
    goto: "/staff",
  },
  {
    id: "partners",
    role: "partner",
    kind: "staff",
    title: "Strategic Partners",
    badge: "GOC · BANK · REGULATOR",
    icon: Handshake,
    accent: "bg-cyan-500",
    ring: "ring-cyan-500/60",
    border: "border-cyan-500/40",
    grad: "from-slate-950 via-cyan-950 to-slate-950",
    testid: "portal-card-partners",
    description: "Bank-guarantee verification, regulatory audit hooks, and co-procurement dashboards.",
    goto: "/staff",
  },
  {
    id: "agents",
    role: "agent",
    kind: "staff",
    title: "Procurement Agents",
    badge: "FIELD OPS",
    icon: Briefcase,
    accent: "bg-emerald-500",
    ring: "ring-emerald-500/60",
    border: "border-emerald-500/40",
    grad: "from-slate-950 via-emerald-950 to-slate-950",
    testid: "portal-card-agents",
    description: "Draft tenders, review bidder dossiers, publish corrigenda, and verify BOQ line items.",
    goto: "/staff",
  },
  {
    id: "vendors",
    role: "vendor",
    kind: "vendor",
    title: "Registered Vendors",
    badge: "BIDDER",
    icon: Store,
    accent: "bg-brand-gold",
    ring: "ring-amber-400/60",
    border: "border-amber-400/50",
    grad: "from-slate-950 via-amber-950 to-slate-950",
    testid: "portal-card-vendors",
    description: "Purchase tender packs, submit digital bids, join live reverse auctions, sign contracts.",
    goto: "/vendor",
  },
];

export default function UnifiedLogin() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [selected, setSelected] = useState(null);
  const [forgotOpen, setForgotOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-brand-navy-sovereign text-white" data-testid="unified-login-page">
      <TopBar dark />

      {/* Gold seal strip */}
      <div className="h-[3px] bg-gradient-to-r from-transparent via-brand-gold to-transparent opacity-70" />

      <main className="flex-1 max-w-7xl mx-auto w-full px-5 sm:px-8 lg:px-12 py-10 lg:py-16">
        {/* Editorial header */}
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-[0.3em] text-brand-gold">
            PMC Managers · Sovereign Gateway
          </div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl leading-[1.05] mt-4 text-white">
            Select your <span className="italic text-brand-gold">command</span> portal
          </h1>
          <p className="mt-5 text-white/70 text-base sm:text-lg leading-relaxed max-w-2xl">
            Five distinct credentials safeguard PMC procurement operations across
            Kazakhstan and the wider CIS. Choose the door that matches your role —
            each portal opens a different set of dashboards, permissions and audit rails.
          </p>
        </div>

        {/* Portal grid */}
        {!selected && (
          <section className="mt-10 grid gap-4 sm:gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
                   data-testid="portal-grid">
            {PORTALS.map((p) => (
              <PortalCard key={p.id} portal={p} onSelect={() => setSelected(p)} />
            ))}
          </section>
        )}

        {/* Credential panel for selected portal */}
        {selected && (
          <section className="mt-10 grid gap-8 lg:grid-cols-[7fr_5fr] items-start">
            <PortalCredentialForm portal={selected} nav={nav} t={t} />
            <PortalSideRail portal={selected} onBack={() => setSelected(null)} onForgot={() => setForgotOpen(true)} />
          </section>
        )}

        {/* Utility row */}
        <div className="mt-10 flex flex-col sm:flex-row items-start sm:items-center gap-4 text-xs text-white/60">
          <button onClick={() => setForgotOpen(true)}
                  data-testid="login-forgot-username"
                  className="underline hover:text-brand-gold">
            Forgot your username?
          </button>
          <span className="hidden sm:inline text-white/25">·</span>
          <a href="/" data-testid="login-browse-notices" className="underline hover:text-brand-gold">
            Browse the public notice board instead
          </a>
          <span className="hidden sm:inline text-white/25">·</span>
          <a href="/register" data-testid="login-vendor-register" className="underline hover:text-brand-gold">
            Register as a supplier
          </a>
        </div>

        <ForgotUsernameModal open={forgotOpen} onClose={() => setForgotOpen(false)} />
      </main>

      {/* Sovereign footer stripe */}
      <div className="border-t border-white/10 py-5 text-center text-[10px] uppercase tracking-[0.35em] text-white/40">
        © {new Date().getFullYear()} PMC Managers Limited · v46k Sovereign Gateway
      </div>
    </div>
  );
}

function PortalCard({ portal, onSelect }) {
  const Icon = portal.icon;
  return (
    <button type="button" onClick={onSelect} data-testid={portal.testid}
            className={`group relative overflow-hidden text-left border ${portal.border} bg-gradient-to-br ${portal.grad} p-6 min-h-[220px] flex flex-col justify-between transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:${portal.ring} hover:ring-2 focus:outline-none focus-visible:ring-2 focus-visible:${portal.ring}`}>
      {/* diagonal accent stripe */}
      <div className={`absolute top-0 right-0 w-[140px] h-[140px] ${portal.accent} opacity-[0.08] rotate-45 -translate-y-16 translate-x-8 pointer-events-none`} />

      <div>
        <div className={`inline-flex items-center justify-center w-11 h-11 border ${portal.border} ${portal.accent}/10`}>
          <Icon className="w-5 h-5 text-white" strokeWidth={1.4} />
        </div>
        <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-white/55 mt-4">
          {portal.badge}
        </div>
        <h3 className="font-display text-xl mt-1.5 text-white leading-tight">{portal.title}</h3>
        <p className="text-[13px] text-white/60 mt-2 leading-relaxed">{portal.description}</p>
      </div>

      <div className="mt-5 flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.25em] text-white/70 group-hover:text-brand-gold">
        Enter portal
        <ArrowRight className="w-3.5 h-3.5" strokeWidth={2} />
      </div>
    </button>
  );
}

function PortalCredentialForm({ portal, nav, t }) {
  const Icon = portal.icon;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !password) return toast.error("Enter your email and password to continue.");
    setBusy(true);
    try {
      if (portal.kind === "vendor") {
        const vr = await vendorApi.login(email, password);
        toast.success("Signed in · vendor");
        if (vr && vr.must_change_password) return nav("/vendor/change-password");
        return nav("/vendor");
      }
      // staff kinds — always try staff login with the portal role first, then admin
      try {
        const r = await staffApi.login(email, password, portal.role, undefined);
        if (r && !r.mfa_required) {
          toast.success(`Signed in · ${r.active_role}`);
          if (["admin", "reviewer"].includes(r.active_role)) return nav("/admin");
          return nav(portal.goto);
        }
      } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("staff login skipped:", err?.response?.status);
      }
      // fall back to admin cookie realm for admin portal only
      if (portal.id === "admin") {
        try {
          await adminApi.login(email, password);
          toast.success("Signed in · admin");
          return nav("/admin");
        } catch (err) {
          if (process.env.NODE_ENV !== "production") console.debug("admin login skipped:", err?.response?.status);
        }
      }
      toast.error(`Those credentials don't match a ${portal.title} account.`);
    } catch (err) {
      showApiError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} data-testid={`portal-form-${portal.id}`}
          className={`relative bg-white/[0.03] border ${portal.border} p-6 sm:p-9 space-y-5`}>
      <div className="flex items-start gap-4 pb-5 border-b border-white/10">
        <div className={`w-14 h-14 border ${portal.border} flex items-center justify-center ${portal.accent}/10`}>
          <Icon className="w-6 h-6 text-white" strokeWidth={1.4} />
        </div>
        <div>
          <div className="text-[10px] font-mono uppercase tracking-[0.3em] text-brand-gold">{portal.badge}</div>
          <h2 className="font-display text-2xl sm:text-3xl text-white leading-tight mt-1">{portal.title}</h2>
        </div>
      </div>

      <div className="space-y-4">
        <label className="block">
          <span className="text-[10px] font-mono uppercase tracking-[0.25em] text-white/60 inline-flex items-center gap-2">
            <Mail className="w-3 h-3" strokeWidth={2} /> Work email
          </span>
          <input type="email" required autoFocus value={email}
                 onChange={(e) => setEmail(e.target.value)}
                 data-testid={`portal-${portal.id}-email`}
                 autoComplete="email"
                 className="mt-2 w-full bg-transparent border-b border-white/25 focus:border-brand-gold focus:outline-none text-white text-base py-2.5 placeholder-white/25"
                 placeholder="you@pmcmanagers.com" />
        </label>
        <label className="block">
          <span className="text-[10px] font-mono uppercase tracking-[0.25em] text-white/60 inline-flex items-center gap-2">
            <KeyRound className="w-3 h-3" strokeWidth={2} /> Password
          </span>
          <input type="password" required value={password}
                 onChange={(e) => setPassword(e.target.value)}
                 data-testid={`portal-${portal.id}-password`}
                 autoComplete="current-password"
                 className="mt-2 w-full bg-transparent border-b border-white/25 focus:border-brand-gold focus:outline-none text-white text-base py-2.5 placeholder-white/25"
                 placeholder="••••••••••" />
        </label>
      </div>

      <button type="submit" disabled={busy}
              data-testid={`portal-${portal.id}-submit`}
              className={`mt-6 w-full px-8 py-4 text-[12px] font-semibold uppercase tracking-[0.25em] text-brand-navy-sovereign bg-brand-gold hover:bg-brand-gold-hover transition-colors disabled:opacity-50`}>
        {busy ? "Verifying…" : `Enter ${portal.title}`}
      </button>

      <div className="text-[11px] font-mono uppercase tracking-[0.2em] text-white/40 pt-3 border-t border-white/10">
        Session secured · TLS 1.3 · Full audit log
      </div>
    </form>
  );
}

function PortalSideRail({ portal, onBack, onForgot }) {
  return (
    <aside className={`border ${portal.border} bg-white/[0.02] p-6 sm:p-8 sticky top-6`}>
      <button type="button" onClick={onBack} data-testid="portal-back"
              className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.25em] text-white/60 hover:text-brand-gold">
        <ArrowLeft className="w-3.5 h-3.5" strokeWidth={2} /> Choose a different portal
      </button>

      <div className="mt-8">
        <div className="text-[10px] font-mono uppercase tracking-[0.3em] text-brand-gold">Portal briefing</div>
        <h3 className="font-display text-2xl text-white mt-2 leading-tight">{portal.title}</h3>
        <p className="text-sm text-white/70 mt-3 leading-relaxed">{portal.description}</p>
      </div>

      <div className="mt-8 space-y-2 text-[13px] text-white/80">
        <Bullet>Role-scoped dashboards & permissions</Bullet>
        <Bullet>Encrypted session cookie, per-portal audit trail</Bullet>
        <Bullet>Multi-factor authentication when configured</Bullet>
      </div>

      <div className="mt-8 pt-5 border-t border-white/10 text-[11px] text-white/50 space-y-2">
        <button onClick={onForgot} className="underline hover:text-brand-gold">Forgot your username or password?</button>
        <div>Need access? Contact your administrator.</div>
      </div>
    </aside>
  );
}

function Bullet({ children }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-1.5 h-1.5 mt-2 bg-brand-gold flex-none" />
      <div>{children}</div>
    </div>
  );
}
