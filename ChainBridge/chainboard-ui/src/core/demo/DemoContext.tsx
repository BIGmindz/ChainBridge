/**
 * Demo Context Provider
 *
 * Global demo state management for guided walkthroughs.
 */

import React, { createContext, useContext } from "react";

import { useDemoEngine, type DemoState } from "./engine";

interface DemoContextValue {
  state: DemoState;
  startScenario: (id: string) => void;
  stop: () => void;
  next: () => void;
  prev: () => void;
}

const DemoContext = createContext<DemoContextValue | undefined>(undefined);

export const DemoProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const engine = useDemoEngine();

  return (
    <DemoContext.Provider value={engine}>{children}</DemoContext.Provider>
  );
};

/**
 * Hook to access demo context
 */
export function useDemo(): DemoContextValue {
  const ctx = useContext(DemoContext);
  if (!ctx) {
    throw new Error("useDemo must be used inside DemoProvider");
  }
  return ctx;
}
