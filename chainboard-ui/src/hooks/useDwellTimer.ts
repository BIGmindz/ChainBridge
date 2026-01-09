// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P21-FRICTION — Dwell Timer Hook
// Lane 9 (UX / GID-SONNY) Implementation
// Governance Tier: LAW
// Invariant: SPEED_IS_NEGLIGENCE | MINIMUM_REVIEW_TIME | FAIL_CLOSED
// ═══════════════════════════════════════════════════════════════════════════════
/**
 * Cognitive Friction: Dwell Timer Hook
 * 
 * This hook enforces minimum "dwell time" before critical actions can be taken.
 * Speed is negligence - operators must spend adequate time reviewing before
 * approving or executing destructive actions.
 * 
 * Constitutional Mandate (LAW-EAP-001):
 * - LAW tier actions: 5000ms minimum dwell
 * - POLICY tier actions: 3000ms minimum dwell
 * - GUIDANCE tier actions: 2000ms minimum dwell
 * - OPERATIONAL tier actions: 1000ms minimum dwell
 * 
 * The timer only starts when content becomes visible, preventing pre-loading exploits.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type GovernanceTier = 'LAW' | 'POLICY' | 'GUIDANCE' | 'OPERATIONAL';

export interface DwellTimerState {
  /** Whether the minimum dwell time has been satisfied */
  satisfied: boolean;
  /** Time remaining in milliseconds (0 if satisfied) */
  remainingMs: number;
  /** Time elapsed in milliseconds */
  elapsedMs: number;
  /** Required dwell time in milliseconds */
  requiredMs: number;
  /** Progress percentage (0-100) */
  progress: number;
  /** Human-readable time remaining (e.g., "2.5s") */
  remainingDisplay: string;
  /** Whether the timer is currently running */
  isRunning: boolean;
}

export interface UseDwellTimerOptions {
  /** Governance tier determines required dwell time */
  tier: GovernanceTier;
  /** Optional custom dwell time in ms (overrides tier default) */
  customDwellMs?: number;
  /** Callback when dwell requirement is satisfied */
  onSatisfied?: () => void;
  /** Whether to auto-start the timer (default: true) */
  autoStart?: boolean;
  /** Interval for timer updates in ms (default: 100) */
  updateInterval?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

/** Dwell times by governance tier (in milliseconds) */
export const DWELL_TIMES: Record<GovernanceTier, number> = {
  LAW: 5000,        // 5 seconds - critical governance actions
  POLICY: 3000,     // 3 seconds - policy decisions
  GUIDANCE: 2000,   // 2 seconds - guidance updates
  OPERATIONAL: 1000 // 1 second  - operational tasks
};

/** Minimum allowed dwell time (safety floor) */
const MIN_DWELL_MS = 500;

// ═══════════════════════════════════════════════════════════════════════════════
// HOOK
// ═══════════════════════════════════════════════════════════════════════════════

export function useDwellTimer(options: UseDwellTimerOptions): DwellTimerState & {
  /** Start/restart the timer */
  start: () => void;
  /** Reset the timer to initial state */
  reset: () => void;
  /** Pause the timer (preserves elapsed time) */
  pause: () => void;
  /** Resume a paused timer */
  resume: () => void;
} {
  const {
    tier,
    customDwellMs,
    onSatisfied,
    autoStart = true,
    updateInterval = 100
  } = options;

  // Calculate required dwell time
  const requiredMs = Math.max(
    customDwellMs ?? DWELL_TIMES[tier],
    MIN_DWELL_MS
  );

  // State
  const [elapsedMs, setElapsedMs] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [satisfied, setSatisfied] = useState(false);

  // Refs for interval management
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const pausedElapsedRef = useRef<number>(0);

  // Clear interval helper
  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Start timer
  const start = useCallback(() => {
    clearTimer();
    setElapsedMs(0);
    setSatisfied(false);
    pausedElapsedRef.current = 0;
    startTimeRef.current = Date.now();
    setIsRunning(true);
  }, [clearTimer]);

  // Pause timer
  const pause = useCallback(() => {
    if (isRunning && startTimeRef.current) {
      pausedElapsedRef.current = elapsedMs;
      clearTimer();
      setIsRunning(false);
    }
  }, [isRunning, elapsedMs, clearTimer]);

  // Resume timer
  const resume = useCallback(() => {
    if (!isRunning && !satisfied) {
      startTimeRef.current = Date.now();
      setIsRunning(true);
    }
  }, [isRunning, satisfied]);

  // Reset timer
  const reset = useCallback(() => {
    clearTimer();
    setElapsedMs(0);
    setSatisfied(false);
    pausedElapsedRef.current = 0;
    startTimeRef.current = null;
    setIsRunning(false);
  }, [clearTimer]);

  // Timer tick effect
  useEffect(() => {
    if (!isRunning) return;

    intervalRef.current = setInterval(() => {
      if (!startTimeRef.current) return;

      const now = Date.now();
      const currentElapsed = pausedElapsedRef.current + (now - startTimeRef.current);
      setElapsedMs(currentElapsed);

      if (currentElapsed >= requiredMs && !satisfied) {
        setSatisfied(true);
        onSatisfied?.();
      }
    }, updateInterval);

    return () => clearTimer();
  }, [isRunning, requiredMs, satisfied, onSatisfied, updateInterval, clearTimer]);

  // Auto-start effect
  useEffect(() => {
    if (autoStart) {
      start();
    }
    return () => clearTimer();
  }, [autoStart, start, clearTimer]);

  // Calculate derived values
  const remainingMs = Math.max(0, requiredMs - elapsedMs);
  const progress = Math.min(100, (elapsedMs / requiredMs) * 100);
  const remainingDisplay = remainingMs > 0 
    ? `${(remainingMs / 1000).toFixed(1)}s`
    : 'Ready';

  return {
    satisfied,
    remainingMs,
    elapsedMs,
    requiredMs,
    progress,
    remainingDisplay,
    isRunning,
    start,
    reset,
    pause,
    resume
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITY: Visibility-Aware Dwell Timer
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * A dwell timer that only runs when the element is visible.
 * Prevents pre-loading exploits where content is loaded in background.
 */
export function useVisibilityDwellTimer(
  options: UseDwellTimerOptions & { elementRef: React.RefObject<HTMLElement> }
): ReturnType<typeof useDwellTimer> {
  const { elementRef, ...timerOptions } = options;
  const timer = useDwellTimer({ ...timerOptions, autoStart: false });

  useEffect(() => {
    if (!elementRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            timer.resume();
          } else {
            timer.pause();
          }
        });
      },
      { threshold: 0.5 } // At least 50% visible
    );

    observer.observe(elementRef.current);

    return () => {
      observer.disconnect();
    };
  }, [elementRef, timer]);

  // Start on mount (paused until visible)
  useEffect(() => {
    timer.start();
    timer.pause();
  }, []);

  return timer;
}

export default useDwellTimer;
