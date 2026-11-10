import { api } from "@/lib/api";

const g = (u, p) => api.get(u, { params: p }).then((r) => r.data);
const p = (u, b) => api.post(u, b || {}).then((r) => r.data);

export const buyerApi = {
  register: (b) => p("/api/v1/buyer/register", b),
  verifyEmail: (token) => p("/api/v1/buyer/verify-email", { token }),
  me: () => api.get("/api/v1/buyer/me", { _skipAuthRedirect: true }).then((r) => r.data),
  updateMe: (b) => api.put("/api/v1/buyer/me", b).then((r) => r.data),
  avatar: (data_url) => p("/api/v1/buyer/me/avatar", { data_url }),
  password: (b) => p("/api/v1/buyer/me/password", b),
  dashboard: () => g("/api/v1/buyer/dashboard"),
  received: (oid) => p(`/api/v1/buyer/orders/${oid}/received`),
  notifications: () => g("/api/v1/buyer/notifications"),
  readOne: (id) => p(`/api/v1/buyer/notifications/${id}/read`),
  readAll: () => p("/api/v1/buyer/notifications/read-all"),
  team: () => g("/api/v1/buyer/team"),
  invite: (b) => p("/api/v1/buyer/team/invite", b),
  remove: (id) => p(`/api/v1/buyer/team/${id}/remove`),
  adminTeamRequests: () => g("/api/v1/buyer/admin/team-requests"),
  adminTeamDecide: (id, action) => p(`/api/v1/buyer/admin/team-requests/${id}/decision`, { action }),
  adminAddBuyer: (b) => p("/api/v1/buyer/admin/buyers", b),
  logout: () => p("/api/v1/staff/auth/logout"),
};

export const money = (c, v) => (v == null ? "—" : `${c || ""} ${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`.trim());
export const day = (s) => (s ? String(s).slice(0, 10) : "—");
