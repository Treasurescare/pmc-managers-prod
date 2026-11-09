import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

export default function NoticeShareBar({ noticeRef, title }) {
  const shareUrl = `${API}/api/v1/share/notice/${encodeURIComponent(noticeRef)}`;
  const imgUrl = `${shareUrl}.png`;
  const text = encodeURIComponent(`New tender on PMC Managers: ${title || noticeRef} ${shareUrl}`);
  const nativeShare = async () => {
    const data = { title: title || noticeRef, text: `New tender on PMC Managers: ${title || noticeRef}`, url: shareUrl };
    try {
      if (window.Capacitor?.isNativePlatform?.()) { const { Share } = await import("@capacitor/share"); return await Share.share(data); }
      if (navigator.share) return await navigator.share(data);
    } catch { return undefined; }
    return copy();
  };
  const copy = () => { navigator.clipboard?.writeText(shareUrl).then(() => toast.success("Share link copied")).catch(() => {}); };
  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "12px" }} data-testid="notice-share-bar">
      <button type="button" className="pmc-btn pmc-btn--onchrome pmc-btn--sm" onClick={nativeShare} data-testid="share-native">Share</button>
      <a className="pmc-btn pmc-btn--onchrome pmc-btn--sm" target="_blank" rel="noreferrer" data-testid="share-linkedin"
         href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`}>Share on LinkedIn</a>
      <a className="pmc-btn pmc-btn--onchrome pmc-btn--sm" target="_blank" rel="noreferrer" data-testid="share-whatsapp"
         href={`https://wa.me/?text=${text}`}>WhatsApp</a>
      <a className="pmc-btn pmc-btn--onchrome pmc-btn--sm" href={imgUrl} download={`${noticeRef}.png`} target="_blank" rel="noreferrer" data-testid="share-image">Download image</a>
      <button type="button" className="pmc-btn pmc-btn--onchrome pmc-btn--sm" onClick={copy} data-testid="share-copy">Copy link</button>
    </div>
  );
}
