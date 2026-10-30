import { useEffect, useState } from "react";
import { toast } from "sonner";
import { whatsappApi, showApiError } from "@/lib/api";

const WHO = { in: "Supplier", ai: "Ask PMC (AI)", staff: "PMC team" };

const Bubble = ({ m }) => {
  const out = m.direction === "out";
  return (
    <div className={"max-w-[80%] p-2 text-sm " + (out ? "ml-auto bg-emerald-50 border border-emerald-200" : "bg-white border border-brand-navy/15")} data-testid={`wa-msg-${m.id}`}>
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{out ? (WHO[m.kind] || m.kind) : WHO.in} · {m.at?.slice(0, 16).replace("T", " ")}{m.status === "failed" ? " · FAILED" : ""}</div>
      <div className="whitespace-pre-wrap">{m.text}</div>
    </div>
  );
};

export const WhatsAppInbox = () => {
  const [threads, setThreads] = useState([]);
  const [open, setOpen] = useState(null);
  const [text, setText] = useState("");
  const loadThreads = () => whatsappApi.threads().then((r) => setThreads(r.items || [])).catch(showApiError);
  const openThread = (id) => whatsappApi.thread(id).then(setOpen).catch(showApiError);
  useEffect(() => { loadThreads(); }, []);
  const send = async (e) => {
    e.preventDefault();
    try { await whatsappApi.reply(open.thread.wa_id, text); setText(""); openThread(open.thread.wa_id); toast.success("Reply sent"); }
    catch (err) { showApiError(err); }
  };
  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]" data-testid="wa-inbox">
      <div className="border border-brand-navy/20 bg-white divide-y divide-brand-navy/10 max-h-[520px] overflow-y-auto">
        {threads.map((t) => (
          <button key={t.id} onClick={() => openThread(t.wa_id)} className="w-full text-left p-3 hover:bg-brand-navy/5" data-testid={`wa-thread-${t.wa_id}`}>
            <div className="flex justify-between text-sm font-semibold"><span>{t.company || t.name || `+${t.wa_id}`}</span>
              {t.unread > 0 && <span className="px-1.5 text-xs bg-emerald-700 text-white">{t.unread}</span>}</div>
            <div className="text-xs text-brand-navy/60 truncate">{t.last_text}</div>
          </button>))}
        {!threads.length && <div className="p-6 text-sm text-center text-brand-navy/60" data-testid="wa-inbox-empty">No WhatsApp conversations yet.</div>}
      </div>
      <div className="border border-brand-navy/20 bg-brand-navy/[0.03] p-3 flex flex-col min-h-[320px]">
        {!open ? <div className="m-auto text-sm text-brand-navy/60">Pick a conversation</div> : <>
          <div className="text-sm font-semibold mb-2">{open.thread.company || open.thread.name || "Contact"} · +{open.thread.wa_id}</div>
          <div className="space-y-2 flex-1 overflow-y-auto max-h-[400px]">{open.messages.map((m) => <Bubble key={m.id} m={m} />)}</div>
          {open.window_open ? (
            <form onSubmit={send} className="flex gap-2 mt-3">
              <input className="px-3 py-2 border border-brand-navy/20 bg-white text-sm flex-1" required value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a reply" data-testid="wa-reply-input" />
              <button className="pmc-btn pmc-btn--primary" data-testid="wa-reply-send">Send</button>
            </form>
          ) : <div className="text-xs text-brand-navy/60 mt-3" data-testid="wa-window-closed">More than 24 hours since their last message — WhatsApp only allows replies after they write again.</div>}
        </>}
      </div>
    </div>
  );
};
