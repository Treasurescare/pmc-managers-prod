import AdminEShell from "./AdminEShell";
import ProductCatalogPanel from "@/apps/admin-console/ProductCatalogPanel";

export default function AdminCatalogE() {
  return (
    <div data-testid="admin-catalog-e" data-pmc-e-page="admin-catalog-e">
      <AdminEShell active="Catalog" crumb={<>Procurement / <b>Catalog</b></>}>
        <ProductCatalogPanel />
      </AdminEShell>
    </div>
  );
}
