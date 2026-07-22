import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Globe2, ShieldCheck, ClipboardList, ChevronRight } from "lucide-react";
import api from "@/lib/api";

const NAV_LINKS = [
  { to: "#platform", label: "Platform" },
  { to: "#how", label: "How it works" },
  { to: "/login", label: "Sign in" },
];

function Logo({ className = "h-10 w-10" }) {
  return <img src="/pmc-logo.png" alt="PMC" className={className} />;
}

export default function Landing() {
  const [stats, setStats] = useState(null);
  const [liveVisible, setLiveVisible] = useState(false);

  useEffect(() => {
    api.get("/public/stats").then(({ data }) => setStats(data)).catch(() => setStats({}));
    // Fade-up on mount for the live card
    const t = setTimeout(() => setLiveVisible(true), 250);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="min-h-screen bg-brand-pale">
      {/* HERO — split layout */}
      <section className="flex flex-col lg:flex-row lg:min-h-screen">
        {/* LEFT: navy content */}
        <div className="relative bg-brand-navy text-white px-8 lg:px-16 py-20 lg:py-24 lg:w-1/2 flex flex-col justify-center">
          <header className="absolute top-8 left-8 lg:top-12 lg:left-16 flex items-center gap-4" data-testid="landing-brand-header">
            <Logo className="h-12 w-12" />
            <div>
              <div className="text-[0.6875rem] font-semibold tracking-[0.25em] uppercase">PMC Managers</div>
              <div className="text-[0.625rem] tracking-[0.15em] uppercase opacity-50">Global Tender Board</div>
            </div>
          </header>

          <nav className="absolute top-8 right-8 lg:top-12 lg:right-16 hidden md:flex items-center gap-6 text-[0.6875rem] tracking-[0.15em] uppercase text-white/70">
            {NAV_LINKS.map((n) => (
              <a key={n.to} href={n.to} className="hover:text-white transition-colors">{n.label}</a>
            ))}
          </nav>

          <div className="mt-24 lg:mt-0 space-y-8" data-testid="landing-hero">
            <div className="pmc-pill pmc-pill-navy" data-testid="landing-hero-pill">
              <span>Est. 2026</span>
              <span className="opacity-40">·</span>
              <span>30+ Jurisdictions</span>
            </div>

            <h1 className="font-display text-5xl lg:text-6xl xl:text-7xl leading-[1.05]">
              Procurement that <span className="pmc-italic-accent">travels borders.</span>
            </h1>

            <p className="max-w-xl text-lg leading-relaxed text-white/70">
              The world's most trusted tender board for enterprises and vetted vendors. Register once, comply with global IDs, and bid across continents from one unified dashboard.
            </p>

            <div className="flex flex-wrap gap-4 pt-2">
              <Link to="/register" data-testid="landing-register-btn"
                className="inline-flex items-center gap-3 bg-brand-navy-soft text-white px-8 py-4 shadow-brand-btn hover:bg-brand-navy-soft/90 transition-colors text-[0.8125rem] uppercase tracking-widest font-semibold">
                Register as vendor <ArrowUpRight className="h-4 w-4" />
              </Link>
              <Link to="/login" data-testid="landing-login-btn"
                className="inline-flex items-center gap-3 bg-transparent border border-brand-navy-soft/50 text-white px-8 py-4 hover:bg-white/5 transition-colors text-[0.8125rem] uppercase tracking-widest font-semibold">
                Access dashboard <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>

        {/* RIGHT: hero image + frosted live card */}
        <div className="relative lg:w-1/2 min-h-[500px] lg:min-h-screen flex items-center justify-center">
          <img src="/hero-containers.jpg" alt="Global shipping port" className="absolute inset-0 w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-brand-navy via-brand-navy/40 to-transparent lg:from-brand-navy lg:via-brand-navy/20 lg:to-transparent" />

          {/* Live Tenders Card */}
          <div data-testid="landing-live-card"
            className={`relative z-10 mx-6 w-full max-w-sm pmc-glass p-8 shadow-brand-live transition-all duration-700 ${liveVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}>
            <div className="flex items-center justify-between mb-8">
              <div className="text-[0.6875rem] font-bold tracking-[0.25em] uppercase text-white/60">Live Tenders Board</div>
              <div className="flex items-center gap-2">
                <span className="relative inline-flex">
                  <span className="absolute inline-flex h-2.5 w-2.5 rounded-full bg-[#22c55e] animate-ping opacity-70" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#22c55e]" />
                </span>
                <span className="text-[0.625rem] font-bold tracking-widest uppercase text-[#4ade80]">Active</span>
              </div>
            </div>

            <div className="space-y-6" data-testid="landing-stats">
              <StatRow label="Open Tenders" value={stats?.tenders_open ?? "—"} testid="stat-tenders" />
              <StatRow label="Vetted Vendors" value={stats?.vendors_approved ?? "—"} testid="stat-vendors" />
              <StatRow label="Board Liquidity" value={stats?.board_liquidity || "$4.2B"} testid="stat-liquidity" />
            </div>

            <div className="mt-8 text-[0.625rem] font-bold tracking-widest uppercase text-brand-navy-soft leading-relaxed">
              Compliance verification engine active across 4 continents.
            </div>
          </div>
        </div>
      </section>

      {/* SECTION — Platform */}
      <section id="platform" className="bg-brand-surface px-8 lg:px-16 py-24">
        <div className="max-w-7xl mx-auto grid gap-12 lg:grid-cols-[4fr_8fr] lg:gap-16">
          <div>
            <div className="pmc-kicker mb-4">The Platform</div>
            <h2 className="font-display text-4xl lg:text-5xl leading-[1.1] text-brand-navy">
              One board. <span className="pmc-italic-accent">Every jurisdiction.</span>
            </h2>
            <p className="mt-6 max-w-md text-lg leading-relaxed text-brand-navy/70">
              A single compliance layer handles the IDs, tax numbers, and regulatory checks so your team can focus on choosing the right vendor, not the right form.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <FeatureCard icon={Globe2} title="Global by default"
              body="Country-aware KYC captures EIN, GSTIN, VAT, UEN, CNPJ, CR, CAC — whatever your jurisdiction requires." />
            <FeatureCard icon={ShieldCheck} title="Vetted supply"
              body="Every vendor is reviewed by our compliance desk before they can bid. No open marketplace roulette." />
            <FeatureCard icon={ClipboardList} title="Fair award"
              body="Side-by-side bid comparison with currency normalization, delivery windows, and evidence trails." />
          </div>
        </div>
      </section>

      {/* SECTION — How it works */}
      <section id="how" className="bg-brand-pale px-8 lg:px-16 py-24">
        <div className="max-w-7xl mx-auto grid gap-12 lg:grid-cols-[4fr_8fr] lg:gap-16">
          <div>
            <div className="pmc-kicker mb-4">How It Works</div>
            <h2 className="font-display text-4xl lg:text-5xl leading-[1.1] text-brand-navy">
              From registration to award, <span className="pmc-italic-accent">in four moves.</span>
            </h2>
            <p className="mt-6 max-w-md text-lg leading-relaxed text-brand-navy/70">
              A single orchestrated flow — designed with procurement officers in mind, not engineers.
            </p>
            <Link to="/register" data-testid="landing-cta-2"
              className="mt-8 inline-flex items-center gap-3 bg-brand-navy text-white px-8 py-4 hover:bg-brand-navy-deep transition-colors text-[0.8125rem] uppercase tracking-widest font-semibold">
              Begin vendor registration <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="border border-brand-navy/10 bg-white">
            {[
              { n: "01", t: "Register your entity", b: "Capture legal type, country-specific ID and KYC documents." },
              { n: "02", t: "Get approved", b: "Compliance reviews your file within a working day." },
              { n: "03", t: "Bid on tenders", b: "Submit price, delivery window and technical proposal." },
              { n: "04", t: "Track the award", b: "Notifications for shortlist, award and rejection with reasons." },
            ].map((s, i, arr) => (
              <div key={s.n}
                className={`grid grid-cols-[3rem_1fr] gap-4 p-6 lg:p-8 ${i < arr.length - 1 ? "border-b border-brand-navy/10" : ""}`}>
                <div className="font-display text-lg font-bold text-brand-navy-soft">{s.n}</div>
                <div>
                  <div className="font-display text-xl text-brand-navy">{s.t}</div>
                  <div className="mt-1 text-brand-navy/70">{s.b}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER CTA */}
      <section className="bg-brand-navy text-white px-8 lg:px-16 py-20 text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-3xl lg:text-5xl leading-tight">
            Ready to bid <span className="pmc-italic-accent">across borders?</span>
          </h2>
          <p className="mt-4 max-w-2xl mx-auto text-lg text-white/70">
            Join the global tender board built for enterprises and vetted vendors.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link to="/register" data-testid="landing-footer-register"
              className="inline-flex items-center gap-3 bg-brand-navy-soft text-white px-8 py-4 shadow-brand-btn hover:bg-brand-navy-soft/90 transition-colors text-[0.8125rem] uppercase tracking-widest font-semibold">
              Register as vendor <ArrowUpRight className="h-4 w-4" />
            </Link>
            <Link to="/login" data-testid="landing-footer-login"
              className="inline-flex items-center gap-3 bg-transparent border border-brand-navy-soft/50 text-white px-8 py-4 hover:bg-white/5 transition-colors text-[0.8125rem] uppercase tracking-widest font-semibold">
              Access dashboard <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        <div className="max-w-7xl mx-auto mt-16 pt-8 border-t border-white/10 flex flex-wrap items-center justify-between gap-4 text-xs text-white/50 tracking-widest uppercase">
          <div className="flex items-center gap-3">
            <Logo className="h-6 w-6" />
            <span>PMC Managers Limited</span>
          </div>
          <div>© 2026 · Est. 2026 · Kazakhstan HQ</div>
        </div>
      </section>
    </div>
  );
}

function StatRow({ label, value, testid }) {
  return (
    <div className="border-b border-white/5 pb-4 last:border-none group" data-testid={testid}>
      <div className="text-[0.6875rem] tracking-[0.15em] uppercase text-white/40 mb-2">{label}</div>
      <div className="flex items-baseline justify-between">
        <span className="font-display text-4xl font-light text-white group-hover:text-brand-navy-soft transition-colors">
          {typeof value === "number" ? value.toLocaleString() : value}
        </span>
      </div>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, body }) {
  return (
    <div className="border border-brand-navy/10 p-8 hover:border-brand-navy-soft/40 transition-colors bg-white">
      <div className="inline-flex w-12 h-12 items-center justify-center border border-brand-navy/10 text-brand-navy-soft mb-6">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="font-display text-xl text-brand-navy">{title}</h3>
      <p className="mt-3 leading-relaxed text-brand-navy/70">{body}</p>
    </div>
  );
}
