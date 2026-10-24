import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/**
 * PortalAvatarMenu — light-theme avatar + dropdown for the staff/escrow top
 * bars. Visually matches the admin avatar (.pmc-avatar) and anchors its menu
 * through a portal to <body> so no ancestor overflow can clip it. `items` is
 * a list of {label,onClick,danger,testid}; a divider is drawn before the
 * last item when it is marked danger (the Sign out convention).
 */
export default function PortalAvatarMenu({ initial, title, sub, items = [], testId }) {
  const [open, setOpen] = useState(false);
  const [anchor, setAnchor] = useState(null);
  const btnRef = useRef(null);
  const menuRef = useRef(null);

  const place = () => {
    const b = btnRef.current;
    if (!b) return;
    const r = b.getBoundingClientRect();
    const narrow = window.innerWidth <= 767;
    const width = narrow ? Math.min(280, window.innerWidth - 16) : 240;
    const top = r.bottom + 8;
    const right = narrow ? 8 : Math.max(8, window.innerWidth - r.right);
    setAnchor({ top, right, width });
  };

  useEffect(() => {
    if (!open) return;
    place();
    const onDoc = (e) => {
      if (menuRef.current && menuRef.current.contains(e.target)) return;
      if (btnRef.current && btnRef.current.contains(e.target)) return;
      setOpen(false);
    };
    const onEsc = (e) => { if (e.key === "Escape") setOpen(false); };
    const onMove = () => place();
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    window.addEventListener("resize", onMove);
    window.addEventListener("scroll", onMove, true);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
      window.removeEventListener("resize", onMove);
      window.removeEventListener("scroll", onMove, true);
    };
  }, [open]);

  return (
    <div style={{ position: "relative" }}>
      <button ref={btnRef} type="button" className="pmc-avatar" title={title}
              aria-haspopup="menu" aria-expanded={open} data-testid={testId}
              onClick={() => setOpen((o) => !o)}
              style={{ cursor: "pointer", border: "none", padding: 0 }}>
        {initial}
      </button>
      {open && anchor && createPortal(
        <div ref={menuRef} role="menu" data-testid={`${testId}-menu`} style={{
          position: "fixed", top: anchor.top, right: anchor.right, width: anchor.width,
          maxHeight: `calc(100vh - ${anchor.top + 16}px)`, overflowY: "auto", zIndex: 2000,
          background: "var(--surface, #fff)", border: "1px solid var(--line, #0001)",
          borderRadius: "var(--radius-md, 6px)", boxShadow: "0 20px 50px rgba(0,0,0,.25)",
          padding: 8, display: "grid", gap: 2,
        }}>
          <div style={{ padding: "8px 10px 10px", borderBottom: "1px solid var(--line)", marginBottom: 4, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title}</div>
            {sub ? <div className="pmc-muted" style={{ fontSize: 12 }}>{sub}</div> : null}
          </div>
          {items.map((it, i) => (
            <button key={i} type="button"
                    className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                    data-testid={it.testid}
                    onClick={() => { setOpen(false); it.onClick?.(); }}
                    style={{ justifyContent: "flex-start", color: it.danger ? "var(--danger)" : undefined,
                             borderTop: it.danger ? "1px solid var(--line)" : undefined,
                             marginTop: it.danger ? 4 : undefined, paddingTop: it.danger ? 8 : undefined }}>
              {it.label}
            </button>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
}
