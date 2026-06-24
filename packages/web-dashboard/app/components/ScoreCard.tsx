import { Mic, Camera, Image, Brain, Lock, LockOpen, CheckCircle2, ArrowUpCircle, VideoOff } from "lucide-react";
import { Card } from "~/components/ui/card";
import { ScoreRing, ScoreBar, scoreColor } from "~/components/ScoreRing";
import { CornerBrackets } from "~/components/chrome/CornerBrackets";
import {
  AI_DISCLAIMER,
  CATEGORY_META,
  formatInsightRefs,
  type Insight,
} from "~/lib/reportFormatting";

export type { Insight };

const CATEGORY_ICONS = {
  voice: Mic,
  body: Camera,
  slide: Image,
  content: Brain,
} as const;

export type ReportData = {
  overall_score: number;
  voice_score: number;
  body_score: number | null;
  slide_score: number;
  content_score: number;
  content_research_status?: "full" | "partial" | "skipped" | "not_applicable";
  insights: Insight[];
  mentor_unlocked: boolean;
  topic?: string;
};

function Panel({
  category,
  score,
  insights,
}: {
  category: Insight["category"];
  score: number | null;
  insights: Insight[];
}) {
  const Icon = CATEGORY_ICONS[category];
  const { title } = CATEGORY_META[category];
  const strengths = insights.filter((i) => i.type === "STRENGTH");
  const improvements = insights.filter((i) => i.type === "IMPROVEMENT");
  const notScored = score === null && insights.length === 0;

  return (
    <Card className="relative p-5">
      <CornerBrackets />
      <div className="flex items-center gap-3">
        <Icon className="size-5 text-teal" aria-hidden="true" />
        <h3 className="flex-1 font-display text-base font-bold text-pearl">{title}</h3>
        {score !== null && (
          <span className="font-mono text-sm font-semibold" style={{ color: scoreColor(score) }}>
            {Math.round(score)}/100
          </span>
        )}
      </div>
      <div className="mt-3">
        <ScoreBar score={score} />
      </div>

      {notScored ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <VideoOff className="size-4 shrink-0" aria-hidden="true" />
          <span>Not scored this session — camera was unavailable.</span>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <h4 className="font-mono text-xs font-semibold tracking-[0.14em] text-teal uppercase">
              Strengths
            </h4>
            {strengths.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">—</p>
            ) : (
              strengths.map((i, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm">
                  <CheckCircle2
                    className="mt-0.5 size-3.5 shrink-0"
                    style={{ color: "var(--green)" }}
                    aria-hidden="true"
                  />
                  <span>{i.message}</span>
                </div>
              ))
            )}
          </div>
          <div className="flex flex-col gap-2">
            <h4 className="font-mono text-xs font-semibold tracking-[0.14em] text-teal uppercase">
              Improvements
            </h4>
            {improvements.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">—</p>
            ) : (
              improvements.map((i, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm">
                  <ArrowUpCircle
                    className="mt-0.5 size-3.5 shrink-0"
                    style={{ color: "var(--amber)" }}
                    aria-hidden="true"
                  />
                  <span>
                    {i.message}
                    <span className="ml-1.5 font-mono text-xs text-muted-foreground">
                      {formatInsightRefs(i)}
                    </span>
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </Card>
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
    <div className="flex flex-col gap-4">
      <Card className="relative flex flex-col items-center gap-6 p-6 sm:flex-row sm:items-center">
        <CornerBrackets />
        <ScoreRing score={overall} />
        {unlocked ? (
          <div className="flex flex-col items-center gap-2 text-center sm:items-start sm:text-left">
            <div className="flex items-center gap-2">
              <LockOpen className="size-4" style={{ color: "var(--green)" }} aria-hidden="true" />
              <h2 className="font-display text-lg font-bold text-pearl">Mentor unlocked</h2>
            </div>
            <a
              href={mentorBookingUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-flex items-center justify-center rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-[var(--primary-hover)]"
            >
              Book your 1-on-1 with a Tikal Expert →
            </a>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center sm:items-start sm:text-left">
            <div className="flex items-center gap-2">
              <Lock className="size-4 text-muted-foreground" aria-hidden="true" />
              <h2 className="font-display text-lg font-bold text-pearl">Mentor locked</h2>
            </div>
            <p className="max-w-md text-sm text-muted-foreground">
              You are{" "}
              <strong className="font-mono font-semibold" style={{ color: "var(--amber)" }}>
                {Math.ceil(delta)}
              </strong>{" "}
              points away from unlocking a 1-on-1 session with a Tikal Expert. Review the targeted
              improvements below and try again.
            </p>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel category="voice" score={report.voice_score} insights={byCat("voice")} />
        <Panel category="body" score={report.body_score} insights={byCat("body")} />
        <Panel category="slide" score={report.slide_score} insights={byCat("slide")} />
        <Panel category="content" score={report.content_score} insights={byCat("content")} />
      </div>

      <p className="px-1 text-xs text-muted-foreground">
        {report.content_research_status === "full"
          ? "Technical content evaluated with all configured reference sources that were attempted for this session."
          : report.content_research_status === "partial"
            ? "Reference lookup partially available — some external sources could not be reached."
            : report.content_research_status === "skipped"
              ? "Reference lookup unavailable — content scored from transcript and AI knowledge only."
              : AI_DISCLAIMER}
      </p>
    </div>
  );
}
