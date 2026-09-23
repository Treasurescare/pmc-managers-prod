import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { vendorRatingsApi } from "@/lib/api";
import { VendorTrustBadge } from "@/components/VendorTrustBadge";

/**
 * v46 — "Trusted Vendors" horizontal strip embedded on the public landing.
 * Loads /public/top and renders anonymised aggregate cards (Platinum → Bronze).
 */
export default function TrustedVendorsSection() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    vendorRatingsApi.publicTop(12)
      .then((res) => { if (!cancelled) setItems(res.items || []); })
      .catch(() => { if (!cancelled) setItems([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading || items.length === 0) return null;

  return (
    <section id="trusted-vendors"
             data-testid="trusted-vendors-section"
             className="border-t border-brand-navy/10 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 py-10 sm:py-14">
        <div className="flex flex-wrap items-baseline justify-between gap-3 mb-6">
          <div>
            <div className="pmc-label">Community trust</div>
            <h2 className="font-display text-3xl mt-1 text-brand-navy">
              Trusted vendors — rated by peers, buyers &amp; PMC
            </h2>
            <p className="text-sm text-brand-navy/60 mt-2 max-w-2xl">
              Anonymised, moderated ratings across delivery, quality, communication,
              compliance and more. Reviewer identities are verified but never shown publicly.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-widest">
            <VendorTrustBadge tier="platinum" compact score={null} />
            <VendorTrustBadge tier="gold"     compact score={null} />
            <VendorTrustBadge tier="silver"   compact score={null} />
            <VendorTrustBadge tier="bronze"   compact score={null} />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="trusted-vendors-grid">
          {items.map((v) => (
            <Link key={v.vendor_ref}
                  to={`/vendors/${v.vendor_ref}`}
                  data-testid={`trusted-vendor-${v.vendor_ref}`}
                  className="border border-brand-navy/10 bg-brand-pale/40 p-5 hover:border-brand-navy-soft/60 transition-colors group">
              <div className="flex items-baseline justify-between gap-3 mb-2">
                <span className="pmc-label text-brand-navy-soft">{v.vendor_ref}</span>
                {v.country && <span className="text-xs text-brand-navy/60">{v.country}</span>}
              </div>
              <div className="font-display text-lg text-brand-navy group-hover:text-brand-navy-soft transition-colors">
                {v.company_name}
              </div>
              <div className="mt-4">
                <VendorTrustBadge tier={v.badge} score={v.average_score} count={v.count}
                                    testid={`badge-${v.vendor_ref}`} />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
