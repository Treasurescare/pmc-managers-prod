// Language-prefixed public URLs (/fr/buyers, /ar/about…) so search engines can index each language.
export const URL_LANGS = ["ru", "kk", "zh-Hans", "zh-Hant", "es", "fr", "de", "hi", "ms", "id", "ko", "ja", "ar"];
const m = window.location.pathname.match(new RegExp(`^/(${URL_LANGS.join("|")})(?=/|$)`));
export const PATH_LANG = m ? m[1] : null;
export const BASENAME = PATH_LANG ? `/${PATH_LANG}` : "";
export const barePath = () => window.location.pathname.slice(BASENAME.length) || "/";
const SKIP_HREF = /^\/(api|downloads|flags|i18n|static|help-videos)(\/|$)|\.\w{2,4}($|[?#])/;
const fixHref = (a) => {
  const h = a.getAttribute("href");
  if (!h || !h.startsWith("/") || h.startsWith("//") || SKIP_HREF.test(h) || h === BASENAME || h.startsWith(`${BASENAME}/`)) return;
  a.setAttribute("href", BASENAME + (h === "/" ? "" : h));
};
// Plain <a href="/x"> links keep the language prefix so crawlers and new tabs stay in the same language.
export function startLinkPrefixer() {
  if (!BASENAME) return;
  document.querySelectorAll("a[href]").forEach(fixHref);
  new MutationObserver((muts) => muts.forEach((m) => {
    if (m.type === "attributes") { if (m.target.tagName === "A") fixHref(m.target); return; }
    m.addedNodes.forEach((n) => { if (n.nodeType !== 1) return; if (n.tagName === "A") fixHref(n); n.querySelectorAll?.("a[href]").forEach(fixHref); });
  })).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["href"] });
}
export const langUrl = (lg, path = barePath()) => (lg === "en" ? "" : `/${lg}`) + (lg !== "en" && path === "/" ? "" : path);
