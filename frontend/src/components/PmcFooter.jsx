import { Link } from "react-router-dom";

/** Editorial footer with Snapchat, Instagram, WhatsApp social integrations.
 *  URLs are read from window.__PMC_SOCIAL__ so the same build can point at
 *  different handles per environment; hard-coded fallback keeps the icons
 *  clickable during preview. */
const social = (typeof window !== "undefined" && window.__PMC_SOCIAL__) || {
  snapchat:  "https://www.snapchat.com/add/pmcmanagers",
  instagram: "https://www.instagram.com/pmcmanagers",
  whatsapp:  "https://wa.me/447700900001",
};

function Icon({ kind }) {
  if (kind === "snapchat") return (<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden><path d="M12 2c3.2 0 5.6 2.2 5.6 5.5 0 1.6-.2 3-.4 4.2 1 .4 2 .7 2.6.7.4 0 .6.2.6.5 0 .6-1 .9-2.1 1.1-.4.1-.6.3-.6.6 0 .6 1 1.7 2.3 2.4.4.2.5.5.3.8-.6 1.2-2.7 1.5-3.4 1.6-.2 0-.3.1-.4.4-.1.3-.2.7-.5.9-.4.3-1 .4-1.8.4-.7 0-1.5-.1-2.4 0-.8.2-1.8.6-3 .6s-2.2-.4-3-.6c-.9-.1-1.7 0-2.4 0-.8 0-1.4-.1-1.8-.4-.3-.2-.4-.6-.5-.9-.1-.3-.2-.4-.4-.4-.7-.1-2.8-.4-3.4-1.6-.2-.3-.1-.6.3-.8 1.3-.7 2.3-1.8 2.3-2.4 0-.3-.2-.5-.6-.6C3.2 14.8 2.2 14.5 2.2 13.9c0-.3.2-.5.6-.5.6 0 1.6-.3 2.6-.7C5.2 11.5 5 10.1 5 8.5 5 5.2 7.4 3 10.6 3 11 3 11.5 2 12 2z"/></svg>);
  if (kind === "instagram") return (<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4.2"/><circle cx="17.4" cy="6.6" r="1" fill="currentColor" stroke="none"/></svg>);
  if (kind === "whatsapp")  return (<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden><path d="M12 2C6.5 2 2 6.4 2 12c0 1.9.5 3.7 1.4 5.3L2 22l4.9-1.3A10 10 0 1 0 12 2zm5.9 14.1c-.3.7-1.6 1.4-2.2 1.5-.6.1-1.4.1-2.2-.1-.5-.2-1.2-.4-2.1-.8-3.6-1.6-6-5.4-6.2-5.6-.2-.2-1.5-2-1.5-3.8s.9-2.7 1.3-3.1c.3-.3.7-.4 1-.4h.7c.2 0 .5 0 .8.6.3.7.9 2.2 1 2.4.1.2.1.3 0 .5-.1.2-.2.3-.4.5s-.4.5-.6.7c-.2.2-.4.4-.2.7.2.4.9 1.5 2 2.4 1.3 1.2 2.4 1.5 2.8 1.7.4.2.6.1.8-.1.2-.2.9-1.1 1.1-1.4.2-.4.4-.3.7-.2.3.1 2.1 1 2.4 1.2.3.2.5.2.6.4.1.1.1.7-.2 1.4z"/></svg>);
  return null;
}

export default function PmcFooter() {
  return (
    <footer className="bg-brand-navy text-white/85 mt-24" data-testid="pmc-footer">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-14 grid gap-10 md:grid-cols-4">
        <div className="md:col-span-1">
          <div className="font-display text-2xl text-white">PMC Managers</div>
          <div className="pmc-label text-brand-gold/80 mt-1">Global Tender Board</div>
          <p className="text-sm text-white/70 leading-relaxed mt-4">
            The Big-4 procurement authority for cross-border public works,
            operating since 2018 across 11 jurisdictions.
          </p>
        </div>

        <div>
          <div className="pmc-label text-brand-gold/80 mb-3">Explore</div>
          <ul className="space-y-2 text-sm">
            <li><Link to="/tenders/live"     className="hover:text-brand-gold" data-testid="footer-live">Live tenders</Link></li>
            <li><Link to="/tenders/completed" className="hover:text-brand-gold" data-testid="footer-completed">Completed tenders</Link></li>
            <li><Link to="/notices" className="hover:text-brand-gold" data-testid="footer-notices">All notices</Link></li>
            <li><Link to="/register" className="hover:text-brand-gold" data-testid="footer-register">Register as supplier</Link></li>
          </ul>
        </div>

        <div>
          <div className="pmc-label text-brand-gold/80 mb-3">Company</div>
          <ul className="space-y-2 text-sm">
            <li><Link to="/about"   className="hover:text-brand-gold" data-testid="footer-about">About us</Link></li>
            <li><Link to="/vision"  className="hover:text-brand-gold" data-testid="footer-vision">Vision &amp; Mission</Link></li>
            <li><Link to="/login"   className="hover:text-brand-gold" data-testid="footer-signin">Sign in</Link></li>
          </ul>
        </div>

        <div>
          <div className="pmc-label text-brand-gold/80 mb-3">Follow</div>
          <div className="flex items-center gap-3">
            <a href={social.snapchat}  target="_blank" rel="noreferrer" aria-label="Snapchat"  data-testid="footer-social-snapchat"
               className="w-9 h-9 border border-white/25 hover:border-brand-gold hover:text-brand-gold flex items-center justify-center transition-colors">
              <Icon kind="snapchat" />
            </a>
            <a href={social.instagram} target="_blank" rel="noreferrer" aria-label="Instagram" data-testid="footer-social-instagram"
               className="w-9 h-9 border border-white/25 hover:border-brand-gold hover:text-brand-gold flex items-center justify-center transition-colors">
              <Icon kind="instagram" />
            </a>
            <a href={social.whatsapp}  target="_blank" rel="noreferrer" aria-label="WhatsApp"  data-testid="footer-social-whatsapp"
               className="w-9 h-9 border border-white/25 hover:border-brand-gold hover:text-brand-gold flex items-center justify-center transition-colors">
              <Icon kind="whatsapp" />
            </a>
          </div>
          <div className="pmc-label text-brand-gold/80 mt-6 mb-2">Legal</div>
          <ul className="space-y-1 text-xs text-white/60">
            <li>Terms of use</li>
            <li>Privacy &amp; GDPR</li>
            <li>Cookie preferences</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10 py-5 text-center text-[11px] uppercase tracking-widest text-white/40">
        © {new Date().getFullYear()} PMC Managers Limited · All rights reserved · v46
      </div>
    </footer>
  );
}
