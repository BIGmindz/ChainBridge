// chainboard-ui/src/hooks/useEventStream.ts
/**
 * useEventStream Hook
 * ===================
 *
 * React hook for consuming real-time SSE events from Control Tower.
 * Returns connection status for "Live" indicator display.
 */

import { useEffect, useRef, useState, useCallback } from "react";

import { config } from "../config/env";
import type { ControlTowerEvent, ControlTowerEventType } from "../core/types/realtime";

export interface UseEventStreamOptions {
  enabled?: boolean;
  filter?: {
    types?: ControlTowerEventType[];
    sources?: string[];
    keys?: string[];
  };
  onEvent: (event: ControlTowerEvent) => void;
}

export interface UseEventStreamResult {
  isConnected: boolean;
  error: string | null;
}

/**
 * Hook to subscribe to real-time SSE events.
 *
 * @param options Configuration options
 * @returns Connection status and error state
 *
 * @example
 * ```tsx
 * const { isConnected } = useEventStream({
 *   enabled: true,
 *   filter: { types: ["alert_updated"] },
 *   onEvent: (event) => {
 *     refetch(); // Refresh data
 *   }
 * });
 *
 * return isConnected && <span className="text-green-400">● Live</span>;
 * ```
 */
export function useEventStream(options: UseEventStreamOptions): UseEventStreamResult {
  const { enabled = true, filter, onEvent } = options;
  const eventSourceRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Stable callback ref to prevent reconnects on onEvent changes
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const filterRef = useRef(filter);
  filterRef.current = filter;

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const baseUrl = config.apiBaseUrl || "http://localhost:8001";
    const url = `${baseUrl}/api/chainboard/events/stream`;

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
      if (import.meta.env.DEV) {
        console.log("[useEventStream] Connected to SSE");
      }
    };

    eventSource.onmessage = (messageEvent) => {
      try {
        const event: ControlTowerEvent = JSON.parse(messageEvent.data);
        const currentFilter = filterRef.current;

        // Apply filter if provided
        if (currentFilter) {
          if (currentFilter.types && !currentFilter.types.includes(event.type)) {
            return;
          }
          if (currentFilter.sources && !currentFilter.sources.includes(event.source)) {
            return;
          }
          if (currentFilter.keys && !currentFilter.keys.includes(event.key)) {
            return;
          }
        }

        // Pass through to callback
        onEventRef.current(event);
      } catch (err) {
        console.error("[useEventStream] Failed to parse event:", err);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      setError("Connection lost");
      if (import.meta.env.DEV) {
        console.warn("[useEventStream] Connection error, will retry...");
      }
    };

    return eventSource;
  }, []);

  useEffect(() => {
    if (!enabled) {
      setIsConnected(false);
      return;
    }

    const eventSource = connect();

    // Cleanup on unmount
    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    };
  }, [enabled, connect]);

  return { isConnected, error };
}
