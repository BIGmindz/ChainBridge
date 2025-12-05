import { useEffect, useState } from 'react';

import type { RiskSnapshot } from '../types/chainpay';
import { operatorRiskSnapshotUrl } from '../config/api';

interface UseRiskSnapshotResult {
  data: RiskSnapshot | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useRiskSnapshot(intentId: string | null): UseRiskSnapshotResult {
  const [data, setData] = useState<RiskSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    if (!intentId) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    let isMounted = true;

    async function fetchData() {
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch(operatorRiskSnapshotUrl(intentId));
        if (!res.ok) {
          throw new Error(`Request failed with status ${res.status}`);
        }
        const json = (await res.json()) as RiskSnapshot;
        if (isMounted) {
          setData(json);
        }
      } catch (err) {
        if (isMounted) {
          setError(err as Error);
          setData(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [intentId, refreshIndex]);

  const refetch = () => setRefreshIndex((i) => i + 1);

  return { data, isLoading, error, refetch };
}
