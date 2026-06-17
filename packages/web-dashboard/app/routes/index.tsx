import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { createSession, storeToken, uploadPptx } from "~/lib/api";

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
    <main className="container landing">
      <h1>🐙 OctoPrep2000</h1>
      <p>AI presentation coach. Upload your deck, record your practice, get scored.</p>

      <form onSubmit={handleStart}>
        <label>
          Topic <small>(required — what's your talk about?)</small>
          <input
            type="text"
            required
            minLength={8}
            maxLength={200}
            placeholder="React 19 new features"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </label>

        <label>
          Audience context <small>(optional)</small>
          <textarea
            rows={2}
            maxLength={500}
            placeholder="Senior frontend devs at Tikal"
            value={topicContext}
            onChange={(e) => setTopicContext(e.target.value)}
          />
        </label>

        <label>
          Slide deck <small>(.pptx, optional but recommended)</small>
          <input
            type="file"
            accept=".pptx"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <button type="submit" disabled={loading}>
          {loading ? "Starting…" : "Start Session →"}
        </button>
        {error && <p style={{ color: "var(--red)" }}>{error}</p>}
      </form>
    </main>
  );
}
