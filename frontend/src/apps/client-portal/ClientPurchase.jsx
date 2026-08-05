/**
 * ClientPurchase — public price page for buyer-side services. Reads catalog
 * live so every admin edit shows up immediately. Powers Wave 36.
 */
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";
import PurchaseGrid from "@/apps/shared/PurchaseGrid";

export default function ClientPurchase() {
  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 lg:px-10 py-10">
        <PurchaseGrid
          side="client"
          kicker="Client Services · Pre-award · Post-award · EOP · Packages"
          title="Services & subscriptions"
        />
      </main>
      <Footer />
    </div>
  );
}
