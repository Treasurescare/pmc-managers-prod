import { useEffect, useState } from "react";
import { useI18n } from "@/context/I18nContext";

const PORTAL = [["/admin", "admin"], ["/vendor", "supplier"], ["/partner", "partner"], ["/staff", "staff"]];

export const manualLink = (map, pathname) => {
  if (!map) return null;
  const keys = Object.keys(map.pages).filter((k) => k.startsWith("/") && (pathname === k || pathname.startsWith(`${k}/`)));
  const best = keys.sort((a, b) => b.length - a.length)[0];
  const portal = (PORTAL.find(([p]) => pathname.startsWith(p)) || [null, "public"])[1];
  const page = (best && map.pages[best]) || map.pages[portal] || 1;
  return { href: `${map.file}#page=${page}`, page, portal };
};

export const ManualDownload = ({ style }) => {
  const { lang } = useI18n();
  const href = lang === "en" ? "/downloads/manual/PMC_v4_Master_Training_Manual.pdf" : `/downloads/manual/PMC_Master_Training_Manual_${lang}.pdf`;
  return <a href={href} target="_blank" rel="noreferrer" className="pmc-btn pmc-btn--ghost" style={style} data-testid="help-manual-download">Download the training manual (PDF)</a>;
};

export const ManualLink = ({ pathname }) => {
  const { lang } = useI18n();
  const [map, setMap] = useState(null);
  useEffect(() => {
    const get = (u) => fetch(u).then((r) => (r.ok ? r.json() : null)).catch(() => null);
    (lang === "en" ? Promise.resolve(null) : get(`/downloads/manual/sections_${lang}.json`))
      .then((m) => m || get("/downloads/manual/sections.json")).then(setMap);
  }, [lang]);
  const l = manualLink(map, pathname);
  if (!l) return null;
  return (
    <a href={l.href} target="_blank" rel="noreferrer" data-testid="help-read-manual"
       style={{ display: "block", padding: "10px 12px", margin: "4px 0 12px", border: "1px solid var(--gold, #B8892B)", borderRadius: 8, textDecoration: "none", color: "inherit" }}>
      <b style={{ fontSize: 14 }}>Read the manual for this screen</b>
      <div className="pmc-muted" style={{ fontSize: 12, marginTop: 2 }}>Opens the PMC Master Training Manual at page {l.page}</div>
    </a>);
};
