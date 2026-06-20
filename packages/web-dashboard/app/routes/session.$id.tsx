import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { endSession } from "~/lib/api";
import { startAudioCapture, startVideoCapture, type CaptureHandles } from "~/lib/capture";
import { connectAudio, connectFeedback, connectVideo } from "~/lib/ws";
import { ToastStack, type ToastEvent } from "~/components/Toast";

export const Route = createFileRoute("/session/$id")({ component: SessionPage });

function SessionPage() {
  const { id } = Route.useParams();
  const nav = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [events, setEvents] = useState<ToastEvent[]>([]);
  const [liveFeedback, setLiveFeedback] = useState(false); // Phase 3 toggle
  const [running, setRunning] = useState(false);
  const handlesRef = useRef<{ video?: CaptureHandles; audio?: CaptureHandles }>({});

  useEffect(() => {
    const fb = connectFeedback(id, {
      onMessage: (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "REPORT_READY") {
            nav({ to: "/session/$id/report", params: { id } });
            return;
          }
          if (data.type === "FALLBACK_ACTIVATED") {
            // banner toast
            setEvents((es) => [
              ...es,
              { id: crypto.randomUUID(), type: data.type, message: data.message, severity: "MEDIUM" },
            ]);
            return;
          }
          if (liveFeedback) {
            setEvents((es) => [
              ...es,
              {
                id: crypto.randomUUID(),
                type: data.type,
                severity: data.severity,
                message: data.message,
                timestamp_ms: data.timestamp_ms,
              },
            ]);
          }
        } catch {
          /* ignore */
        }
      },
    });
    return () => fb.close();
  }, [id, liveFeedback, nav]);

  const reportDeviceLost = (label: string) => {
    setEvents((es) => [
      ...es,
      {
        id: crypto.randomUUID(),
        type: "DEVICE_DISCONNECTED",
        severity: "HIGH",
        message: `${label} disconnected mid-session (e.g. Continuity Camera/mic handoff dropped) — it stopped capturing. Check System Settings > Sound and restart the recording.`,
      },
    ]);
  };

  const start = async () => {
    if (running) return;
    setRunning(true);
    const video = connectVideo(id);
    const audio = connectAudio(id);

    const [videoResult, audioResult] = await Promise.allSettled([
      startVideoCapture(videoRef.current!, (buf) => video.send(buf), () => reportDeviceLost("Camera")),
      startAudioCapture((buf) => audio.send(buf), 2, () => reportDeviceLost("Microphone")),
    ]);

    if (videoResult.status === "fulfilled") {
      handlesRef.current.video = videoResult.value;
    } else {
      console.error("Camera capture failed:", videoResult.reason);
      setEvents((es) => [
        ...es,
        {
          id: crypto.randomUUID(),
          type: "CAPTURE_ERROR",
          severity: "HIGH",
          message: "Camera unavailable — body language won't be scored. Check camera permission.",
        },
      ]);
    }

    if (audioResult.status === "fulfilled") {
      handlesRef.current.audio = audioResult.value;
    } else {
      console.error("Mic capture failed:", audioResult.reason);
      setEvents((es) => [
        ...es,
        {
          id: crypto.randomUUID(),
          type: "CAPTURE_ERROR",
          severity: "HIGH",
          message: "Microphone unavailable — voice won't be scored. Check mic permission.",
        },
      ]);
    }

    if (videoResult.status === "rejected" && audioResult.status === "rejected") {
      video.close();
      audio.close();
      setRunning(false);
    }
  };

  const stop = async () => {
    handlesRef.current.video?.stop();
    handlesRef.current.audio?.stop();
    setRunning(false);
    await endSession(id);
    // server emits REPORT_READY → nav happens via feedback WS handler
  };

  return (
    <main className="container">
      <h1>Practice Session</h1>
      <div className="session">
        <div>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video ref={videoRef} muted playsInline />
          <div className="controls">
            {!running ? (
              <button onClick={start}>Start Recording</button>
            ) : (
              <button className="stop" onClick={stop}>
                End Session
              </button>
            )}
            <label style={{ marginLeft: "auto", color: "var(--muted)" }}>
              <input
                type="checkbox"
                checked={liveFeedback}
                onChange={(e) => setLiveFeedback(e.target.checked)}
                disabled={running}
              />{" "}
              Show live feedback during session
            </label>
          </div>
        </div>
        <aside>
          <h3>Session ID</h3>
          <code style={{ fontSize: 12, color: "var(--muted)" }}>{id}</code>
          <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 16 }}>
            Mic + camera permission required. When you click End Session, your scored report
            renders in ≤60s.
          </p>
        </aside>
      </div>
      <ToastStack events={events} />
    </main>
  );
}
