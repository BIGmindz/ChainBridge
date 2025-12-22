import { useEffect, useState } from 'react';
import { fetchSettlementStatus, fetchChainPayAnalyticsUsdMxn, fetchUsdMxnGuardrails } from '../../api/chainpay';
import type { SettlementStatus } from '../../types/chainpay';
import type { ChainPayAnalyticsSnapshot } from '../../types/chainpayAnalytics';
import type { GuardrailStatusSnapshot } from '../../types/chainpayGuardrails';

interface UseChainPaySettlementResult {
  data: SettlementStatus | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useChainPaySettlement(shipmentId: string | null): UseChainPaySettlementResult {
  const [data, setData] = useState<SettlementStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    if (!shipmentId) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const status = await fetchSettlementStatus(shipmentId);
        if (!cancelled) {
          setData(status);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err as Error);
          setData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [shipmentId, refreshIndex]);

  const refetch = () => setRefreshIndex((i) => i + 1);

  return { data, loading, error, refetch };
}

interface UseChainPayAnalyticsResult {
  data: ChainPayAnalyticsSnapshot | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useChainPayAnalyticsUsdMxn(): UseChainPayAnalyticsResult {
  const [data, setData] = useState<ChainPayAnalyticsSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const snapshot = await fetchChainPayAnalyticsUsdMxn();
        if (!cancelled) {
          setData(snapshot);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err as Error);
          setData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [refreshIndex]);

  const refetch = () => setRefreshIndex((i) => i + 1);

  return { data, loading, error, refetch };
}

interface UseGuardrailsResult {
  data: GuardrailStatusSnapshot | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useUsdMxnGuardrails(): UseGuardrailsResult {
  const [data, setData] = useState<GuardrailStatusSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const snapshot = await fetchUsdMxnGuardrails();
        if (!cancelled) {
          setData(snapshot);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err as Error);
          setData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [refreshIndex]);

  const refetch = () => setRefreshIndex((i) => i + 1);

  return { data, loading, error, refetch };
}
