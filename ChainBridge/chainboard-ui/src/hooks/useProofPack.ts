/**
 * useProofPack Hook
 *
 * Fetches ProofPack evidence bundle for a payment milestone.
 * Implements stale-while-revalidate pattern with conditional fetching.
 *
 * Pattern: Skip fetch if milestoneId is null (no milestone selected).
 */

import { useState, useEffect, useRef, useCallback } from "react";

import { ChainboardAPI } from "../core/api/client";
import { cacheStore, getCacheKey } from "../core/cache";
import type { ProofPack } from "../core/types/proofpack";

export interface UseProofPackResult {
  data: ProofPack | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch ProofPack evidence for a settlement milestone
 *
 * @param milestoneId - The milestone ID to fetch evidence for (null to skip)
 * @returns ProofPack data, loading state, error, and refetch function
 */
export function useProofPack(milestoneId: string | null): UseProofPackResult {
  const [data, setData] = useState<ProofPack | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Prevent double-fetch in React StrictMode
  const mountedRef = useRef(true);

  // Build cache key based on milestone ID
  const cacheKey = milestoneId ? getCacheKey(["proofpack", milestoneId]) : null;

  const fetchProofPack = useCallback(async (skipCache = false): Promise<void> => {
    // If no milestone selected, clear state and skip fetch
    if (!milestoneId) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    try {
      // Check cache first unless explicitly skipping
      if (!skipCache && cacheKey) {
        const cached = cacheStore.get<ProofPack>(cacheKey);
        if (cached) {
          setData(cached);
          setLoading(false);

          // If stale, trigger background refresh
          if (cacheStore.isStale(cacheKey)) {
            fetchProofPack(true).catch(console.error);
          }
          return;
        }
      }

      setLoading(true);
      const result = await ChainboardAPI.getProofPack(milestoneId);

      // Cache the result
      if (cacheKey) {
        cacheStore.set(cacheKey, result);
      }

      if (mountedRef.current) {
        setData(result);
        setError(null);
      }
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      if (mountedRef.current) {
        setError(errorObj);
        setData(null);
      }
      console.error(`Failed to fetch ProofPack for ${milestoneId}:`, errorObj);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [milestoneId, cacheKey]);

  useEffect(() => {
    mountedRef.current = true;
    fetchProofPack().catch(console.error);

    return () => {
      mountedRef.current = false;
    };
  }, [fetchProofPack]);

  const refetch = useCallback(async () => {
    await fetchProofPack(true);
  }, [fetchProofPack]);

  return {
    data,
    loading,
    error,
    refetch,
  };
}
