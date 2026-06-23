import { createFileRoute, Link } from "@tanstack/react-router";
import { Lock, LockOpen, VideoOff } from "lucide-react";
import { cn } from "~/lib/utils";

export const Route = createFileRoute("/archive")({ component: ArchivePage });

type Tape = {
  num: string;
  id: string;
  mock: string;
  topic: string;
  date: string;
  score: number;
  unlocked: boolean;
  noCamera?: boolean;
};

const TAPES: Tape[] = [
  { num: "005", id: "demo-perfect", mock: "perfect", topic: "Israeli Tech Radar Vol. 9 — Keynote Walkthrough", date: "2026-06-21", score: 96, unlocked: true },
  { num: "004", id: "demo-unlocked", mock: "unlocked", topic: "Tech Radar Voice Podcast — Season Intro", date: "2026-06-18", score: 87, unlocked: true },
  { num: "003", id: "demo-no-camera", mock: "no-camera", topic: "2026-27 Tech Trends: Agent-Oriented Design", date: "2026-06-14", score: 71, unlocked: false, noCamera: true },
  { num: "002", id: "demo-locked", mock: "locked", topic: "Tikal Meetup: Harness Engineering 101", date: "2026-06-09", score: 64, unlocked: false },
  { num: "001", id: "demo-rough-cut", mock: "rough-cut", topic: "First dry run — AI Economics talk", date: "2026-06-02", score: 41, unlocked: false },
];

function scoreTone(score: number) {
  if (score >= 80) return "text-green";
  if (score >= 60) return "text-amber";
  return "text-red";
}

function ArchivePage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-8 py-16">
      <p className="font-mono text-xs tracking-[0.2em] text-teal uppercase">Reports Archive</p>
      <h1 className="mt-3 font-display text-3xl font-bold tracking-tight text-pearl">
        Tape Rack
      </h1>
      <p className="mt-3 max-w-xl text-sm text-muted-foreground">
        Every rehearsal you've logged, cued up and ready — pick a tape to replay its scored report.
      </p>

      <div className="mt-8 flex flex-col gap-3">
        {TAPES.map((tape) => (
          <Link
            key={tape.num}
            to="/session/$id/report"
            params={{ id: tape.id }}
            search={{ mock: tape.mock }}
            className="group flex items-center gap-4 rounded-lg border border-border bg-card px-5 py-4 transition-colors motion-safe:duration-150 hover:border-teal/50 hover:bg-navy-3/60"
          >
            <span className="font-mono text-xs tracking-[0.1em] text-ash">TAPE {tape.num}</span>
            <span className="h-8 w-px bg-border" aria-hidden="true" />
            <div className="flex flex-1 flex-col">
              <span className="font-display text-sm font-bold text-pearl">{tape.topic}</span>
              <span className="font-mono text-[11px] text-ash">{tape.date}</span>
            </div>
            {tape.noCamera && (
              <span className="flex items-center gap-1 font-mono text-[10px] tracking-wide text-ash">
                <VideoOff className="size-3" aria-hidden="true" />
                NO CAM
              </span>
            )}
            <span className={cn("font-mono text-sm font-bold", scoreTone(tape.score))}>
              {tape.score}/100
            </span>
            {tape.unlocked ? (
              <LockOpen className="size-4 text-green" aria-hidden="true" />
            ) : (
              <Lock className="size-4 text-muted-foreground" aria-hidden="true" />
            )}
          </Link>
        ))}
      </div>
    </main>
  );
}
