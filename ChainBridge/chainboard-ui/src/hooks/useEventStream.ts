// chainboard-ui/src/hooks/useEventStream.ts
/**
 * useEventStream Hook
 * ===================
 *
 * React hook for consuming real-time SSE events from Control Tower.
 */

import { useEffect, useRef } from "react";

import { createEventStreamClient } from "../core/realtime/eventSource";
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

/**
 * Hook to subscribe to real-time SSE events.
 *
 * @param options Configuration options
 * @returns void
 *
 * @example
 * ```tsx
 * useEventStream({
 *   enabled: true,
 *   filter: { types: ["alert_updated"] },
 *   onEvent: (event) => {
 *     mutate(); // Refetch SWR cache
 *   }
 * });
 * ```
 */
export function useEventStream(options: UseEventStreamOptions): void {
  const { enabled = true, filter, onEvent } = options;
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

    // Create EventSource
    eventSourceRef.current = createEventStreamClient(baseUrl, {
      onEvent: (event) => {
        // Apply filter if provided
        if (filter) {
          if (filter.types && !filter.types.includes(event.type)) {
            return;
          }
          if (filter.sources && !filter.sources.includes(event.source)) {
            return;
          }
          if (filter.keys && !filter.keys.includes(event.key)) {
            return;
          }
        }

        // Pass through to callback
        onEvent(event);
      },
      onError: (error) => {
        console.error("[useEventStream] Error:", error);
      },
    });

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [enabled, filter, onEvent]);
}
