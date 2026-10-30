import { Facebook, Linkedin } from "lucide-react";

const LINKS = [
  { key: "linkedin", label: "LinkedIn", href: "https://www.linkedin.com/feed/update/urn:li:activity:7521796802216611840/", Icon: Linkedin },
  { key: "facebook", label: "Facebook", href: "https://www.facebook.com/profile.php?id=61596254811635", Icon: Facebook },
];

export default function PmcSocialLinks() {
  return (
    <div style={{ display: "flex", gap: "10px", marginTop: "18px" }} data-testid="footer-social-links">
      {LINKS.map(({ key, label, href, Icon }) => (
        <a key={key} href={href} target="_blank" rel="noopener noreferrer" aria-label={`PMC Managers on ${label}`}
           className="pmc-social-link" data-testid={`footer-social-${key}`}>
          <Icon size={16} strokeWidth={1.8} />
        </a>
      ))}
    </div>
  );
}
