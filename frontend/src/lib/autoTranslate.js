// Whole-page translator: swaps visible text, placeholders and titles for the chosen language.
// Originals are kept so switching back to English restores them; new text (React updates) is picked up by a MutationObserver.
const API = process.env.REACT_APP_BACKEND_URL;
const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "CODE", "PRE", "TEXTAREA", "SVG", "KBD"]);
const ATTRS = ["placeholder", "title", "aria-label"];
const orig = new WeakMap();  // text node -> { src, out }
const attrOrig = new WeakMap(); // element -> { attr: { src, out } }
const dicts = {};
const failed = {}; // lang -> Map(text -> retryAfter ms)
let lang = "en";
let observer = null;
let queue = new Set();
let timer = null;

const worth = (s) => s.length > 1 && s.length <= 600 && /\p{L}{2,}/u.test(s) && !/^[\w.+-]+@[\w-]+\.[\w.]+$/.test(s)
  && !/^https?:\/\//.test(s) && !/^[A-Z0-9][A-Z0-9-/.]{4,}$/.test(s);
const skipEl = (el) => {
  for (let e = el; e && e !== document.body; e = e.parentElement) {
    if (SKIP.has(e.tagName) || e.isContentEditable || e.getAttribute?.("translate") === "no" || e.classList?.contains("notranslate")) return true;
  }
  return false;
};
const want = (key) => {
  const f = failed[lang]?.get(key);
  return !f || f < Date.now();
};
const wrap = (raw, tr) => raw.replace(raw.trim(), tr);

function applyText(node) {
  const cur = node.nodeValue;
  let rec = orig.get(node);
  if (!rec || (cur !== rec.out && cur !== rec.src)) { rec = { src: cur, out: null }; orig.set(node, rec); }
  const key = rec.src.trim();
  if (lang === "en") { if (rec.out && cur !== rec.src) node.nodeValue = rec.src; rec.out = null; return; }
  if (!worth(key)) return;
  const tr = dicts[lang]?.[key];
  if (tr) { const out = wrap(rec.src, tr); rec.out = out; if (cur !== out) node.nodeValue = out; } else if (want(key)) queue.add(key);
}

function applyAttrs(el) {
  let rec = attrOrig.get(el);
  ATTRS.forEach((a) => {
    const cur = el.getAttribute(a);
    if (cur == null) return;
    rec = rec || {}; attrOrig.set(el, rec);
    let r = rec[a];
    if (!r || (cur !== r.out && cur !== r.src)) { r = { src: cur, out: null }; rec[a] = r; }
    if (lang === "en") { if (r.out) el.setAttribute(a, r.src); r.out = null; return; }
    const key = r.src.trim();
    if (!worth(key)) return;
    const tr = dicts[lang]?.[key];
    if (tr) { r.out = tr; if (cur !== tr) el.setAttribute(a, tr); } else if (want(key)) queue.add(key);
  });
}

function walk(root) {
  if (!root) return;
  if (root.nodeType === 3) { if (root.parentElement && !skipEl(root.parentElement)) applyText(root); return; }
  if (root.nodeType !== 1 || skipEl(root)) return;
  applyAttrs(root);
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
    acceptNode: (n) => (n.nodeType === 1 ? (SKIP.has(n.tagName) || n.getAttribute("translate") === "no" || n.classList.contains("notranslate")
      ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) : NodeFilter.FILTER_ACCEPT),
  });
  for (let n = tw.nextNode(); n; n = tw.nextNode()) { if (n.nodeType === 3) applyText(n); else applyAttrs(n); }
  flushSoon();
}

function flushSoon() {
  if (!queue.size || timer) return;
  timer = setTimeout(async () => {
    timer = null;
    const forLang = lang;
    const texts = [...queue].slice(0, 100);
    texts.forEach((t) => queue.delete(t));
    const f = (failed[forLang] = failed[forLang] || new Map());
    texts.forEach((t) => f.set(t, Date.now() + 60000));
    try {
      const r = await fetch(`${API}/api/v1/i18n/translate`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lang: forLang, texts }) });
      const j = r.ok ? await r.json() : { map: {} };
      dicts[forLang] = { ...(dicts[forLang] || {}), ...j.map };
      Object.keys(j.map || {}).forEach((t) => f.delete(t));
      if (forLang === lang) walk(document.body);
    } catch { /* offline: keep original text */ }
    if (queue.size) flushSoon();
  }, 250);
}

export async function setAutoLang(next) {
  lang = next || "en";
  queue = new Set();
  if (lang !== "en" && !dicts[lang]) {
    try { const r = await fetch(`${API}/api/v1/i18n/dict/${lang}`); dicts[lang] = r.ok ? (await r.json()).map : {}; } catch { dicts[lang] = {}; }
  }
  if (lang !== next) return;
  walk(document.body);
  if (!observer) {
    observer = new MutationObserver((muts) => {
      muts.forEach((m) => {
        if (m.type === "characterData") { if (m.target.parentElement && !skipEl(m.target.parentElement)) applyText(m.target); }
        else if (m.type === "attributes") { if (!skipEl(m.target)) applyAttrs(m.target); }
        else m.addedNodes.forEach((n) => walk(n));
      });
      flushSoon();
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }
}
