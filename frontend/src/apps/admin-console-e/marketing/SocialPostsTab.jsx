import { useEffect, useState } from "react";
import { toast } from "sonner";
import { marketingApi, showApiError } from "@/lib/api";

const btn = "pmc-btn border border-brand-navy/40 bg-white px-3 py-1.5 text-xs";

function PostRow({ p, onChange }) {
  const [text, setText] = useState(p.text);
  const act = async (fn, ok) => { try { await fn(); toast.success(ok); onChange(); } catch (e) { showApiError(e); } };
  const manual = () => {
    navigator.clipboard?.writeText(`${text}\n${p.share_url}`).catch(() => {});
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(p.share_url)}`, "_blank", "noopener");
    toast.success("Text copied — paste it into the LinkedIn post, then click Mark posted");
  };
  return (
    <div className="border border-brand-navy/15 bg-white p-4 grid gap-4 md:grid-cols-[320px_1fr]" data-testid={`sp-row-${p.id}`}>
      <img src={`${p.share_url}.png`} alt="" className="w-full border border-brand-navy/10" />
      <div className="space-y-2">
        <div className="flex gap-2 items-center text-sm">
          <b>{p.notice_ref}</b><span className="flex-1 truncate">{p.title}</span>
          <span className="text-xs uppercase px-2 py-0.5 bg-brand-navy/10" data-testid={`sp-status-${p.id}`}>{p.status}</span>
        </div>
        <textarea className="w-full border border-brand-navy/20 p-2 text-sm" rows={6} value={text} disabled={p.status !== "pending"}
                  onChange={(e) => setText(e.target.value)} data-testid={`sp-text-${p.id}`} />
        {p.status === "pending" && (
          <div className="flex flex-wrap gap-2">
            <button className="pmc-btn pmc-btn--primary px-3 py-1.5 text-xs" data-testid={`sp-approve-${p.id}`}
              onClick={() => act(async () => { if (text !== p.text) await marketingApi.editSocialPost(p.id, text); await marketingApi.approveSocialPost(p.id); }, "Posted to LinkedIn")}>Approve &amp; post</button>
            <button className={btn} onClick={() => act(() => marketingApi.editSocialPost(p.id, text), "Saved")} data-testid={`sp-save-${p.id}`}>Save text</button>
            <button className={btn} onClick={manual} data-testid={`sp-manual-${p.id}`}>Post manually</button>
            <button className={btn} onClick={() => act(() => marketingApi.markSocialPosted(p.id), "Marked as posted")} data-testid={`sp-mark-${p.id}`}>Mark posted</button>
            <button className={btn + " text-red-700"} onClick={() => act(() => marketingApi.rejectSocialPost(p.id), "Skipped")} data-testid={`sp-reject-${p.id}`}>Skip</button>
          </div>)}
      </div>
    </div>
  );
}

export const SocialPostsTab = () => {
  const [d, setD] = useState(null);
  const load = () => marketingApi.socialPosts().then(setD).catch(showApiError);
  useEffect(() => { load(); }, []);
  const connect = async () => { try { const r = await marketingApi.linkedinConnect(); window.location.href = r.url; } catch (e) { showApiError(e); } };
  if (!d) return null;
  const li = d.linkedin;
  return (
    <div className="space-y-4" data-testid="mkt-social">
      <div className="border border-brand-navy/20 bg-white p-4 flex flex-wrap gap-3 items-center text-sm" data-testid="sp-linkedin-status">
        <b>LinkedIn company page:</b>
        {!li.app_configured ? <span className="text-amber-700">LinkedIn app keys not added yet — use "Post manually" for now.</span>
          : !li.org_configured ? <span className="text-amber-700">Company page ID (LINKEDIN_ORG_ID) not added yet.</span>
          : li.connected ? <span className="text-emerald-700">Connected by {li.connected_by} · expires {li.expires_at?.slice(0, 10)}</span>
          : <span>Not connected</span>}
        {li.app_configured && <button className="pmc-btn pmc-btn--primary px-3 py-1.5 text-xs ml-auto" onClick={connect} data-testid="sp-connect">{li.connected ? "Reconnect" : "Connect LinkedIn page"}</button>}
      </div>
      <div className="text-xs text-brand-navy/60">Every newly published tender lands here for your approval. Nothing is posted until you approve it.</div>
      {d.items.map((p) => <PostRow key={p.id} p={p} onChange={load} />)}
      {!d.items.length && <div className="p-6 text-sm text-brand-navy/60 border border-dashed border-brand-navy/20">No posts waiting. New tenders appear here when they're published.</div>}
    </div>
  );
};
