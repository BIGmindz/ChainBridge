// chainboard-ui/src/core/realtime/eventSource.ts
/**
 * EventSource Client
 * ==================
 *
 * Wrapper for browser EventSource API to consume SSE from Control Tower.
 */

import type { ControlTowerEvent } from "../types/realtime";

export interface EventStreamOptions {
  onEvent: (event: ControlTowerEvent) => void;
  onError?: (error: Event) => void;
}

export function createEventStreamClient(
  baseUrl: string,
  options: EventStreamOptions
): EventSource {
  const url = `${baseUrl}/api/chainboard/events/stream`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (messageEvent) => {
    try {
      const event: ControlTowerEvent = JSON.parse(messageEvent.data);
      options.onEvent(event);
    } catch (error) {
      console.error("[EventSource] Failed to parse event:", error);
    }
  };

  eventSource.onerror = (error) => {
    console.error("[EventSource] Connection error:", error);
    if (options.onError) {
      options.onError(error);
    }
  };

  return eventSource;
}
