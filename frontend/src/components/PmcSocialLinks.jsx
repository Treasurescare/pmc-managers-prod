import { useEffect, useState } from "react";
import { Facebook, Instagram, Linkedin, MessageCircle } from "lucide-react";
import { siteApi } from "@/lib/api";

const ICONS = [["linkedin", "LinkedIn", Linkedin], ["facebook", "Facebook", Facebook], ["instagram", "Instagram", Instagram], ["whatsapp", "WhatsApp", MessageCircle]];
const hrefFor = (k, v) => (k === "whatsapp" ? `https://wa.me/${v}` : v);
let cache = null;
export const resetSocialLinksCache = () => { cache = null; };

export default function PmcSocialLinks() {
  const [links, setLinks] = useState(cache || {});
  useEffect(() => {
    if (!cache) {
      cache = siteApi.social().catch(() => ({}));
    }
    Promise.resolve(cache).then((d) => { cache = d; setLinks(d); });
  }, []);
  const shown = ICONS.filter(([k]) => links[k]);
  const partner = <a href="/partner/register" className="pmc-muted" style={{ fontSize: "13px", display: "inline-block", marginTop: "14px" }} data-testid="footer-become-partner">Become a PMC partner →</a>;
  if (!shown.length) return partner;
  return (
    <>
    <div style={{ display: "flex", gap: "10px", marginTop: "18px" }} data-testid="footer-social-links">
      {shown.map(([key, label, Icon]) => (
        <a key={key} href={hrefFor(key, links[key])} target="_blank" rel="noopener noreferrer" aria-label={`PMC Managers on ${label}`}
           className="pmc-social-link" data-testid={`footer-social-${key}`}>
          <Icon size={16} strokeWidth={1.8} />
        </a>
      ))}
    </div>
    <div>{partner}</div>
    </>
  );
}
