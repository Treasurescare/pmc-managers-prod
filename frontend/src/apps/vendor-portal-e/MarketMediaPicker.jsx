import { useRef, useState } from "react";
import { FileText, ImagePlus, Paperclip, X } from "lucide-react";
import { marketApi, mediaUrl } from "@/lib/marketApi";
import { showApiError } from "@/lib/api";
import { PhotoCropDialog } from "./PhotoCropDialog";

function useUpload(kind, onDone) {
  const [busy, setBusy] = useState(false);
  const run = async (files) => {
    setBusy(true);
    try { for (const f of files) onDone(await marketApi.uploadMedia(f, kind)); } catch (e) { showApiError(e); }
    setBusy(false);
  };
  return [busy, run];
}

export function PhotoStrip({ photos, onChange, testid = "mkt-photos" }) {
  const ref = useRef();
  const [queue, setQueue] = useState([]);
  const [busy, upload] = useUpload("photo", (m) => onChange((p) => [...p, m.id].slice(0, 12)));
  const next = (f) => { setQueue((q) => q.slice(1)); upload([f]); };
  return (
    <div className="flex flex-wrap gap-2 items-center" data-testid={testid}>
      {photos.map((id) => (
        <div key={id} className="relative">
          <img src={mediaUrl(id)} alt="" className="w-24 h-[72px] object-cover rounded border border-white/20" />
          <button type="button" className="absolute -top-2 -right-2 bg-black/80 text-white rounded-full p-0.5" onClick={() => onChange((p) => p.filter((x) => x !== id))} aria-label="Remove photo" data-testid={`${testid}-remove-${id}`}><X size={14} /></button>
        </div>))}
      {photos.length < 12 && <button type="button" className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => ref.current?.click()} disabled={busy} data-testid={`${testid}-add`}>
        <ImagePlus size={14} className="inline mr-1" />{busy ? "Uploading…" : "Upload photos"}</button>}
      <input ref={ref} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={(e) => { setQueue([...e.target.files].slice(0, 12 - photos.length)); e.target.value = ""; }} data-testid={`${testid}-input`} />
      <PhotoCropDialog file={queue[0]} onDone={next} onSkip={() => next(queue[0])} />
    </div>);
}

export function DocList({ docs, onChange, testid = "mkt-docs" }) {
  const ref = useRef();
  const [busy, upload] = useUpload("document", (m) => onChange((d) => [...d, { id: m.id, name: m.name }].slice(0, 6)));
  return (
    <div className="space-y-1" data-testid={testid}>
      {docs.map((d) => (
        <div key={d.id} className="flex items-center gap-2 text-sm">
          <FileText size={14} /><a href={mediaUrl(d.id)} target="_blank" rel="noreferrer" className="underline truncate">{d.name}</a>
          <button type="button" onClick={() => onChange((x) => x.filter((y) => y.id !== d.id))} aria-label="Remove document" data-testid={`${testid}-remove-${d.id}`}><X size={14} /></button>
        </div>))}
      {docs.length < 6 && <button type="button" className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => ref.current?.click()} disabled={busy} data-testid={`${testid}-add`}>
        <Paperclip size={14} className="inline mr-1" />{busy ? "Uploading…" : "Attach spec sheet (PDF)"}</button>}
      <input ref={ref} type="file" accept="application/pdf" multiple hidden onChange={(e) => { upload([...e.target.files]); e.target.value = ""; }} data-testid={`${testid}-input`} />
    </div>);
}
