import { cn } from "~/lib/utils";

/** HUD-style corner accents — apply to a `relative` panel for the broadcast-chrome look. */
export function CornerBrackets({ className }: { className?: string }) {
  return (
    <div className={cn("pointer-events-none absolute inset-0", className)} aria-hidden="true">
      <span className="chrome-bracket chrome-bracket-tl" />
      <span className="chrome-bracket chrome-bracket-tr" />
      <span className="chrome-bracket chrome-bracket-bl" />
      <span className="chrome-bracket chrome-bracket-br" />
    </div>
  );
}
