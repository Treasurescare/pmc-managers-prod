import { useEffect, useState } from "react";
import Cropper from "react-easy-crop";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const CARD_W = 1200;
export const CARD_H = 900;

async function cropToFile(src, area, name) {
  const img = await new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = bad; i.src = src; });
  const c = document.createElement("canvas");
  c.width = CARD_W; c.height = CARD_H;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, CARD_W, CARD_H);
  ctx.drawImage(img, area.x, area.y, area.width, area.height, 0, 0, CARD_W, CARD_H);
  const blob = await new Promise((ok) => c.toBlob(ok, "image/jpeg", 0.9));
  return new File([blob], name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
}

// Lets the supplier frame each photo to the marketplace card size (4:3, 1200x900) before upload.
export function PhotoCropDialog({ file, onDone, onSkip, onCancel }) {
  const [src, setSrc] = useState(null);
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [area, setArea] = useState(null);
  useEffect(() => {
    if (!file) { setSrc(null); return undefined; }
    const u = URL.createObjectURL(file);
    setSrc(u); setZoom(1); setCrop({ x: 0, y: 0 });
    return () => URL.revokeObjectURL(u);
  }, [file]);
  return (
    <Dialog open={!!file} onOpenChange={(o) => { if (!o) onCancel(); }}>
      <DialogContent className="max-w-2xl" data-testid="mkt-crop-dialog">
        <DialogHeader><DialogTitle>Frame your photo</DialogTitle></DialogHeader>
        <p className="text-xs opacity-75">Marketplace photos are shown at 4:3 (1200 × 900). Drag to position, zoom to fit.</p>
        <div className="relative w-full h-80 bg-black/80 rounded">
          {src && <Cropper image={src} crop={crop} zoom={zoom} aspect={CARD_W / CARD_H} objectFit="cover" onCropChange={setCrop} onZoomChange={setZoom} onCropComplete={(_, px) => setArea(px)} />}
        </div>
        <input type="range" min={1} max={4} step={0.05} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} aria-label="Zoom" data-testid="mkt-crop-zoom" />
        <div className="flex gap-2 justify-end flex-wrap">
          <button type="button" className="pmc-btn pmc-btn--secondary" onClick={onCancel} data-testid="mkt-crop-cancel">Don't upload</button>
          <button type="button" className="pmc-btn pmc-btn--secondary" onClick={onSkip} data-testid="mkt-crop-auto">Fit automatically</button>
          <button type="button" className="pmc-btn pmc-btn--primary" disabled={!area} onClick={async () => onDone(await cropToFile(src, area, file.name))} data-testid="mkt-crop-use">Use this photo</button>
        </div>
      </DialogContent>
    </Dialog>);
}
