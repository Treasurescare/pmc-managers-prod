// PMC v2 API client — Build Sheet v2 Part 4 contract.
// Auth: httpOnly cookies set by /api/v1/{admin|staff|vendor}/auth/login.
// CSRF: double-submit-cookie pattern (X-CSRF-Token header on non-GET).
import axios from "axios";
import { toast } from "sonner";

function resolveBackendUrl() {
  if (typeof window !== "undefined") {
    const h = window.location.hostname;
    // On production/custom domains (pmcmanagers.com, www.pmcmanagers.com, etc.),
    // always use same-origin relative URLs ("") so CloudFront routes /api
    // directly to Elastic Beanstalk. Never allow a baked-in preview URL to
    // hijack production API calls.
    // v51k — preview-host marker assembled from fragments so the shipped
    // bundle contains no platform-identifying literal.
    const PREVIEW_HOST = [".pre", "view.em", "ergent", "agent.com"].join("");
    if (h && !h.includes("localhost") && !h.includes("127.0.0.1") && !h.includes(PREVIEW_HOST)) {
      return "";
    }
  }
  return process.env.REACT_APP_BACKEND_URL || "";
}

export const BACKEND_URL = resolveBackendUrl();

export const api = axios.create({
  baseURL: BACKEND_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
  // v46x — never let a request hang forever (a stale service worker once
  // swallowed POST /api/* responses and left the UI stuck on "Verifying…").
  timeout: 20000,
});

function readCookie(name) {
  try {
    const match = document.cookie
      .split(";")
      .map((c) => c.trim())
      .find((c) => c.startsWith(`${name}=`));
    return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : null;
  } catch (err) {
    if (process.env.NODE_ENV !== "production") console.warn("Cookie read failed:", err);
    return null;
  }
}

// v51be — CSRF resilience. On some browser/profile combos the JS-readable
// `csrf_token` cookie set at login is silently dropped (strict ITP, 3rd-party
// cookie partitioning, or private-browsing). Without the cookie our request
// interceptor had no CSRF value and every POST/PUT/DELETE 403'd with
// "CSRF token missing or invalid". We now also cache the token returned in
// the login JSON body and use it as a fallback.
// v52g — expose cacheCsrf so escrow account/signatory login paths can
// stash the CSRF token in sessionStorage as a fallback (same resilience
// as adminApi.login / vendorApi.login).
export { cacheCsrf };

function cacheCsrf(token) {
  try { if (token) sessionStorage.setItem("pmc.csrf", token); } catch { /* ignore */ }
}
function readCsrf() {
  return readCookie("csrf_token") || (() => {
    try { return sessionStorage.getItem("pmc.csrf"); } catch { return null; }
  })();
}

// v56b — CSRF auto-recovery. If the browser drops the JS-readable csrf_token
// cookie (Safari ITP / cookie partitioning / long-idle tab) while the session
// is still valid, the server's double-submit check 403s. A single shared
// refresh re-issues the cookie for the authenticated session; the failed
// request is then retried once. Backed by GET /api/v1/staff/auth/csrf.
let _csrfRefreshInFlight = null;
function refreshCsrf() {
  if (!_csrfRefreshInFlight) {
    _csrfRefreshInFlight = api
      .get("/api/v1/staff/auth/csrf", { _skipCsrfRecovery: true })
      .then((r) => {
        const token = r?.data?.csrf_token;
        if (token) cacheCsrf(token);
        return token;
      })
      .finally(() => { _csrfRefreshInFlight = null; });
  }
  return _csrfRefreshInFlight;
}

api.interceptors.request.use((cfg) => {
  const method = (cfg.method || "get").toLowerCase();
  if (method !== "get" && method !== "head" && method !== "options") {
    // v56h — a retried request already carries a FRESH session-bound token
    // (set by the 403-recovery handler). Never clobber it with a possibly
    // stale cookie value, or the retry would 403 again.
    if (cfg._freshCsrf) return cfg;
    const csrf = readCsrf();
    if (csrf) cfg.headers["X-CSRF-Token"] = csrf;
  }
  return cfg;
});

// v50b — stale-session handler. When the auth cookie lapses mid-session
// (24 h Max-Age), API calls start failing with 401 "Not authenticated".
// Previously every surface showed that raw string (e.g. the DPR analyzer
// row). Now we redirect to /login once, with a return path, instead of
// letting each panel show a cryptic failure.
api.interceptors.response.use(
  (res) => {
    // v54v — CloudFront's SPA "Error Pages" rule rewrites a backend 4xx on
    // /api/* (e.g. a 403 for a wrong staff role, or a 404) into the app's
    // index.html with HTTP 200. That HTML arrives here looking like a success,
    // which made the unified /login "sign in" with no cookie set (then /me
    // 401'd and bounced to /login). Treat an HTML body on an API call as the
    // error it really is so callers never mistake it for a real response.
    try {
      const ct = (res?.headers?.["content-type"] || "").toLowerCase();
      const url = res?.config?.url || "";
      const looksHtml = ct.includes("text/html") ||
        (typeof res?.data === "string" && /^\s*<!doctype html/i.test(res.data));
      if (url.includes("/api/") && looksHtml) {
        return Promise.reject({
          response: { status: 502, data: { detail: "The server returned an unexpected response. Please try again." }, config: res.config },
          config: res.config,
          __pmcHtmlGuard: true,
        });
      }
    } catch { /* never let the guard itself break a response */ }
    return res;
  },
  async (err) => {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail;
    const cfg = err?.config;
    // v56b — recover from a dropped csrf_token cookie: refresh the cookie once
    // for the still-valid session, then retry the original request exactly once.
    // Match ANY 403 whose detail mentions CSRF (wording-agnostic).
    const detailStr = typeof detail === "string" ? detail : "";
    if (status === 403 && /csrf/i.test(detailStr) &&
        cfg && !cfg._skipCsrfRecovery && !cfg._csrfRetried) {
      cfg._csrfRetried = true;
      try {
        const token = await refreshCsrf();
        if (token) {
          cfg.headers = cfg.headers || {};
          cfg.headers["X-CSRF-Token"] = token;
          cfg._freshCsrf = true;
          return api.request(cfg);
        }
      } catch { /* fall through to normal error handling (likely 401) */ }
    }
    // v52bk — opt-out flag: probe calls (useAuthSession) deliberately hit
    // the three /me endpoints as unauthed and must NOT trigger a session
    // expiry redirect when they 401.
    const skipRedirect = err?.config?._skipAuthRedirect === true;
    if (status === 401 && !skipRedirect && (detail === "Not authenticated" || detail === "Token expired")) {
      const path = window.location.pathname;
      const onAuthPage = path === "/login" || path.startsWith("/register") || path === "/" || path.startsWith("/agent/") || path.startsWith("/partner/") || path.startsWith("/supplier-invite/");
      if (!onAuthPage && !window.__pmcAuthRedirecting) {
        window.__pmcAuthRedirecting = true;
        window.location.href = `/login?expired=1&next=${encodeURIComponent(path)}`;
      }
    }
    return Promise.reject(err);
  }
);

export function formatApiError(err) {
  const d = err?.response?.data?.detail;
  if (d == null) return err?.message || "Something went wrong. Please try again.";
  if (typeof d === "string") return d;
  if (Array.isArray(d))
    return d.map((e) => (e && typeof e.msg === "string" ? e.msg.replace(/^Value error, /, "") : JSON.stringify(e))).filter(Boolean).join(" ");
  if (d && typeof d.msg === "string") return d.msg;
  // v52bh — structured details (e.g. 412 {code, message, corrigenda:[…]})
  // must render as readable text, never "[object Object]".
  if (d && typeof d.message === "string") {
    const extra = Array.isArray(d.corrigenda) && d.corrigenda.length
      ? " (" + d.corrigenda.map((c) => c.title || c.corrigendum_no || c.id).join("; ") + ")"
      : "";
    return d.message + extra;
  }
  if (d && typeof d.error === "string") return d.error;
  if (d && typeof d.detail === "string") return d.detail;
  if (d && typeof d === "object") {
    try { return JSON.stringify(d); } catch { /* fall through */ }
  }
  return String(d);
}

/**
 * Loud, persistent, dismissable error toast for API failures.
 * Splits the backend detail into a short title (HTTP context + first sentence)
 * and a long description (full remediation text) so the user sees the WHY
 * immediately and can read the HOW below without truncation.
 *
 *   import { toast } from "sonner";
 *   import { showApiError } from "@/lib/api";
 *   try { ... } catch (e) { showApiError(e, { fallbackTitle: "Sign failed" }); }
 */
export function showApiError(err, { fallbackTitle = "Something went wrong" } = {}) {
  // v51c — top-level ESM import (require("sonner") resolved to the CJS build,
  // a SEPARATE store from the mounted <Toaster/>, so error toasts never
  // rendered — the "silent dead button" root cause on 4xx/5xx failures).
  const status = err?.response?.status;
  const detail = formatApiError(err);
  // Split on the first period+space (or newline) into headline + details.
  const [head, ...rest] = detail.split(/(?:\.\s+|\n)/);
  const description = rest.join(" ").trim();
  const title = status ? `${fallbackTitle} · HTTP ${status}` : fallbackTitle;
  toast.error(title, {
    description: description ? `${head}${head.endsWith(".") ? "" : "."}\n${description}` : head,
    duration: status && status >= 400 && status < 500 ? 10000 : 8000,
    closeButton: true,
  });
  // Also mirror to the browser console so operators / support can copy full
  // stack + response body when reporting a bug.
  if (typeof console !== "undefined") {
    console.error(`[api-error] ${title}\n${detail}`, err);
  }
}

export const publicApi = {
  listNotices: (params = {}) => api.get("/api/v1/notices", { params }).then((r) => r.data),
  getNotice: (ref) => api.get(`/api/v1/notices/${ref}`).then((r) => r.data),
  publicStats: () => api.get("/api/v1/meta/public/stats").then((r) => r.data),
  kzMeta: () => api.get("/api/v1/meta/kz-licenses").then((r) => r.data),
  countries: () => api.get("/api/v1/meta/countries").then((r) => r.data),
  listSectorsPublic: () => api.get("/api/v1/masters/sectors/public").then((r) => r.data),
  listContractTypesPublic: () => api.get("/api/v1/masters/contract-types/public").then((r) => r.data),
  listCategoriesPublic: (country) =>
    api.get("/api/v1/masters/categories/public", { params: { country: country || undefined } }).then((r) => r.data),
  goLive: () => api.get("/api/v1/settings/go-live/public").then((r) => r.data),
};

// v56s — admin Go-Live switch (persisted; OFF by default).
export const settingsApi = {
  getGoLive: () => api.get("/api/v1/settings/go-live").then((r) => r.data),
  setGoLive: (enabled) => api.put("/api/v1/settings/go-live", { enabled }).then((r) => r.data),
};

// v52cy — allowed PATCH fields on a registration draft. Pydantic
// `RegistrationUpdateIn` uses `extra="forbid"` so sending anything outside
// this list raises HTTP 422 ("Extra inputs are not permitted"). Admins were
// hitting this when the Admin "fill full form" screen leaked `email`,
// `document_slots`, `kzMeta`, `vendor_ref`, etc. into the save payload. We
// now whitelist on the client so every caller is safe.
const REGISTRATION_UPDATE_FIELDS = new Set([
  "company_name", "trade_name", "registered_address", "mailing_address", "country",
  "country_id_label", "registration_number", "incorporation_date", "tax_id",
  "legal_entity_type", "website", "employees_count",
  "contact_name", "contact_title", "contact_office_phone", "contact_mobile",
  "contact_email", "signatory_name", "signatory_title", "signatory_contact",
  "bank_name", "bank_branch", "bank_account_number", "bank_swift", "bank_address",
  "turnover_year1", "turnover_year2", "turnover_year3", "turnover_currency",
  "primary_sector", "business_description", "operating_regions",
  "business_categories", "previous_projects", "references", "iso_certifications",
  "licenses_permits", "insurance_details", "litigation_history", "kz_licenses",
  "documents", "decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
  "decl_data_consent", "decl_fee", "decl_notification",
  "primary_unspsc_code", "primary_unspsc_title",
  "sector_code", "sector_name", "contract_type_code", "contract_type_name",
  // v54c — Section E signature block + Directors section were silently
  // stripped by this whitelist, so the signature never reached the DB and
  // submit always failed with "Missing signature field: signature_name".
  "signature_name", "signature_title", "signature_date",
  "directors",
  // NOTE: `document_slots` is deliberately NOT here. Uploads manage their
  // own state through the dedicated slot endpoints; if a stale-tab PATCH
  // carried document_slots it could wipe a doc uploaded in another tab —
  // the exact "file is gone after navigating" bug.
]);
const _stripRegExtras = (payload) => {
  if (!payload || typeof payload !== "object") return payload;
  const clean = {};
  for (const k of Object.keys(payload)) {
    if (REGISTRATION_UPDATE_FIELDS.has(k)) clean[k] = payload[k];
  }
  return clean;
};

export const registrationApi = {
  createDraft: (payload) => api.post("/api/v1/registrations", payload).then((r) => r.data),
  resume: (token) => api.get(`/api/v1/registrations/resume/${token}`).then((r) => r.data),
  update: (id, token, payload) =>
    api.patch(`/api/v1/registrations/${id}`, _stripRegExtras(payload),
              { params: { token } }).then((r) => r.data),
  submit: (id, token) =>
    api.post(`/api/v1/registrations/${id}/submit`, {}, { params: { token } }).then((r) => r.data),
  status: (token) => api.get(`/api/v1/registrations/status/${token}`).then((r) => r.data),
  slotSchema: () => api.get("/api/v1/registrations/document-slots/schema").then((r) => r.data),
  uploadDocument: (registration_id, token, slot, file) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("token", token);
    return api.post(`/api/v1/registrations/${registration_id}/documents/${slot}`, fd,
      { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  deleteDocument: (registration_id, token, slot) =>
    api.delete(`/api/v1/registrations/${registration_id}/documents/${slot}`, { params: { token } }).then((r) => r.data),
};

export const adminApi = {
  login: (email, password) =>
    api.post("/api/v1/admin/auth/login", { email, password }).then((r) => {
      cacheCsrf(r.data?.csrf_token);
      return r.data;
    }),
  logout: () => api.post("/api/v1/admin/auth/logout").then((r) => {
    try { sessionStorage.removeItem("pmc.csrf"); } catch { /* ignore */ }
    return r;
  }),
  me: () => api.get("/api/v1/admin/auth/me").then((r) => r.data),
  changePassword: (current_password, new_password) =>
    api.post("/api/v1/admin/auth/change-password",
             { current_password, new_password }).then((r) => r.data),
  uploadAvatar: (data_url) =>
    api.post("/api/v1/admin/auth/avatar", { data_url }).then((r) => r.data),
  removeAvatar: () => api.delete("/api/v1/admin/auth/avatar").then((r) => r.data),
  uploadTenantLogo: (tenant_id, data_url) =>
    api.post(`/api/v1/tenants/${tenant_id}/logo`, { data_url }).then((r) => r.data),
  removeTenantLogo: (tenant_id) =>
    api.delete(`/api/v1/tenants/${tenant_id}/logo`).then((r) => r.data),
  listHelpRequests: (status) =>
    api.get("/api/v1/admin/help-requests",
            { params: status !== undefined && status !== "" ? { status } : {} })
      .then((r) => r.data),
  resolveHelpRequest: (id, resolution_notes) =>
    api.post(`/api/v1/admin/help-requests/${id}/resolve`,
             { resolution_notes }).then((r) => r.data),
  listRegistrations: (params = {}) => api.get("/api/v1/registrations", { params }).then((r) => r.data),
  // v51ac — admin opens the vendor's own resume URL to edit a non-approved
  // registration using the same 5-section stepper the vendor fills.
  registrationResumeLink: (rid) => api.get(`/api/v1/registrations/admin/${rid}/resume-link`).then((r) => r.data),
  registrationAdminUpdate: (rid, payload) =>
    api.patch(`/api/v1/registrations/admin/${rid}`, _stripRegExtras(payload)).then((r) => r.data),
  getRegistration: (id) => api.get(`/api/v1/registrations/${id}`).then((r) => r.data),
  decideRegistration: (id, action, notes) =>
    api.post(`/api/v1/registrations/${id}/decision`, { action, notes }).then((r) => r.data),
  createNotice: (payload) => api.post("/api/v1/notices", payload).then((r) => r.data),
  updateNotice: (ref, payload) => api.patch(`/api/v1/notices/${ref}`, payload).then((r) => r.data),
  getNoticeAdmin: (ref) => api.get(`/api/v1/notices/${ref}/admin`).then((r) => r.data),
  deleteNotice: (ref) => api.delete(`/api/v1/notices/${ref}`).then((r) => r.data),
  listAllNotices: (params = {}) => api.get("/api/v1/notices/admin/all", { params }).then((r) => r.data),
  taxonomyBackfillList: () => api.get("/api/v1/notices/admin/taxonomy-backfill").then((r) => r.data),
  taxonomyBackfillSave: (items) => api.post("/api/v1/notices/admin/taxonomy-backfill", { items }).then((r) => r.data),
  // Investor Demo Mode — one-click seed / reset / status
  demoStatus: () => api.get("/api/v1/admin/demo/status").then((r) => r.data),
  demoSeed: () => api.post("/api/v1/admin/demo/seed").then((r) => r.data),
  demoReset: () => api.post("/api/v1/admin/demo/reset").then((r) => r.data),
  publishNotice: (ref) => api.post(`/api/v1/notices/${ref}/publish`).then((r) => r.data),
  listPackages: (params = {}) => api.get("/api/v1/packages", { params }).then((r) => r.data),
  createPackage: (payload) => api.post("/api/v1/packages", payload).then((r) => r.data),
  updatePackage: (id, payload) => api.patch(`/api/v1/packages/${id}`, payload).then((r) => r.data),
  audit: (params = {}) => api.get("/api/v1/audit-events", { params }).then((r) => r.data),
  verifyAudit: () => api.get("/api/v1/audit-events/verify").then((r) => r.data),
  repairAudit: () => api.post("/api/v1/audit-events/rechain", null, { timeout: 120000 }).then((r) => r.data),
};

// ---------- Public auth helpers (forgot username / help request / reset) ----------
export const authApi = {
  usernameLookup: (payload) =>
    api.post("/api/v1/auth/username-lookup", payload).then((r) => r.data),
  helpRequest: (payload) =>
    api.post("/api/v1/auth/help-request", payload).then((r) => r.data),
  // v50 — real password reset flow (vendor + admin/staff)
  requestPasswordReset: (email, portal) =>
    api.post("/api/v1/auth/password-reset/request", { email, portal }).then((r) => r.data),
  verifyPasswordReset: (token) =>
    api.post("/api/v1/auth/password-reset/verify", { token }).then((r) => r.data),
  confirmPasswordReset: (token, new_password) =>
    api.post("/api/v1/auth/password-reset/confirm", { token, new_password }).then((r) => r.data),
};

// ---------- Wave 1: Staff (multi-role) ----------
export const staffApi = {
  login: (email, password, active_role, otp_code) =>
    api.post("/api/v1/staff/auth/login", { email, password, active_role, otp_code }).then((r) => {
      cacheCsrf(r.data?.csrf_token);
      return r.data;
    }),
  logout: () => api.post("/api/v1/staff/auth/logout").then((r) => {
    try { sessionStorage.removeItem("pmc.csrf"); } catch { /* ignore */ }
    return r;
  }),
  me: () => api.get("/api/v1/staff/auth/me").then((r) => r.data),
  roleChoices: () => api.get("/api/v1/staff/roles").then((r) => r.data),
  listStaff: () => api.get("/api/v1/staff").then((r) => r.data),
  createStaff: (p) => api.post("/api/v1/staff", p).then((r) => r.data),
  updateStaff: (id, p) => api.patch(`/api/v1/staff/${id}`, p).then((r) => r.data),
  // v53p — multi-role staff can swap their active role without logging out.
  switchRole: (active_role) =>
    api.post("/api/v1/staff/auth/switch-role", { active_role }).then((r) => {
      cacheCsrf(r.data?.csrf_token);
      return r.data;
    }),
  // v56f — PMC-officer escrow signing surface (scoped to the officer's email).
  escrowSignatures: () =>
    api.get("/api/v1/staff/escrow/signatures").then((r) => r.data),
  escrowTx: (tid) =>
    api.get(`/api/v1/staff/escrow/transactions/${tid}`).then((r) => r.data),
  escrowDocuSignUrl: (tid) =>
    api.get(`/api/v1/staff/escrow/transactions/${tid}/docusign-url`).then((r) => r.data),
  escrowRefresh: (tid) =>
    api.post(`/api/v1/staff/escrow/transactions/${tid}/docusign/refresh`).then((r) => r.data),
  escrowSignedDoc: (tid) =>
    api.get(`/api/v1/staff/escrow/transactions/${tid}/signed-document`).then((r) => r.data),
  myProcessedBids: () =>
    api.get("/api/v1/staff/my-processed-bids").then((r) => r.data),
};

// ---------- Wave 1: Vendor ----------
export const vendorApi = {
  login: (email, password) =>
    api.post("/api/v1/vendor/auth/login", { email, password }).then((r) => {
      cacheCsrf(r.data?.csrf_token);
      return r.data;
    }),
  logout: () => api.post("/api/v1/vendor/auth/logout").then((r) => {
    try { sessionStorage.removeItem("pmc.csrf"); } catch { /* ignore */ }
    return r;
  }),
  me: () => api.get("/api/v1/vendor/auth/me").then((r) => r.data),
  changePassword: (current_password, new_password) =>
    api.post("/api/v1/vendor/auth/change-password", { current_password, new_password }).then((r) => r.data),
  uploadAvatar: (data_url) =>
    api.post("/api/v1/vendor/auth/avatar", { data_url }).then((r) => r.data),
  removeAvatar: () => api.delete("/api/v1/vendor/auth/avatar").then((r) => r.data),
  revokeOtherSessions: () =>
    api.post("/api/v1/vendor/auth/sessions/revoke-others").then((r) => r.data),
  // v50m — profile edit with admin-approval gate
  getProfile: () => api.get("/api/v1/vendor/profile").then((r) => r.data),
  listProfileRequests: () => api.get("/api/v1/vendor/profile/requests").then((r) => r.data),
  requestProfileChange: (field, new_value, reason, parts, evidence) =>
    api.post("/api/v1/vendor/profile/request-change",
             { field, new_value, reason: reason || null,
               ...(parts ? { parts } : {}),
               ...(evidence?.evidence_key ? { evidence_key: evidence.evidence_key,
                                              evidence_filename: evidence.evidence_filename } : {}) }).then((r) => r.data),
  confirmEmailChange: (token) =>
    api.get(`/api/v1/vendor/profile/email-verify/${token}`).then((r) => r.data),
  confirmPhoneChange: (token) =>
    api.get(`/api/v1/vendor/profile/phone-verify/${token}`).then((r) => r.data),
  // v50l — vendor category interest (vendor side)
  myCategories: () => api.get("/api/v1/vendor/categories/mine").then((r) => r.data),
  categoryFeeQuote: (category_name) => api.get("/api/v1/vendor/categories/fee-quote", { params: { category_name } }).then((r) => r.data),
  categoryCheckout: (id, origin_url) => api.post(`/api/v1/vendor/categories/requests/${id}/checkout`, { origin_url }).then((r) => r.data),
  categoryCheckoutStatus: (sid) => api.get(`/api/v1/vendor/categories/checkout/status/${sid}`).then((r) => r.data),
  requestCategory: (p) =>
    api.post("/api/v1/vendor/categories/request", p).then((r) => r.data),
  // v50n — licences & certificates (Company & KYC tab)
  listLicenses: () => api.get("/api/v1/vendor/licenses").then((r) => r.data),
  addLicense: (p) => api.post("/api/v1/vendor/licenses", p).then((r) => r.data),
  updateLicense: (id, p) => api.put(`/api/v1/vendor/licenses/${id}`, p).then((r) => r.data),
  deleteLicense: (id) => api.delete(`/api/v1/vendor/licenses/${id}`).then((r) => r.data),
};

export const criteriaApi = {
  templates: () => api.get("/api/v1/tender-criteria/templates").then((r) => r.data),
  adminGet: (ref) => api.get(`/api/v1/tender-criteria/${ref}/admin`).then((r) => r.data),
  get: (ref) => api.get(`/api/v1/tender-criteria/${ref}`).then((r) => r.data),
  save: (ref, body) => api.put(`/api/v1/tender-criteria/${ref}`, body).then((r) => r.data),
  aiSuggest: (ref) => api.post(`/api/v1/tender-criteria/${ref}/ai-suggest`, {}, { timeout: 120000 }).then((r) => r.data),
  prefill: (ref) => api.get(`/api/v1/tender-criteria/${ref}/prefill`).then((r) => r.data),
  aiCheck: (ref) => api.post(`/api/v1/tender-criteria/${ref}/ai-check`, {}, { timeout: 120000 }).then((r) => r.data),
  mineGet: (ref) => api.get(`/api/v1/tender-criteria/${ref}/mine`).then((r) => r.data),
  mineSave: (ref, body) => api.put(`/api/v1/tender-criteria/${ref}/mine`, body).then((r) => r.data),
  mineAiSuggest: (ref) => api.post(`/api/v1/tender-criteria/${ref}/mine/ai-suggest`, {}, { timeout: 120000 }).then((r) => r.data),
  tplGet: (tid) => api.get(`/api/v1/tender-criteria/template/${tid}/mine`).then((r) => r.data),
  tplSave: (tid, body) => api.put(`/api/v1/tender-criteria/template/${tid}/mine`, body).then((r) => r.data),
  tplAiSuggest: (tid) => api.post(`/api/v1/tender-criteria/template/${tid}/mine/ai-suggest`, {}, { timeout: 120000 }).then((r) => r.data),
  qualification: (ref) => api.get(`/api/v1/tender-criteria/${ref}/qualification`).then((r) => r.data),
  proofVote: (ref, bidId, cid, body) => api.post(`/api/v1/tender-criteria/${ref}/bids/${bidId}/proofs/${cid}/vote`, body).then((r) => r.data),
  proofAiRun: (ref) => api.post(`/api/v1/tender-criteria/${ref}/proof-ai/run`).then((r) => r.data),
  doubt: (ref, bidId, body) => api.post(`/api/v1/tender-criteria/${ref}/bids/${bidId}/doubt`, body).then((r) => r.data),
  resolve: (ref, bidId, body) => api.post(`/api/v1/tender-criteria/${ref}/bids/${bidId}/resolve`, body).then((r) => r.data),
  score: (ref, bidId, body) => api.post(`/api/v1/tender-criteria/${ref}/bids/${bidId}/score`, body).then((r) => r.data),
  myResults: () => api.get("/api/v1/tender-criteria/results/vendor/mine").then((r) => r.data),
  resultNotices: (ref) => api.get(`/api/v1/tender-criteria/${ref}/result-notices`).then((r) => r.data),
  resendNotice: (ref, body) => api.post(`/api/v1/tender-criteria/${ref}/result-notices/resend`, body).then((r) => r.data),
  consortiumSplit: (tid) => api.get(`/api/v1/escrow/transactions/${tid}/consortium-split`).then((r) => r.data),
  splitPaid: (tid, idx, reference, proof_key) => api.post(`/api/v1/escrow/transactions/${tid}/consortium-split/${idx}/paid`, { reference, proof_key }).then((r) => r.data),
  splitSign: (tid, idx, comment) => api.post(`/api/v1/escrow/transactions/${tid}/consortium-split/${idx}/sign`, { comment }).then((r) => r.data),
};

export const criteriaLibApi = {
  get: () => api.get("/api/v1/criteria-library").then((r) => r.data),
  addItem: (b) => api.post("/api/v1/criteria-library/items", b).then((r) => r.data),
  editItem: (id, b) => api.put(`/api/v1/criteria-library/items/${id}`, b).then((r) => r.data),
  archiveItem: (id) => api.delete(`/api/v1/criteria-library/items/${id}`).then((r) => r.data),
  addSet: (b) => api.post("/api/v1/criteria-library/sets", b).then((r) => r.data),
  editSet: (id, b) => api.put(`/api/v1/criteria-library/sets/${id}`, b).then((r) => r.data),
  archiveSet: (id) => api.delete(`/api/v1/criteria-library/sets/${id}`).then((r) => r.data),
};

export const consortiumApi = {
  settings: () => api.get("/api/v1/consortia/settings").then((r) => r.data),
  saveSettings: (body) => api.put("/api/v1/consortia/settings", body).then((r) => r.data),
  mine: (noticeRef) => api.get("/api/v1/consortia/mine", { params: noticeRef ? { notice_ref: noticeRef } : {} }).then((r) => r.data),
  create: (body) => api.post("/api/v1/consortia", body).then((r) => r.data),
  addMember: (id, body) => api.post(`/api/v1/consortia/${id}/members`, body).then((r) => r.data),
  removeMember: (id, vid) => api.delete(`/api/v1/consortia/${id}/members/${vid}`).then((r) => r.data),
  respond: (id, accept) => api.post(`/api/v1/consortia/${id}/respond`, { accept }).then((r) => r.data),
  terms: (id, body) => api.put(`/api/v1/consortia/${id}/terms`, body).then((r) => r.data),
  uploadAgreement: (id, body) => api.post(`/api/v1/consortia/${id}/agreement/upload`, body).then((r) => r.data),
  sign: (id, body) => api.post(`/api/v1/consortia/${id}/agreement/sign`, body).then((r) => r.data),
  withdraw: (id) => api.post(`/api/v1/consortia/${id}/withdraw`).then((r) => r.data),
  leave: (id) => api.post(`/api/v1/consortia/${id}/leave`).then((r) => r.data),
  myPayouts: () => api.get("/api/v1/escrow/consortium-payouts/mine").then((r) => r.data),
};

// ---------- Wave 1: Bids ----------
export const bidApi = {
  create: (p) => api.post("/api/v1/bids", p).then((r) => r.data),
  mine: () => api.get("/api/v1/bids/mine").then((r) => r.data),
  get: (id) => api.get(`/api/v1/bids/${id}`).then((r) => r.data),
  withdraw: (id) => api.post(`/api/v1/bids/${id}/withdraw`).then((r) => r.data),
  sendEmdLink: (id) => api.post(`/api/v1/bids/${id}/emd/send-link`).then((r) => r.data),
  update: (id, payload) => api.patch(`/api/v1/bids/${id}`, payload).then((r) => r.data),
  list: (params = {}) => api.get("/api/v1/bids", { params }).then((r) => r.data),
  listAll: (params = {}) => api.get("/api/v1/bids", { params }).then((r) => r.data),
  decide: (id, payload) => api.post(`/api/v1/bids/${id}/decision`, payload).then((r) => r.data),
  assignCertifier: (id, certifierId) =>
    api.post(`/api/v1/bids/${id}/assign-certifier`, null, { params: { certifier_id: certifierId } }).then((r) => r.data),
  // v56 — assign (or clear with staff_id=null) a specialist role on a bid.
  assign: (id, role, staff_id) =>
    api.post(`/api/v1/bids/${id}/assign`, { role, staff_id: staff_id || null }).then((r) => r.data),
  technicalClear: (id) => api.post(`/api/v1/bids/${id}/technical-clear`).then((r) => r.data),
  financialOpen: (id) => api.post(`/api/v1/bids/${id}/financial-open`).then((r) => r.data),
  // v51bd — server-side bid drafts so vendors can switch devices mid-bid
  getDraft: (noticeRef) => api.get(`/api/v1/bids/drafts/${encodeURIComponent(noticeRef)}`).then((r) => r.data),
  saveDraft: (noticeRef, payload) => api.put(`/api/v1/bids/drafts/${encodeURIComponent(noticeRef)}`, payload).then((r) => r.data),
  deleteDraft: (noticeRef) => api.delete(`/api/v1/bids/drafts/${encodeURIComponent(noticeRef)}`).then((r) => r.data),
  listDrafts: () => api.get("/api/v1/bids/drafts").then((r) => r.data),
};

// ---------- Wave 1: Payments (Stripe EMD) ----------
export const paymentApi = {
  checkout: (bid_id, origin_url) =>
    api.post("/api/v1/payments/emd/checkout", { bid_id, origin_url }).then((r) => r.data),
  status: (session_id) => api.get(`/api/v1/payments/status/${session_id}`).then((r) => r.data),
  refund: (bid_id, reason) =>
    api.post("/api/v1/payments/emd/refund", { bid_id, reason }).then((r) => r.data),
  // v52bu — per-bid EMD receipt (authenticated blob download).
  receiptPdf: (bid_id, bid_ref) =>
    downloadAuthedFile(`/api/v1/payments/emd/bid/${bid_id}/receipt.pdf`,
      `PMC-EMD-Receipt-${bid_ref || bid_id}.pdf`),
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
export const agentApi = {
  agreement: () => api.get("/api/v1/agents/agreement").then((r) => r.data),
  joinInfo: (t) => api.get(`/api/v1/agents/join/${t}`).then((r) => r.data),
  join: (t, password) => api.post(`/api/v1/agents/join/${t}`, { password }).then((r) => { cacheCsrf(r.data?.csrf_token); return r.data; }),
  login: (email, password) => api.post("/api/v1/agents/auth/login", { email, password }).then((r) => { cacheCsrf(r.data?.csrf_token); return r.data; }),
  logout: () => api.post("/api/v1/agents/auth/logout").then((r) => r.data),
  me: () => api.get("/api/v1/agents/me").then((r) => { cacheCsrf(r.data?.csrf_token); return r.data; }),
  saveProfile: (p) => api.patch("/api/v1/agents/me/profile", p).then((r) => r.data),
  sign: (signer_name, consents) => api.post("/api/v1/agents/me/agreement", { signer_name, consents }).then((r) => r.data),
  submit: () => api.post("/api/v1/agents/me/submit").then((r) => r.data),
  adminList: () => api.get("/api/v1/admin/agents").then((r) => r.data),
  adminGet: (id) => api.get(`/api/v1/admin/agents/${id}`).then((r) => r.data),
  invite: (email, name) => api.post("/api/v1/admin/agents/invite", { email, name }).then((r) => r.data),
  resend: (id) => api.post(`/api/v1/admin/agents/${id}/resend`).then((r) => r.data),
  adminEdit: (id, body) => api.patch(`/api/v1/admin/agents/${id}/profile`, body).then((r) => r.data),
  register: (email, name, country) => api.post("/api/v1/agents/register", { email, name, country }).then((r) => r.data),
  refreshPayment: () => api.post("/api/v1/agents/me/payment/refresh").then((r) => r.data),
  decide: (id, action, note, waive_fee = false) => api.post(`/api/v1/admin/agents/${id}/decision`, { action, note, waive_fee }).then((r) => r.data),
  suppliers: () => api.get("/api/v1/agents/me/suppliers").then((r) => r.data),
  inviteSupplier: (p) => api.post("/api/v1/agents/me/suppliers", p).then((r) => r.data),
  resendSupplier: (rid) => api.post(`/api/v1/agents/me/suppliers/${rid}/resend`).then((r) => r.data),
  supplierEditLink: (rid) => api.post(`/api/v1/agents/me/suppliers/${rid}/edit-link`).then((r) => r.data),
  sendForReview: (rid) => api.post(`/api/v1/agents/me/suppliers/${rid}/send-for-review`).then((r) => r.data),
  wallet: () => api.get("/api/v1/agents/me/wallet").then((r) => r.data),
  requestPayout: () => api.post("/api/v1/agents/me/wallet/request-payout").then((r) => r.data),
  inviteInfo: (t) => api.get(`/api/v1/supplier-invites/${t}`).then((r) => r.data),
  inviteDecide: (t, p) => api.post(`/api/v1/supplier-invites/${t}`, p).then((r) => r.data),
  revokePartner: (rid, token) => api.post(`/api/v1/registrations/${rid}/partner-access/revoke`, {}, { params: { token } }).then((r) => r.data),
  switchMode: (rid, token, mode, signer_name = "") => api.post(`/api/v1/registrations/${rid}/partner-access/mode`, { mode, signer_name }, { params: { token } }).then((r) => r.data),
  reassign: (rid, partner_id, note) => api.post(`/api/v1/admin/partner-suppliers/${rid}/reassign`, { partner_id, note }).then((r) => r.data),
  leaderboard: () => api.get("/api/v1/agents/me/leaderboard").then((r) => r.data),
  adminLeaderboard: () => api.get("/api/v1/admin/partners/leaderboard").then((r) => r.data),
  setLeaderboard: (show_names) => api.put("/api/v1/admin/partners/leaderboard", { show_names }).then((r) => r.data),
  badges: () => api.get("/api/v1/agents/me/badges").then((r) => r.data),
  sendStatements: (month, resend = false) => api.post("/api/v1/admin/partners/statements/send", { month, resend }).then((r) => r.data),
  openStatement: async (url) => {
    const w = window.open("", "_blank");
    try {
      const r = await api.get(url, { responseType: "blob" });
      const href = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      if (w) w.location.href = href; else window.location.href = href;
    } catch (e) { if (w) w.close(); throw e; }
  },
  highlights: () => api.get("/api/v1/public/partner-highlights").then((r) => r.data),
  publicPartner: (code) => api.get(`/api/v1/public/partner/${encodeURIComponent(code)}`).then((r) => r.data),
  publicProfile: () => api.get("/api/v1/agents/me/public-profile").then((r) => r.data),
  savePublicProfile: (p) => api.put("/api/v1/agents/me/public-profile", p).then((r) => r.data),
  uploadPublicPhoto: (file) => { const fd = new FormData(); fd.append("file", file); return api.post("/api/v1/agents/me/public-photo", fd, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data); },
  hidePublicProfile: (id, hidden) => api.post(`/api/v1/admin/agents/${id}/public-profile/hide`, { hidden }).then((r) => r.data),
  commissionSettings: () => api.get("/api/v1/admin/partner-commission/settings").then((r) => r.data),
  saveCommissionSettings: (p) => api.put("/api/v1/admin/partner-commission/settings", p).then((r) => r.data),
  setPartnerRule: (id, rule) => api.put(`/api/v1/admin/agents/${id}/commission`, { rule }).then((r) => r.data),
  adminWallet: (id) => api.get(`/api/v1/admin/agents/${id}/wallet`).then((r) => r.data),
  addDeal: (id, p) => api.post(`/api/v1/admin/agents/${id}/commissions`, p).then((r) => r.data),
  settle: (cid, action, reference, paid_on = "") => api.post(`/api/v1/admin/partner-commissions/${cid}`, { action, reference, paid_on }).then((r) => r.data),
};

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
  // v52h — Partitioned (CHIPS) auth cookies are isolated to the top-level
  // site that set them. A plain <a target="_blank"> to /uploads/files/{key}
  // becomes its own top-level navigation, so the cookie isn't attached and
  // the gate returns 401. Fetch the bytes inside the SPA (same partition),
  // then open the blob URL in a new tab — works for images, PDFs, zips.
  openFile: async (key) => {
    if (!key) return;
    const r = await api.get(`/api/v1/uploads/files/${key}`, { responseType: "blob" });
    const url = URL.createObjectURL(r.data);
    const w = window.open(url, "_blank", "noopener,noreferrer");
    if (!w) {
      const a = document.createElement("a");
      a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer";
      a.click();
    }
    // Revoke after a minute — long enough for the tab to load the content.
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  },
  uploadFile: async (file, { scope = "escrow-docs" } = {}) => {
    if (!file) throw new Error("No file selected");
    const pre = await api.post("/api/v1/uploads/presign", {
      file_name: file.name,
      content_type: file.type || "application/octet-stream",
      scope,
      size_bytes: file.size || 0,
    }).then((r) => r.data);
    const fd = new FormData();
    fd.append("key", pre.key);
    fd.append("file", file);
    const up = await api.post("/api/v1/uploads/direct", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
    return {
      key: pre.key,
      filename: file.name,
      content_type: file.type || "application/octet-stream",
      size_bytes: up.size_bytes || file.size || 0,
      uploaded_at: new Date().toISOString(),
    };
  },
  // v52cz — "Download all" bundler: POST a list of upload keys, get back a
  // single ZIP. Used by the Vendor bid screen so a bidder can pull every
  // uploaded envelope/support document in one click without hitting View on
  // each row. Reuses the authenticated axios instance so admin AND vendor
  // sessions are honoured.
  downloadBundle: async (keys, { filename } = {}) => {
    const list = (keys || []).filter(Boolean);
    if (!list.length) throw new Error("No files selected for download");
    const res = await api.post("/api/v1/uploads/bundle",
      { keys: list, filename: filename || "documents" },
      { responseType: "blob" });
    const blob = new Blob([res.data], { type: res.headers?.["content-type"] || "application/zip" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(filename || "documents").replace(/[^A-Za-z0-9._ -]/g, "")}.zip`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  },
  // v51bd — authenticated-fetch of an uploaded file, returning a blob URL.
  // Browser `target=_blank` to the gated file endpoint does not reliably
  // forward the vendor's httpOnly cookie across the preview domain
  // (SameSite=None + Partitioned CHIPS), so a raw <a> tab 401s. Fetch via
  // axios (withCredentials) → blob → URL.createObjectURL so the user sees
  // the file inline on both admin + vendor sides.
  // v52cy rev6 — the new-tab popup path kept breaking (popup blockers on
  // async window.open, Chromium ignoring blob: location navigation, Safari
  // quirks). Replaced with an in-page viewer modal: zero popups involved.
  // PDF / image / text render inline; Office + DWG files download instead.
  openInNewTab: async (key, { download = false, filename } = {}) => {
    const res = await api.get(`/api/v1/uploads/files/${encodeURI(key)}`,
                               { params: download ? { download: 1 } : {},
                                 responseType: "blob" });
    const blob = new Blob([res.data], { type: res.headers?.["content-type"] || "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const fname = filename || key.split("/").pop() || "file";
    const ct = blob.type || "application/octet-stream";
    const inlineOk = ct === "application/pdf" || ct.startsWith("image/") || ct.startsWith("text/");

    const triggerDownload = () => {
      const a = document.createElement("a");
      a.href = url; a.download = fname;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    };

    if (download || !inlineOk) { triggerDownload(); return; }

    // In-page modal viewer (imperative DOM — this helper is not a React
    // component, so we build and tear down the overlay manually).
    const overlay = document.createElement("div");
    overlay.setAttribute("data-testid", "doc-viewer-modal");
    overlay.style.cssText =
      "position:fixed;inset:0;z-index:99999;background:rgba(15,23,42,.55);" +
      "display:flex;align-items:center;justify-content:center;padding:16px";
    const box = document.createElement("div");
    box.style.cssText =
      "background:#fff;width:min(980px,96vw);height:90vh;display:flex;flex-direction:column;" +
      "box-shadow:0 24px 64px rgba(0,0,0,.35);border-radius:8px;overflow:hidden";
    const bar = document.createElement("div");
    bar.style.cssText =
      "display:flex;align-items:center;gap:12px;padding:10px 14px;border-bottom:1px solid #e2e8f0;" +
      "font:600 13px system-ui;color:#0f172a";
    const title = document.createElement("span");
    title.textContent = fname;
    title.style.cssText = "flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
    const dlBtn = document.createElement("button");
    dlBtn.textContent = "Download";
    dlBtn.setAttribute("data-testid", "doc-viewer-download");
    dlBtn.style.cssText =
      "padding:6px 14px;font:600 11px system-ui;letter-spacing:.08em;text-transform:uppercase;" +
      "background:#0f172a;color:#fff;border:0;border-radius:4px;cursor:pointer";
    dlBtn.onclick = triggerDownload;
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "✕ Close";
    closeBtn.setAttribute("data-testid", "doc-viewer-close");
    closeBtn.style.cssText =
      "padding:6px 12px;font:600 11px system-ui;letter-spacing:.08em;text-transform:uppercase;" +
      "background:#f1f5f9;color:#0f172a;border:1px solid #cbd5e1;border-radius:4px;cursor:pointer";
    const viewer = document.createElement("embed");
    viewer.src = url;
    viewer.type = ct;
    viewer.setAttribute("data-testid", "doc-viewer-embed");
    viewer.style.cssText = "flex:1;width:100%;border:0;background:#525659";
    const close = () => {
      try { document.body.removeChild(overlay); } catch { /* already gone */ }
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      document.removeEventListener("keydown", onKey);
    };
    const onKey = (e) => { if (e.key === "Escape") close(); };
    closeBtn.onclick = close;
    overlay.onclick = (e) => { if (e.target === overlay) close(); };
    document.addEventListener("keydown", onKey);
    bar.appendChild(title); bar.appendChild(dlBtn); bar.appendChild(closeBtn);
    box.appendChild(bar); box.appendChild(viewer);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
  },
};

// v52br — authenticated file download for admin-gated endpoints reached by
// a click (CSV exports, sample files). A raw <a href target="_blank"> drops
// the Bearer token and the new tab shows {"detail":"Not authenticated"};
// this fetches via axios (token attached) and downloads a Blob instead.
export const downloadAuthedFile = async (path, filename) => {
  const res = await api.get(path, { responseType: "blob" });
  const blob = new Blob([res.data], { type: res.headers?.["content-type"] || "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
};

// ---------- Wave 2: Evaluations ----------
export const evalApi = {
  lockEnvelope: (notice_ref, kind) =>
    api.post("/api/v1/evaluations/lock-envelope", { notice_ref, kind }).then((r) => r.data),
  lockState: (notice_ref) =>
    api.get(`/api/v1/evaluations/lock-state/${encodeURIComponent(notice_ref)}`).then((r) => r.data),
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
  updateTemplate: (id, p) => api.patch(`/api/v1/boq/templates/${id}`, p).then((r) => r.data),
  importExcel: (id, file) => {
    const fd = new FormData(); fd.append("file", file);
    return api.post(`/api/v1/boq/templates/${id}/import-excel`, fd,
      { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  // v52by — authenticated Excel + PDF export of a BOQ template.
  exportXlsx: (id, name) =>
    downloadAuthedFile(`/api/v1/boq/templates/${id}/export.xlsx`,
      `BOQ-${(name || id).replace(/\s+/g, "-")}.xlsx`),
  exportPdf: (id, name) =>
    downloadAuthedFile(`/api/v1/boq/templates/${id}/export.pdf`,
      `BOQ-${(name || id).replace(/\s+/g, "-")}.pdf`),
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
  blacklistDashboard: () => api.get("/api/v1/vendor-intel/blacklist-dashboard").then((r) => r.data),
  decideAppeal: (ref, idx, payload) =>
    api.post(`/api/v1/vendor-intel/blacklist/${ref}/appeals/${idx}/decision`, payload).then((r) => r.data),
  // v51bd — blacklist evidence (admin) + vendor appeal
  getBlacklist: (ref) => api.get(`/api/v1/vendor-intel/blacklist/${ref}`).then((r) => r.data),
  addEvidence: (ref, p) =>
    api.post(`/api/v1/vendor-intel/blacklist/${ref}/evidence`, p).then((r) => r.data),
  updateEvidence: (ref, idx, p) =>
    api.patch(`/api/v1/vendor-intel/blacklist/${ref}/evidence/${idx}`, p).then((r) => r.data),
  deleteEvidence: (ref, idx) =>
    api.delete(`/api/v1/vendor-intel/blacklist/${ref}/evidence/${idx}`).then((r) => r.data),
  myBlacklist: () => api.get("/api/v1/vendor-intel/my-blacklist").then((r) => r.data),
  submitAppeal: (p) =>
    api.post("/api/v1/vendor-intel/my-blacklist/appeal", p).then((r) => r.data),
  addAppealEvidence: (p) =>
    api.post("/api/v1/vendor-intel/my-blacklist/appeal/evidence", p).then((r) => r.data),
  deleteAppealEvidence: (idx) =>
    api.delete(`/api/v1/vendor-intel/my-blacklist/appeal/evidence/${idx}`).then((r) => r.data),
};

// v52cx — admin-only "invite escrow institution by email" flow. The admin
// never fills third-party KYC data; we send the institution a magic-link
// and the institution self-fills the registration before our admin review.
export const escrowInstitutionsApi = {
  adminInvite: (payload) =>
    api.post("/api/v1/escrow-institutions/admin-invite", payload).then((r) => r.data),
  // v53k — admin list of institutions (status filter optional).
  list: (params = {}) =>
    api.get("/api/v1/escrow-institutions", { params }).then((r) => r.data),
  // v53m — admin cleanup for institutions sharing a primary_contact_email.
  duplicates: () =>
    api.get("/api/v1/escrow-institutions/duplicates").then((r) => r.data),
  delete: (iid) =>
    api.delete(`/api/v1/escrow-institutions/${iid}`).then((r) => r.data),
  // v56 — set institution country scope ([] = global). Admin/reviewer.
  setScope: (iid, country_scope) =>
    api.patch(`/api/v1/escrow-institutions/${iid}/scope`, { country_scope }).then((r) => r.data),
};


export const mastersApi = {
  listCompanies: () => api.get("/api/v1/masters/companies").then((r) => r.data),
  createCompany: (p) => api.post("/api/v1/masters/companies", p).then((r) => r.data),
  // v56 — full company master: profile update + document/license management.
  updateCompany: (id, p) => api.patch(`/api/v1/masters/companies/${id}`, p).then((r) => r.data),
  setCompanyDocument: (id, slot, p) =>
    api.put(`/api/v1/masters/companies/${id}/documents/${slot}`, p).then((r) => r.data),
  deleteCompanyDocument: (id, slot) =>
    api.delete(`/api/v1/masters/companies/${id}/documents/${slot}`).then((r) => r.data),
  addCompanyLicense: (id, p) =>
    api.post(`/api/v1/masters/companies/${id}/licenses`, p).then((r) => r.data),
  deleteCompanyLicense: (id, index) =>
    api.delete(`/api/v1/masters/companies/${id}/licenses/${index}`).then((r) => r.data),
  listRoles: () => api.get("/api/v1/masters/roles").then((r) => r.data),
  createRole: (p) => api.post("/api/v1/masters/roles", p).then((r) => r.data),
  listMatrices: () => api.get("/api/v1/masters/approval-matrices").then((r) => r.data),
  createMatrix: (p) => api.post("/api/v1/masters/approval-matrices", p).then((r) => r.data),
  // v52cx — admin edit / delete for approval matrices.
  updateMatrix: (id, p) => api.patch(`/api/v1/masters/approval-matrices/${id}`, p).then((r) => r.data),
  deleteMatrix: (id) => api.delete(`/api/v1/masters/approval-matrices/${id}`).then((r) => r.data),
  // v50g — procurement Category master (replaces hardcoded free-text category).
  listCategories: (country, { includeInactive = false } = {}) =>
    api.get("/api/v1/masters/categories", {
      params: { country: country || undefined, include_inactive: includeInactive },
    }).then((r) => r.data),
  listCategoriesPublic: (country) =>
    api.get("/api/v1/masters/categories/public", {
      params: { country: country || undefined },
    }).then((r) => r.data),
  createCategory: (p) => api.post("/api/v1/masters/categories", p).then((r) => r.data),
  updateCategory: (id, p) => api.patch(`/api/v1/masters/categories/${id}`, p).then((r) => r.data),
  deactivateCategory: (id) => api.delete(`/api/v1/masters/categories/${id}`).then((r) => r.data),
  // v56q — Sector & Contract-type taxonomy masters
  listSectors: (opts = {}) => api.get("/api/v1/masters/sectors", { params: { include_inactive: opts.includeInactive ? true : undefined } }).then((r) => r.data),
  createSector: (p) => api.post("/api/v1/masters/sectors", p).then((r) => r.data),
  updateSector: (id, p) => api.patch(`/api/v1/masters/sectors/${id}`, p).then((r) => r.data),
  deactivateSector: (id) => api.delete(`/api/v1/masters/sectors/${id}`).then((r) => r.data),
  listContractTypes: (opts = {}) => api.get("/api/v1/masters/contract-types", { params: { include_inactive: opts.includeInactive ? true : undefined } }).then((r) => r.data),
  createContractType: (p) => api.post("/api/v1/masters/contract-types", p).then((r) => r.data),
  updateContractType: (id, p) => api.patch(`/api/v1/masters/contract-types/${id}`, p).then((r) => r.data),
  deactivateContractType: (id) => api.delete(`/api/v1/masters/contract-types/${id}`).then((r) => r.data),
  // v52bk — ISO-4217 currency master (Notice/Bid/EMD money fields)
  listCurrencies: ({ includeInactive = false } = {}) =>
    api.get("/api/v1/masters/currencies", {
      params: { include_inactive: includeInactive },
    }).then((r) => r.data),
  listCurrenciesPublic: () =>
    api.get("/api/v1/masters/currencies/public").then((r) => r.data),
  createCurrency: (p) => api.post("/api/v1/masters/currencies", p).then((r) => r.data),
  updateCurrency: (id, p) => api.patch(`/api/v1/masters/currencies/${id}`, p).then((r) => r.data),
  deactivateCurrency: (id) => api.delete(`/api/v1/masters/currencies/${id}`).then((r) => r.data),
  // v52cz rev4 — country-specific identifier formats (reg no / tax id / VAT).
  // Used by any KYC form that needs per-country live-validation instead of
  // free-text accept-anything behaviour (escrow institutions first; vendor
  // registration can migrate next). Falls back cleanly to null fields when a
  // country isn't seeded yet.
  getCountryFormats: (cc) => cc
    ? api.get(`/api/v1/masters/country-formats/${encodeURIComponent(cc)}`)
         .then((r) => r.data)
    : Promise.resolve(null),
  listCountriesPublic: () =>
    api.get("/api/v1/masters/countries").then((r) => r.data),
  setCountryCurrencies: (code, p) =>
    api.patch(`/api/v1/masters/countries/${code}/currencies`, p).then((r) => r.data),
  dedupeTaxonomy: () => api.post("/api/v1/masters/dedupe-taxonomy").then((r) => r.data),
  listStates: (country_code) =>
    api.get("/api/v1/masters/states", { params: { country_code } }).then((r) => r.data),
  listCities: (country_code, state_code, q, limit = 200) =>
    api.get("/api/v1/masters/cities",
      { params: { country_code, state_code, q: q || undefined, limit } }
    ).then((r) => r.data),
  // v52cz rev6 — banks master for the escrow banking step (country + optional q).
  listBanks: (country_code, q) =>
    api.get("/api/v1/masters/banks",
      { params: { country_code, q: q || undefined } }
    ).then((r) => r.data).catch(() => []),
  // rev9 — "+" affordance on the banking step: persist a bank the registrant
  // typed but couldn't find, so it becomes selectable for everyone after.
  suggestBank: (payload) =>
    api.post("/api/v1/masters/banks", payload).then((r) => r.data),
  // v50y — legal entity types master (vendor registration Section A dropdown)
  listLegalEntityTypes: ({ includeInactive = false, country } = {}) =>
    api.get("/api/v1/masters/legal-entity-types", {
      params: { include_inactive: includeInactive, country: country || undefined },
    }).then((r) => r.data),
  listLegalEntityTypesPublic: (country) =>
    api.get("/api/v1/masters/legal-entity-types/public",
            { params: { country: country || undefined } }).then((r) => r.data),
  createLegalEntityType: (p) =>
    api.post("/api/v1/masters/legal-entity-types", p).then((r) => r.data),
  updateLegalEntityType: (id, p) =>
    api.patch(`/api/v1/masters/legal-entity-types/${id}`, p).then((r) => r.data),
  deactivateLegalEntityType: (id) =>
    api.delete(`/api/v1/masters/legal-entity-types/${id}`).then((r) => r.data),
  // v50l — vendor category requests (admin side)
  listCategoryRequests: (status = "pending") =>
    api.get("/api/v1/vendors/category-requests", { params: { status } }).then((r) => r.data),
  approveCategoryRequest: (id, notes) =>
    api.post(`/api/v1/vendors/category-requests/${id}/approve`, { notes: notes || null }).then((r) => r.data),
  rejectCategoryRequest: (id, notes) =>
    api.post(`/api/v1/vendors/category-requests/${id}/reject`, { notes }).then((r) => r.data),
  sendBackCategoryPayment: (id, notes) =>
    api.post(`/api/v1/vendors/category-requests/${id}/payment-pending`, { notes: notes || null, origin_url: window.location.origin }).then((r) => r.data),
  // v50m — vendor profile change requests (admin side)
  listProfileChangeRequests: (status = "pending") =>
    api.get("/api/v1/vendors/profile-change-requests", { params: { status } }).then((r) => r.data),
  approveProfileChangeRequest: (id, notes) =>
    api.post(`/api/v1/vendors/profile-change-requests/${id}/approve`, { notes: notes || null }).then((r) => r.data),
  rejectProfileChangeRequest: (id, notes) =>
    api.post(`/api/v1/vendors/profile-change-requests/${id}/reject`, { notes }).then((r) => r.data),
};

// ---------- Wave 5: Analytics + AI ----------
export const analyticsApi = {
  dashboard: () => api.get("/api/v1/analytics/dashboard").then((r) => r.data),
  bidAnomaly: (bid_id) => api.post(`/api/v1/analytics/ai/bid-anomaly/${bid_id}`).then((r) => r.data),
  auditCopilot: (bid_id) => api.post(`/api/v1/analytics/ai/audit-copilot/${bid_id}`).then((r) => r.data),
};

// ---------- Wave 8: KYC ----------
export const kycApi = {  start: (vendor_ref, level = "basic") =>
    api.post("/api/v1/kyc/start", { vendor_ref, level }).then((r) => r.data),
  get: (case_id) => api.get(`/api/v1/kyc/${case_id}`).then((r) => r.data),
  listForVendor: (vendor_ref) =>
    api.get(`/api/v1/kyc/vendor/${vendor_ref}`).then((r) => r.data),
  manual: (vendor_ref, decision, notes = null) =>
    api.post("/api/v1/kyc/manual", { vendor_ref, decision, notes }).then((r) => r.data),
};

// ---------- R8: Vendor Tender Preparation ----------
export const vendorTenderApi = {
  subscription: () => api.get("/api/v1/vendor-tenders/subscription").then((r) => r.data),
  startCheck: () => api.get("/api/v1/vendor-tenders/start/check").then((r) => r.data),
  startQuote: (p) => api.post("/api/v1/vendor-tenders/start/quote", p).then((r) => r.data),
  startCheckout: (p) => api.post("/api/v1/vendor-tenders/start/checkout", p).then((r) => r.data),
  startStatus: (sid) => api.get(`/api/v1/vendor-tenders/start/checkout/status/${sid}`).then((r) => r.data),
  receipts: () => api.get("/api/v1/vendor-tenders/receipts").then((r) => r.data),
  receiptPdf: (no) => downloadAuthedFile(`/api/v1/vendor-tenders/receipts/${encodeURIComponent(no)}.pdf`, `${no}.pdf`),
  fees: (tid) => api.get(`/api/v1/vendor-tenders/fees/${tid}`).then((r) => r.data),
  feeCheckout: (tid, fee_code, origin_url) => api.post(`/api/v1/vendor-tenders/fees/${tid}/checkout`, { fee_code, origin_url }).then((r) => r.data),
  feeStatus: (sid) => api.get(`/api/v1/vendor-tenders/fees/checkout/status/${sid}`).then((r) => r.data),
  scope: () => api.get("/api/v1/vendor-tenders/scope").then((r) => r.data),
  getScopeRules: () => api.get("/api/v1/vendor-tenders/scope-rules").then((r) => r.data),
  setScopeRules: (payload) => api.put("/api/v1/vendor-tenders/scope-rules", payload).then((r) => r.data),
  subCheckout: (origin_url) => api.post("/api/v1/vendor-tenders/subscription/checkout", { origin_url }).then((r) => r.data),
  subStatus: (sid) => api.get(`/api/v1/vendor-tenders/subscription/checkout/status/${sid}`).then((r) => r.data),
  getSubConfig: () => api.get("/api/v1/vendor-tenders/subscription/config").then((r) => r.data),
  setSubConfig: (payload) => api.post("/api/v1/vendor-tenders/subscription/config", payload).then((r) => r.data),
  create: (payload) => api.post("/api/v1/vendor-tenders", payload).then((r) => r.data),
  update: (ref, payload) => api.put(`/api/v1/vendor-tenders/${ref}`, payload).then((r) => r.data),
  submit: (ref) => api.post(`/api/v1/vendor-tenders/${ref}/submit`).then((r) => r.data),
  mine: () => api.get("/api/v1/vendor-tenders/mine").then((r) => r.data),
  reviewQueue: (status) => api.get("/api/v1/vendor-tenders/review/queue", { params: status ? { status } : {} }).then((r) => r.data),
  approve: (ref, note) => api.post(`/api/v1/vendor-tenders/${ref}/approve`, { note }).then((r) => r.data),
  requestChanges: (ref, note) => api.post(`/api/v1/vendor-tenders/${ref}/request-changes`, { note }).then((r) => r.data),
  reject: (ref, note) => api.post(`/api/v1/vendor-tenders/${ref}/reject`, { note }).then((r) => r.data),
};

// ---------- R7: Governance controls ----------
export const governanceApi = {
  listExceptions: (kind) => api.get("/api/v1/governance-controls/exceptions", { params: kind ? { kind } : {} }).then((r) => r.data),
  listBuyerClassifications: (status) => api.get("/api/v1/governance-controls/buyer-classifications", { params: status ? { status } : {} }).then((r) => r.data),
  classifyBuyer: (payload) => api.post("/api/v1/governance-controls/buyer-classifications", payload).then((r) => r.data),
  verifyBuyer: (payload) => api.post("/api/v1/governance-controls/buyer-classifications/verify", payload).then((r) => r.data),
  listIntegrityCases: (status) => api.get("/api/v1/governance-controls/integrity-cases", { params: status ? { status } : {} }).then((r) => r.data),
  raiseIntegrity: (payload) => api.post("/api/v1/governance-controls/integrity-cases", payload).then((r) => r.data),
  reviewIntegrity: (payload) => api.post("/api/v1/governance-controls/integrity-cases/review", payload).then((r) => r.data),
  resolveIntegrity: (payload) => api.post("/api/v1/governance-controls/integrity-cases/resolve", payload).then((r) => r.data),
  overrideIntegrity: (payload) => api.post("/api/v1/governance-controls/integrity-cases/senior-override", payload).then((r) => r.data),
  collusion: (noticeRef) => api.get(`/api/v1/governance-controls/collusion/${noticeRef}`).then((r) => r.data),
  listFeeWaivers: (status) => api.get("/api/v1/governance-controls/fee-waivers", { params: status ? { status } : {} }).then((r) => r.data),
  requestFeeWaiver: (payload) => api.post("/api/v1/governance-controls/fee-waivers", payload).then((r) => r.data),
  decideFeeWaiver: (payload) => api.post("/api/v1/governance-controls/fee-waivers/decide", payload).then((r) => r.data),
  listLegalRegister: () => api.get("/api/v1/governance-controls/legal-register").then((r) => r.data),
  upsertLegalRegister: (payload) => api.post("/api/v1/governance-controls/legal-register", payload).then((r) => r.data),
  listIncidents: () => api.get("/api/v1/governance-controls/incidents").then((r) => r.data),
  createIncident: (payload) => api.post("/api/v1/governance-controls/incidents", payload).then((r) => r.data),
  updateIncident: (payload) => api.post("/api/v1/governance-controls/incidents/update", payload).then((r) => r.data),
  publicIncidents: () => api.get("/api/v1/governance-controls/public/incidents").then((r) => r.data),
};

// ---------- Wave 9: Admin vendor invite + Permissions Matrix ----------
export const vendorInviteApi = {
  invite: (payload) => api.post("/api/v1/vendors/invite", payload).then((r) => r.data),
  inviteBulk: (csv_text) => api.post("/api/v1/vendors/invite-bulk", { csv_text }).then((r) => r.data),
  adminCreate: (payload) => api.post("/api/v1/vendors/admin-create", payload).then((r) => r.data),
  verifyMeta: (token) => api.get(`/api/v1/vendors/verify/${token}`).then((r) => r.data),
  complete: (token, password) =>
    api.post(`/api/v1/vendors/verify/${token}/complete`, { password }).then((r) => r.data),
  uploadTemplate: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/api/v1/vendors/registration-template", fd,
      { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  templateMeta: () => api.get("/api/v1/vendors/registration-template/meta").then((r) => r.data),
  // v52cz — RELATIVE path only. Baking REACT_APP_BACKEND_URL into the
  // production bundle pointed this at the preview host and triggered CORS
  // from pmcmanagers.com. CloudFront routes /api same-origin to EB.
  templateDownloadUrl: () => `/api/v1/vendors/registration-template`,
  // v44 — Admin one-click activation for an existing inactive vendor row.
  // mode: "resend_link" (default) resends the verify email; "set_password"
  // force-activates immediately using the supplied password.
  activate: (vendor_ref, { mode = "resend_link", password } = {}) =>
    api.post(`/api/v1/vendors/${vendor_ref}/activate`,
             { mode, password }).then((r) => r.data),
  // v51aa — rich bulk-invite CSV template that covers every Section A–E field.
  // v52cz — relative, see templateDownloadUrl above.
  bulkTemplateUrl: () => `/api/v1/vendors/invite-bulk/template`,
  // v51aa — full vendor doc (includes `profile` sub-dict) for the Edit screen.
  getFull: (vendor_ref) =>
    api.get(`/api/v1/vendors/admin/${vendor_ref}/full`).then((r) => r.data),
  updateFull: (vendor_ref, payload) =>
    api.patch(`/api/v1/vendors/admin/${vendor_ref}/full`, payload).then((r) => r.data),
};

export const permissionsApi = {
  get: () => api.get("/api/v1/permissions").then((r) => r.data),
  put: (rows) => api.put("/api/v1/permissions", { rows }).then((r) => r.data),
  reset: () => api.post("/api/v1/permissions/reset").then((r) => r.data),
};

export const noticeDocsApi = {
  uploadPrimary: (notice_ref, file) => {
    const fd = new FormData();
    fd.append("kind", "primary");
    fd.append("file", file);
    return api.post(`/api/v1/notices/${notice_ref}/document`, fd,
      { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  uploadAttachment: (notice_ref, file) => {
    const fd = new FormData();
    fd.append("kind", "attachment");
    fd.append("file", file);
    return api.post(`/api/v1/notices/${notice_ref}/document`, fd,
      { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  delete: (notice_ref) => api.delete(`/api/v1/notices/${notice_ref}`).then((r) => r.data),
  deleteDocument: (notice_ref, kind, file_name) =>
    api.delete(`/api/v1/notices/${notice_ref}/document`,
               { params: { kind, file_name } }).then((r) => r.data),
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
  publicByHost: (host) =>
    api.get("/api/v1/tenants/by-host", { params: { host } }).then((r) => r.data),
};

export const tenderTemplateApi = {
  // Bucket C fix — cache-buster prevents CloudFront/browser from returning
  // stale list after clone/delete. Bug reported: "delete gives success but
  // draft still listed" — usually the DELETE succeeded but the follow-up
  // list was served from cache.
  _cb: () => ({ _: Date.now() }),
  list: (kind) =>
    api.get("/api/v1/tender-templates", { params: { ...(kind ? { kind } : {}), _: Date.now() } }).then((r) => r.data),
  get: (id) => api.get(`/api/v1/tender-templates/${id}`).then((r) => r.data),
  create: (p, creditId) => api.post("/api/v1/tender-templates", p, creditId ? { params: { credit_id: creditId } } : undefined).then((r) => r.data),
  update: (id, p) => api.patch(`/api/v1/tender-templates/${id}`, p).then((r) => r.data),
  remove: (id) => api.delete(`/api/v1/tender-templates/${id}`).then((r) => r.data),
  reseed: () => api.post("/api/v1/tender-templates/seed").then((r) => r.data),
  uploadSectionAttachment: (id, code, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post(`/api/v1/tender-templates/${id}/sections/${encodeURIComponent(code)}/attachment`, fd,
      { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  removeSectionAttachment: (id, code) =>
    api.delete(`/api/v1/tender-templates/${id}/sections/${encodeURIComponent(code)}/attachment`).then((r) => r.data),
  aiDraftSection: (id, code, opts) =>
    api.post(`/api/v1/tender-templates/${id}/sections/${encodeURIComponent(code)}/ai-draft`, opts || {}).then((r) => r.data),
  bulkUpload: (id, files) => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    return api.post(`/api/v1/tender-templates/${id}/attachments/bulk`, fd,
      { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  listVersions: (id) =>
    api.get(`/api/v1/tender-templates/${id}/versions`).then((r) => r.data),
  restoreVersion: (id, index) =>
    api.post(`/api/v1/tender-templates/${id}/versions/${index}/restore`).then((r) => r.data),
  // R9 — vendor submit-for-review + active-reviewer moderation
  submitReview: (id) =>
    api.post(`/api/v1/tender-templates/${id}/submit-review`).then((r) => r.data),
  reviewQueue: (status) =>
    api.get("/api/v1/tender-templates/review/queue", { params: status ? { status } : {} }).then((r) => r.data),
  reviewApprove: (id, note) =>
    api.post(`/api/v1/tender-templates/${id}/review/approve`, { note }).then((r) => r.data),
  reviewRequestChanges: (id, note) =>
    api.post(`/api/v1/tender-templates/${id}/review/request-changes`, { note }).then((r) => r.data),
  reviewReject: (id, note) =>
    api.post(`/api/v1/tender-templates/${id}/review/reject`, { note }).then((r) => r.data),
  pendingMasters: () =>
    api.get("/api/v1/tender-templates/masters/pending").then((r) => r.data),
  approveMaster: (id) =>
    api.post(`/api/v1/tender-templates/${id}/master/approve`).then((r) => r.data),
  rejectMaster: (id, note) =>
    api.post(`/api/v1/tender-templates/${id}/master/reject`, { note }).then((r) => r.data),
};

export const siteApi = {
  social: () => api.get("/api/v1/site/social").then((r) => r.data),
  saveSocial: (p) => api.put("/api/v1/marketing/site-social", p).then((r) => r.data),
  emailHealth: () => api.get("/api/v1/admin/email/health").then((r) => r.data),
  emailTest: (to) => api.post("/api/v1/admin/email/test", { to }).then((r) => r.data),
};

export const whatsappApi = {
  status: () => api.get("/api/v1/admin/whatsapp/status").then((r) => r.data),
  saveSettings: (p) => api.put("/api/v1/admin/whatsapp/settings", p).then((r) => r.data),
  test: (number) => api.post("/api/v1/admin/whatsapp/test", { number }).then((r) => r.data),
  threads: () => api.get("/api/v1/admin/whatsapp/threads").then((r) => r.data),
  thread: (id) => api.get(`/api/v1/admin/whatsapp/threads/${id}`).then((r) => r.data),
  reply: (id, text) => api.post(`/api/v1/admin/whatsapp/threads/${id}/reply`, { text }).then((r) => r.data),
  mine: () => api.get("/api/v1/vendor/whatsapp").then((r) => r.data),
  saveMine: (p) => api.put("/api/v1/vendor/whatsapp", p).then((r) => r.data),
};

export const marketingApi = {
  contacts: (params = {}) => api.get("/api/v1/marketing/contacts", { params }).then((r) => r.data),
  addContact: (p) => api.post("/api/v1/marketing/contacts", p).then((r) => r.data),
  importCsv: (p) => api.post("/api/v1/marketing/contacts/import", p).then((r) => r.data),
  syncPlatform: () => api.post("/api/v1/marketing/contacts/sync").then((r) => r.data),
  deleteContact: (id) => api.delete(`/api/v1/marketing/contacts/${id}`).then((r) => r.data),
  segments: () => api.get("/api/v1/marketing/segments").then((r) => r.data),
  previewSegment: (p) => api.post("/api/v1/marketing/segments/preview", p).then((r) => r.data),
  createSegment: (p) => api.post("/api/v1/marketing/segments", p).then((r) => r.data),
  deleteSegment: (id) => api.delete(`/api/v1/marketing/segments/${id}`).then((r) => r.data),
  aiCopy: (p) => api.post("/api/v1/marketing/ai-copy", p).then((r) => r.data),
  campaigns: () => api.get("/api/v1/marketing/campaigns").then((r) => r.data),
  createCampaign: (p) => api.post("/api/v1/marketing/campaigns", p).then((r) => r.data),
  updateCampaign: (id, p) => api.put(`/api/v1/marketing/campaigns/${id}`, p).then((r) => r.data),
  deleteCampaign: (id) => api.delete(`/api/v1/marketing/campaigns/${id}`).then((r) => r.data),
  testCampaign: (id, email) => api.post(`/api/v1/marketing/campaigns/${id}/test`, { email }).then((r) => r.data),
  sendCampaign: (id) => api.post(`/api/v1/marketing/campaigns/${id}/send`).then((r) => r.data),
  alerts: () => api.get("/api/v1/marketing/alerts").then((r) => r.data),
  saveAlerts: (p) => api.put("/api/v1/marketing/alerts", p).then((r) => r.data),
  referrals: () => api.get("/api/v1/marketing/referrals").then((r) => r.data),
  myReferral: () => api.get("/api/v1/marketing/referral/me").then((r) => r.data),
  digestNow: () => api.post("/api/v1/marketing/alerts/digest-now").then((r) => r.data),
  subscribe: (p) => api.post("/api/v1/marketing/subscribe", p).then((r) => r.data),
  buyerInvites: () => api.get("/api/v1/marketing/buyer-invites").then((r) => r.data),
  sendBuyerInvite: (p) => api.post("/api/v1/marketing/buyer-invites", p).then((r) => r.data),
  markBuyerJoined: (id) => api.post(`/api/v1/marketing/buyer-invites/${id}/joined`).then((r) => r.data),
  googleExchange: (p) => api.post("/api/v1/auth/google/exchange", p).then((r) => r.data),
  googleStart: (p) => api.post("/api/v1/auth/google/start", p).then((r) => r.data),
  googleConfig: () => api.get("/api/v1/auth/google/config").then((r) => r.data),
  linkedinStatus: () => api.get("/api/v1/auth/linkedin/status").then((r) => r.data),
  linkedinConnect: () => api.get("/api/v1/marketing/linkedin/connect").then((r) => r.data),
  socialPosts: () => api.get("/api/v1/marketing/social-posts").then((r) => r.data),
  editSocialPost: (id, text) => api.put(`/api/v1/marketing/social-posts/${id}`, { text }).then((r) => r.data),
  approveSocialPost: (id) => api.post(`/api/v1/marketing/social-posts/${id}/approve`).then((r) => r.data),
  rejectSocialPost: (id) => api.post(`/api/v1/marketing/social-posts/${id}/reject`).then((r) => r.data),
  markSocialPosted: (id) => api.post(`/api/v1/marketing/social-posts/${id}/mark-posted`).then((r) => r.data),
  assistantChat: (p) => api.post("/api/v1/assistant/chat", p).then((r) => r.data),
};


// v45 — Tender Pro: DPR upload, AI fill-all, per-section save, masters, ratings.
export const vendorMessagesApi = {
  list: () => api.get("/api/v1/vendor/messages").then((r) => r.data),
  unreadCount: () => api.get("/api/v1/vendor/messages/unread-count").then((r) => r.data),
  read: (id) => api.post(`/api/v1/vendor/messages/${id}/read`).then((r) => r.data),
  readAll: () => api.post("/api/v1/vendor/messages/read-all").then((r) => r.data),
};

export const extraPayApi = {
  categoryInterest: (ref) => api.post(`/api/v1/notices/${ref}/category-interest`).then((r) => r.data),
  docFee: (ref) => api.get(`/api/v1/notices/${ref}/doc-fee`).then((r) => r.data),
  docFeeCheckout: (ref) => api.post(`/api/v1/notices/${ref}/doc-fee/checkout`, { origin_url: window.location.origin }).then((r) => r.data),
  docFeeStatus: (sid) => api.get(`/api/v1/notices/doc-fee/status/${sid}`).then((r) => r.data),
  hostingQuote: (ref) => api.get(`/api/v1/notices/${ref}/hosting-fee`).then((r) => r.data),
  hostingRequest: (ref, payer_email) => api.post(`/api/v1/notices/${ref}/hosting-fee/request`, { payer_email }).then((r) => r.data),
  payStatus: (sid) => api.get(`/api/v1/pay/status/${sid}`).then((r) => r.data),
  refundAlerts: () => api.get("/api/v1/billing/refund-alerts").then((r) => r.data),
  refund: (sid) => api.post(`/api/v1/billing/refund-alerts/${sid}/refund`).then((r) => r.data),
  intelCreate: (p) => api.post("/api/v1/data-intel/requests", p).then((r) => r.data),
  intelMine: () => api.get("/api/v1/data-intel/requests/mine").then((r) => r.data),
  intelPay: (id) => api.post(`/api/v1/data-intel/requests/${id}/checkout`, { origin_url: window.location.origin }).then((r) => r.data),
  intelAdmin: () => api.get("/api/v1/data-intel/admin").then((r) => r.data),
  intelQuote: (id, p) => api.post(`/api/v1/data-intel/admin/${id}/quote`, p).then((r) => r.data),
  intelDeliver: (id, p) => api.post(`/api/v1/data-intel/admin/${id}/deliver`, p).then((r) => r.data),
  intelDecline: (id, notes) => api.post(`/api/v1/data-intel/admin/${id}/decline`, { notes }).then((r) => r.data),
};

export const feeTypesApi = {
  list: () => api.get("/api/v1/fee-types").then((r) => r.data),
  create: (p) => api.post("/api/v1/fee-types", p).then((r) => r.data),
  update: (id, p) => api.patch(`/api/v1/fee-types/${id}`, p).then((r) => r.data),
  remove: (id) => api.delete(`/api/v1/fee-types/${id}`).then((r) => r.data),
};

export const tenderProApi = {
  analyzeDpr: (file, kind = "tender", templateId = null) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("Could not read file"));
      reader.onload = () => {
        const dataUrl = String(reader.result || "");
        const content_b64 = dataUrl.substring(dataUrl.indexOf(",") + 1);
        // v45c — base64 JSON path bypasses AWS WAF binary-body rules.
        // v45d — template_id makes the AI fill the master's exact sections.
        const tpl = templateId ? `&template_id=${encodeURIComponent(templateId)}` : "";
        api.post(`/api/v1/tender-pro/dpr/analyze-json?kind=${kind}${tpl}`,
          { filename: file.name, content_b64 }, { timeout: 300000 })
          .then((r) => resolve(r.data))
          .catch(reject);
      };
      reader.readAsDataURL(file);
    }),
  // v46l — background pipeline for large tenders. Returns {job_id} then
  // caller polls dprJobStatus every few seconds until status === "done".
  analyzeDprAsync: (file, kind = "tender", templateId = null) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("Could not read file"));
      reader.onload = () => {
        const dataUrl = String(reader.result || "");
        const content_b64 = dataUrl.substring(dataUrl.indexOf(",") + 1);
        const tpl = templateId ? `&template_id=${encodeURIComponent(templateId)}` : "";
        // v50b — 20 s default timeout is too short for multi-MB base64
        // uploads on slow links; the async kick only stores the payload
        // and returns, but the UPLOAD itself can take minutes.
        api.post(`/api/v1/tender-pro/dpr/analyze-async?kind=${kind}${tpl}`,
          { filename: file.name, content_b64 }, { timeout: 300000 })
          .then((r) => resolve(r.data))
          .catch(reject);
      };
      reader.readAsDataURL(file);
    }),
  dprJobStatus: (jobId) =>
    api.get(`/api/v1/tender-pro/dpr/jobs/${encodeURIComponent(jobId)}`).then((r) => r.data),
  aiFillAll: (tid, opts) =>
    api.post(`/api/v1/tender-pro/templates/${tid}/ai-fill-all`, opts || {}).then((r) => r.data),
  aiFillAllAsync: (tid, opts) =>
    api.post(`/api/v1/tender-pro/templates/${tid}/ai-fill-all-async`, opts || {}).then((r) => r.data),
  aiFillJob: (jobId) =>
    api.get(`/api/v1/tender-pro/ai-fill-jobs/${encodeURIComponent(jobId)}`).then((r) => r.data),
  nextReference: (country, industry, kind) =>
    api.post(`/api/v1/tender-pro/next-reference`, null,
             { params: { country, industry, kind } }).then((r) => r.data),
  patchSection: (tid, code, patch) =>
    api.patch(`/api/v1/tender-pro/templates/${tid}/sections/${encodeURIComponent(code)}`, patch).then((r) => r.data),
  saveAsMaster: (tid, payload) =>
    api.post(`/api/v1/tender-pro/templates/${tid}/save-as-master`, payload).then((r) => r.data),
  // EMD masters
  listEmdMasters: (country, kind, category) =>
    api.get(`/api/v1/tender-pro/emd-masters`, { params: { country, kind, category } }).then((r) => r.data),
  createEmdMaster: (p) => api.post(`/api/v1/tender-pro/emd-masters`, p).then((r) => r.data),
  updateEmdMaster: (id, p) => api.patch(`/api/v1/tender-pro/emd-masters/${id}`, p).then((r) => r.data),
  deleteEmdMaster: (id) => api.delete(`/api/v1/tender-pro/emd-masters/${id}`).then((r) => r.data),
  computeEmd: (master_id, tender_value) =>
    api.post(`/api/v1/tender-pro/emd-masters/compute`, { master_id, tender_value }).then((r) => r.data),
  // Rating criteria
  listCriteriaSets: () => api.get(`/api/v1/tender-pro/rating-criteria`).then((r) => r.data),
  createCriteriaSet: (p) => api.post(`/api/v1/tender-pro/rating-criteria`, p).then((r) => r.data),
  updateCriteriaSet: (id, p) => api.patch(`/api/v1/tender-pro/rating-criteria/${id}`, p).then((r) => r.data),
  deleteCriteriaSet: (id) => api.delete(`/api/v1/tender-pro/rating-criteria/${id}`).then((r) => r.data),
  submitMultiRating: (p) => api.post(`/api/v1/tender-pro/ratings/multi`, p).then((r) => r.data),
  ratingAggregate: (vendor_ref) =>
    api.get(`/api/v1/tender-pro/ratings/aggregate/${vendor_ref}`).then((r) => r.data),
};

// v46 — Vendor Rating & Review portal (peer + PMC + public buyer).
export const vendorRatingsApi = {
  // Public — no auth
  publicAggregate: (ref) =>
    api.get(`/api/v1/vendor-ratings/public/${encodeURIComponent(ref)}`).then((r) => r.data),
  publicRubric: () =>
    api.get(`/api/v1/vendor-ratings/public/rubric`).then((r) => r.data),
  publicTop: (limit = 12) =>
    api.get(`/api/v1/vendor-ratings/public/top`, { params: { limit } }).then((r) => r.data),
  publicSubmit: (payload) =>
    api.post(`/api/v1/vendor-ratings/public/submit`, payload).then((r) => r.data),
  // Peer vendor — authenticated vendor
  peerDirectory: (q, tender_ref) =>
    api.get(`/api/v1/vendor-ratings/directory`, { params: { ...(q ? { q } : {}), ...(tender_ref ? { tender_ref } : {}) } }).then((r) => r.data),
  peerMyTenders: () =>
    api.get(`/api/v1/vendor-ratings/my-tenders`).then((r) => r.data),
  peerSubmit: (payload) =>
    api.post(`/api/v1/vendor-ratings/peer/submit`, payload).then((r) => r.data),
  peerListMine: () =>
    api.get(`/api/v1/vendor-ratings/peer/mine`).then((r) => r.data),
  // PMC admin
  adminSubmit: (payload) =>
    api.post(`/api/v1/vendor-ratings/admin/submit`, payload).then((r) => r.data),
  adminList: (params) =>
    api.get(`/api/v1/vendor-ratings/admin/reviews`, { params }).then((r) => r.data),
  adminModerate: (id, payload) =>
    api.post(`/api/v1/vendor-ratings/admin/reviews/${id}/moderate`, payload).then((r) => r.data),
  adminDelete: (id) =>
    api.delete(`/api/v1/vendor-ratings/admin/reviews/${id}`).then((r) => r.data),
  adminPendingCount: () =>
    api.get(`/api/v1/vendor-ratings/admin/pending-count`).then((r) => r.data),
};

export const noticeQaApi = {
  listPublic: (ref) => api.get(`/api/v1/notices/${ref}/qa`).then((r) => r.data),
  ask: (ref, body) => api.post(`/api/v1/notices/${ref}/qa`, body).then((r) => r.data),
  listAdmin: (ref) => api.get(`/api/v1/notices/${ref}/qa/admin`).then((r) => r.data),
  reply: (ref, qid, answer) =>
    api.post(`/api/v1/notices/${ref}/qa/${qid}/reply`, { answer }).then((r) => r.data),
};

export const bidsAiApi = {
  compare: (payload) =>
    api.post(`/api/v1/bids/compare-ai`, payload).then((r) => r.data),
};

export const escrowApi = {
  listAccounts: (activeOnly = false) =>
    api.get("/api/v1/escrow/accounts", { params: { active_only: activeOnly } }).then((r) => r.data),
  createAccount: (p) => api.post("/api/v1/escrow/accounts", p).then((r) => r.data),
  patchAccount: (aid, p) => api.patch(`/api/v1/escrow/accounts/${aid}`, p).then((r) => r.data),
  // v53l — one-click backfill for legacy accounts: match institution to
  // master + refresh signatory emails from the pool. Returns diagnostics.
  backfillSigners: (aid) =>
    api.post(`/api/v1/escrow/accounts/${aid}/backfill-signers`).then((r) => r.data),
  // v53k — dropdown source for PMC officers + approved institutions + their signatories.
  magicIssue: (account_id, officer_email) =>
    api.post("/api/v1/escrow/magic-tokens", { account_id, officer_email }).then((r) => r.data),
  signatoryPool: () =>
    api.get("/api/v1/escrow/signatory-pool").then((r) => r.data),
  listTransactions: (params) =>
    api.get("/api/v1/escrow/transactions", { params: params || {} }).then((r) => r.data),
  initTransaction: (p) => api.post("/api/v1/escrow/transactions/init", p).then((r) => r.data),
  sign: (tid, p) => api.post(`/api/v1/escrow/transactions/${tid}/sign`, p).then((r) => r.data),
  release: (tid, p) => api.post(`/api/v1/escrow/transactions/${tid}/release`, p).then((r) => r.data),
  cancel: (tid) => api.post(`/api/v1/escrow/transactions/${tid}/cancel`).then((r) => r.data),
  duplicates: () => api.get("/api/v1/escrow/transactions/duplicates").then((r) => r.data),
  exportReleasesCsvUrl: (year) => `/api/v1/escrow/exports/releases.csv${year ? `?year=${year}` : ""}`,
  // v54a — payment entries + DocuSign envelope on a transaction
  listPaymentEntries: (tid) =>
    api.get(`/api/v1/escrow/transactions/${tid}/payment-entries`).then((r) => r.data),
  createPaymentEntry: (p) =>
    api.post("/api/v1/escrow/payment-entries", p).then((r) => r.data),
  signPaymentEntry: (peid, p) =>
    api.post(`/api/v1/escrow/payment-entries/${peid}/sign`, p).then((r) => r.data),
  voidPaymentEntry: (peid) =>
    api.post(`/api/v1/escrow/payment-entries/${peid}/void`).then((r) => r.data),
  sendTxDocuSign: (tid) =>
    api.post(`/api/v1/escrow/transactions/${tid}/docusign`).then((r) => r.data),
  refreshTxDocuSign: (tid) =>
    api.post(`/api/v1/escrow/transactions/${tid}/docusign/refresh`).then((r) => r.data),
  getTxDocuSignUrl: (tid, side = "pmc") =>
    api.get(`/api/v1/escrow/transactions/${tid}/docusign-url`, { params: { side } }).then((r) => r.data),
};

// v54a — institution-portal-scoped escrow APIs
export const escrowMeApi = {
  getTransaction: (tid) =>
    api.get(`/api/v1/escrow-accounts/me/transactions/${tid}`).then((r) => r.data),
  createPaymentEntry: (tid, p) =>
    api.post(`/api/v1/escrow-accounts/me/transactions/${tid}/payment-entries`, p).then((r) => r.data),
  signPaymentEntry: (peid, p) =>
    api.post(`/api/v1/escrow-accounts/me/payment-entries/${peid}/sign`, p).then((r) => r.data),
  getDocuSignUrl: (tid) =>
    api.get(`/api/v1/escrow-accounts/me/transactions/${tid}/docusign-url`).then((r) => r.data),
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

// v47e — vendor-facing in-app notifications
export const vendorNotifyApi = {
  list: () => api.get("/api/v1/notifications/vendor/mine").then((r) => r.data),
  markRead: (id) => api.post(`/api/v1/notifications/vendor/${id}/read`).then((r) => r.data),
  markAllRead: () => api.post("/api/v1/notifications/vendor/read-all").then((r) => r.data),
};

// ---------- Wave 39: Corrigenda ----------
export const corrigendaApi = {
  listPublic: (ref) => api.get(`/api/v1/notices/${ref}/corrigenda`).then((r) => r.data),
  listAdmin: (ref) => api.get(`/api/v1/notices/${ref}/corrigenda/admin`).then((r) => r.data),
  publish: (ref, body) => api.post(`/api/v1/notices/${ref}/corrigenda`, body).then((r) => r.data),
  withdraw: (ref, cid, reason) => api.delete(`/api/v1/notices/${ref}/corrigenda/${cid}`, { params: { reason } }).then((r) => r.data),
  // v51ad — vendor-side acknowledge flow + admin ack-list.
  outstanding: () => api.get(`/api/v1/corrigenda/outstanding`).then((r) => r.data),
  acknowledge: (cid) => api.post(`/api/v1/corrigenda/${cid}/acknowledge`).then((r) => r.data),
  listAcks: (ref, cid) => api.get(`/api/v1/notices/${ref}/corrigenda/${cid}/acknowledgements`).then((r) => r.data),
  // v52bn — attach a supporting document (revised BOQ, drawing…) to a
  // corrigendum. On live notices ALL document changes must flow through a
  // corrigendum for a clean audit trail (no direct notice-doc edits).
  attach: (ref, cid, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post(`/api/v1/notices/${ref}/corrigenda/${cid}/attachment`, fd).then((r) => r.data);
  },
};

// v51ad — Admin's personal MoneyFilterBar presets, scoped per panel.
export const filterPresetsApi = {
  list: (scope) => api.get(`/api/v1/filter-presets`, { params: scope ? { scope } : {} }).then((r) => r.data),
  save: (scope, name, criteria) => api.post(`/api/v1/filter-presets`, { scope, name, criteria }).then((r) => r.data),
  remove: (id) => api.delete(`/api/v1/filter-presets/${id}`).then((r) => r.data),
};

// ---------- Wave 39: Awards / Post-Award docs ----------
export const awardsApi = {
  list: (bid_id) => api.get(`/api/v1/awards/bid/${bid_id}`).then((r) => r.data),
  listMine: (bid_id) => api.get(`/api/v1/awards/bid/${bid_id}/mine`).then((r) => r.data),
  regenerate: (bid_id) => api.post(`/api/v1/awards/bid/${bid_id}/regenerate`).then((r) => r.data),
};

// ---------- Wave 40: Reverse-auction live room ----------
export const reverseAuctionApi = {
  create: (p) => api.post("/api/v1/reverse-auctions", p).then((r) => r.data),
  update: (aid, p) => api.patch(`/api/v1/reverse-auctions/${aid}`, p).then((r) => r.data),
  list: (params = {}) => api.get("/api/v1/reverse-auctions", { params }).then((r) => r.data),
  award: (aid) => api.post(`/api/v1/reverse-auctions/${aid}/award`).then((r) => r.data),
  // v52bx — vendor-scoped list for the vendor home KPI tile.
  mine: () => api.get("/api/v1/reverse-auctions/mine").then((r) => r.data),
  get: (aid) => api.get(`/api/v1/reverse-auctions/${aid}`).then((r) => r.data),
  start: (aid) => api.post(`/api/v1/reverse-auctions/${aid}/start`).then((r) => r.data),
  close: (aid) => api.post(`/api/v1/reverse-auctions/${aid}/close`).then((r) => r.data),
  register: (aid) => api.post(`/api/v1/reverse-auctions/${aid}/register`).then((r) => r.data),
  bid: (aid, price) => api.post(`/api/v1/reverse-auctions/${aid}/bid`, { price }).then((r) => r.data),
  autobid: (aid, body) => api.post(`/api/v1/reverse-auctions/${aid}/autobid`, body).then((r) => r.data),
  state: (aid) => api.get(`/api/v1/reverse-auctions/${aid}/state`).then((r) => r.data),
  stateMine: (aid) => api.get(`/api/v1/reverse-auctions/${aid}/state-mine`).then((r) => r.data),
  // v46b — invitations
  invite: (aid, emails, note, opts) =>
    api.post(`/api/v1/reverse-auctions/${aid}/invite`,
             { emails, note, ...(opts || {}) }).then((r) => r.data),
  listInvitations: (aid) =>
    api.get(`/api/v1/reverse-auctions/${aid}/invitations`).then((r) => r.data),
  resolveInvite: (token) =>
    api.get(`/api/v1/reverse-auctions/invite/resolve/${token}`).then((r) => r.data),
  acceptInvite: (token) =>
    api.post(`/api/v1/reverse-auctions/invite/accept/${token}`).then((r) => r.data),
  // v53j — resend / decline / awarded digest
  resendInvite: (aid, token, origin_url) =>
    api.post(`/api/v1/reverse-auctions/${aid}/invite/${token}/resend`,
             null, { params: { origin_url } }).then((r) => r.data),
  declineInvite: (token, reason) =>
    api.post(`/api/v1/reverse-auctions/invite/decline/${token}`,
             { reason }).then((r) => r.data),
  awardedList: () =>
    api.get(`/api/v1/reverse-auctions/awarded/list`).then((r) => r.data),
  // v46c — invitation templates
  listTemplates: () =>
    api.get(`/api/v1/reverse-auctions/invite/tpl`).then((r) => r.data),
  createTemplate: (p) =>
    api.post(`/api/v1/reverse-auctions/invite/tpl`, p).then((r) => r.data),
  updateTemplate: (id, p) =>
    api.patch(`/api/v1/reverse-auctions/invite/tpl/${id}`, p).then((r) => r.data),
  deleteTemplate: (id) =>
    api.delete(`/api/v1/reverse-auctions/invite/tpl/${id}`).then((r) => r.data),
  // v57e — public discovery + live transport
  publicList: (status) =>
    api.get(`/api/v1/reverse-auctions/public/list`,
            { params: status ? { status } : {} }).then((r) => r.data),
  events: (aid) =>
    api.get(`/api/v1/reverse-auctions/${aid}/events`).then((r) => r.data),
  heartbeat: (aid, viewer_id) =>
    api.post(`/api/v1/reverse-auctions/${aid}/heartbeat`, { viewer_id }).then((r) => r.data),
  streamUrl: (aid) => `${BACKEND_URL}/api/v1/reverse-auctions/${aid}/stream`,
};

// v46c — Fee master → Stripe checkout + refund + transactions
export const feeBillingApi = {
  feeCheckout: (payload) =>
    api.post(`/api/v1/billing/fee-checkout`, payload).then((r) => r.data),
  listTransactions: (limit = 50) =>
    api.get(`/api/v1/billing/transactions`, { params: { limit } }).then((r) => r.data),
  refund: (session_id, reason) =>
    api.post(`/api/v1/billing/refund/${session_id}`, { reason }).then((r) => r.data),
  webhookHealth: () =>
    api.get("/api/v1/billing/webhook-health").then((r) => r.data),
  resyncPending: (limit = 200) =>
    api.post("/api/v1/billing/resync-pending", null, { params: { limit } }).then((r) => r.data),
};

// ---------- Wave 40: UNSPSC taxonomy ----------
// v52cn — `search` now hits the full 150k UNSPSC codeset exposed by
// masters_v2 (`/api/v1/masters/unspsc/public/search`) instead of the old
// curated 87-node taxonomy. Response is normalised to the shape the picker
// expects: { items: [{ code, title, level }] }. A silent fallback to the
// legacy taxonomy keeps the picker usable even if masters is empty.
export const taxonomyApi = {
  tree: () => api.get("/api/v1/taxonomy/tree").then((r) => r.data),
  search: async (q) => {
    try {
      const r = await api.get("/api/v1/masters/unspsc/public/search", {
        params: { q, limit: 30 },
      });
      const rows = Array.isArray(r.data) ? r.data : [];
      if (rows.length) {
        return { items: rows.map((x) => ({ code: x.code, title: x.title_en, level: "commodity" })) };
      }
    } catch { /* fall through */ }
    try {
      const r = await api.get("/api/v1/taxonomy/search", { params: { q } });
      return r.data || { items: [] };
    } catch { return { items: [] }; }
  },
  lookup: (code) => api.get(`/api/v1/taxonomy/lookup/${code}`).then((r) => r.data),
};

// ---------- v52cn — Masters v2: geography + country licenses ----------
export const mastersGeoApi = {
  countries: () => api.get("/api/v1/masters/countries").then((r) => r.data),
  states: (cc) =>
    api.get("/api/v1/masters/states", { params: { country_code: cc } }).then((r) => r.data),
  cities: (cc, state_code, q, limit = 100) =>
    api.get("/api/v1/masters/cities", {
      params: { country_code: cc, state_code: state_code || undefined,
                q: q || undefined, limit },
    }).then((r) => r.data),
  getCountryLicenses: (cc) =>
    api.get(`/api/v1/masters/country-licenses/${cc}`).then((r) => r.data),
  listCountryLicenses: () =>
    api.get("/api/v1/masters/country-licenses").then((r) => r.data),
  putCountryLicenses: (cc, licenses) =>
    api.put(`/api/v1/masters/country-licenses/${cc}`, { licenses }).then((r) => r.data),
};

// ---------- G4 Rebuild: Stakeholder Reports (v50m — bug #45) ----------
export const stakeholderReportsApi = {
  tenders: () => api.get("/api/v1/stakeholder-reports/tenders").then((r) => r.data),
  awards:  () => api.get("/api/v1/stakeholder-reports/awards").then((r) => r.data),
  escrow:  () => api.get("/api/v1/stakeholder-reports/escrow").then((r) => r.data),
  sla:     () => api.get("/api/v1/stakeholder-reports/sla").then((r) => r.data),
  // v52bs — PATH ONLY (axios instance already carries baseURL). Returning
  // a full URL made production calls go cross-origin from pmcmanagers.com
  // and the Download CSV button failed with "Network Error".
  csvUrl:  (kind) => `/api/v1/stakeholder-reports/${kind}?format=csv`,
};

// ---------- Wave 41: Meetings + Jitsi ----------
export const meetingsApi = {
  create: (p) => api.post("/api/v1/meetings", p).then((r) => r.data),
  list: (params = {}) => api.get("/api/v1/meetings", { params }).then((r) => r.data),
  get: (mid) => api.get(`/api/v1/meetings/${mid}`).then((r) => r.data),
  addInvitees: (mid, list) => api.post(`/api/v1/meetings/${mid}/invitees`, list).then((r) => r.data),
  uploadMinutes: (mid, minutes) => api.post(`/api/v1/meetings/${mid}/minutes`, { minutes }).then((r) => r.data),
  cancel: (mid) => api.delete(`/api/v1/meetings/${mid}`).then((r) => r.data),
};

// ---------- Wave 41: L1 Auto-Comparison ----------
export const comparisonApi = {
  runL1: (notice_ref) => api.post(`/api/v1/comparison/l1/${notice_ref}`).then((r) => r.data),
  latestL1: (notice_ref) => api.get(`/api/v1/comparison/l1/${notice_ref}/latest`).then((r) => r.data),
  awardL1: (notice_ref, body) => api.post(`/api/v1/comparison/l1/${notice_ref}/award`, body).then((r) => r.data),
};

// ---------- Wave 43: DocuSign eSignature ----------
export const docusignApi = {
  resendEnvelope: (envelopeId) =>
    api.post(`/api/v1/docusign/envelopes/${envelopeId}/resend`).then((r) => r.data),
  status: () => api.get("/api/v1/docusign/status").then((r) => r.data),
  consentUrl: () => api.get("/api/v1/docusign/consent-url").then((r) => r.data),
  signAward: (bidId, kind, payload) =>
    api.post(`/api/v1/docusign/awards/${bidId}/${kind}/envelope`, payload).then((r) => r.data),
  signBidAck: (bidId, payload) =>
    api.post(`/api/v1/docusign/bids/${bidId}/ack/envelope`, payload).then((r) => r.data),
  envelope: (eid) => api.get(`/api/v1/docusign/envelopes/${eid}`).then((r) => r.data),
  listEnvelopes: (params = {}) =>
    api.get("/api/v1/docusign/envelopes", { params: { limit: 100, ...params } }).then((r) => r.data),
  // Vendor-facing (Wave 44)
  refresh: (envelopeId) => api.post(`/api/v1/docusign/envelopes/${envelopeId}/refresh`).then((r) => r.data),
  listMine: () => api.get("/api/v1/docusign/mine").then((r) => r.data),
  // v49n — re-mint a recipient-view URL for an envelope the vendor needs to sign
  resumeSign: (envelopeId) =>
    api.post(`/api/v1/docusign/mine/${envelopeId}/sign`).then((r) => r.data),
  vendorSignAward: (bidId, kind, payload) =>
    api.post(`/api/v1/docusign/mine/awards/${bidId}/${kind}/envelope`, payload).then((r) => r.data),
  // Wave 44 — signed PDF download
  downloadPdf: (envelopeId) =>
    api.get(`/api/v1/docusign/envelopes/${envelopeId}/combined-pdf`, { responseType: "blob" })
      .then((r) => r.data),
  vendorDownloadPdf: (envelopeId) =>
    api.get(`/api/v1/docusign/mine/envelopes/${envelopeId}/combined-pdf`, { responseType: "blob" })
      .then((r) => r.data),
  // v50q — admin: re-archive a completed envelope's signed PDF into our storage
  archivePdf: (envelopeId) =>
    api.post(`/api/v1/docusign/envelopes/${envelopeId}/archive-pdf`).then((r) => r.data),
  // v51b — admin: reassign an envelope to a new signer / hide it from vendors
  reassignEnvelope: (envelopeId, payload) =>
    api.post(`/api/v1/docusign/envelopes/${envelopeId}/reassign`, payload).then((r) => r.data),
  archiveEnvelope: (envelopeId, reason = "") =>
    api.post(`/api/v1/docusign/envelopes/${envelopeId}/archive`, { reason }).then((r) => r.data),
  unarchiveEnvelope: (envelopeId) =>
    api.post(`/api/v1/docusign/envelopes/${envelopeId}/unarchive`).then((r) => r.data),
  // v49p — envelope's current document as PDF in ANY status (unsigned while
  // pending, signed once completed). disposition=inline → open in tab,
  // attachment → browser download.
  downloadDocPdf: (envelopeId, disposition = "inline") =>
    api.get(`/api/v1/docusign/mine/envelopes/${envelopeId}/document.pdf?disposition=${disposition}`, { responseType: "blob" })
      .then((r) => r.data),
};

// ---------- Dashboard Drill-through (Wave E-2) ----------
export const dashboardDrillApi = {
  anomalies: () => api.get("/api/v1/dashboard-drill/anomalies").then((r) => r.data),
  pipeline: (status) => api.get("/api/v1/dashboard-drill/pipeline", { params: status ? { status } : {} }).then((r) => r.data),
  topPriced: (limit = 10) => api.get("/api/v1/dashboard-drill/top-priced", { params: { limit } }).then((r) => r.data),
};

// ---------- Product Catalog (Wave 38) ----------
export const productCatalogApi = {
  publicList: (side) => api.get("/api/v1/products/public", { params: side ? { side } : {} }).then((r) => r.data),
  adminList: (active_only = false) => api.get("/api/v1/products", { params: { active_only, _: Date.now() } }).then((r) => r.data),
  create: (p) => api.post("/api/v1/products", p).then((r) => r.data),
  update: (id, p) => api.patch(`/api/v1/products/${id}`, p).then((r) => r.data),
  setActive: (id, is_active) => api.patch(`/api/v1/products/${id}/active`, null, { params: { is_active } }).then((r) => r.data),
  delete: (id) => api.delete(`/api/v1/products/${id}`).then((r) => r.data),
  reseed: () => api.post("/api/v1/products/reseed").then((r) => r.data),
};

// ---------- Engagements & Quotes (Wave 38) ----------
export const engagementsApi = {
  quoteRequest: (payload) => api.post("/api/v1/engagements/quote-request", payload).then((r) => r.data),
  // v52bv — vendor-scoped list of own engagements (quote requests).
  mine: () => api.get("/api/v1/engagements/mine").then((r) => r.data),
  checkout: (id, origin_url) => api.post(`/api/v1/engagements/${id}/checkout`, { origin_url }).then((r) => r.data),
  // v52bl — cancel now requires a non-empty reason (backend enforces min_length 5).
  cancel: (id, reason) => api.post(`/api/v1/engagements/${id}/cancel`, { reason }).then((r) => r.data),
  saveQuote: (id, payload) => api.patch(`/api/v1/engagements/${id}/quote`, payload).then((r) => r.data),
  listAdmin: () => api.get("/api/v1/engagements").then((r) => r.data),
  // v52bl — lightweight PMC-internal meetings (buyer/supplier).
  scheduleMeeting: (id, payload) =>
    api.post(`/api/v1/engagements/${id}/meetings`, payload).then((r) => r.data),
  listMeetings: (id) =>
    api.get(`/api/v1/engagements/${id}/meetings`).then((r) => r.data),
};

// ---------- Escrow Magic-Sign ----------
export const escrowMagicApi = {
  get: (token) => api.get(`/api/v1/escrow/magic/${token}`).then((r) => r.data),
  sign: (token, payload) => api.post(`/api/v1/escrow/magic/${token}/sign`, payload).then((r) => r.data),
  splits: (token) => api.get(`/api/v1/escrow/magic/${token}/consortium-splits`).then((r) => r.data),
  signSplit: (token, tid, idx, comment) => api.post(`/api/v1/escrow/magic/${token}/consortium-split/${tid}/${idx}/sign`, { comment }).then((r) => r.data),
};

// ---------- Public Roadmap ----------
export const publicRoadmapApi = {
  get: () => api.get("/api/v1/reports/public/roadmap").then((r) => r.data),
};

// ---------- Billing Checkout & Status ----------
export const billingCheckoutApi = {
  checkout: (payload) => api.post("/api/v1/billing/checkout", payload).then((r) => r.data),
  status: (sid) => api.get(`/api/v1/billing/status/${sid}`).then((r) => r.data),
};

export default api;
