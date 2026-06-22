import { Link, useRouterState } from "@tanstack/react-router";
import {
  Archive,
  Award,
  Home,
  PlayCircle,
  Settings,
  Trophy,
  User,
  Wifi,
} from "lucide-react";
import { cn } from "~/lib/utils";
import { useWallet } from "~/lib/wallet";
import octoprepLogo from "./octoprep-logo.png";

type NavItem = {
  label: string;
  to: string;
  icon: typeof Home;
  match: (pathname: string) => boolean;
  kind: "real" | "mock";
};

const NAV_ITEMS: NavItem[] = [
  { label: "Home", to: "/", icon: Home, match: (p) => p === "/", kind: "real" },
  {
    label: "Start Session",
    to: "/start",
    icon: PlayCircle,
    match: (p) => p.startsWith("/start") || p.startsWith("/session"),
    kind: "real",
  },
  {
    label: "Reports Archive",
    to: "/archive",
    icon: Archive,
    match: (p) => p.startsWith("/archive"),
    kind: "mock",
  },
  {
    label: "Leaderboard",
    to: "/leaderboard",
    icon: Trophy,
    match: (p) => p.startsWith("/leaderboard"),
    kind: "mock",
  },
  {
    label: "Achievements",
    to: "/achievements",
    icon: Award,
    match: (p) => p.startsWith("/achievements"),
    kind: "mock",
  },
  {
    label: "Settings",
    to: "/settings",
    icon: Settings,
    match: (p) => p.startsWith("/settings"),
    kind: "mock",
  },
];

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { points, justIncreased } = useWallet();

  return (
    <aside className="relative z-10 flex h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="flex flex-col gap-4 border-b border-sidebar-border px-5 py-6">
        <div className="flex items-center gap-3">
          <div
            className="flex size-11 shrink-0 items-center justify-center rounded-md border border-dashed border-teal/50 bg-teal/10 text-teal"
            aria-hidden="true"
          >
            <User className="size-5" />
          </div>
          <div className="flex flex-col">
            <span className="font-display text-sm font-bold tracking-tight text-pearl">
              LIOR KANFI
            </span>
            <span className="font-mono text-[11px] tracking-wide text-ash">FOUNDER & CEO</span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-mono text-[11px] tracking-[0.12em] text-green">
            <Wifi className="size-3.5" aria-hidden="true" />
            <span>ONLINE</span>
          </div>
          <div className="inline-flex items-center gap-1.5 rounded-full border border-orange/40 bg-orange/10 px-2.5 py-1 font-mono text-[10px] font-bold tracking-[0.1em] text-orange">
            <Award className="size-3" aria-hidden="true" />
            GOLD FOUNDER
          </div>
        </div>

        <div className="flex items-center justify-between rounded-md border border-teal/20 bg-navy-2/60 px-3 py-2">
          <span className="font-mono text-[10px] tracking-[0.14em] text-ash uppercase">
            Tape Credits
          </span>
          <span
            className={cn(
              "font-mono text-sm font-bold text-pearl transition-transform motion-safe:duration-300",
              justIncreased && "motion-safe:scale-110 text-orange",
            )}
          >
            {points.toLocaleString()}
          </span>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2.5 font-sans text-sm font-medium transition-colors motion-safe:duration-150",
                active
                  ? "bg-sidebar-accent text-pearl"
                  : "text-ash hover:bg-sidebar-accent/60 hover:text-pearl",
              )}
            >
              <Icon
                className={cn("size-4 shrink-0", active ? "text-orange" : "text-teal/70")}
                aria-hidden="true"
              />
              <span className="flex-1">{item.label}</span>
              {item.kind === "mock" && (
                <span className="font-mono text-[9px] tracking-widest text-ash">DEMO</span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center border-t border-sidebar-border px-5 py-4">
        <img src={octoprepLogo} alt="OctoPrep2000" className="h-9 w-auto shrink-0" />
      </div>
    </aside>
  );
}
