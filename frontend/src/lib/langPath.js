// Language-prefixed public URLs (/fr/buyers, /ar/about…) so search engines can index each language.
export const URL_LANGS = ["ru", "kk", "zh-Hans", "zh-Hant", "es", "fr", "de", "hi", "ms", "id", "ko", "ja", "ar"];
const m = window.location.pathname.match(new RegExp(`^/(${URL_LANGS.join("|")})(?=/|$)`));
export const PATH_LANG = m ? m[1] : null;
export const BASENAME = PATH_LANG ? `/${PATH_LANG}` : "";
export const barePath = () => window.location.pathname.slice(BASENAME.length) || "/";
export const langUrl = (lg, path = barePath()) => (lg === "en" ? "" : `/${lg}`) + (lg !== "en" && path === "/" ? "" : path);
