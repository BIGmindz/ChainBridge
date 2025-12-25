/**
 * Governance Ledger Hook — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * React hook for fetching and polling governance ledger data.
 * All state is read-only — no mutations from UI.
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  GovernanceLedger,
  PACRegistry,
  PACRegistryEntry,
  GovernanceSummary,
  TimelineNode,
} from '../types/governanceLedger';
import {
  fetchGovernanceLedger,
  fetchPACRegistry,
  fetchPACById,
  fetchGovernanceSummary,
  ledgerToTimeline,
} from '../services/governanceLedgerApi';

const DEFAULT_POLL_INTERVAL = 30000; // 30 seconds

export interface UseGovernanceLedgerResult {
  /** Current ledger state */
  ledger: GovernanceLedger | null;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: Error | null;
  /** Refresh ledger data */
  refresh: () => Promise<void>;
  /** Timeline nodes derived from ledger */
  timeline: TimelineNode[];
}

/**
 * Hook to fetch and poll governance ledger.
 */
export function useGovernanceLedger(
  pollInterval: number = DEFAULT_POLL_INTERVAL
): UseGovernanceLedgerResult {
  const [ledger, setLedger] = useState<GovernanceLedger | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [timeline, setTimeline] = useState<TimelineNode[]>([]);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchGovernanceLedger();
      if (mountedRef.current) {
        setLedger(data);
        setTimeline(ledgerToTimeline(data.entries));
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err : new Error('Failed to fetch ledger'));
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    refresh();

    const interval = setInterval(refresh, pollInterval);

    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, [refresh, pollInterval]);

  return { ledger, loading, error, refresh, timeline };
}

export interface UsePACRegistryResult {
  /** Current registry state */
  registry: PACRegistry | null;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: Error | null;
  /** Refresh registry data */
  refresh: () => Promise<void>;
}

/**
 * Hook to fetch and poll PAC registry.
 */
export function usePACRegistry(
  pollInterval: number = DEFAULT_POLL_INTERVAL
): UsePACRegistryResult {
  const [registry, setRegistry] = useState<PACRegistry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchPACRegistry();
      if (mountedRef.current) {
        setRegistry(data);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err : new Error('Failed to fetch registry'));
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    refresh();

    const interval = setInterval(refresh, pollInterval);

    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, [refresh, pollInterval]);

  return { registry, loading, error, refresh };
}

export interface UsePACDetailResult {
  /** PAC entry */
  pac: PACRegistryEntry | null;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: Error | null;
  /** Not found state */
  notFound: boolean;
  /** Refresh data */
  refresh: () => Promise<void>;
  /** Timeline nodes for this PAC */
  timeline: TimelineNode[];
}

/**
 * Hook to fetch single PAC details.
 */
export function usePACDetail(pacId: string | null): UsePACDetailResult {
  const [pac, setPac] = useState<PACRegistryEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [timeline, setTimeline] = useState<TimelineNode[]>([]);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    if (!pacId) {
      setPac(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setNotFound(false);
      const data = await fetchPACById(pacId);
      if (mountedRef.current) {
        if (data) {
          setPac(data);
          setTimeline(ledgerToTimeline(data.ledger_entries));
        } else {
          setNotFound(true);
        }
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err : new Error('Failed to fetch PAC'));
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [pacId]);

  useEffect(() => {
    mountedRef.current = true;
    refresh();

    return () => {
      mountedRef.current = false;
    };
  }, [refresh]);

  return { pac, loading, error, notFound, refresh, timeline };
}

export interface UseGovernanceSummaryResult {
  /** Summary data */
  summary: GovernanceSummary | null;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: Error | null;
  /** Refresh data */
  refresh: () => Promise<void>;
}

/**
 * Hook to fetch governance summary.
 */
export function useGovernanceSummary(
  pollInterval: number = DEFAULT_POLL_INTERVAL
): UseGovernanceSummaryResult {
  const [summary, setSummary] = useState<GovernanceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchGovernanceSummary();
      if (mountedRef.current) {
        setSummary(data);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err : new Error('Failed to fetch summary'));
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    refresh();

    const interval = setInterval(refresh, pollInterval);

    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, [refresh, pollInterval]);

  return { summary, loading, error, refresh };
}
