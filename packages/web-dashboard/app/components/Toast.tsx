import { useEffect, useState } from "react";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";
import { cn } from "~/lib/utils";

export type ToastEvent = {
  id: string;
  type: string;
  severity?: "LOW" | "MEDIUM" | "HIGH";
  message?: string;
  timestamp_ms?: number;
};

const severityConfig = {
  HIGH: { Icon: AlertTriangle, className: "text-destructive" },
  MEDIUM: { Icon: AlertCircle, className: "text-[var(--amber)]" },
  LOW: { Icon: Info, className: "text-muted-foreground" },
} as const;

export function Toast({ event, onDismiss }: { event: ToastEvent; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 5000);
    return () => clearTimeout(t);
  }, [event.id, onDismiss]);

  const { Icon, className } = severityConfig[event.severity ?? "LOW"];

  return (
    <div
      role="status"
      className="flex min-w-60 items-center gap-2.5 rounded-lg border border-border bg-card px-4 py-3 text-sm text-card-foreground motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-right-8 motion-safe:duration-300 motion-safe:ease-out"
    >
      <Icon className={cn("size-4 shrink-0", className)} aria-hidden="true" />
      <strong className="font-medium">{event.message ?? event.type}</strong>
    </div>
  );
}

export function ToastStack({ events }: { events: ToastEvent[] }) {
  const [visible, setVisible] = useState<ToastEvent[]>([]);
  useEffect(() => {
    setVisible(events.slice(-3));
  }, [events]);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
      {visible.map((e) => (
        <Toast
          key={e.id}
          event={e}
          onDismiss={() => setVisible((v) => v.filter((x) => x.id !== e.id))}
        />
      ))}
    </div>
  );
}
