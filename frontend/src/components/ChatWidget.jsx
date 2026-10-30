import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { marketingApi } from "@/lib/api";

const sid = () => {
  try {
    let s = localStorage.getItem("pmc_chat_sid");
    if (!s) { s = (crypto.randomUUID?.() || String(Date.now()) + Math.random()).replace(/[^a-zA-Z0-9-]/g, "").slice(0, 40); localStorage.setItem("pmc_chat_sid", s); }
    return s;
  } catch { return "anon-" + Date.now(); }
};
const HELLO = { role: "assistant", text: "Hi, I'm PMC Assistant. Ask me about registering, fees, open tenders or how bidding works." };

export default function ChatWidget() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([HELLO]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, open]);
  if (/^\/(admin|staff|escrow|auth)/.test(pathname)) return null;
  const send = async (e) => {
    e.preventDefault();
    const m = text.trim();
    if (!m || busy) return;
    setText(""); setMsgs((x) => [...x, { role: "user", text: m }]); setBusy(true);
    try {
      const r = await marketingApi.assistantChat({ session_id: sid(), message: m });
      setMsgs((x) => [...x, { role: "assistant", text: r.reply }]);
    } catch (err) {
      const d = err?.response?.data?.detail;
      setMsgs((x) => [...x, { role: "assistant", text: typeof d === "string" ? d : "Sorry, I couldn't answer just now. Please try again." }]);
    } finally { setBusy(false); }
  };
  const panel = { position: "fixed", right: "16px", bottom: "84px", width: "min(380px, calc(100vw - 32px))", height: "min(520px, calc(100vh - 120px))",
    background: "#fff", border: "1px solid rgba(15,59,46,.2)", boxShadow: "0 18px 50px rgba(0,0,0,.18)", zIndex: 60, display: "flex", flexDirection: "column" };
  return (
    <>
      {open && (
        <div style={panel} data-testid="chat-panel">
          <div style={{ background: "#0F3B2E", color: "#F3EFE4", padding: "12px 14px", display: "flex", alignItems: "center" }}>
            <b style={{ flex: 1 }}>PMC Assistant</b>
            <button onClick={() => setOpen(false)} aria-label="Close chat" style={{ color: "#F3EFE4", fontSize: "18px" }} data-testid="chat-close">×</button>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "grid", gap: "8px", alignContent: "start" }} data-testid="chat-messages">
            {msgs.map((m, i) => (
              <div key={i} data-testid={`chat-msg-${m.role}`} style={{ justifySelf: m.role === "user" ? "end" : "start", maxWidth: "85%",
                background: m.role === "user" ? "#0F3B2E" : "#F3EFE4", color: m.role === "user" ? "#fff" : "#1f3a2e",
                padding: "8px 11px", fontSize: "14px", lineHeight: "20px", whiteSpace: "pre-wrap" }}>{m.text}</div>))}
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
              style={{ position: "fixed", right: "16px", bottom: "16px", zIndex: 60, background: "#0F3B2E", color: "#F3EFE4",
                       padding: "12px 18px", borderRadius: "999px", boxShadow: "0 10px 30px rgba(0,0,0,.25)", fontWeight: 600 }}>
        {open ? "Close" : "Ask PMC"}
      </button>
    </>
  );
}
