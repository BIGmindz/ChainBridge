/**
 * useGovernanceState Hook — PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 *
 * React hook for governance state management.
 * Provides real-time governance context to UI components.
 *
 * Features:
 * - Auto-polling for state updates (configurable interval)
 * - Error state handling
 * - Loading state management
 * - Derived state helpers
 *
 * CONSTRAINTS:
 * - Read-only — NO state mutation
 * - All state from backend
 * - Errors surfaced, never hidden
 *
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  fetchGovernanceContext,
  isSystemBlocked,
  hasActiveEscalation,
  getHighestEscalationLevel,
} from '../services/governanceStateApi';
import type {
  GovernanceContext,
  GovernanceUIState,
  EscalationLevel,
} from '../types/governanceState';
import {
  areActionsEnabled,
  isBannerRequired,
  getAllowedAction,
  GOVERNANCE_UI_RULES,
} from '../types/governanceState';

/**
 * Default polling interval in milliseconds.
 */
const DEFAULT_POLL_INTERVAL = 5000;

/**
 * Hook return type.
 */
export interface UseGovernanceStateResult {
  /** Current governance context */
  context: GovernanceContext | null;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: Error | null;
  /** Current governance UI state */
  state: GovernanceUIState;
  /** Current escalation level */
  escalationLevel: EscalationLevel;
  /** Whether system is blocked */
  isBlocked: boolean;
  /** Whether escalation is pending */
  hasEscalation: boolean;
  /** Whether actions are enabled */
  actionsEnabled: boolean;
  /** Whether banner is required */
  bannerRequired: boolean;
  /** Allowed action if any */
  allowedAction: string | null;
  /** Banner severity */
  bannerSeverity: 'info' | 'warning' | 'error' | 'critical';
  /** Manual refresh function */
  refresh: () => Promise<void>;
}

/**
 * Hook for governance state management.
 *
 * @param pollInterval - Polling interval in milliseconds (default 5000)
 * @param enabled - Whether to enable polling (default true)
 */
export function useGovernanceState(
  pollInterval: number = DEFAULT_POLL_INTERVAL,
  enabled: boolean = true
): UseGovernanceStateResult {
  const [context, setContext] = useState<GovernanceContext | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Fetch governance context from backend.
   */
  const fetchContext = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchGovernanceContext();
      setContext(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Manual refresh function.
   */
  const refresh = useCallback(async () => {
    setIsLoading(true);
    await fetchContext();
  }, [fetchContext]);

  /**
   * Initial fetch and polling setup.
   */
  useEffect(() => {
    if (!enabled) return;

    // Initial fetch
    fetchContext();

    // Set up polling
    const interval = setInterval(fetchContext, pollInterval);

    return () => clearInterval(interval);
  }, [enabled, pollInterval, fetchContext]);

  /**
   * Derived state values.
   */
  const state = context?.state ?? 'OPEN';
  const escalationLevel = context ? getHighestEscalationLevel(context) : 'NONE';
  const isBlocked = context ? isSystemBlocked(context) : false;
  const hasEscalation = context ? hasActiveEscalation(context) : false;
  const actionsEnabled = areActionsEnabled(state);
  const bannerRequired = isBannerRequired(state);
  const allowedAction = getAllowedAction(state);
  const bannerSeverity = GOVERNANCE_UI_RULES[state].banner_severity;

  return useMemo(() => ({
    context,
    isLoading,
    error,
    state,
    escalationLevel,
    isBlocked,
    hasEscalation,
    actionsEnabled,
    bannerRequired,
    allowedAction,
    bannerSeverity,
    refresh,
  }), [
    context,
    isLoading,
    error,
    state,
    escalationLevel,
    isBlocked,
    hasEscalation,
    actionsEnabled,
    bannerRequired,
    allowedAction,
    bannerSeverity,
    refresh,
  ]);
}

/**
 * Hook for checking if a specific action is allowed.
 *
 * @param actionType - The action type to check
 */
export function useActionAllowed(actionType: string): boolean {
  const { actionsEnabled, allowedAction } = useGovernanceState();

  // Actions enabled globally, or this specific action is allowed
  return actionsEnabled || allowedAction === actionType;
}

/**
 * Hook for getting governance block information.
 */
export function useGovernanceBlocks() {
  const { context, isBlocked } = useGovernanceState();

  return useMemo(() => ({
    isBlocked,
    blocks: context?.active_blocks ?? [],
    blockCount: context?.active_blocks.length ?? 0,
    primaryBlock: context?.active_blocks[0] ?? null,
  }), [context, isBlocked]);
}

/**
 * Hook for getting escalation information.
 */
export function useGovernanceEscalations() {
  const { context, hasEscalation, escalationLevel } = useGovernanceState();

  return useMemo(() => ({
    hasEscalation,
    escalationLevel,
    escalations: context?.pending_escalations ?? [],
    escalationCount: context?.pending_escalations.length ?? 0,
    pendingEscalations: context?.pending_escalations.filter(e => e.status === 'PENDING') ?? [],
  }), [context, hasEscalation, escalationLevel]);
}
