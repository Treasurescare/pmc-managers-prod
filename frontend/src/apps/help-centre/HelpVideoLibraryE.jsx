import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import PublicChrome from "@/apps/shared/PublicChrome";
import { useSeo } from "@/lib/useSeo";
import { useHelpVideos, ShareRow } from "@/apps/help-centre/HelpVideo";

const Card = ({ slug, v, onPlay }) => (
  <button type="button" onClick={() => onPlay(slug)} data-testid={`video-card-${slug}`}
    style={{ textAlign: "left", background: "#fff", border: "1px solid rgba(22,41,33,.12)", borderRadius: 12, padding: 0, overflow: "hidden", cursor: "pointer" }}>
    <div style={{ position: "relative", aspectRatio: "16/9", background: "#162921" }}>
      <img src={v.file.replace(/\.mp4$/, ".jpg")} alt="" loading="lazy" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
      <span style={{ position: "absolute", right: 10, bottom: 10, background: "rgba(22,41,33,.9)", color: "#d9bd72", fontSize: 12, fontWeight: 600, padding: "3px 8px", borderRadius: 6 }}>
        ▶ {Math.floor(v.seconds / 60)}:{String(v.seconds % 60).padStart(2, "0")}
      </span>
    </div>
    <div style={{ padding: "12px 14px 14px" }}>
      <div style={{ fontWeight: 600, color: "#162921" }}>{v.title}</div>
      <div className="pmc-muted" style={{ fontSize: 12, marginTop: 2 }}>{slug.startsWith("admin-") ? "Admin" : "Portal"} · updated {v.updated}</div>
    </div>
  </button>);

const Player = ({ slug, v, onClose }) => (
  <div role="dialog" aria-modal="true" onClick={onClose} data-testid="video-player-modal"
    style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(10,20,16,.85)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
    <div onClick={(e) => e.stopPropagation()} style={{ width: "min(1000px,100%)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "#fff", marginBottom: 10, gap: 12 }}>
        <b>{v.title}</b>
        <span style={{ display: "flex", gap: 14 }}>
          <a href={`/help/${slug}`} style={{ color: "#d9bd72" }} data-testid="video-open-guide">Open the written guide</a>
          <button type="button" onClick={onClose} aria-label="Close" data-testid="video-close"
            style={{ background: "none", border: 0, color: "#fff", fontSize: 24, cursor: "pointer", lineHeight: 1 }}>×</button>
        </span>
      </div>
      <video src={v.file} poster={v.file.replace(/\.mp4$/, ".jpg")} controls autoPlay playsInline style={{ width: "100%", borderRadius: 10, background: "#000" }} data-testid="video-modal-player" />
      <div style={{ marginTop: 12 }}><ShareRow slug={slug} title={v.title} dark /></div>
    </div>
  </div>);

export default function HelpVideoLibraryE() {
  useSeo({ title: "Video library — how-to videos for every section", description: "Short narrated walkthroughs of every part of the Global Tender Grid: supplier registration, bidding, notices, evaluation, awards, escrow and every admin section." });
  const vids = useHelpVideos();
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("all");
  const [params, setParams] = useSearchParams();
  const playing = params.get("v");
  const setPlaying = (s) => setParams(s ? { v: s } : {}, { replace: !s });
  useEffect(() => {
    if (playing && vids[playing]) { document.title = `${vids[playing].title} — how-to video | PMC Managers · Global Tender Grid`; }
  }, [playing, vids]);
  const list = useMemo(() => Object.entries(vids)
    .filter(([s, v]) => (group === "all" || (group === "admin") === s.startsWith("admin-"))
      && `${v.title} ${s}`.toLowerCase().includes(q.trim().toLowerCase()))
    .sort((a, b) => a[1].title.localeCompare(b[1].title)), [vids, q, group]);
  return (
    <PublicChrome testid="help-video-library">
      <main className="pmc-wrap" style={{ padding: "48px 0 96px" }}>
        <a href="/help" className="pmc-muted" style={{ fontSize: 14 }} data-testid="video-back-help">← Help Centre</a>
        <h1 className="pmc-display" style={{ fontSize: 48, lineHeight: "52px", margin: "10px 0 8px" }}>Video library</h1>
        <p className="pmc-muted" style={{ margin: "0 0 24px", maxWidth: 640 }}>{Object.keys(vids).length} short walkthroughs with voice-over, one for every part of the portal.</p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 24 }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search videos, e.g. “bid”, “escrow”, “KYC”" data-testid="video-search"
            style={{ flex: "1 1 320px", height: 46, padding: "0 14px", border: "1px solid rgba(22,41,33,.2)", borderRadius: 8, fontSize: 15 }} />
          {[["all", "All"], ["portal", "Suppliers & portals"], ["admin", "Admin"]].map(([k, l]) => (
            <button key={k} type="button" onClick={() => setGroup(k)} data-testid={`video-filter-${k}`}
              className={`pmc-btn pmc-btn--sm ${group === k ? "pmc-btn--primary" : "pmc-btn--secondary"}`}>{l}</button>))}
        </div>
        {list.length === 0 && <p className="pmc-muted" data-testid="video-no-results">No video matches that search.</p>}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 18 }} data-testid="video-grid">
          {list.map(([s, v]) => <Card key={s} slug={s} v={v} onPlay={setPlaying} />)}
        </div>
      </main>
      {playing && vids[playing] && <Player slug={playing} v={vids[playing]} onClose={() => setPlaying(null)} />}
    </PublicChrome>);
}
