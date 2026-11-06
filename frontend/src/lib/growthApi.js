import { api } from "@/lib/api";

const g = (u, params) => api.get(u, { params }).then((r) => r.data);
const p = (u, b) => api.post(u, b).then((r) => r.data);
const put = (u, b) => api.put(u, b).then((r) => r.data);

export const growthApi = {
  aiSummary: (form) => api.post("/api/v1/supplier-ai/summary", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data),
  aiReadiness: (b) => p("/api/v1/supplier-ai/readiness", b),
  i18nStats: () => g("/api/v1/i18n/admin/stats"),
  i18nPhrases: (params) => g("/api/v1/i18n/admin/phrases", params),
  saveI18nPhrase: (b) => put("/api/v1/i18n/admin/phrases", b),
  aiReports: () => g("/api/v1/supplier-ai/reports"),
  aiPrices: () => g("/api/v1/supplier-ai/prices"),
  alerts: () => g("/api/v1/vendor-alerts/saved"),
  createAlert: (b) => p("/api/v1/vendor-alerts/saved", b),
  updateAlert: (id, b) => put(`/api/v1/vendor-alerts/saved/${id}`, b),
  deleteAlert: (id) => api.delete(`/api/v1/vendor-alerts/saved/${id}`).then((r) => r.data),
  previewAlert: (id) => g(`/api/v1/vendor-alerts/saved/${id}/preview`),
  directory: (params) => g("/api/v1/directory", params),
  myListing: () => g("/api/v1/directory/me"),
  setMyListing: (b) => put("/api/v1/directory/me", b),
  buyFeature: () => p("/api/v1/directory/me/feature"),
  adminDirectory: () => g("/api/v1/directory/admin"),
  adminFeature: (ref, days) => put(`/api/v1/directory/admin/${ref}/feature`, { days }),
  services: () => g("/api/v1/consulting/services"),
  adminServices: () => g("/api/v1/consulting/admin/services"),
  createService: (b) => p("/api/v1/consulting/admin/services", b),
  updateService: (id, b) => put(`/api/v1/consulting/admin/services/${id}`, b),
  requestService: (b) => p("/api/v1/consulting/requests", b),
  adminRequests: () => g("/api/v1/consulting/admin/requests"),
  updateRequest: (id, b) => api.patch(`/api/v1/consulting/admin/requests/${id}`, b).then((r) => r.data),
  applyBuyer: (b) => p("/api/v1/buyer-applications", b),
  buyerApps: () => g("/api/v1/buyer-applications"),
  decideBuyer: (id, b) => p(`/api/v1/buyer-applications/${id}/decision`, b),
  apiClients: () => g("/api/v1/data-api/clients"),
  createApiClient: (b) => p("/api/v1/data-api/clients", b),
  updateApiClient: (id, b) => put(`/api/v1/data-api/clients/${id}`, b),
  rotateApiClient: (id) => p(`/api/v1/data-api/clients/${id}/rotate`),
  sources: () => g("/api/v1/tender-feeds/sources"),
  updateSource: (code, b) => put(`/api/v1/tender-feeds/sources/${code}`, b),
  runSource: (code) => p(`/api/v1/tender-feeds/sources/${code}/run`),
  globalTenders: (params) => g("/api/v1/global-tenders", params),
};

// 402 = pay-per-use: returns { message, checkout_url } or null
export const payNeeded = (e) => (e?.response?.status === 402 && typeof e.response.data?.detail === "object" ? e.response.data.detail : null);
