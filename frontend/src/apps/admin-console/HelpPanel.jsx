import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import HelpVideo from "@/apps/help-centre/HelpVideo";

/**
 * HelpPanel — in-app comprehensive manual for the admin console.
 *
 * Sourced from /api/v1/meta/help which serves scripts/manual_content.py.
 * Left nav lists all modules grouped by surface; right pane renders the
 * purpose, prerequisites, and every action (steps · controls · errors).
 */
export default function HelpPanel() {
  const [data, setData]     = useState(null);
  const [error, setError]   = useState(null);
  const [active, setActive] = useState(null);
  const [q, setQ]           = useState(() => {
    try {
      const jump = sessionStorage.getItem("pmc.help.jumpTo");
      if (jump) { sessionStorage.removeItem("pmc.help.jumpTo"); return jump; }
    } catch {}
    return "";
  });

  useEffect(() => {
    api.get("/api/v1/meta/help")
      .then((r) => {
        setData(r.data);
        const codes = Object.keys(r.data.modules || {});
        setActive(codes[0] || null);
      })
      .catch((e) => setError(e?.message || "Failed to load help content"));
  }, []);

  const modules = data?.modules || {};
  const filtered = useMemo(() => {
    if (!q) return Object.entries(modules);
    const needle = q.toLowerCase();
    return Object.entries(modules).filter(([code, m]) =>
      code.includes(needle) ||
      (m.title || "").toLowerCase().includes(needle) ||
      (m.purpose || "").toLowerCase().includes(needle) ||
      (m.actions || []).some((a) => (a.label || "").toLowerCase().includes(needle))
    );
  }, [modules, q]);

  const bySurface = useMemo(() => {
    const groups = {};
    filtered.forEach(([code, m]) => {
      const key = m.surface || "misc";
      (groups[key] ||= []).push([code, m]);
    });
    return groups;
  }, [filtered]);

  const selected = active ? modules[active] : null;

  if (error) return (
    <div className="p-6 bg-red-50 border border-red-200 text-red-800 text-sm"
         data-testid="help-panel-error">
      Failed to load help: {error}
    </div>
  );

  if (!data) return (
    <div className="p-6 text-sm text-brand-navy/50" data-testid="help-panel-loading">
      Loading manual…
    </div>
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[4fr_8fr]" data-testid="admin-help-panel">
      <aside className="lg:sticky lg:top-4 lg:self-start lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto">
        <div className="sticky top-0 bg-brand-pale/95 backdrop-blur pb-2 z-10">
          <input
            type="search" value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search modules or actions…"
            data-testid="help-search"
            className="w-full px-3 py-2 border border-brand-navy/20 text-sm bg-white"
          />
          <div className="text-[10px] text-brand-navy/50 mt-1">{filtered.length} of {Object.keys(modules).length} modules</div>
        </div>
        {Object.entries(bySurface).map(([surface, items]) => (
          <div key={surface} className="mb-4">
            <div className="pmc-label mb-1 uppercase">{surface}</div>
            <ul className="border border-brand-navy/10 bg-white">
              {items.map(([code, m]) => (
                <li key={code}>
                  <button
                    type="button"
                    onClick={() => setActive(code)}
                    data-testid={`help-nav-${code}`}
                    className={"w-full text-left px-3 py-2 border-b border-brand-navy/10 text-sm " +
                      (active === code ? "bg-brand-navy text-white" : "hover:bg-brand-navy/5")}
                  >
                    {m.title}
                    <span className={"ml-2 text-[10px] " +
                      (active === code ? "text-white/60" : "text-brand-navy/40")}>
                      {(m.actions || []).length} action(s)
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </aside>

      <section>
        {selected ? (
          <article className="bg-white border border-brand-navy/10 p-6">
            <div className="pmc-label">{selected.surface}</div>
            <h2 className="font-display text-2xl text-brand-navy mt-1">{selected.title}</h2>
            <div className="text-xs font-mono text-brand-navy-soft mt-1">{selected.url_path}</div>
            <p className="text-sm text-brand-navy/80 leading-relaxed mt-4">{selected.purpose}</p>
            <HelpVideo slug={active} />

            {selected.prerequisites?.length > 0 && (
              <div className="mt-5">
                <div className="pmc-label mb-1">Prerequisites</div>
                <ul className="list-disc pl-5 text-sm text-brand-navy/80">
                  {selected.prerequisites.map((p) => <li key={p}>{p}</li>)}
                </ul>
              </div>
            )}

            {(selected.actions || []).length === 0 && (
              <div className="mt-6 p-4 bg-amber-50 border border-amber-200 text-sm text-amber-900">
                Content in progress — this module's actions will be authored in the next batch.
              </div>
            )}

            {(selected.actions || []).map((a, i) => (
              <section key={a.id || i} className="mt-8 border-t border-brand-navy/10 pt-6"
                       data-testid={`help-action-${a.id || i}`}>
                <h3 className="font-display text-lg text-brand-navy">{i + 1}. {a.label}</h3>
                {a.when && <p className="text-xs text-brand-navy/60 mt-1"><b>When:</b> {a.when}</p>}

                {a.steps?.length > 0 && (
                  <>
                    <div className="pmc-label mt-3 mb-1">Steps</div>
                    <ol className="list-decimal pl-5 text-sm text-brand-navy/85 space-y-1">
                      {a.steps.map((s, j) => <li key={j}>{s}</li>)}
                    </ol>
                  </>
                )}
                {a.expected && (
                  <p className="mt-3 text-sm"><b className="text-emerald-700">Expected: </b>{a.expected}</p>
                )}

                {a.controls?.length > 0 && (
                  <>
                    <div className="pmc-label mt-4 mb-1">Controls &amp; fields</div>
                    <ul className="text-sm text-brand-navy/85 space-y-1">
                      {a.controls.map((c, k) => (
                        <li key={k}><b>{c.name}:</b> {c.desc}</li>
                      ))}
                    </ul>
                  </>
                )}

                {a.errors?.length > 0 && (
                  <>
                    <div className="pmc-label mt-4 mb-1">Common errors &amp; fixes</div>
                    <ul className="text-sm space-y-2">
                      {a.errors.map((e, k) => (
                        <li key={k} className="border-l-2 border-red-400 pl-3">
                          <div><b className="text-red-700">{e.code}</b> — {e.msg}</div>
                          <div className="text-brand-navy/80 italic">Fix: {e.fix}</div>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </section>
            ))}
          </article>
        ) : (
          <div className="p-6 text-sm text-brand-navy/50">Select a module on the left.</div>
        )}
      </section>
    </div>
  );
}
