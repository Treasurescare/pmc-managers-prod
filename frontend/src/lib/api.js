// PMC v2 API client — Build Sheet v2 Part 4 contract
import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const api = axios.create({
  baseURL: BACKEND_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Attach admin token if cached
api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem("pmc_admin_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } catch { /* noop */ }
  return config;
});

export function formatApiError(err) {
  const d = err?.response?.data?.detail;
  if (d == null) return err?.message || "Something went wrong. Please try again.";
  if (typeof d === "string") return d;
  if (Array.isArray(d))
    return d.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (d && typeof d.msg === "string") return d.msg;
  return String(d);
}

export const publicApi = {
  listNotices: (params = {}) => api.get("/api/v1/notices", { params }).then((r) => r.data),
  getNotice: (ref) => api.get(`/api/v1/notices/${ref}`).then((r) => r.data),
  publicStats: () => api.get("/api/v1/meta/public/stats").then((r) => r.data),
  kzMeta: () => api.get("/api/v1/meta/kz-licenses").then((r) => r.data),
  countries: () => api.get("/api/v1/meta/countries").then((r) => r.data),
};

export const registrationApi = {
  createDraft: (payload) => api.post("/api/v1/registrations", payload).then((r) => r.data),
  resume: (token) => api.get(`/api/v1/registrations/resume/${token}`).then((r) => r.data),
  update: (id, token, payload) =>
    api.patch(`/api/v1/registrations/${id}`, payload, { params: { token } }).then((r) => r.data),
  submit: (id, token) =>
    api.post(`/api/v1/registrations/${id}/submit`, {}, { params: { token } }).then((r) => r.data),
  status: (token) => api.get(`/api/v1/registrations/status/${token}`).then((r) => r.data),
};

export const adminApi = {
  login: (email, password) =>
    api.post("/api/v1/admin/auth/login", { email, password }).then((r) => {
      try { localStorage.setItem("pmc_admin_token", r.data.token); } catch { /* noop */ }
      return r.data;
    }),
  logout: () => api.post("/api/v1/admin/auth/logout").then(() => {
    try { localStorage.removeItem("pmc_admin_token"); } catch { /* noop */ }
  }),
  me: () => api.get("/api/v1/admin/auth/me").then((r) => r.data),
  listRegistrations: (params = {}) => api.get("/api/v1/registrations", { params }).then((r) => r.data),
  getRegistration: (id) => api.get(`/api/v1/registrations/${id}`).then((r) => r.data),
  decideRegistration: (id, action, notes) =>
    api.post(`/api/v1/registrations/${id}/decision`, { action, notes }).then((r) => r.data),
  createNotice: (payload) => api.post("/api/v1/notices", payload).then((r) => r.data),
  publishNotice: (ref) => api.post(`/api/v1/notices/${ref}/publish`).then((r) => r.data),
  listPackages: (params = {}) => api.get("/api/v1/packages", { params }).then((r) => r.data),
  createPackage: (payload) => api.post("/api/v1/packages", payload).then((r) => r.data),
  updatePackage: (id, payload) => api.patch(`/api/v1/packages/${id}`, payload).then((r) => r.data),
  audit: (params = {}) => api.get("/api/v1/audit-events", { params }).then((r) => r.data),
  verifyAudit: () => api.get("/api/v1/audit-events/verify").then((r) => r.data),
};

export default api;
