import { useEffect, useState } from 'react';

import { IoTHealthResponse } from '../types/iot';
import { IOT_HEALTH_URL } from '../config/api';

interface UseIoTHealthResult {
  data: IoTHealthResponse | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useIoTHealth(): UseIoTHealthResult {
  const [data, setData] = useState<IoTHealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch(IOT_HEALTH_URL);
        if (!res.ok) {
          throw new Error(`Request failed with status ${res.status}`);
        }
        const json = (await res.json()) as IoTHealthResponse;
        if (isMounted) {
          setData(json);
        }
      } catch (err) {
        if (isMounted) {
          setError(err as Error);
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
  }, [refreshIndex]);

  const refetch = () => setRefreshIndex((idx) => idx + 1);

  return { data, isLoading, error, refetch };
}
