import { createFileRoute, Link } from "@tanstack/react-router";
import { Archive, Lock, PlayCircle, User } from "lucide-react";
import { CornerBrackets } from "~/components/chrome/CornerBrackets";

export const Route = createFileRoute("/")({ component: HomePage });

type Advisor = { name: string; specialty: string };

/**
 * Demo-only — stand-ins for the real OctoPrep2000 build team, framed as the
 * Tikal Experts you unlock a 1-on-1 with at 80+. Photos are placeholders
 * until real headshots land; swap the icon tile for a real photo per advisor then.
 */
const ADVISORS: Advisor[] = [
  { name: "Aviv", specialty: "Architecture & Delivery Coach" },
  { name: "Naor", specialty: "Body Language & Camera Presence" },
  { name: "Or Yam", specialty: "Voice & Delivery Coach" },
  { name: "Din", specialty: "Technical Content Accuracy" },
  { name: "Stav", specialty: "Slide Design & Clarity" },
  { name: "Avner", specialty: "Systems & Storytelling" },
  { name: "Ortal", specialty: "Audience Experience Design" },
  { name: "Lihi", specialty: "Narrative & Stage Presence" },
];

function HomePage() {
  return (
    <main className="mx-auto flex h-screen w-full max-w-5xl flex-col justify-center overflow-hidden px-10 py-6">
      <p className="font-mono text-xs tracking-[0.2em] text-teal uppercase">
        Tikal Fuse Day · System Online
      </p>
      <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-balance text-pearl">
        Welcome back, Lior.
      </h1>
      <p className="mt-2 max-w-xl text-sm text-muted-foreground">
        Your rehearsal deck is standing by. Start a session to get a scored report, or pull up
        a past run from the archive.
      </p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <Link
          to="/start"
          className="group relative flex flex-col gap-2 overflow-hidden rounded-xl border border-border bg-card p-4 transition-colors motion-safe:duration-200 hover:border-orange/50"
        >
          <CornerBrackets className="opacity-0 transition-opacity motion-safe:duration-200 group-hover:opacity-100" />
          <PlayCircle className="size-5 text-orange" aria-hidden="true" />
          <span className="font-display text-base font-bold text-pearl">Start Session</span>
          <span className="text-xs text-muted-foreground">
            Upload a deck, rehearse live, get your 4-vector score.
          </span>
        </Link>

        <Link
          to="/archive"
          className="group relative flex flex-col gap-2 overflow-hidden rounded-xl border border-border bg-card p-4 transition-colors motion-safe:duration-200 hover:border-teal/50"
        >
          <CornerBrackets className="opacity-0 transition-opacity motion-safe:duration-200 group-hover:opacity-100" />
          <Archive className="size-5 text-teal" aria-hidden="true" />
          <span className="font-display text-base font-bold text-pearl">Reports Archive</span>
          <span className="text-xs text-muted-foreground">
            Browse past rehearsals and revisit their scored reports.
          </span>
        </Link>
      </div>

      <div className="mt-6">
        <p className="font-mono text-xs tracking-[0.2em] text-teal uppercase">Unlock Tier</p>
        <h2 className="mt-1 font-display text-xl font-bold tracking-tight text-pearl">
          Your Tikal Expert Advisors
        </h2>
        <p className="mt-1 max-w-xl text-xs text-muted-foreground">
          Score 80+ overall to unlock a live 1-on-1 session with any advisor below.
        </p>

        <div className="mt-3 grid grid-cols-4 gap-2 sm:grid-cols-8">
          {ADVISORS.map((advisor) => (
            <div
              key={advisor.name}
              className="group relative flex flex-col items-center gap-1.5 overflow-hidden rounded-xl border border-border bg-card px-2 py-3 text-center transition-colors motion-safe:duration-200 hover:border-teal/50"
            >
              <CornerBrackets className="opacity-0 transition-opacity motion-safe:duration-200 group-hover:opacity-100" />
              <div className="relative flex size-11 shrink-0 items-center justify-center rounded-full border border-dashed border-teal/50 bg-teal/10 text-teal">
                <User className="size-4" aria-hidden="true" />
                <span className="absolute -right-1 -bottom-1 flex size-4 items-center justify-center rounded-full border border-border bg-navy text-ash">
                  <Lock className="size-2" aria-hidden="true" />
                </span>
              </div>
              <span className="font-display text-xs font-bold text-pearl">{advisor.name}</span>
              <span className="font-mono text-[9px] leading-tight tracking-wide text-ash">
                {advisor.specialty}
              </span>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
