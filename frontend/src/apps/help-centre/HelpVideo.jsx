import { useEffect, useState } from "react";

let cache;
export const loadManifest = () => {
  cache = cache || fetch("/help-videos/manifest.json", { cache: "no-cache" }).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
  return cache;
};

export function useHelpVideos() {
  const [m, setM] = useState({});
  useEffect(() => { loadManifest().then(setM); }, []);
  return m;
}

export const PlayBadge = ({ testid }) => (
  <span title="Has a video walkthrough" data-testid={testid}
    style={{ display: "inline-flex", alignItems: "center", gap: 4, marginLeft: 8, padding: "2px 8px", borderRadius: 999,
      background: "#162921", color: "#d9bd72", fontSize: 11, fontWeight: 600, verticalAlign: "middle" }}>
    <svg width="9" height="10" viewBox="0 0 9 10" aria-hidden="true"><path d="M0 0l9 5-9 5z" fill="currentColor" /></svg>Video
  </span>);

export default function HelpVideo({ slug, preload = "metadata" }) {
  const [v, setV] = useState(null);
  useEffect(() => { loadManifest().then((m) => setV(m[slug] || null)); }, [slug]);
  if (!v) return null;
  return (
    <figure style={{ margin: "20px 0 28px" }} data-testid="help-video">
      <video src={v.file} poster={v.file.replace(/\.mp4$/, ".jpg")} controls preload={preload} playsInline
        style={{ width: "100%", borderRadius: 10, background: "#162921", boxShadow: "0 10px 30px rgba(0,0,0,.18)" }}
        data-testid="help-video-player" />
      <figcaption className="pmc-muted" style={{ fontSize: 13, marginTop: 8 }}>
        Video walkthrough · {Math.max(1, Math.round(v.seconds / 60))} min · updated {v.updated}
      </figcaption>
    </figure>);
}
