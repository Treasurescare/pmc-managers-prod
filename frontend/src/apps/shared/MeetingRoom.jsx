import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";

/** Wave 41 — Jitsi Meet embedded room, joined via magic-link `/meet/:token`.
 *
 * Uses the public `meet.jit.si` instance via the external Jitsi Iframe API.
 * No auth needed. Each meeting has a deterministic room name (`pmc-{mid}`)
 * that's unguessable if the meeting id is not leaked.
 *
 * Recording: participants can hit the record button *inside* the Jitsi room —
 * files download to their own device. Cloud recording requires paid JaaS
 * (upgrade path preserved).
 */
const JITSI_DOMAIN = "meet.jit.si";
const JITSI_SCRIPT = "https://meet.jit.si/external_api.js";

function loadJitsiScript() {
  return new Promise((resolve, reject) => {
    if (window.JitsiMeetExternalAPI) return resolve();
    const existing = document.querySelector(`script[src="${JITSI_SCRIPT}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Jitsi script failed")));
      return;
    }
    const s = document.createElement("script");
    s.src = JITSI_SCRIPT;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Jitsi script failed"));
    document.body.appendChild(s);
  });
}

export default function MeetingRoom() {
  const { token } = useParams();
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [joined, setJoined] = useState(false);
  const containerRef = useRef(null);
  const apiRef = useRef(null);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/meetings/join/${token}`)
      .then(async (r) => {
        if (!r.ok) {
          const j = await r.json().catch(() => ({}));
          throw new Error(j.detail || `HTTP ${r.status}`);
        }
        return r.json();
      })
      .then(setMeta)
      .catch((e) => setError(e.message));
  }, [token]);

  const joinRoom = async () => {
    if (!meta || !containerRef.current) return;
    try {
      await loadJitsiScript();
      apiRef.current = new window.JitsiMeetExternalAPI(JITSI_DOMAIN, {
        roomName: meta.jitsi_room,
        parentNode: containerRef.current,
        width: "100%",
        height: "100%",
        userInfo: { displayName: meta.display_name || "Guest" },
        configOverwrite: {
          prejoinPageEnabled: true,
          enableWelcomePage: false,
          enableClosePage: false,
          disableDeepLinking: true,
          startWithAudioMuted: true,
          startWithVideoMuted: true,
          subject: meta.subject,
        },
        interfaceConfigOverwrite: {
          MOBILE_APP_PROMO: false,
          SHOW_JITSI_WATERMARK: false,
          SHOW_WATERMARK_FOR_GUESTS: false,
          TOOLBAR_BUTTONS: [
            "microphone", "camera", "desktop", "chat", "raisehand", "tileview",
            "fullscreen", "recording", "settings", "hangup",
          ],
        },
      });
      apiRef.current.addListener("readyToClose", () => {
        toast.info("Meeting closed");
        setJoined(false);
        try { apiRef.current.dispose(); } catch { /* noop */ }
      });
      setJoined(true);
    } catch (e) {
      toast.error(e.message);
    }
  };

  useEffect(() => () => {
    try { apiRef.current?.dispose(); } catch { /* noop */ }
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-brand-navy text-white flex items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <div className="text-red-400 uppercase tracking-widest text-xs">Invite link error</div>
          <h1 className="font-display text-3xl mt-3">{error}</h1>
          <p className="mt-4 text-white/60 text-sm">Ask the meeting organiser to send a fresh invite link.</p>
        </div>
      </div>
    );
  }

  if (!meta) {
    return (
      <div className="min-h-screen bg-brand-navy text-white flex items-center justify-center">
        <div className="text-white/60">Resolving invite…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-navy text-white flex flex-col" data-testid="meeting-room">
      <header className="px-6 py-4 border-b border-white/10 flex items-baseline justify-between flex-wrap gap-3">
        <div>
          <div className="pmc-label" style={{ color: "rgba(255,255,255,0.5)" }}>PMC · Live meeting</div>
          <h1 className="font-display text-xl mt-1">{meta.subject}</h1>
          {meta.notice_ref && <span className="text-xs text-white/60 font-mono">{meta.notice_ref}</span>}
        </div>
        <div className="text-right text-xs">
          <div className="text-white/50">You are joining as</div>
          <div className="font-semibold">{meta.display_name} · <span className="uppercase tracking-widest text-white/40">{meta.role}</span></div>
        </div>
      </header>

      {!joined && (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="max-w-xl text-center">
            <div className="pmc-label" style={{ color: "rgba(255,255,255,0.5)" }}>Pre-flight</div>
            <h2 className="font-display text-4xl mt-3">Ready to join?</h2>
            {meta.agenda && (
              <div className="mt-6 text-left bg-white/5 border border-white/10 p-5">
                <div className="pmc-label" style={{ color: "rgba(255,255,255,0.5)" }}>Agenda</div>
                <div className="mt-2 whitespace-pre-line text-white/85 text-sm">{meta.agenda}</div>
              </div>
            )}
            <div className="mt-6 text-white/60 text-sm">
              Scheduled: {meta.scheduled_at?.slice(0, 16).replace("T", " ")} UTC · {meta.duration_min} min
            </div>
            {meta.status === "cancelled" ? (
              <div className="mt-8 text-red-300">This meeting was cancelled.</div>
            ) : (
              <button type="button" onClick={joinRoom} data-testid="mtg-enter-room"
                className="mt-8 px-10 py-4 bg-white text-brand-navy uppercase tracking-widest text-sm font-semibold hover:bg-white/90">
                Enter the room
              </button>
            )}
            <div className="mt-6 text-white/40 text-[11px]">
              To record locally, click the ⋮ menu inside the room → Start recording.
              The file downloads to your own device.
            </div>
          </div>
        </div>
      )}

      <div ref={containerRef}
           className={joined ? "flex-1" : "hidden"}
           style={{ minHeight: joined ? "70vh" : 0 }}
           data-testid="jitsi-container" />
    </div>
  );
}
