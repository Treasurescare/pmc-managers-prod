import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useI18n } from "@/context/I18nContext";

export const videoLink = (slug) => `${window.location.origin}/help/videos?v=${encodeURIComponent(slug)}`;

export const ShareRow = ({ slug, title, dark = false }) => {
  const url = videoLink(slug);
  const msg = `How-to video: ${title} — ${url}`;
  const copy = async () => {
    try { await navigator.clipboard.writeText(url); toast.success("Video link copied"); }
    catch { window.prompt("Copy this link", url); }
  };
  const c = dark ? "#d9bd72" : "#162921";
  const btn = { background: "none", border: `1px solid ${c}`, color: c, borderRadius: 999, padding: "4px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer", textDecoration: "none" };
  return (
    <span style={{ display: "inline-flex", gap: 8, flexWrap: "wrap" }} data-testid={`video-share-${slug}`}>
      <button type="button" style={btn} onClick={copy} data-testid={`video-copy-link-${slug}`}>Copy link</button>
      <a style={btn} href={`https://wa.me/?text=${encodeURIComponent(msg)}`} target="_blank" rel="noreferrer" data-testid={`video-share-whatsapp-${slug}`}>WhatsApp</a>
      <a style={btn} href={`mailto:?subject=${encodeURIComponent(`How-to video: ${title}`)}&body=${encodeURIComponent(`Watch this short walkthrough:\n${url}`)}`} data-testid={`video-share-email-${slug}`}>Email</a>
    </span>);
};

const cache = {};
const getJson = (u) => fetch(u, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
// Videos narrated in the chosen language replace the English ones where available.
export const loadManifest = (lang = "en") => {
  cache.en = cache.en || getJson("/help-videos/manifest.json");
  if (lang !== "en" && !cache[lang]) cache[lang] = Promise.all([cache.en, getJson(`/help-videos/${lang}/manifest.json`)]).then(([a, b]) => ({ ...a, ...b }));
  return cache[lang];
};

export function useHelpVideos() {
  const { lang } = useI18n();
  const [m, setM] = useState({});
  useEffect(() => { loadManifest(lang).then(setM); }, [lang]);
  return m;
}

export const PlayBadge = ({ testid }) => (
  <span title="Has a video walkthrough" data-testid={testid}
    style={{ display: "inline-flex", alignItems: "center", gap: 4, marginLeft: 8, padding: "2px 8px", borderRadius: 999,
      background: "#162921", color: "#d9bd72", fontSize: 11, fontWeight: 600, verticalAlign: "middle" }}>
    <svg width="9" height="10" viewBox="0 0 9 10" aria-hidden="true"><path d="M0 0l9 5-9 5z" fill="currentColor" /></svg>Video
  </span>);

export default function HelpVideo({ slug, preload = "metadata" }) {
  const vids = useHelpVideos();
  const v = vids[slug] || null;
  if (!v) return null;
  return (
    <figure style={{ margin: "20px 0 28px" }} data-testid="help-video">
      <video key={v.file} src={v.file} poster={v.file.replace(/\.mp4$/, ".jpg")} controls preload={preload} playsInline
        style={{ width: "100%", borderRadius: 10, background: "#162921", boxShadow: "0 10px 30px rgba(0,0,0,.18)" }}
        data-testid="help-video-player" />
      <figcaption className="pmc-muted" style={{ fontSize: 13, marginTop: 8, display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <span>Video walkthrough · {Math.max(1, Math.round(v.seconds / 60))} min · updated {v.updated}</span>
        <ShareRow slug={slug} title={v.title} />
      </figcaption>
    </figure>);
}
