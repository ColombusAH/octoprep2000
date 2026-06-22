import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

/**
 * Demo-only gamified wallet for the dashboard shell. Local React state, no
 * persistence, no backend — deliberately mock per the Y2K dashboard pivot.
 * Initial value is a fixed constant (not random) so SSR and client render match.
 */
type WalletContextValue = {
  points: number;
  justIncreased: boolean;
  addPoints: (amount: number) => void;
};

const WalletContext = createContext<WalletContextValue | null>(null);

const STARTING_BALANCE = 1240;

export function WalletProvider({ children }: { children: ReactNode }) {
  const [points, setPoints] = useState(STARTING_BALANCE);
  const [justIncreased, setJustIncreased] = useState(false);
  const flashTimer = useRef<ReturnType<typeof setTimeout>>();

  const addPoints = useCallback((amount: number) => {
    setPoints((p) => p + amount);
    setJustIncreased(true);
    clearTimeout(flashTimer.current);
    flashTimer.current = setTimeout(() => setJustIncreased(false), 900);
  }, []);

  return (
    <WalletContext.Provider value={{ points, justIncreased, addPoints }}>
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useWallet must be used within WalletProvider");
  return ctx;
}
