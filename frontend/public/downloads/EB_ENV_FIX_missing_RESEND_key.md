# EB env-vars fix — sender is still emergentmails.com in production

## What your EB screenshot revealed

Production is missing `RESEND_API_KEY`. The code in `emails.py` uses this logic:

```python
if config.RESEND_API_KEY:        # → sends via Resend from mail.pmcmanagers.com  ✅
    ...
elif config.EMAIL_KEY:            # → sends via legacy relay from emergentmails.com  ❌
    ...
```

Your EB has `EMERGENT_EMAIL_KEY` set but not `RESEND_API_KEY` → every email (including the vendor activation I just fired for `watorim801@pumpoly.com`) went out via the **legacy relay from `emergentmails.com`**, not from `admin@mail.pmcmanagers.com`.

## Fix — add these on EB (Configuration → Software → Environment properties → Edit)

Add **4 new rows** (and optionally delete one):

| Action | Name | Value |
|---|---|---|
| **Add** | `RESEND_API_KEY` | `re_3FzTQ6J2_P2doLUVcihNbMN7DewoSt2nh` |
| **Add** | `EMAIL_FROM_ADDRESS` | `admin@mail.pmcmanagers.com` |
| **Add** | `VAPID_PUBLIC_KEY` | `BFaNQAW9cYuOvkmEZSH_w6gXTkmdSQaLx3w5mvgAAwo1DL_eaUiG1tr2dbh7hELvUWAVaeMLJ9zPbfyj_CBFlHs` |
| **Add** | `VAPID_PRIVATE_KEY` | `-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgN9gczGouPMzzi1SW\nCq7JdoLraE3VbtFRipJ8OBrXieWhRANCAARWjUAFvXGLjr5JhGUh/8OoF05JnUkG\ni8d8OZr4AAMKNQy/3mlIhtba9nW4e4RC71FgFWnjCyfcz238o/wgRZR7\n-----END PRIVATE KEY-----\n` |
| **Add** | `VAPID_CLAIM_EMAIL` | `mailto:adminsupport@pmcmanagers.com` |
| **Delete** *(optional cleanup)* | `EMERGENT_EMAIL_KEY` | — |

For `VAPID_PRIVATE_KEY`: paste as a single line, exactly as shown, including the literal `\n` characters (backslash-n, not actual newlines). The code translates them back into real newlines on load (`push.py` line 36).

`EMERGENT_EMAIL_KEY` deletion is optional — the code prefers Resend when both are set. But removing it is cleaner and eliminates any chance of a future fallback back to the old sender.

Click **Apply**. EB restarts (~2 min).

---

## Verify after restart

```
# 1. Push config now shows a key
curl https://www.pmcmanagers.com/api/v1/push/config
# → {"public_key":"BFaNQAW9...","enabled":true}
```

Then trigger a real vendor activation from the Admin UI (or ping me and I'll do it via API again) — the welcome mail should now arrive from **admin@mail.pmcmanagers.com** with your DKIM ✅ next to it in the recipient's mail client "view details".

---

## Also worth cleaning up while you're in Env Properties
- `ADMIN_PASSWORD=Admin@12345` is in plain text. Once you have a working admin session, rotate it to something 16+ chars and update this env-var so the seed matches on the next cold-start.
- `EMAIL_REPLY_TO` is optional but recommended — set it to a monitored inbox like `admin@mail.pmcmanagers.com` so vendors replying to activation mails reach you.
