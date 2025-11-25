/**
 * useOperatorEvents - Real-time operator event stream
 *
 * Polls /operator/events/stream every 10s and pushes new events to toast notifications.
 * Color-coded by severity:
 * - ❗ Red: PAYMENT_ERROR
 * - ⚠ Yellow: SLA_DEGRADED
 * - 🔔 Blue: INFO
 * - 💸 Green: PAYMENT_CONFIRMED
 */

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { fetchOperatorEventsStream } from "../services/operatorApi";
import type { OperatorEvent } from "../types/backend";

interface UseOperatorEventsOptions {
  onNewEvent?: (event: OperatorEvent) => void;
  enabled?: boolean;
}

/**
 * Hook to poll operator event stream and trigger toast notifications
 */
export function useOperatorEvents(options: UseOperatorEventsOptions = {}) {
  const { onNewEvent, enabled = true } = options;
  const lastEventIdRef = useRef<string | undefined>(undefined);

  const { data, isLoading, error } = useQuery({
    queryKey: ["operatorEventsStream", lastEventIdRef.current],
    queryFn: () =>
      fetchOperatorEventsStream({
        since_eventId: lastEventIdRef.current,
        limit: 50,
      }),
    refetchInterval: 10_000, // Poll every 10s
    staleTime: 8_000,
    enabled,
    retry: 2,
    retryDelay: 3000,
  });

  // Process new events
  useEffect(() => {
    if (!data || !data.events.length) return;

    // Update last event ID
    if (data.last_eventId) {
      lastEventIdRef.current = data.last_eventId;
    }

    // Trigger callback for each new event
    if (onNewEvent) {
      data.events.forEach((event) => {
        onNewEvent(event);
      });
    }
  }, [data, onNewEvent]);

  return {
    events: data?.events ?? [],
    hasMore: data?.has_more ?? false,
    isLoading,
    error,
  };
}

/**
 * Get toast variant based on event severity
 * Maps to NotificationContext types: success | error | info
 */
export function getToastVariant(
  eventType: OperatorEvent["eventType"]
): "error" | "info" | "success" {
  switch (eventType) {
    case "PAYMENT_ERROR":
      return "error"; // ❗ Red
    case "SLA_DEGRADED":
      return "error"; // ⚠️ Red (no warning variant in NotificationContext)
    case "PAYMENT_CONFIRMED":
      return "success"; // 💸 Green
    case "INFO":
    default:
      return "info"; // 🔔 Blue
  }
}

/**
 * Get emoji icon for event type
 */
export function getEventIcon(eventType: OperatorEvent["eventType"]): string {
  switch (eventType) {
    case "PAYMENT_ERROR":
      return "❗";
    case "SLA_DEGRADED":
      return "⚠️";
    case "PAYMENT_CONFIRMED":
      return "💸";
    case "INFO":
    default:
      return "🔔";
  }
}
