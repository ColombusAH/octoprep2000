import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { createSession, storeToken, uploadPptx } from "~/lib/api";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Label } from "~/components/ui/label";

export const Route = createFileRoute("/")({ component: LandingPage });

function LandingPage() {
  const nav = useNavigate();
  const [topic, setTopic] = useState("");
  const [topicContext, setTopicContext] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { session_id, access_token } = await createSession({
        topic,
        topic_context: topicContext || undefined,
      });
      storeToken(session_id, access_token);
      if (file) await uploadPptx(session_id, file);
      nav({ to: "/session/$id", params: { id: session_id } });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6 py-16">
      <div className="mb-10">
        <p className="font-mono text-xs tracking-[0.2em] text-muted-foreground uppercase">
          OctoPrep2000
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-balance">
          Rehearse. Get a score you can trust.
        </h1>
        <p className="mt-3 text-base text-muted-foreground">
          Upload your deck, practice live on camera, and get specific, timestamped feedback —
          not a generic grade.
        </p>
      </div>

      <Card>
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

            <Button type="submit" disabled={loading} size="lg" className="mt-1">
              {loading ? "Starting…" : "Start Session →"}
            </Button>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
