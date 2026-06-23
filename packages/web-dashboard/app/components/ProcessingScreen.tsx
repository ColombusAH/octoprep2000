import { useEffect, useRef, useState, type RefObject } from "react";
import { Mic, Camera, Image as ImageIcon, Brain, CheckCircle2 } from "lucide-react";
import { cn } from "~/lib/utils";
import { CornerBrackets } from "~/components/chrome/CornerBrackets";

type StageKey = "voice" | "body" | "slide" | "content";

type Stage = {
  key: StageKey;
  label: string;
  icon: typeof Mic;
  threshold: number;
};

const STAGES: Stage[] = [
  { key: "voice", label: "Voice", icon: Mic, threshold: 22 },
  { key: "body", label: "Body", icon: Camera, threshold: 48 },
  { key: "slide", label: "Slides", icon: ImageIcon, threshold: 72 },
  { key: "content", label: "Content", icon: Brain, threshold: 92 },
];

const STAGE_TAGLINES: Record<StageKey, string> = {
  voice: "Analyzing voice & pace…",
  body: "Scanning body language…",
  slide: "Grading slide quality…",
  content: "Verifying technical content…",
};

/** Animated teal/orange plasma glow behind the HUD — cheap canvas 2D, no WebGL. */
function usePlasmaCanvas(canvasRef: RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let raf = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, rect.width * dpr);
      canvas.height = Math.max(1, rect.height * dpr);
    };
    resize();
    window.addEventListener("resize", resize);

    const blobs = [
      { rgb: "77,212,204", phase: 0 },
      { rgb: "255,122,26", phase: 2.1 },
    ];

    const draw = (t: number) => {
      const { width: w, height: h } = canvas;
      ctx.clearRect(0, 0, w, h);
      const time = t / 1000;
      blobs.forEach((b, i) => {
        const cx = w / 2 + Math.cos(time * 0.25 + b.phase) * w * 0.18;
        const cy = h / 2 + Math.sin(time * 0.3 + b.phase) * h * 0.18;
        const r = Math.min(w, h) * (0.36 + 0.05 * Math.sin(time * 0.6 + i));
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        grad.addColorStop(0, `rgba(${b.rgb},0.16)`);
        grad.addColorStop(1, `rgba(${b.rgb},0)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
      });
      if (!reduceMotion) raf = requestAnimationFrame(draw);
    };

    if (reduceMotion) {
      draw(0);
    } else {
      raf = requestAnimationFrame(draw);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, [canvasRef]);
}

const RING_R = 80;
const RING_C = 2 * Math.PI * RING_R;

/** Big Y2K-broadcast "decoding the tape" HUD for the report-generation wait. */
export function ProcessingScreen({ complete }: { complete: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  usePlasmaCanvas(canvasRef);

  const startRef = useRef(performance.now());
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setElapsedMs(performance.now() - startRef.current), 200);
    return () => clearInterval(id);
  }, []);

  const progress = complete ? 100 : Math.min(96, 96 * (1 - Math.exp(-elapsedMs / 18000)));
  const activeStage = STAGES.find((s) => progress < s.threshold) ?? STAGES[STAGES.length - 1];
  const elapsedSeconds = Math.floor(elapsedMs / 1000);
  const mm = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
  const ss = String(elapsedSeconds % 60).padStart(2, "0");

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border border-border bg-card px-8 py-12",
        complete && "processing-complete-flash",
      )}
    >
      <CornerBrackets />
      <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 size-full opacity-80" aria-hidden="true" />

      <div className="relative z-10 flex flex-col items-center gap-7 text-center">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-teal/30 bg-teal/10 px-3 py-1 font-mono text-[10px] font-bold tracking-[0.18em] text-teal uppercase">
          <span className="rec-dot size-1.5 rounded-full bg-teal motion-reduce:opacity-100" aria-hidden="true" />
          {complete ? "Report Ready" : "Processing"}
        </div>

        <div className="relative flex size-44 items-center justify-center">
          <div
            className="absolute inset-0 rounded-full motion-safe:animate-spin motion-reduce:hidden [animation-duration:3s]"
            style={{
              background:
                "conic-gradient(from 0deg, transparent 0deg, rgba(77,212,204,0.35) 60deg, transparent 120deg)",
            }}
          />
          <span
            className="absolute inset-0 rounded-full border border-teal/30 motion-safe:animate-[sonarPing_2.4s_ease-out_infinite] motion-reduce:hidden"
            aria-hidden="true"
          />
          <span
            className="absolute inset-0 rounded-full border border-orange/20 motion-safe:animate-[sonarPing_2.4s_ease-out_infinite_1.2s] motion-reduce:hidden"
            aria-hidden="true"
          />

          <svg width={176} height={176} className="-rotate-90">
            <circle cx={88} cy={88} r={RING_R} fill="none" stroke="var(--border)" strokeWidth={6} />
            <circle
              cx={88}
              cy={88}
              r={RING_R}
              fill="none"
              stroke="var(--orange)"
              strokeWidth={6}
              strokeLinecap="round"
              strokeDasharray={RING_C}
              strokeDashoffset={RING_C * (1 - progress / 100)}
              style={{ filter: "drop-shadow(0 0 6px var(--orange))" }}
              className="transition-[stroke-dashoffset] duration-300 ease-[var(--ease-standard)] motion-reduce:transition-none"
            />
          </svg>
          <div className="absolute flex flex-col items-center">
            <span className="font-mono text-4xl font-bold text-pearl">{Math.round(progress)}%</span>
            <span className="mt-1 font-mono text-[10px] tracking-widest text-ash">
              {mm}:{ss}
            </span>
          </div>
        </div>

        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-pearl">
            {complete ? "Tape Decoded" : "Analyzing Tape…"}
          </h2>
          <p
            key={activeStage.key}
            className="mt-1.5 font-mono text-xs tracking-[0.14em] text-teal uppercase motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300"
          >
            {complete ? "Cueing up your scored report." : STAGE_TAGLINES[activeStage.key]}
          </p>
        </div>

        <div className="flex w-full max-w-sm items-center justify-between gap-2">
          {STAGES.map((stage) => {
            const done = complete || progress >= stage.threshold;
            const active = !done && stage.key === activeStage.key;
            const Icon = stage.icon;
            return (
              <div key={stage.key} className="flex flex-1 flex-col items-center gap-1.5">
                <div
                  className={cn(
                    "flex size-9 items-center justify-center rounded-full border",
                    done
                      ? "border-green/40 bg-green/10 text-green"
                      : active
                        ? "border-teal/50 bg-teal/10 text-teal"
                        : "border-border text-ash/50",
                  )}
                >
                  {done ? (
                    <CheckCircle2 className="size-4" aria-hidden="true" />
                  ) : (
                    <Icon className={cn("size-4", active && "motion-safe:animate-pulse")} aria-hidden="true" />
                  )}
                </div>
                <span
                  className={cn(
                    "font-mono text-[9px] tracking-wide uppercase",
                    done ? "text-green" : active ? "text-teal" : "text-ash/50",
                  )}
                >
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
