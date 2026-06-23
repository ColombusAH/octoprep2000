import { createFileRoute } from "@tanstack/react-router";
import { Crown, Medal } from "lucide-react";
import { cn } from "~/lib/utils";
import { useWallet } from "~/lib/wallet";

export const Route = createFileRoute("/leaderboard")({ component: LeaderboardPage });

type Entrant = { name: string; score: number; sessions: number; isYou?: boolean };

// No fixed rank field — rank is always derived from score, so the board can never
// drift out of order as the live wallet balance (the YOU row) changes.
const OTHERS: Entrant[] = [
  { name: "A. DANIEL", score: 1042, sessions: 26 },
  { name: "O. NEHORAY", score: 968, sessions: 19 },
  { name: "N. BITON", score: 911, sessions: 22 },
  { name: "A. HATAB", score: 887, sessions: 14 },
  { name: "R. SPIEGEL", score: 802, sessions: 17 },
  { name: "A. MAOR", score: 749, sessions: 12 },
  { name: "N. KAUFMAN", score: 695, sessions: 9 },
];

function medalColor(rank: number) {
  if (rank === 1) return "text-amber";
  if (rank === 2) return "text-ash";
  if (rank === 3) return "text-orange-d";
  return "text-ash/40";
}

function LeaderboardPage() {
  const { points } = useWallet();
  const you: Entrant = { name: "LIOR KANFI (YOU)", score: points, sessions: 8, isYou: true };
  const ranked = [...OTHERS, you]
    .sort((a, b) => b.score - a.score)
    .map((entrant, i) => ({ ...entrant, rank: i + 1 }));

  return (
    <main className="mx-auto w-full max-w-3xl px-8 py-16">
      <p className="font-mono text-xs tracking-[0.2em] text-teal uppercase">Demo</p>
      <h1 className="mt-3 flex items-center gap-3 font-display text-3xl font-bold tracking-tight text-pearl">
        <Crown className="size-7 text-amber" aria-hidden="true" />
        Tape Credits Leaderboard
      </h1>
      <p className="mt-3 max-w-xl text-sm text-muted-foreground">
        Every Tape Credit on this board was earned the same way — one rehearsal at a time. Here's who's leading the season.
      </p>

      <div className="mt-8 flex flex-col gap-2">
        {ranked.map((r) => (
          <div
            key={r.rank}
            className={cn(
              "flex items-center gap-4 rounded-lg border px-5 py-3.5",
              r.isYou ? "border-orange/40 bg-orange/5" : "border-border bg-card",
            )}
          >
            <Medal className={cn("size-5 shrink-0", medalColor(r.rank))} aria-hidden="true" />
            <span className="w-6 font-mono text-sm text-ash">#{r.rank}</span>
            <span className="flex-1 font-display text-sm font-bold text-pearl">{r.name}</span>
            <span className="font-mono text-xs text-ash">{r.sessions} sessions</span>
            <span className="font-mono text-sm font-bold text-orange">{r.score.toLocaleString()} CR</span>
          </div>
        ))}
      </div>
    </main>
  );
}
