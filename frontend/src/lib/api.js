// PMC v2 API client — Build Sheet v2 Part 4 contract.
// Auth: httpOnly cookies set by /api/v1/{admin|staff|vendor}/auth/login.
// CSRF: double-submit-cookie pattern (X-CSRF-Token header on non-GET).
import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const api = axios.create({
  baseURL: BACKEND_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

function readCookie(name) {
  try {
    const match = document.cookie
      .split(";")
      .map((c) => c.trim())
      .find((c) => c.startsWith(`${name}=`));
    return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : null;
  } catch (err) {
    console.warn("Cookie read failed:", err);
    return null;
  }
}

api.interceptors.request.use((cfg) => {
  const method = (cfg.method || "get").toLowerCase();
  if (method !== "get" && method !== "head" && method !== "options") {
    const csrf = readCookie("csrf_token");
    if (csrf) cfg.headers["X-CSRF-Token"] = csrf;
  }
  return cfg;
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
    api.post("/api/v1/admin/auth/login", { email, password }).then((r) => r.data),
  logout: () => api.post("/api/v1/admin/auth/logout"),
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

// ---------- Wave 1: Staff (multi-role) ----------
export const staffApi = {
  login: (email, password, active_role, otp_code) =>
    api.post("/api/v1/staff/auth/login", { email, password, active_role, otp_code }).then((r) => r.data),
  logout: () => api.post("/api/v1/staff/auth/logout"),
  me: () => api.get("/api/v1/staff/auth/me").then((r) => r.data),
  roleChoices: () => api.get("/api/v1/staff/roles").then((r) => r.data),
  listStaff: () => api.get("/api/v1/staff").then((r) => r.data),
  createStaff: (p) => api.post("/api/v1/staff", p).then((r) => r.data),
  updateStaff: (id, p) => api.patch(`/api/v1/staff/${id}`, p).then((r) => r.data),
};

// ---------- Wave 1: Vendor ----------
export const vendorApi = {
  login: (email, password) =>
    api.post("/api/v1/vendor/auth/login", { email, password }).then((r) => r.data),
  logout: () => api.post("/api/v1/vendor/auth/logout"),
  me: () => api.get("/api/v1/vendor/auth/me").then((r) => r.data),
  changePassword: (current_password, new_password) =>
    api.post("/api/v1/vendor/auth/change-password", { current_password, new_password }).then((r) => r.data),
};

// ---------- Wave 1: Bids ----------
export const bidApi = {
  create: (p) => api.post("/api/v1/bids", p).then((r) => r.data),
  mine: () => api.get("/api/v1/bids/mine").then((r) => r.data),
  get: (id) => api.get(`/api/v1/bids/${id}`).then((r) => r.data),
  withdraw: (id) => api.post(`/api/v1/bids/${id}/withdraw`).then((r) => r.data),
  list: (params = {}) => api.get("/api/v1/bids", { params }).then((r) => r.data),
  decide: (id, payload) => api.post(`/api/v1/bids/${id}/decision`, payload).then((r) => r.data),
  assignCertifier: (id, certifierId) =>
    api.post(`/api/v1/bids/${id}/assign-certifier`, null, { params: { certifier_id: certifierId } }).then((r) => r.data),
};

// ---------- Wave 1: Payments (Stripe EMD) ----------
export const paymentApi = {
  checkout: (bid_id, origin_url) =>
    api.post("/api/v1/payments/emd/checkout", { bid_id, origin_url }).then((r) => r.data),
  status: (session_id) => api.get(`/api/v1/payments/status/${session_id}`).then((r) => r.data),
  refund: (bid_id, reason) =>
    api.post("/api/v1/payments/emd/refund", { bid_id, reason }).then((r) => r.data),
};

// ---------- Wave 1: Committee ----------
export const committeeApi = {
  create: (p) => api.post("/api/v1/committees", p).then((r) => r.data),
  list: () => api.get("/api/v1/committees").then((r) => r.data),
  vote: (p) => api.post("/api/v1/committees/vote", p).then((r) => r.data),
  close: (p) => api.post("/api/v1/committees/close", p).then((r) => r.data),
};

// ---------- Wave 1: Tasks + Chat ----------
export const taskApi = {
  list: (params = {}) => api.get("/api/v1/tasks", { params }).then((r) => r.data),
  create: (p) => api.post("/api/v1/tasks", p).then((r) => r.data),
  update: (id, p) => api.patch(`/api/v1/tasks/${id}`, p).then((r) => r.data),
  addFollowup: (id, p) => api.post(`/api/v1/tasks/${id}/followups`, p).then((r) => r.data),
};

export const chatApi = {
  list: (context_type, context_id) =>
    api.get("/api/v1/chat/messages", { params: { context_type, context_id } }).then((r) => r.data),
  send: (p) => api.post("/api/v1/chat/messages", p).then((r) => r.data),
  del: (id) => api.delete(`/api/v1/chat/messages/${id}`).then((r) => r.data),
};

// ---------- Wave 1: Inspections ----------
export const inspectionApi = {
  list: (params = {}) => api.get("/api/v1/inspections", { params }).then((r) => r.data),
  assign: (p) => api.post("/api/v1/inspections", p).then((r) => r.data),
  update: (id, p) => api.patch(`/api/v1/inspections/${id}`, p).then((r) => r.data),
  addMedia: (id, item) => api.post(`/api/v1/inspections/${id}/media`, item).then((r) => r.data),
  deleteMedia: (id, index) => api.delete(`/api/v1/inspections/${id}/media/${index}`).then((r) => r.data),
};

// ---------- Wave 1: Uploads ----------
export const uploadsApi = {
  presign: (file_name, content_type, scope, size_bytes) =>
    api.post("/api/v1/uploads/presign", { file_name, content_type, scope, size_bytes }).then((r) => r.data),
  direct: (key, file) => {
    const fd = new FormData();
    fd.append("key", key);
    fd.append("file", file);
    return api.post("/api/v1/uploads/direct", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
  },
};

// ---------- Wave 2: Evaluations ----------
export const evalApi = {
  lockEnvelope: (notice_ref, kind) =>
    api.post("/api/v1/evaluations/lock-envelope", { notice_ref, kind }).then((r) => r.data),
  saveRubric: (p) => api.post("/api/v1/evaluations/rubric", p).then((r) => r.data),
  getRubric: (ref) => api.get(`/api/v1/evaluations/rubric/${ref}`).then((r) => r.data),
  declareCOI: (p) => api.post("/api/v1/evaluations/coi", p).then((r) => r.data),
  listCOI: (ref) => api.get(`/api/v1/evaluations/coi/${ref}`).then((r) => r.data),
  score: (p) => api.post("/api/v1/evaluations/score", p).then((r) => r.data),
  awardReport: (ref) => api.get(`/api/v1/evaluations/award-report/${ref}`).then((r) => r.data),
};

// ---------- Wave 3: BOQ + Contracts ----------
export const boqApi = {
  createTemplate: (p) => api.post("/api/v1/boq/templates", p).then((r) => r.data),
  listTemplates: () => api.get("/api/v1/boq/templates").then((r) => r.data),
  getTemplate: (id) => api.get(`/api/v1/boq/templates/${id}`).then((r) => r.data),
  importExcel: (id, file) => {
    const fd = new FormData(); fd.append("file", file);
    return api.post(`/api/v1/boq/templates/${id}/import-excel`, fd,
      { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  compare: (id) => api.get(`/api/v1/boq/compare/${id}`).then((r) => r.data),
};

export const contractApi = {
  create: (p) => api.post("/api/v1/contracts", p).then((r) => r.data),
  list: () => api.get("/api/v1/contracts").then((r) => r.data),
  get: (id) => api.get(`/api/v1/contracts/${id}`).then((r) => r.data),
  completeMilestone: (id, order) =>
    api.post(`/api/v1/contracts/${id}/milestones/${order}/complete`).then((r) => r.data),
  addVariation: (p) => api.post("/api/v1/contracts/variations", p).then((r) => r.data),
};

// ---------- Wave 4: Vendor Intelligence + Masters ----------
export const vendorIntelApi = {
  rate: (p) => api.post("/api/v1/vendor-intel/ratings", p).then((r) => r.data),
  blacklist: (p) => api.post("/api/v1/vendor-intel/blacklist", p).then((r) => r.data),
  unblacklist: (ref) => api.delete(`/api/v1/vendor-intel/blacklist/${ref}`).then((r) => r.data),
  watchlist: (p) => api.post("/api/v1/vendor-intel/watchlist", p).then((r) => r.data),
  esg: (p) => api.post("/api/v1/vendor-intel/esg", p).then((r) => r.data),
  summary: () => api.get("/api/v1/vendor-intel/summary").then((r) => r.data),
};

export const mastersApi = {
  listCompanies: () => api.get("/api/v1/masters/companies").then((r) => r.data),
  createCompany: (p) => api.post("/api/v1/masters/companies", p).then((r) => r.data),
  listRoles: () => api.get("/api/v1/masters/roles").then((r) => r.data),
  createRole: (p) => api.post("/api/v1/masters/roles", p).then((r) => r.data),
  listMatrices: () => api.get("/api/v1/masters/approval-matrices").then((r) => r.data),
  createMatrix: (p) => api.post("/api/v1/masters/approval-matrices", p).then((r) => r.data),
};

// ---------- Wave 5: Analytics + AI ----------
export const analyticsApi = {
  dashboard: () => api.get("/api/v1/analytics/dashboard").then((r) => r.data),
  bidAnomaly: (bid_id) => api.post(`/api/v1/analytics/ai/bid-anomaly/${bid_id}`).then((r) => r.data),
  auditCopilot: (bid_id) => api.post(`/api/v1/analytics/ai/audit-copilot/${bid_id}`).then((r) => r.data),
};

// ---------- Wave 8: KYC ----------
export const kycApi = {
  start: (vendor_ref, level = "basic") =>
    api.post("/api/v1/kyc/start", { vendor_ref, level }).then((r) => r.data),
  get: (case_id) => api.get(`/api/v1/kyc/${case_id}`).then((r) => r.data),
  listForVendor: (vendor_ref) =>
    api.get(`/api/v1/kyc/vendor/${vendor_ref}`).then((r) => r.data),
};

// ---------- Wave 6: Auctions + Helpdesk ----------
export const auctionApi = {
  create: (p) => api.post("/api/v1/auctions", p).then((r) => r.data),
  list: () => api.get("/api/v1/auctions").then((r) => r.data),
  bid: (p) => api.post("/api/v1/auctions/bid", p).then((r) => r.data),
};

export const supportApi = {
  create: (p) => api.post("/api/v1/support/tickets", p).then((r) => r.data),
  list: () => api.get("/api/v1/support/tickets").then((r) => r.data),
  reply: (p) => api.post("/api/v1/support/tickets/reply", p).then((r) => r.data),
  close: (id) => api.post(`/api/v1/support/tickets/${id}/close`).then((r) => r.data),
};

// ---------- Wave 5 (extended): Sandbox EMD gateways (PayPal / Kaspi) ----------
export const sandboxPayApi = {
  checkout: (bid_id, gateway, origin_url) =>
    api.post("/api/v1/payments/sandbox/checkout", { bid_id, gateway, origin_url }).then((r) => r.data),
  session: (sid) => api.get(`/api/v1/payments/sandbox/session/${sid}`).then((r) => r.data),
  confirm: (session_id) => api.post("/api/v1/payments/sandbox/confirm", { session_id }).then((r) => r.data),
};

// ---------- Wave 7: MFA + Tenants + GDPR ----------
export const mfaApi = {
  status: () => api.get("/api/v1/staff/mfa/status").then((r) => r.data),
  enroll: () => api.post("/api/v1/staff/mfa/enroll").then((r) => r.data),
  verify: (otp_code) => api.post("/api/v1/staff/mfa/verify", { otp_code }).then((r) => r.data),
  disable: (otp_code) => api.post("/api/v1/staff/mfa/disable", { otp_code }).then((r) => r.data),
};

export const tenantApi = {
  list: () => api.get("/api/v1/tenants").then((r) => r.data),
  create: (p) => api.post("/api/v1/tenants", p).then((r) => r.data),
  update: (id, p) => api.patch(`/api/v1/tenants/${id}`, p).then((r) => r.data),
  publicGet: (code) => api.get(`/api/v1/tenants/public/${code}`).then((r) => r.data),
};

export const gdprApi = {
  forget: (registration_id) =>
    api.post(`/api/v1/registrations/${registration_id}/gdpr-forget`).then((r) => r.data),
  vendorSelfForget: (password) =>
    api.post("/api/v1/vendor/gdpr-forget", { password }).then((r) => r.data),
};

// ---------- Notifications ----------
export const notifyApi = {
  list: () => api.get("/api/v1/notifications").then((r) => r.data),
  markRead: (id) => api.post(`/api/v1/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () => api.post("/api/v1/notifications/read-all").then((r) => r.data),
};

export default api;
