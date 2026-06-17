import { useEffect, useState } from "react";

export type ToastEvent = {
  id: string;
  type: string;
  severity?: "LOW" | "MEDIUM" | "HIGH";
  message?: string;
  timestamp_ms?: number;
};

export function Toast({ event, onDismiss }: { event: ToastEvent; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 5000);
    return () => clearTimeout(t);
  }, [event.id, onDismiss]);

  const sevColor =
    event.severity === "HIGH" ? "#e02b2b" : event.severity === "MEDIUM" ? "#e68a00" : "#3a3a3a";

  return (
    <div className="toast" style={{ borderLeftColor: sevColor }}>
      <strong>{event.message ?? event.type}</strong>
    </div>
  );
}

export function ToastStack({ events }: { events: ToastEvent[] }) {
  const [visible, setVisible] = useState<ToastEvent[]>([]);
  useEffect(() => {
    setVisible(events.slice(-3));
  }, [events]);

  return (
    <div className="toast-stack">
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
