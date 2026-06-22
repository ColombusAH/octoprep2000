import { useRouterState } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import { Atmosphere } from "~/components/chrome/Atmosphere";
import { WalletProvider } from "~/lib/wallet";
import { Sidebar } from "./Sidebar";

/** Plays once per hard page load, never blocks interaction, skipped under reduced motion. */
function BootFlash() {
  const [show, setShow] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setShow(false), 650);
    return () => clearTimeout(t);
  }, []);
  if (!show) return null;
  return (
    <div
      className="boot-bars pointer-events-none fixed inset-0 z-[200] flex motion-reduce:hidden"
      aria-hidden="true"
    >
      {["#FFFFFF", "#4DD4CC", "#FF7A1A", "#060D1A"].map((c) => (
        <span key={c} className="h-full flex-1" style={{ background: c }} />
      ))}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <WalletProvider>
      <BootFlash />
      <Atmosphere />
      <div className="relative z-10 flex h-screen overflow-hidden">
        <Sidebar />
        <main className="relative flex-1 overflow-y-auto">
          <div
            key={pathname}
            className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:ease-[var(--ease-standard)]"
          >
            {children}
          </div>
        </main>
      </div>
    </WalletProvider>
  );
}
