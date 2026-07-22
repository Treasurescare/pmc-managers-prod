import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { ArrowUpRight, Globe2, ShieldCheck, Gavel, ArrowRight } from "lucide-react";
import PmcLogo from "@/components/app/PmcLogo";
import api from "@/lib/api";

export default function Landing() {
  const [stats, setStats] = useState({ tenders_open: 0, vendors_approved: 0, total_tenders: 0 });
  useEffect(() => {
    api.get("/public/stats").then(({ data }) => setStats(data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-[#FDFDFD] text-foreground">
      {/* Top nav */}
      <div className="border-b bg-white sticky top-0 z-40 backdrop-blur">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12 py-5 flex items-center justify-between">
          <PmcLogo />
          <nav className="hidden md:flex items-center gap-8 text-sm">
            <a href="#how" className="text-muted-foreground hover:text-foreground">How it works</a>
            <a href="#pillars" className="text-muted-foreground hover:text-foreground">Platform</a>
            <a href="#trust" className="text-muted-foreground hover:text-foreground">Trust</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link data-testid="landing-login-btn" to="/login" className="text-sm px-4 py-2 border border-foreground hover:bg-foreground hover:text-white transition-colors">
              Log in
            </Link>
            <Link data-testid="landing-register-btn" to="/register" className="text-sm px-4 py-2 bg-primary text-white hover:-translate-y-0.5 transition-transform inline-flex items-center gap-2">
              Register
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* Hero */}
      <section className="relative overflow-hidden border-b" style={{ backgroundColor: "#050505" }}>
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              'url("https://images.unsplash.com/photo-1494412519320-aa613dfb7738?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1OTV8MHwxfHNlYXJjaHw0fHxnbG9iYWwlMjBsb2dpc3RpY3MlMjBzaGlwcGluZyUyMGNvbnRhaW5lcnMlMjBjYXJnb3xlbnwwfHx8fDE3ODQ3MDc2Njh8MA&ixlib=rb-4.1.0&q=85")',
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="absolute inset-0 pmc-noise opacity-70" />
        <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(5,5,5,0.55) 0%, rgba(5,5,5,0.9) 100%)" }} />

        <div className="relative max-w-[1400px] mx-auto px-6 lg:px-12 pt-24 pb-32 grid grid-cols-12 gap-6 text-white">
          <div className="col-span-12 md:col-span-8">
            <div className="pmc-label text-white/70 mb-6">Est. 2026 · Global Procurement · 30+ Jurisdictions</div>
            <h1 className="font-serif font-black text-[clamp(3rem,7vw,6.5rem)] leading-[0.95] tracking-tighter">
              Procurement that <br /> travels borders.
            </h1>
            <p className="mt-8 text-white/70 max-w-xl text-base md:text-lg leading-relaxed">
              PMC Managers Limited is the global tender board for enterprises and vetted vendors. Register once, comply with jurisdiction-specific IDs, and bid across continents from a single dashboard.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Link data-testid="hero-register-btn" to="/register" className="inline-flex items-center gap-3 bg-white text-black px-6 py-4 text-sm font-medium hover:-translate-y-0.5 transition-transform">
                Register as vendor
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link data-testid="hero-login-btn" to="/login" className="inline-flex items-center gap-3 border border-white/40 text-white px-6 py-4 text-sm font-medium hover:bg-white/10 transition-colors">
                Access dashboard
              </Link>
            </div>
          </div>

          <div className="col-span-12 md:col-span-4 md:col-start-9 md:row-start-1 flex md:justify-end">
            <div className="w-full md:w-[280px] mt-4 md:mt-0 border border-white/20 backdrop-blur-sm bg-white/5 p-6 self-start">
              <div className="pmc-label text-white/60 mb-4">Live board</div>
              <div className="space-y-4">
                <StatRow label="Open tenders" value={stats.tenders_open} testid="stat-open-tenders" />
                <StatRow label="Vetted vendors" value={stats.vendors_approved} testid="stat-vetted-vendors" />
                <StatRow label="Total tenders" value={stats.total_tenders} testid="stat-total-tenders" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pillars */}
      <section id="pillars" className="max-w-[1400px] mx-auto px-6 lg:px-12 py-24 grid grid-cols-12 gap-8">
        <div className="col-span-12 md:col-span-4">
          <div className="pmc-label mb-4">The platform</div>
          <h2 className="font-serif text-4xl md:text-5xl tracking-tight leading-tight">
            One board.<br />Every jurisdiction.
          </h2>
        </div>
        <div className="col-span-12 md:col-span-8 grid md:grid-cols-3 gap-0 border-t border-l">
          <Pillar
            icon={<Globe2 className="h-5 w-5" />}
            title="Global by default"
            body="Country-aware KYC captures EIN, GSTIN, VAT, UEN, CNPJ, CR, CAC — whatever your jurisdiction requires."
          />
          <Pillar
            icon={<ShieldCheck className="h-5 w-5" />}
            title="Vetted supply"
            body="Every vendor is reviewed by our compliance desk before they can bid. No open marketplace roulette."
          />
          <Pillar
            icon={<Gavel className="h-5 w-5" />}
            title="Fair award"
            body="Side-by-side bid comparison with currency normalization, delivery windows, and evidence trails."
          />
        </div>
      </section>

      {/* How */}
      <section id="how" className="border-t bg-white">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12 py-24 grid grid-cols-12 gap-8">
          <div className="col-span-12 md:col-span-5">
            <div className="pmc-label mb-4">How it works</div>
            <h2 className="font-serif text-4xl md:text-5xl tracking-tight leading-tight">
              From registration to award, in four moves.
            </h2>
            <p className="mt-6 text-muted-foreground">A single opinionated flow — designed with procurement officers in mind, not engineers.</p>
            <Link data-testid="how-cta-register" to="/register" className="mt-8 inline-flex items-center gap-2 bg-primary text-white px-5 py-3 text-sm">
              Begin vendor registration <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <ol className="col-span-12 md:col-span-7 space-y-0 border-t border-l">
            <Step n="01" title="Register your entity" body="Capture legal type, country-specific ID and KYC documents." />
            <Step n="02" title="Get approved" body="Compliance reviews your file within a working day." />
            <Step n="03" title="Bid on tenders" body="Submit price, delivery window and technical proposal." />
            <Step n="04" title="Track the award" body="Notifications for shortlist, award and rejection with reasons." />
          </ol>
        </div>
      </section>

      {/* Trust */}
      <section id="trust" className="border-t">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12 py-24 grid grid-cols-12 gap-8 items-end">
          <div className="col-span-12 md:col-span-7">
            <div className="pmc-label mb-4">Trust · Governance</div>
            <h2 className="font-serif text-4xl md:text-5xl tracking-tight leading-tight">
              Procurement is a matter of record.
            </h2>
            <p className="mt-6 text-muted-foreground max-w-2xl">
              Every bid submission and status change is timestamped and stored against the tender. Vendors keep a clean paper trail. Buyers keep audit-ready evidence for finance and legal.
            </p>
          </div>
          <div className="col-span-12 md:col-span-5 border border-foreground p-8 pmc-hard-shadow">
            <div className="pmc-label">Ready to publish?</div>
            <h3 className="font-serif text-2xl mt-3">Buyers create your first tender in minutes.</h3>
            <Link data-testid="trust-cta-buyer" to="/register" className="mt-6 inline-flex items-center gap-2 border border-foreground px-5 py-3 text-sm hover:bg-foreground hover:text-white transition-colors">
              Register as buyer <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t bg-[#050505] text-white/70">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12 py-10 flex flex-col md:flex-row justify-between gap-6">
          <PmcLogo variant="dark" />
          <div className="text-xs text-white/50">© {new Date().getFullYear()} PMC Managers Limited · Global Tender Board</div>
        </div>
      </footer>
    </div>
  );
}

function StatRow({ label, value, testid }) {
  return (
    <div className="flex items-end justify-between border-b border-white/10 pb-3">
      <span className="text-xs uppercase tracking-widest text-white/60">{label}</span>
      <span data-testid={testid} className="font-mono text-2xl text-white">{value}</span>
    </div>
  );
}

function Pillar({ icon, title, body }) {
  return (
    <div className="p-8 border-r border-b">
      <div className="inline-flex h-9 w-9 items-center justify-center border border-foreground text-foreground">{icon}</div>
      <h3 className="font-serif text-xl mt-6">{title}</h3>
      <p className="text-sm text-muted-foreground mt-3 leading-relaxed">{body}</p>
    </div>
  );
}

function Step({ n, title, body }) {
  return (
    <li className="flex items-start gap-6 border-r border-b p-6">
      <span className="font-mono text-sm text-primary min-w-[3rem]">{n}</span>
      <div>
        <h4 className="font-serif text-xl">{title}</h4>
        <p className="text-sm text-muted-foreground mt-2">{body}</p>
      </div>
    </li>
  );
}
