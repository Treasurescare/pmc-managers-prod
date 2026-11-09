import { api, BACKEND_URL } from "@/lib/api";

const g = (u, p) => api.get(u, { params: p }).then((r) => r.data);
const p = (u, b) => api.post(u, b || {}).then((r) => r.data);

export const marketApi = {
  browse: (params) => g("/api/v1/market/listings", params),
  detail: (id) => g(`/api/v1/market/listings/${id}`),
  bid: (id, amount) => p(`/api/v1/market/listings/${id}/bid`, { amount }),
  offer: (id, amount, note) => p(`/api/v1/market/listings/${id}/offer`, { amount, note }),
  buy: (id) => p(`/api/v1/market/listings/${id}/buy`),
  purchases: () => g("/api/v1/market/my-purchases"),
  pay: (oid) => p(`/api/v1/market/orders/${oid}/pay`),
  orderStatus: (oid) => g(`/api/v1/market/orders/${oid}/status`),
  mine: () => g("/api/v1/market/mine"),
  create: (b) => p("/api/v1/market/listings", b),
  update: (id, b) => api.put(`/api/v1/market/listings/${id}`, b).then((r) => r.data),
  submit: (id) => p(`/api/v1/market/listings/${id}/submit`),
  withdraw: (id) => p(`/api/v1/market/listings/${id}/withdraw`),
  acceptOffer: (bid) => p(`/api/v1/market/offers/${bid}/accept`),
  adminListings: (status) => g("/api/v1/market/admin/listings", { status }),
  decide: (id, b) => p(`/api/v1/market/admin/listings/${id}/decision`, b),
  settings: () => g("/api/v1/market/admin/settings"),
  saveSettings: (b) => api.put("/api/v1/market/admin/settings", b).then((r) => r.data),
  adminOrders: () => g("/api/v1/market/admin/orders"),
  payout: (id, reference) => p(`/api/v1/market/admin/orders/${id}/payout`, { reference }),
  uploadMedia: (file, kind) => { const fd = new FormData(); fd.append("file", file); fd.append("kind", kind); return api.post("/api/v1/market/media", fd, { timeout: 180000 }).then((r) => r.data); },
  startImport: (file) => { const fd = new FormData(); fd.append("file", file); return api.post("/api/v1/market/catalogue/import", fd, { timeout: 300000 }).then((r) => r.data); },
  getImport: (id) => g(`/api/v1/market/catalogue/import/${id}`),
  bulk: (items) => p("/api/v1/market/listings/bulk", { items }),
};

export const mediaUrl = (id, download) => `${BACKEND_URL || ""}/api/v1/market/media/${id}${download ? "?download=true" : ""}`;
export const coverOf = (l) => (l.photos?.length ? mediaUrl(l.photos[0]) : l.image_url || "");

export const MODE_LABEL = { auction: "Timed auction", best_offer: "Best offer", fixed: "Fixed price" };
export const money = (cur, v) => (v == null ? "—" : `${cur} ${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);
