import { useEffect, useState } from "react";
import { toast } from "sonner";
import { siteApi, showApiError } from "@/lib/api";
import { resetSocialLinksCache } from "@/components/PmcSocialLinks";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm w-full";
const FIELDS = [["linkedin", "LinkedIn link", "https://www.linkedin.com/company/…", "url"], ["facebook", "Facebook link", "https://www.facebook.com/…", "url"],
  ["instagram", "Instagram link", "https://www.instagram.com/…", "url"], ["whatsapp", "WhatsApp business number", "Country code + number, e.g. 447700900123", "tel"]];

export const WebsiteLinksTab = () => {
  const [f, setF] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { siteApi.social().then(setF).catch(showApiError); }, []);
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { setF(await siteApi.saveSocial(f)); resetSocialLinksCache(); toast.success("Footer links saved — live on the website now"); }
    catch (err) { showApiError(err); } finally { setBusy(false); }
  };
  if (!f) return null;
  return (
    <form onSubmit={save} className="border border-brand-navy/20 bg-white p-4 space-y-4 max-w-xl" data-testid="mkt-website-links">
      <div className="pmc-label">Social links in the website footer</div>
      {FIELDS.map(([k, label, ph, type]) => (
        <label key={k} className="block text-sm space-y-1">
          <span className="font-semibold">{label}</span>
          <input className={inp} type={type} placeholder={ph} value={f[k] || ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} data-testid={`site-social-${k}`} />
        </label>
      ))}
      <button className="pmc-btn pmc-btn--primary" disabled={busy} data-testid="site-social-save">{busy ? "Saving…" : "Save links"}</button>
      <div className="text-xs text-brand-navy/60">Links must start with https://. For WhatsApp enter the number only — the footer button opens a chat with it. Leave a box empty to hide that icon.</div>
    </form>
  );
};
