/**
 * useSettlementActions Hook
 *
 * Fetches recent settlement operator actions for audit trail display.
 * Provides refetch capability to refresh after new actions are posted.
 */

import { useEffect, useState } from "react";

import { ChainboardAPI } from "../core/api/client";
import type { SettlementActionResponse } from "../core/types/settlements";

export interface UseSettlementActionsResult {
  actions: SettlementActionResponse[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useSettlementActions(limit: number = 20): UseSettlementActionsResult {
  const [actions, setActions] = useState<SettlementActionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [version, setVersion] = useState(0); // bump to force refetch

  useEffect(() => {
    let cancelled = false;

    async function fetchActions() {
      setIsLoading(true);
      setError(null);

      try {
        const data = await ChainboardAPI.getRecentSettlementActions(limit);
        if (!cancelled) {
          setActions(data);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error("Failed to fetch settlement actions"));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchActions();

    return () => {
      cancelled = true;
    };
  }, [limit, version]);

  return {
    actions,
    isLoading,
    error,
    refetch: () => setVersion(v => v + 1),
  };
}
