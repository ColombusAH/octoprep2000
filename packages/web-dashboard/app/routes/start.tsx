import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";
import {
  createSession,
  storeToken,
  uploadPptx,
  uploadVideo,
  waitForPptxReady,
  waitForVideoReady,
} from "~/lib/api";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Label } from "~/components/ui/label";
import { CornerBrackets } from "~/components/chrome/CornerBrackets";
import { useWallet } from "~/lib/wallet";

export const Route = createFileRoute("/start")({ component: LandingPage });

function LandingPage() {
  const nav = useNavigate();
  const { addPoints } = useWallet();
  const [topic, setTopic] = useState("");
  const [topicContext, setTopicContext] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [analysing, setAnalysing] = useState(false);
  const [processingVideo, setProcessingVideo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startInFlightRef = useRef(false);

  const isStarting = loading || analysing || processingVideo;
  const startButtonLabel = processingVideo
    ? "Analysing your video…"
    : analysing
      ? "Analysing your deck…"
      : loading
        ? "Starting…"
        : video
          ? "Upload & Analyze →"
          : "Start Session →";

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (startInFlightRef.current) return;

    startInFlightRef.current = true;
    setError(null);
    setLoading(true);
    try {
      const { session_id, access_token } = await createSession({
        topic,
        topic_context: topicContext || undefined,
      });
      storeToken(session_id, access_token);
      if (file) {
        await uploadPptx(session_id, file);
        setAnalysing(true);
        await waitForPptxReady(session_id);
        setAnalysing(false);
      }
      addPoints(50); // cosmetic — Tape Credits tick on a successful session start
      if (video) {
        // Uploaded-video path: batch analysis instead of a live rehearsal (feature 003).
        setProcessingVideo(true);
        await uploadVideo(session_id, video);
        await waitForVideoReady(session_id);
        await nav({ to: "/session/$id/report", params: { id: session_id } });
        return;
      }
      await nav({ to: "/session/$id", params: { id: session_id } });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
      setAnalysing(false);
      setProcessingVideo(false);
      startInFlightRef.current = false;
    }
  };

  return (
    <main className="mx-auto w-full max-w-2xl px-8 py-16">
      <div className="mb-10">
        <p className="flex items-center gap-2 font-mono text-xs tracking-[0.2em] text-teal uppercase">
          <span className="rec-dot size-2 rounded-full bg-orange motion-reduce:opacity-100" aria-hidden="true" />
          OctoPrep2000 // Rehearsal Deck
        </p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-tight text-balance text-pearl">
          Rehearse. Get a score you can trust.
        </h1>
        <p className="mt-3 text-base text-muted-foreground">
          Upload your deck, practice live on camera, and get specific, timestamped feedback —
          not a generic grade.
        </p>
      </div>

      <Card className="relative">
        <CornerBrackets />
        <CardHeader>
          <CardTitle>Start a session</CardTitle>
          <CardDescription>Takes about a minute to set up.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleStart} className="flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <Label htmlFor="topic">
                Topic <span className="text-muted-foreground">— what&apos;s your talk about?</span>
              </Label>
              <Input
                id="topic"
                type="text"
                required
                minLength={8}
                maxLength={200}
                placeholder="React 19 new features"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="audience">
                Audience context <span className="text-muted-foreground">— optional</span>
              </Label>
              <Textarea
                id="audience"
                rows={2}
                maxLength={500}
                placeholder="Senior frontend devs at Tikal"
                value={topicContext}
                onChange={(e) => setTopicContext(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="deck">
                Slide deck{" "}
                <span className="text-muted-foreground">— .pptx, optional but recommended</span>
              </Label>
              <Input
                id="deck"
                type="file"
                accept=".pptx"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="video">
                Recorded rehearsal{" "}
                <span className="text-muted-foreground">
                  — .mp4/.mov/.webm, optional. Upload instead of rehearsing live (max 15 min).
                </span>
              </Label>
              <Input
                id="video"
                type="file"
                accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.m4v,.webm"
                onChange={(e) => setVideo(e.target.files?.[0] ?? null)}
              />
            </div>

            <Button
              type="submit"
              disabled={isStarting}
              aria-busy={isStarting}
              size="lg"
              className="mt-1"
            >
              {isStarting && (
                <span
                  className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent"
                  aria-hidden="true"
                />
              )}
              {startButtonLabel}
            </Button>

            {error && (
              <p
                className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 font-mono text-xs text-destructive"
                role="alert"
              >
                {error}
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
