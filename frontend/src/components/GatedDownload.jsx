import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { vendorApi, adminApi } from "@/lib/api";

/**
 * GatedDownload — v50k.
 *
 * Public Notice Board attachments and primary documents can no longer be
 * downloaded anonymously. This component checks for a vendor or admin
 * session (vendor cookie or admin bearer token in localStorage) and
 * either renders a normal download link OR a "Sign in to download" CTA.
 *
 * The check is best-effort client-side; the server also enforces 401 on
 * every /api/v1/uploads/files/* request, so a bypass of the UI gate
 * still fails at the backend.
 */
export default function GatedDownload({ href, fileName, sizeKb, testid, compact }) {
  const [checking, setChecking] = useState(true);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        // Try vendor cookie first (most tender bidders are vendors).
        try {
          const v = await vendorApi.me();
          if (v && alive) { setAuthed(true); return; }
        } catch (_) {}
        // Fall back to admin bearer token in localStorage.
        if (localStorage.getItem("admin_token")) {
          try {
            const a = await adminApi.me();
            if (a && alive) { setAuthed(true); return; }
          } catch (_) {}
        }
      } finally { if (alive) setChecking(false); }
    })();
    return () => { alive = false; };
  }, []);

  const handleClick = async (e) => {
    if (authed) return; // let the link work normally
    e.preventDefault();
    toast.error("Sign in required", {
      description: "Only verified suppliers can download tender documents. Click the Sign in button on the top bar.",
    });
  };

  if (checking) {
    return (
      <span className={compact
        ? "inline-flex items-center gap-2 text-sm text-brand-navy/40"
        : "mt-2 inline-flex items-center gap-2 px-4 py-3 border border-brand-navy/10 text-brand-navy/40 text-sm"}
        data-testid={`${testid}-loading`}>
        ⌛ Checking access…
      </span>
    );
  }

  if (!authed) {
    return (
      <div className={compact
        ? "inline-flex items-center gap-2 text-sm w-full justify-between"
        : "mt-2 inline-flex items-center gap-2 px-4 py-3 border border-amber-500 bg-amber-50 text-amber-900 text-sm w-full justify-between flex-wrap"}
        data-testid={`${testid}-locked`}>
        <span className="truncate flex-1 min-w-0">
          🔒 <span className="font-medium">{fileName}</span>
          {sizeKb != null && <span className="text-xs text-amber-900/60 ml-1">({sizeKb} KB)</span>}
        </span>
        <Link to="/login"
          data-testid={`${testid}-signin`}
          className="shrink-0 text-[11px] uppercase tracking-widest px-3 py-1.5 bg-amber-900 text-white hover:bg-amber-800">
          Sign in to download
        </Link>
      </div>
    );
  }

  return (
    <a href={href} target="_blank" rel="noreferrer"
       onClick={handleClick}
       data-testid={testid}
       className={compact
         ? "hover:underline text-brand-navy-soft text-sm"
         : "mt-2 inline-flex items-center gap-2 px-4 py-3 border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white transition-colors text-sm"}>
      📄 <span>{fileName}</span>
      {sizeKb != null && <span className="text-xs text-brand-navy/50">({sizeKb} KB)</span>}
    </a>
  );
}
