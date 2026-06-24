import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, ChevronLeft, ChevronRight, VideoOff } from "lucide-react";
import { endSession, getSession } from "~/lib/api";
import { getCameraPreview, startAudioCapture, startVideoCapture, type CaptureHandles } from "~/lib/capture";
import { connectAudio, connectFeedback, connectSlide, connectVideo, type WSHandle } from "~/lib/ws";
import { ToastStack, type ToastEvent } from "~/components/Toast";
import { Button } from "~/components/ui/button";
import { Switch } from "~/components/ui/switch";
import { Label } from "~/components/ui/label";
import { CornerBrackets } from "~/components/chrome/CornerBrackets";

type SlideEventMessage = {
  slide_index: number;
  timestamp_ms: number;
  source?: "manual" | "keyboard";
};

export const Route = createFileRoute("/session/$id")({ component: SessionPage });

function SessionPage() {
  const { id } = Route.useParams();
  const nav = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [events, setEvents] = useState<ToastEvent[]>([]);
  const [liveFeedback, setLiveFeedback] = useState(false);
  const [running, setRunning] = useState(false);
  const [awaitingReport, setAwaitingReport] = useState(false);
  const [previewReady, setPreviewReady] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const [slideCount, setSlideCount] = useState<number | null>(null);
  const [currentSlide, setCurrentSlide] = useState(1);
  const previewStreamRef = useRef<MediaStream | null>(null);
  const handlesRef = useRef<{ video?: CaptureHandles; audio?: CaptureHandles }>({});
  const slideWsRef = useRef<WSHandle | null>(null);
  const recordingStartedAtRef = useRef<number>(0);
  const endingInFlightRef = useRef(false);

  useEffect(() => {
    getSession(id)
      .then((session) => {
        if (session.pptx_ready && session.slide_count != null) {
          setSlideCount(session.slide_count);
        }
      })
      .catch(() => {
        /* session metadata optional for slide tracker */
      });
  }, [id]);

  useEffect(() => {
    let stopped = false;
    getCameraPreview(videoRef.current!)
      .then((stream) => {
        if (stopped) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        previewStreamRef.current = stream;
        setPreviewReady(true);
      })
      .catch(() => {
        if (!stopped) setPreviewError(true);
      });
    return () => {
      stopped = true;
      previewStreamRef.current?.getTracks().forEach((t) => t.stop());
      previewStreamRef.current = null;
    };
  }, []);

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

  const sendSlideEvent = useCallback(
    (slideIndex: number, source: SlideEventMessage["source"] = "manual") => {
      if (!slideWsRef.current || slideCount == null) return;
      const payload: SlideEventMessage = {
        slide_index: slideIndex,
        timestamp_ms: Math.max(0, Date.now() - recordingStartedAtRef.current),
        source,
      };
      slideWsRef.current.send(JSON.stringify(payload));
    },
    [slideCount],
  );

  const goToSlide = useCallback(
    (next: number, source: SlideEventMessage["source"] = "manual") => {
      if (slideCount == null || next < 1 || next > slideCount || next === currentSlide) return;
      setCurrentSlide(next);
      sendSlideEvent(next, source);
    },
    [slideCount, currentSlide, sendSlideEvent],
  );

  useEffect(() => {
    if (!running || slideCount == null) return;

    const onKeyDown = (ev: KeyboardEvent) => {
      if (ev.target instanceof HTMLInputElement || ev.target instanceof HTMLTextAreaElement) return;
      if (ev.key === "ArrowLeft") {
        ev.preventDefault();
        goToSlide(currentSlide - 1, "keyboard");
      } else if (ev.key === "ArrowRight") {
        ev.preventDefault();
        goToSlide(currentSlide + 1, "keyboard");
      } else if (ev.key >= "1" && ev.key <= "9") {
        const n = Number(ev.key);
        if (n <= slideCount) {
          ev.preventDefault();
          goToSlide(n, "keyboard");
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [running, slideCount, currentSlide, goToSlide]);

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

  const acquireVideoStream = async (): Promise<MediaStream> => {
    if (previewStreamRef.current) return previewStreamRef.current;
    const stream = await getCameraPreview(videoRef.current!);
    previewStreamRef.current = stream;
    setPreviewReady(true);
    return stream;
  };

  const start = async () => {
    if (running || awaitingReport) return;
    setRunning(true);
    recordingStartedAtRef.current = Date.now();
    setCurrentSlide(1);

    const video = connectVideo(id);
    const audio = connectAudio(id);
    if (slideCount != null) {
      slideWsRef.current = connectSlide(id);
      slideWsRef.current.send(
        JSON.stringify({
          slide_index: 1,
          timestamp_ms: 0,
          source: "manual",
        } satisfies SlideEventMessage),
      );
    }

    const [videoResult, audioResult] = await Promise.allSettled([
      acquireVideoStream().then((stream) =>
        startVideoCapture(stream, videoRef.current!, (buf) => video.send(buf), () => reportDeviceLost("Camera")),
      ),
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
      slideWsRef.current?.close();
      slideWsRef.current = null;
      setRunning(false);
    }
  };

  const stop = async () => {
    if (awaitingReport || endingInFlightRef.current) return;

    endingInFlightRef.current = true;
    handlesRef.current.video?.stop();
    handlesRef.current.audio?.stop();
    slideWsRef.current?.close();
    slideWsRef.current = null;
    previewStreamRef.current = null;
    setRunning(false);
    setAwaitingReport(true);
    try {
      await endSession(id);
    } catch (err) {
      setAwaitingReport(false);
      endingInFlightRef.current = false;
      setEvents((es) => [
        ...es,
        {
          id: crypto.randomUUID(),
          type: "SESSION_END_ERROR",
          severity: "HIGH",
          message: err instanceof Error ? err.message : "Could not end session — try again.",
        },
      ]);
    }
  };

  const trackerEnabled = slideCount != null && slideCount > 0;

  return (
    <main className="mx-auto w-full max-w-5xl px-8 py-10">
      <h1 className="mb-6 font-display text-2xl font-bold tracking-tight text-pearl">
        Practice Session
      </h1>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_300px]">
        <div>
          <div className="relative overflow-hidden rounded-xl bg-black">
            <CornerBrackets />
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video ref={videoRef} muted playsInline className="aspect-video w-full" />
            {!previewReady && !previewError && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/70 font-mono text-xs tracking-wide text-ash">
                <Camera className="size-5 text-teal" aria-hidden="true" />
                Requesting camera access…
              </div>
            )}
            {previewError && !running && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/70 px-6 text-center font-mono text-xs tracking-wide text-ash">
                <VideoOff className="size-5 text-red" aria-hidden="true" />
                Camera unavailable — check permission, then try Start Recording.
              </div>
            )}
            {running ? (
              <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 font-mono text-xs font-medium tracking-wide text-white backdrop-blur-sm">
                <span className="rec-dot size-1.5 rounded-full bg-orange motion-reduce:opacity-100" />
                REC
              </div>
            ) : previewReady && (
              <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 font-mono text-xs font-medium tracking-wide text-ash backdrop-blur-sm">
                <span className="size-1.5 rounded-full bg-green" />
                CAMERA READY
              </div>
            )}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            {!running && !awaitingReport ? (
              <Button onClick={start} size="lg" disabled={previewError}>
                Start Recording
              </Button>
            ) : running ? (
              <Button
                onClick={stop}
                size="lg"
                className="bg-red-solid text-white hover:bg-red-solid/85"
              >
                End Session
              </Button>
            ) : (
              <Button size="lg" disabled aria-busy="true">
                <span
                  className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent"
                  aria-hidden="true"
                />
                Generating report…
              </Button>
            )}
            {trackerEnabled && running && (
              <div className="flex items-center gap-2 rounded-lg border border-border px-3 py-2">
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  aria-label="Previous slide"
                  disabled={currentSlide <= 1}
                  onClick={() => goToSlide(currentSlide - 1)}
                >
                  <ChevronLeft className="size-4" />
                </Button>
                <span className="min-w-[7rem] text-center font-mono text-sm text-pearl">
                  Slide {currentSlide} / {slideCount}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  aria-label="Next slide"
                  disabled={currentSlide >= slideCount!}
                  onClick={() => goToSlide(currentSlide + 1)}
                >
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            )}
            <div className="ml-auto flex items-center gap-2">
              <Switch
                id="live-feedback"
                checked={liveFeedback}
                onCheckedChange={setLiveFeedback}
                disabled={running || awaitingReport}
              />
              <Label htmlFor="live-feedback" className="text-muted-foreground">
                Show live feedback during session
              </Label>
            </div>
          </div>
          {trackerEnabled && running && (
            <p className="mt-2 font-mono text-xs text-muted-foreground">
              Use ← / → or number keys 1–9 to track which slide you are presenting.
            </p>
          )}
        </div>
        <aside>
          <h3 className="font-mono text-xs font-semibold tracking-[0.14em] text-teal uppercase">
            Session ID
          </h3>
          <code className="mt-1 block font-mono text-xs text-muted-foreground">{id}</code>
          <p className="mt-4 text-sm text-muted-foreground">
            Mic + camera permission required. When you click End Session, your scored report
            renders in ≤60s.
          </p>
          {trackerEnabled && (
            <p className="mt-3 text-sm text-muted-foreground">
              Deck loaded ({slideCount} slides). Advance the slide tracker as you rehearse so
              delivery feedback can align speech with slides.
            </p>
          )}
        </aside>
      </div>
      <ToastStack events={events} />
    </main>
  );
}
