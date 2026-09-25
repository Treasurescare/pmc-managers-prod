/**
 * Web Push helper — subscribes the browser to the platform's VAPID feed and
 * exposes a hook so any component can render an "Enable notifications"
 * affordance. Works on Chrome/Edge/Samsung (Android desktop + mobile) and on
 * iOS 16.4+ **installed** PWAs (Safari refuses in-tab).
 */
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const b64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

async function _publicKey() {
  const { data } = await api.get("/api/v1/push/config");
  if (!data?.enabled || !data?.public_key) throw new Error("Push not configured on server");
  return data.public_key;
}

export function pushSupported() {
  return typeof window !== "undefined"
    && "serviceWorker" in navigator
    && "PushManager" in window
    && "Notification" in window;
}

export function isStandalonePwa() {
  return window.matchMedia?.("(display-mode: standalone)").matches
      || window.navigator.standalone === true;
}

export function useWebPush({ role = "vendor", userRef = null } = {}) {
  const [state, setState] = useState({
    supported: pushSupported(),
    permission: pushSupported() ? Notification.permission : "unsupported",
    subscribed: false,
    working: false,
    error: null,
  });

  const refresh = useCallback(async () => {
    if (!pushSupported()) return;
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      setState((s) => ({ ...s, subscribed: !!sub, permission: Notification.permission }));
    } catch (e) {
      setState((s) => ({ ...s, error: e.message }));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const enable = useCallback(async () => {
    if (!pushSupported()) return;
    setState((s) => ({ ...s, working: true, error: null }));
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") throw new Error(`Permission ${perm}`);
      const reg = await navigator.serviceWorker.ready;
      const key = await _publicKey();
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(key),
      });
      await api.post("/api/v1/push/subscribe", {
        endpoint: sub.endpoint,
        keys: {
          p256dh: btoa(String.fromCharCode(...new Uint8Array(sub.getKey("p256dh"))))
                    .replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_"),
          auth: btoa(String.fromCharCode(...new Uint8Array(sub.getKey("auth"))))
                    .replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_"),
        },
        user_agent: navigator.userAgent,
        role, user_ref: userRef,
      });
      setState({ supported: true, permission: "granted", subscribed: true, working: false, error: null });
    } catch (e) {
      setState((s) => ({ ...s, working: false, error: e.message }));
    }
  }, [role, userRef]);

  const disable = useCallback(async () => {
    if (!pushSupported()) return;
    setState((s) => ({ ...s, working: true, error: null }));
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await api.post("/api/v1/push/unsubscribe", { endpoint: sub.endpoint });
        await sub.unsubscribe();
      }
      setState({ supported: true, permission: Notification.permission, subscribed: false, working: false, error: null });
    } catch (e) {
      setState((s) => ({ ...s, working: false, error: e.message }));
    }
  }, []);

  return { ...state, enable, disable, refresh };
}
