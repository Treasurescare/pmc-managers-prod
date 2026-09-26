# v47e — In-app notifications for vendors + sign-in alerts in the bell

## Answers to your questions
- **In-app notifications existed only for staff** (admin console bell polls every 20s). Vendors got emails only — no bell, no records. v47e closes that.
- **The bell top-right on the homepage** is the **Web Push subscribe toggle** (`EnablePushButton`). "Off" meant the browser wasn't subscribed to push. It was effectively dead until the VAPID keys went live on EB — now it works: click it → browser asks permission → award/corrigenda/deadline pushes arrive even with the tab closed.

## What's new

### 1 · Vendor in-app notification bell
- New endpoints: `GET /api/v1/notifications/vendor/mine`, `POST …/vendor/{id}/read`, `POST …/vendor/read-all` — scoped to the signed-in vendor (`user_ref`/`user_email`), so vendors can only ever see their own records.
- New `VendorNotificationBell` component mounted in the Vendor Portal header (next to the profile avatar). Polls every 20s, unread count badge, per-item + mark-all read.
- Records are inserted for: bid stage transitions (approved / cleared / on-hold / awarded / rejected), and sign-in alerts.

### 2 · Sign-in alerts now also appear in-app
- `login_alert()` gained `user_id` (staff) / `user_ref` (vendor) addressing — every login alert email also drops an in-app record, so the bell shows the sign-in history the moment you open it.
- Staff records are addressed by `user_id` (visible to that staff member only); vendor records by `user_ref`+`user_email`.

### 3 · Staff bell unchanged
Admin/staff console bell keeps working exactly as before — verified 5 records load including the new sign-in entries.

## Verified on preview
- Vendor login → `GET /notifications/vendor/mine` → "New sign-in to your account (Vendor Portal)" record ✅
- `POST /notifications/vendor/read-all` → 200 ✅
- Staff `GET /notifications` → 5 records incl. new sign-in alert ✅
- Frontend prod build clean, zero preview-URL references ✅

## Deploy
- `pmc-backend-v47e.zip` → EB (carries v47d + v47c + v47b + v47a + v46z + v46y)
- `pmc-frontend-v47e-prod-build.zip` → S3 sync + CloudFront invalidate (usual commands)

## Note on push vs bell
The two channels now complement each other:
- **Bell (in-app)** — full history while signed in.
- **Push (bell toggle)** — reaches the vendor when the tab is closed (award, deadline, corrigenda).
- **Email** — permanent record with CTA links.
