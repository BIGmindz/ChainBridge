/**
 * Demo Engine Hook
 *
 * Centralized demo state management with step navigation and hero shipment selection.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { DEMO_SCENARIOS } from "./registry";
import type { DemoScenario, DemoStep } from "./types";

export interface DemoState {
  activeScenario?: DemoScenario;
  currentStep?: DemoStep;
  currentIndex: number;
  isRunning: boolean;
}

export interface UseDemoEngineResult {
  state: DemoState;
  startScenario: (id: string) => void;
  stop: () => void;
  next: () => void;
  prev: () => void;
}

/**
 * Hook for managing demo walkthrough state and navigation
 */
export function useDemoEngine(): UseDemoEngineResult {
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);

  const activeScenario = useMemo(
    () => DEMO_SCENARIOS.find((s) => s.id === scenarioId),
    [scenarioId]
  );

  const steps = activeScenario?.steps ?? [];
  const currentStep = steps[stepIndex];

  const startScenario = useCallback((id: string) => {
    setScenarioId(id);
    setStepIndex(0);
    setIsRunning(true);
  }, []);

  const stop = useCallback(() => {
    setIsRunning(false);
    setScenarioId(null);
    setStepIndex(0);
  }, []);

  const next = useCallback(() => {
    if (!activeScenario) return;
    setStepIndex((idx) => Math.min(idx + 1, activeScenario.steps.length - 1));
  }, [activeScenario]);

  const prev = useCallback(() => {
    setStepIndex((idx) => Math.max(idx - 1, 0));
  }, []);

  // Optional: persist demo state to sessionStorage for page reloads
  useEffect(() => {
    if (!isRunning) return;
    // Could add sessionStorage persistence here
  }, [isRunning, scenarioId, stepIndex]);

  const state: DemoState = {
    activeScenario,
    currentStep,
    currentIndex: stepIndex,
    isRunning,
  };

  return {
    state,
    startScenario,
    stop,
    next,
    prev,
  };
}
