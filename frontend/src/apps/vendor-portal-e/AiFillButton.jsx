import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";
import { marketApi } from "@/lib/marketApi";
import { payNeeded } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";

// Reads one spec sheet / brochure page / product photo with AI and fills the listing form.
export function AiFillButton({ onFill }) {
  const ref = useRef();
  const [job, setJob] = useState(null);
  useEffect(() => {
    if (!job?.id) return undefined;
    const t = setInterval(() => {
      marketApi.getImport(job.id).then((d) => {
        if (d.status === "reading") return;
        setJob(null);
        if (d.status === "failed") { toast.error(d.error); return; }
        const p = (d.products || [])[0];
        if (!p) { toast.error("AI could not find a product in this file — please fill the form by hand"); return; }
        onFill(p, d.catalogue_doc);
        toast.success((d.products.length > 1 ? `AI found ${d.products.length} products; the first one was filled in. Use "Import from a catalogue with AI" to list them all. ` : "Filled in by AI. ") + "Check and edit everything before saving.");
      }).catch(() => {});
    }, 4000);
    return () => clearInterval(t);
  }, [job, onFill]);
  const start = async (file) => {
    if (!file) return;
    setJob({ name: file.name });
    try { setJob({ ...(await marketApi.startImport(file)), name: file.name }); } catch (e) {
      setJob(null);
      const pay = payNeeded(e);
      if (pay?.checkout_url) toast(pay.message, { action: { label: "Pay", onClick: () => { window.location.href = pay.checkout_url; } } });
      else showApiError(e);
    }
  };
  return (
    <div className="md:col-span-2 pmc-panel p-3 flex flex-wrap items-center gap-3" data-testid="mkt-ai-fill">
      <Sparkles size={16} />
      <span className="text-sm flex-1 min-w-[200px]">Have a spec sheet, brochure page or product photo? Let AI read it and fill in the title, description, category and photo for you.</span>
      <button type="button" className="pmc-btn pmc-btn--primary pmc-btn--sm" disabled={!!job} onClick={() => ref.current?.click()} data-testid="mkt-ai-fill-btn">
        {job ? `AI is reading ${job.name}…` : "Fill with AI from a file"}</button>
      <input ref={ref} type="file" hidden accept="application/pdf,image/jpeg,image/png" onChange={(e) => { start(e.target.files[0]); e.target.value = ""; }} data-testid="mkt-ai-fill-input" />
    </div>);
}
