import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";
import HelpVideo from "@/apps/help-centre/HelpVideo";

// v51l — was a static mockup that ignored the :slug. Now renders the real
// guide from /api/v1/meta/help, so deep links like /help/admin-docusign work.

export default function HelpArticleE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const { slug } = useParams();
  const [mod, setMod] = useState(null);
  const [state, setState] = useState("loading"); // loading | ok | missing | error

  useEffect(() => {
    if (!isE) return;
    let live = true;
    fetch("/api/v1/meta/help")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d) => {
        if (!live) return;
        const m = (d.modules || {})[slug];
        setMod(m || null);
        setState(m ? "ok" : "missing");
      })
      .catch(() => { if (live) setState("error"); });
    return () => { live = false; };
  }, [isE, slug]);

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="help-article-e" data-pmc-e-page="help-article-e">
      <header className="pmc-chrome" style={{ borderBottom: "1px solid var(--chrome-line)" }}>
        <div className="hc-wrap" style={{ display: "flex", alignItems: "center", height: 64, gap: 24 }}>
          <Link to="/help" style={{ display: "flex", flexDirection: "column", color: "var(--on-chrome)", textDecoration: "none" }}>
            <span style={{ fontFamily: "var(--font-display)", fontSize: 22, lineHeight: "22px", fontWeight: 600 }}>PMC Managers</span>
            <span className="pmc-eyebrow" style={{ fontSize: 11 }}>Help Centre</span>
          </Link>
          <div style={{ marginLeft: "auto" }}>
            <button type="button" onClick={() => (window.history.length > 1 ? window.history.back() : (window.location.href = "/help"))}
                    className="pmc-btn pmc-btn--onchrome" data-testid="help-back-to-centre">← Back</button>
          </div>
        </div>
      </header>

      <div className="hc-wrap" style={{ maxWidth: 820, padding: "40px 16px 80px" }}>
        {state === "loading" && <p className="pmc-muted" data-testid="help-article-loading">Loading guide…</p>}
        {state === "error" && <p className="pmc-muted" data-testid="help-article-error">Could not load this guide. Please try again.</p>}
        {state === "missing" && (
          <div data-testid="help-article-missing">
            <h1 className="pmc-display" style={{ fontSize: 36 }}>Guide not found</h1>
            <p className="pmc-muted">This guide may have been moved. Browse the full list from the Help Centre.</p>
            <Link to="/help" className="pmc-btn pmc-btn--primary" style={{ display: "inline-flex", marginTop: 12 }}>Open Help Centre</Link>
          </div>
        )}
        {state === "ok" && mod && (
          <article className="ha" data-testid="help-article-body">
            <div className="pmc-crumb"><Link to="/help">Help Centre</Link> / {mod.title}</div>
            <h1 className="pmc-display" style={{ fontSize: 42, lineHeight: "48px", margin: "12px 0 10px" }}>{mod.title}</h1>
            {mod.purpose && <p className="lead">{mod.purpose}</p>}
            <HelpVideo slug={slug} />
            {(mod.prerequisites || []).length > 0 && (
              <div className="pmc-callout pmc-callout--info">
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>
                <div><b>Before you start:</b> {mod.prerequisites.join(" · ")}</div>
              </div>
            )}
            {(mod.actions || []).map((a) => (
              <section key={a.id} style={{ marginTop: 28 }} data-testid={`help-article-action-${a.id}`}>
                <h2>{a.label}</h2>
                {a.when && <p className="pmc-muted">{a.when}</p>}
                {(a.steps || []).length > 0 && (
                  <ol className="ha-steps">
                    {a.steps.map((s, i) => <li key={i}><div>{s}</div></li>)}
                  </ol>
                )}
                {a.expected && <p><b>Expected:</b> {a.expected}</p>}
                {(a.errors || []).length > 0 && (
                  <div className="pmc-callout pmc-callout--warn">
                    <svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>
                    <div>
                      {a.errors.map((e, i) => (
                        <div key={i}><b>{e.code}:</b> {e.msg} — {e.fix}</div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            ))}
            <div className="ha-fb" style={{ marginTop: 36 }}>
              <b>Need more?</b>
              <Link to="/help" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Back to all guides</Link>
            </div>
          </article>
        )}
      </div>
    </div>
  );
}
