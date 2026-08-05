/**
 * VendorPurchase — public price page for supplier-side services. Includes
 * Supplier Success SME/Mid/Tier1 subscriptions, project-setup fees and the
 * 13 monthly reporting add-ons. Powers Wave 37.
 */
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";
import PurchaseGrid from "@/apps/shared/PurchaseGrid";

export default function VendorPurchase() {
  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 lg:px-10 py-10">
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
