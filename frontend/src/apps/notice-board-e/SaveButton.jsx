import { useEffect, useState } from "react";
import { toast } from "sonner";
import { buyerApi } from "@/lib/buyerApi";
import { marketApi } from "@/lib/marketApi";
import { showApiError } from "@/lib/api";

let _ids = null;
const loadIds = () => {
  if (!_ids) {
    _ids = marketApi.whoami().then((me) => (me?.kind === "buyer" ? buyerApi.watchlist().then((r) => new Set(r.ids)) : null)).catch(() => null);
  }
  return _ids;
};

// Heart toggle shown only to signed-in buyers; saved products get a reminder an hour before an auction closes.
export function SaveButton({ id, compact = false }) {
  const [set, setSet] = useState(null);
  const [on, setOn] = useState(false);
  useEffect(() => {
    let live = true;
    loadIds().then((s) => { if (live && s) { setSet(s); setOn(s.has(id)); } });
    return () => { live = false; };
  }, [id]);
  if (!set) return null;
  const toggle = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      if (on) { await buyerApi.unwatch(id); set.delete(id); setOn(false); toast.success("Removed from your watchlist"); }
      else { await buyerApi.watch(id); set.add(id); setOn(true); toast.success("Saved — we'll remind you an hour before the auction closes"); }
    } catch (err) { showApiError(err); }
  };
  return (
    <button type="button" onClick={toggle} aria-pressed={on} title={on ? "Saved to watchlist" : "Save to watchlist"}
      className={compact ? "absolute top-2 right-2 rounded-full bg-white/90 text-black px-2 py-1 text-xs shadow" : "pmc-btn pmc-btn--secondary pmc-btn--sm"}
      data-testid={`market-save-${id}`}>
      {on ? "\u2665 Saved" : "\u2661 Save"}
    </button>);
}
