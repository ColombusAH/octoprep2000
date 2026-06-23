import { createFileRoute } from "@tanstack/react-router";
import { Award, Flame, Lock, Mic, Sparkles, Target, Trophy, Zap } from "lucide-react";
import { cn } from "~/lib/utils";

export const Route = createFileRoute("/achievements")({ component: AchievementsPage });

const BADGES = [
  { icon: Mic, title: "First Take", desc: "Complete your first rehearsal session.", unlocked: true },
  { icon: Target, title: "Sharp Shooter", desc: "Score 80+ on Slide Quality.", unlocked: true },
  { icon: Flame, title: "On a Roll", desc: "3 sessions in one week.", unlocked: true },
  { icon: Trophy, title: "Mentor Unlocked", desc: "Score 80+ overall.", unlocked: true },
  { icon: Zap, title: "No Filler", desc: "Zero filler-word flags in a session.", unlocked: false },
  { icon: Sparkles, title: "Perfect Take", desc: "Score 95+ overall.", unlocked: false },
];

function AchievementsPage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-8 py-16">
      <p className="font-mono text-xs tracking-[0.2em] text-teal uppercase">Demo</p>
      <h1 className="mt-3 flex items-center gap-3 font-display text-3xl font-bold tracking-tight text-pearl">
        <Award className="size-7 text-orange" aria-hidden="true" />
        Achievements
      </h1>
      <p className="mt-3 max-w-xl text-sm text-muted-foreground">
        Small wins, stacked — every badge here gets earned by showing up and doing the reps.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {BADGES.map((b) => {
          const Icon = b.unlocked ? b.icon : Lock;
          return (
            <div
              key={b.title}
              className={cn(
                "flex flex-col gap-3 rounded-xl border p-5",
                b.unlocked ? "border-orange/30 bg-orange/5" : "border-border bg-card opacity-60",
              )}
            >
              <Icon
                className={cn("size-6", b.unlocked ? "text-orange" : "text-muted-foreground")}
                aria-hidden="true"
              />
              <span className="font-display text-base font-bold text-pearl">{b.title}</span>
              <span className="text-sm text-muted-foreground">{b.desc}</span>
              <span
                className={cn(
                  "font-mono text-[10px] tracking-[0.12em] uppercase",
                  b.unlocked ? "text-green" : "text-ash",
                )}
              >
                {b.unlocked ? "Unlocked" : "Locked"}
              </span>
            </div>
          );
        })}
      </div>
    </main>
  );
}
