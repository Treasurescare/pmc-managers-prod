/**
 * VendorPurchase — public price page for supplier-side services. Includes
 * Supplier Success SME/Mid/Tier1 subscriptions, project-setup fees and the
 * 13 monthly reporting add-ons. Powers Wave 37.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { vendorApi } from "@/lib/api";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";
import PurchaseGrid from "@/apps/shared/PurchaseGrid";

export default function VendorPurchase() {
  const navigate = useNavigate();
  // v52bv — signed-in vendors land here from the portal sidebar; give them
  // an explicit way back. Public visitors fall back to the home page.
  const [isVendor, setIsVendor] = useState(false);
  useEffect(() => {
    vendorApi.me().then(() => setIsVendor(true)).catch(() => setIsVendor(false));
  }, []);

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 lg:px-10 py-10">
        <div className="mb-6">
          <button type="button"
                  onClick={() => navigate(isVendor ? "/vendor" : "/")}
                  data-testid="services-back-btn"
                  className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy text-brand-navy bg-white hover:bg-brand-navy hover:text-white">
            ← {isVendor ? "Back to supplier portal" : "Back to home"}
          </button>
        </div>
        <PurchaseGrid
          side="supplier"
          kicker="Supplier Programme · Tender-stage · Post-award · Supplier Success"
          title="Supplier services & subscriptions"
        />
      </main>
      <Footer />
    </div>
  );
}
