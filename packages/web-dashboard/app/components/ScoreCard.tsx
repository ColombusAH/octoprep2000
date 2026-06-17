/**
 * Scorecard per PRD §10 + FR-009.
 * Hero score + lock/unlock at 80, 4 sub-category panels w/ Strengths + Improvements.
 * Mentor URL injected via prop (sourced from GET /config at runtime).
 */

type Insight = {
  category: "voice" | "body" | "slide" | "content";
  type: "STRENGTH" | "IMPROVEMENT";
  message: string;
  timestamps?: number[];
  slides?: number[];
};

export type ReportData = {
  overall_score: number;
  voice_score: number;
  body_score: number | null;
  slide_score: number;
  content_score: number;
  insights: Insight[];
  mentor_unlocked: boolean;
};

function scoreColor(score: number): string {
  if (score >= 80) return "#1f9d55";
  if (score >= 60) return "#f59e0b";
  return "#dc2626";
}

function formatTs(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = (total % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function Panel({
  icon,
  title,
  score,
  insights,
}: {
  icon: string;
  title: string;
  score: number | null;
  insights: Insight[];
}) {
  const strengths = insights.filter((i) => i.type === "STRENGTH");
  const improvements = insights.filter((i) => i.type === "IMPROVEMENT");
  return (
    <section className="panel">
      <header>
        <span className="panel-icon">{icon}</span>
        <h3>{title}</h3>
        {score !== null && (
          <span className="panel-score" style={{ color: scoreColor(score) }}>
            {Math.round(score)}/100
          </span>
        )}
      </header>
      <div className="panel-body">
        <div className="col strengths">
          <h4>🌟 Strengths</h4>
          {strengths.length === 0 ? <p className="muted">—</p> : null}
          {strengths.map((i, idx) => (
            <p key={idx}>{i.message}</p>
          ))}
        </div>
        <div className="col improvements">
          <h4>⚠️ Improvements</h4>
          {improvements.length === 0 ? <p className="muted">—</p> : null}
          {improvements.map((i, idx) => (
            <p key={idx}>
              {i.message}
              {i.timestamps && i.timestamps.length > 0 ? (
                <> &nbsp;<span className="meta">→ {i.timestamps.map(formatTs).join(", ")}</span></>
              ) : null}
              {i.slides && i.slides.length > 0 ? (
                <> &nbsp;<span className="meta">→ slides {i.slides.join(", ")}</span></>
              ) : null}
            </p>
          ))}
        </div>
      </div>
    </section>
  );
}

export function ScoreCard({
  report,
  mentorBookingUrl,
}: {
  report: ReportData;
  mentorBookingUrl: string;
}) {
  const overall = report.overall_score;
  const unlocked = report.mentor_unlocked;
  const delta = Math.max(0, 80 - overall);

  const byCat = (cat: Insight["category"]) => report.insights.filter((i) => i.category === cat);

  return (
    <div className="scorecard">
      <header className="hero">
        <div className="ring" style={{ borderColor: scoreColor(overall) }}>
          <span className="overall" style={{ color: scoreColor(overall) }}>
            {Math.round(overall)}
          </span>
          <span className="overall-suffix">/ 100</span>
        </div>
        {unlocked ? (
          <div className="unlock">
            <h2>🎉 Mentor unlocked</h2>
            <a className="cta" href={mentorBookingUrl} target="_blank" rel="noreferrer">
              Book Your 1-on-1 with a Tikal Expert →
            </a>
          </div>
        ) : (
          <div className="lock">
            <h2>🔒 Mentor locked</h2>
            <p>
              You are <strong>{Math.ceil(delta)}</strong> points away from unlocking a 1-on-1
              session with a Tikal Expert. Review the targeted improvements below and try again.
            </p>
          </div>
        )}
      </header>

      <Panel icon="🗣️" title="Voice & Delivery" score={report.voice_score} insights={byCat("voice")} />
      <Panel icon="🎥" title="Body Language & Camera" score={report.body_score} insights={byCat("body")} />
      <Panel icon="🖼️" title="Slide Quality" score={report.slide_score} insights={byCat("slide")} />
      <Panel icon="🧠" title="Technical Content" score={report.content_score} insights={byCat("content")} />
      <p className="disclaimer">
        Content accuracy powered by AI training data. May not reflect features released after the
        model's training cutoff.
      </p>
    </div>
  );
}
