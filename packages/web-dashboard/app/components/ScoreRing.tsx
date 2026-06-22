import { useEffect, useState } from "react";

const STROKE = 8;

export function scoreColor(score: number): string {
  if (score >= 80) return "var(--green)";
  if (score >= 60) return "var(--amber)";
  return "var(--red)";
}

/** Hero score readout — DESIGN.md "Score Ring" signature component. */
export function ScoreRing({ score, size = 160 }: { score: number; size?: number }) {
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const radius = (size - STROKE) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - (drawn ? score : 0) / 100);
  const color = scoreColor(score);

  return (
    <div
      className="relative inline-flex shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth={STROKE}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-[600ms] ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono text-5xl font-bold leading-none tracking-tight" style={{ color }}>
          {Math.round(score)}
        </span>
        <span className="mt-1.5 text-xs text-muted-foreground">/ 100</span>
      </div>
    </div>
  );
}

/** Sub-category bar — DESIGN.md "bar list" for the 4 vector scores. */
export function ScoreBar({ score }: { score: number | null }) {
  if (score === null) {
    return <div className="h-1.5 w-full rounded-full bg-muted" />;
  }
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <div
        className="h-full rounded-full transition-[width] duration-700 ease-out motion-reduce:transition-none"
        style={{ width: `${Math.round(score)}%`, backgroundColor: scoreColor(score) }}
      />
    </div>
  );
}
