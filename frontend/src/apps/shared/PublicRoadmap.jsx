/**
 * PublicRoadmap — the shareable /roadmap URL. Pulls the live comparative
 * statement from the backend (same source of truth as the exported reports)
 * and lets vendors see what's built vs what's on the roadmap.
 */
import { useEffect, useMemo, useState } from "react";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_STYLE = {
  Delivered: "bg-emerald-100 text-emerald-900 border-emerald-500",
  Partial:   "bg-amber-100 text-amber-900 border-amber-500",
  Planned:   "bg-indigo-100 text-indigo-900 border-indigo-500",
};

function StatusPill({ s }) {
  const cls = STATUS_STYLE[s] || "bg-brand-navy/5 text-brand-navy border-brand-navy/20";
  return (
    <span className={`inline-block px-2 py-0.5 border text-[10px] uppercase tracking-widest ${cls}`}>{s}</span>
  );
}

export default function PublicRoadmap() {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    document.title = "PMC Managers · Live Roadmap";
    fetch(`${API}/api/v1/reports/public/roadmap`)
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  const areas = useMemo(() => {
    if (!data) return [];
    if (filter === "all") return data.areas;
    return data.areas.map((a) => ({
      ...a, items: a.items.filter((i) => i.status === filter),
    })).filter((a) => a.items.length > 0);
  }, [data, filter]);

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 lg:px-10 py-10" data-testid="public-roadmap">
        <div className="pmc-label">Live roadmap</div>
        <h1 className="font-display text-3xl lg:text-4xl mt-2 text-brand-navy">
          What's built vs what's coming
        </h1>
        <p className="text-sm text-brand-navy/60 mt-3 max-w-2xl">
          A live view of every scope item on the platform. Delivered = shipped and audit-logged.
          Partial = waiting on external credentials. Planned = roadmap. This page updates the moment
          the team ships a new wave.
        </p>

        {data && (
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {[
              ["Delivered", data.delivered, "emerald"],
              ["Partial", data.partial, "amber"],
              ["Planned", data.planned, "indigo"],
            ].map(([label, v, tone]) => (
              <button key={label}
                      onClick={() => setFilter((f) => f === label ? "all" : label)}
                      data-testid={`roadmap-stat-${label.toLowerCase()}`}
                      className={`border-2 p-5 text-left transition-colors ${
                        filter === label ? "bg-brand-navy text-white border-brand-navy"
                          : "bg-white border-brand-navy/15 hover:border-brand-navy/50 text-brand-navy"}`}>
                <div className={`text-xs uppercase tracking-widest ${filter === label ? "text-white/70" : `text-${tone}-800`}`}>{label}</div>
                <div className="font-display text-4xl mt-1 tabular-nums">{v}</div>
                <div className="text-[11px] mt-1 opacity-70">of {data.total_items} tracked</div>
              </button>
            ))}
          </div>
        )}

        <div className="mt-10 space-y-8">
          {areas.map((a) => (
            <section key={a.area} data-testid={`roadmap-area-${a.area.toLowerCase().replace(/\W+/g, "-")}`}>
              <div className="pmc-label border-b border-brand-navy/20 pb-2">{a.area}</div>
              <ul className="mt-4 space-y-3">
                {a.items.map((it, i) => (
                  <li key={i} className="border border-brand-navy/10 bg-white p-4">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div className="flex-1 min-w-[280px]">
                        <div className="text-xs uppercase tracking-widest text-brand-navy/60">Asked</div>
                        <div className="text-sm text-brand-navy mt-0.5">{it.asked}</div>
                      </div>
                      <div className="flex-1 min-w-[280px]">
                        <div className="text-xs uppercase tracking-widest text-brand-navy/60">Delivered</div>
                        <div className="text-sm text-brand-navy mt-0.5">{it.delivered}</div>
                      </div>
                      <StatusPill s={it.status}/>
                    </div>
                    {it.note && (
                      <div className="mt-2 text-[11px] text-brand-navy/50 italic">{it.note}</div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}
