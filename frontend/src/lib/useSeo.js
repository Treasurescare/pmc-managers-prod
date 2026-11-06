import { useEffect } from "react";
import { refreshHead } from "@/lib/autoTranslate";
import { URL_LANGS, barePath, langUrl } from "@/lib/langPath";

const SITE = "PMC Managers · Global Tender Grid";
const DEFAULT_IMG = "/downloads/pmc-logo-full.png";

export const SEO_PAGES = {
  home: ["Global Tender Grid — e-tendering for buyers and suppliers worldwide",
    "Publish tenders, receive sealed two-envelope bids, evaluate with committees and award with e-signature. Suppliers from any country register once and bid on public tenders."],
  buyers: ["For buyers — run audited e-tenders from project report to contract",
    "AI tender builder, sealed bids, evaluation committees, L1 comparison, escrowed EMD, e-signature and a hash-chained audit ledger for programme owners and PMC teams."],
  suppliers: ["For suppliers — find and bid on international tenders",
    "Register once, complete KYC and get matched to public tenders in your categories. Submit sealed technical and commercial bids and track every step to contract."],
  trust: ["Trust & security — how every tender stays honest",
    "Sealed envelopes, role-based access, two-factor sign-in, escrowed EMD and a SHA-256 hash-chained audit ledger anyone with audit rights can verify."],
  about: ["About PMC Managers — procurement people can trust",
    "PMC Managers runs project management and procurement for large programmes worldwide, with offices in the United Kingdom and Malaysia and offices opening in India, the United States and Kazakhstan."],
  vision: ["Our vision — transparent procurement for every major project",
    "Why PMC Managers built the Global Tender Grid: open access for qualified suppliers and provable decisions for buyers."],
  contact: ["Contact the PMC tender desk", "Questions about a tender, registration, KYC or EMD? Contact the PMC Managers tender desk."],
  live: ["Live tenders open for bids", "Browse public tenders, RFPs and RFQs open for bids on the Global Tender Grid, with budgets, deadlines and categories."],
  awards: ["Completed tenders and awards", "Published award results for tenders run on the Global Tender Grid."],
  help: ["Help Centre — guides for suppliers and buyers", "Step-by-step help on registering, KYC, bidding, EMD, evaluation and awards."],
};

const setMeta = (attr, key, val) => {
  let el = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!el) { el = document.createElement("meta"); el.setAttribute(attr, key); document.head.appendChild(el); }
  el.setAttribute("content", val);
};

export function useSeo({ page, title, description, image, jsonLd } = {}) {
  const [pt, pd] = SEO_PAGES[page] || [];
  const t = title || pt;
  const d = description || pd;
  const ld = jsonLd ? JSON.stringify(jsonLd) : "";
  useEffect(() => {
    if (!t) { return; }
    const full = `${t} | ${SITE}`;
    const url = window.location.origin + window.location.pathname;
    const img = new URL(image || DEFAULT_IMG, window.location.origin).href;
    document.title = full;
    setMeta("name", "description", d || "");
    [["og:title", full], ["og:description", d || ""], ["og:url", url], ["og:image", img], ["og:type", "website"],
      ["og:site_name", SITE]].forEach(([k, v]) => setMeta("property", k, v));
    [["twitter:card", "summary_large_image"], ["twitter:title", full], ["twitter:description", d || ""], ["twitter:image", img]]
      .forEach(([k, v]) => setMeta("name", k, v));
    let can = document.head.querySelector('link[rel="canonical"]');
    if (!can) { can = document.createElement("link"); can.rel = "canonical"; document.head.appendChild(can); }
    can.href = url;
    document.head.querySelectorAll("link[data-pmc-alt]").forEach((e) => e.remove());
    const bare = barePath();
    [["x-default", "en"], ["en", "en"], ...URL_LANGS.map((l) => [l, l])].forEach(([hl, lg]) => {
      const a = document.createElement("link");
      a.rel = "alternate"; a.hreflang = hl; a.href = window.location.origin + langUrl(lg, bare); a.setAttribute("data-pmc-alt", "");
      document.head.appendChild(a);
    });
    refreshHead();
    let s = document.getElementById("pmc-page-ld");
    if (ld) {
      if (!s) { s = document.createElement("script"); s.type = "application/ld+json"; s.id = "pmc-page-ld"; document.head.appendChild(s); }
      s.textContent = ld;
    } else if (s) { s.remove(); }
  }, [t, d, image, ld]);
}
