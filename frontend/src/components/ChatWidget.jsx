import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { marketingApi } from "@/lib/api";
import { useHelpVideos } from "@/apps/help-centre/HelpVideo";
import { useI18n } from "@/context/I18nContext";
import { BASENAME } from "@/lib/langPath";

const key = (staff) => (staff ? "pmc_chat_sid_staff" : "pmc_chat_sid");
const sid = (staff) => {
  try {
    let s = localStorage.getItem(key(staff));
    if (!s) { s = (crypto.randomUUID?.() || String(Date.now()) + Math.random()).replace(/[^a-zA-Z0-9-]/g, "").slice(0, 40); localStorage.setItem(key(staff), s); }
    return s;
  } catch { return (window.__pmcSid = window.__pmcSid || "anon-" + Date.now()); }
};
const resetSid = (staff) => { try { localStorage.removeItem(key(staff)); } catch { window.__pmcSid = null; } };
const LINK = /(\/(?:register|notices|buyers|login|help(?:\/[a-z0-9-]+)?)\b)/g;
const linkify = (t) => t.split(LINK).map((p, i) =>
  /^\/(register|notices|buyers|login|help)/.test(p) ? <a key={i} href={BASENAME + p} style={{ textDecoration: "underline" }}>{p}</a> : p);
const HELLO = {
  public: "Hi, I'm PMC Assistant. Ask me about registering, fees, open tenders or how bidding works.",
  staff: "Hi, I'm PMC Assistant for the team. Ask how to do anything in the admin or staff portal — e.g. \"how do I approve a registration?\" — and I'll show the steps and a video.",
};

const VideoAnswer = ({ v, slug }) => (
  <div style={{ justifySelf: "start", width: "85%", background: "#162921", padding: 8, borderRadius: 6 }} data-testid={`chat-video-${slug}`}>
    <video src={v.file} poster={v.file.replace(/\.mp4$/, ".jpg")} controls preload="none" playsInline style={{ width: "100%", borderRadius: 4 }} />
    <a href={`${BASENAME}/help/videos?v=${slug}`} style={{ color: "#d9bd72", fontSize: 12, fontWeight: 600 }} data-testid={`chat-video-link-${slug}`}>
      ▶ {v.title} · {Math.max(1, Math.round(v.seconds / 60))} min
    </a>
  </div>);

const Msg = ({ m, vids }) => (
  <>
    <div data-testid={`chat-msg-${m.role}`} translate={m.hello ? undefined : "no"} className={m.hello ? undefined : "notranslate"} dir="auto" style={{ justifySelf: m.role === "user" ? "end" : "start", maxWidth: "85%",
      background: m.role === "user" ? "#0F3B2E" : "#F3EFE4", color: m.role === "user" ? "#fff" : "#1f3a2e",
      padding: "8px 11px", fontSize: "14px", lineHeight: "20px", whiteSpace: "pre-wrap" }}>{m.role === "assistant" ? linkify(m.text) : m.text}</div>
    {(m.videos || []).filter((x) => vids[x.slug]).map((x) => <VideoAnswer key={x.slug} slug={x.slug} v={vids[x.slug]} />)}
  </>);

export default function ChatWidget() {
  const { pathname } = useLocation();
  const staff = /^\/(admin|staff)/.test(pathname);
  const mode = staff ? "staff" : "public";
  const vids = useHelpVideos();
  const { lang } = useI18n();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState({ public: [], staff: [] });
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  const list = [{ role: "assistant", text: HELLO[mode], hello: true }, ...msgs[mode]];
  const push = (m) => setMsgs((x) => ({ ...x, [mode]: [...x[mode], m] }));
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, open]);
  if (/^\/(escrow|auth)/.test(pathname) || /^\/(admin|staff)\/login/.test(pathname)) return null;
  const send = async (e) => {
    e.preventDefault();
    const m = text.trim();
    if (!m || busy) return;
    setText(""); push({ role: "user", text: m }); setBusy(true);
    try {
      const r = await marketingApi.assistantChat({ session_id: sid(staff), message: m, mode, lang });
      push({ role: "assistant", text: r.reply, videos: r.videos });
    } catch (err) {
      const d = err?.response?.data?.detail;
      if (err?.response?.status === 409) { resetSid(staff); }
      push({ role: "assistant", text: typeof d === "string" ? d : "Sorry, I couldn't answer just now. Please try again." });
    } finally { setBusy(false); }
  };
  const panel = { position: "fixed", right: "16px", bottom: "140px", width: "min(380px, calc(100vw - 32px))", height: "min(560px, calc(100vh - 160px))",
    background: "#fff", border: "1px solid rgba(15,59,46,.2)", boxShadow: "0 18px 50px rgba(0,0,0,.18)", zIndex: 60, display: "flex", flexDirection: "column" };
  return (
    <>
      {open && (
        <div style={panel} data-testid="chat-panel" data-mode={mode}>
          <div style={{ background: "#0F3B2E", color: "#F3EFE4", padding: "12px 14px", display: "flex", alignItems: "center" }}>
            <b style={{ flex: 1 }} data-testid="chat-title">PMC Assistant{staff ? " · Team help" : ""}</b>
            <button onClick={() => setOpen(false)} aria-label="Close chat" style={{ color: "#F3EFE4", fontSize: "18px" }} data-testid="chat-close">×</button>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "grid", gap: "8px", alignContent: "start" }} data-testid="chat-messages">
            {list.map((m, i) => <Msg key={i} m={m} vids={vids} />)}
            {busy && <div style={{ fontSize: "13px", opacity: 0.6 }} data-testid="chat-typing">Typing…</div>}
            <div ref={end} />
          </div>
          <form onSubmit={send} style={{ display: "flex", gap: "6px", padding: "10px", borderTop: "1px solid rgba(15,59,46,.12)" }}>
            <input value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} placeholder="Type your question…"
                   className="pmc-input" style={{ flex: 1 }} data-testid="chat-input" />
            <button className="pmc-btn pmc-btn--primary" disabled={busy || !text.trim()} data-testid="chat-send">Send</button>
          </form>
          <div style={{ fontSize: "10px", padding: "0 10px 8px", opacity: 0.55 }}>AI answers can be wrong. Don't share passwords or card details.</div>
        </div>
      )}
      <button onClick={() => setOpen((o) => !o)} data-testid="chat-toggle" aria-label="Chat with PMC Assistant"
              style={{ position: "fixed", right: "16px", bottom: "76px", zIndex: 60, background: "#0F3B2E", color: "#F3EFE4",
                       padding: "12px 18px", borderRadius: "999px", boxShadow: "0 10px 30px rgba(0,0,0,.25)", fontWeight: 600 }}>
        {open ? "Close" : "Ask PMC"}
      </button>
    </>
  );
}
