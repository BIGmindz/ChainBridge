import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import {
    fetchEventFeed,
    fetchEventsHeartbeat,
    type EventFeedParams,
    type EventFeedResponse,
    type EventsHeartbeatResponse,
} from "../services/apiClient";

export interface UseEventsFeedOptions {
  limit?: number;
  paymentIntentId?: string;
  shipmentId?: string;
}

export function useEventsFeed(options: UseEventsFeedOptions = {}) {
  const { limit = 25, paymentIntentId, shipmentId } = options;

  return useInfiniteQuery<EventFeedResponse, Error>({
    queryKey: [
      "eventsFeed",
      {
        limit,
        paymentIntentId,
        shipmentId,
      },
    ],
    queryFn: ({ pageParam }) => {
      const feedParams: EventFeedParams = {
        limit,
        cursor: (pageParam as string | null) ?? null,
        payment_intent_id: paymentIntentId,
        shipmentId: shipmentId,
      };

      return fetchEventFeed(feedParams);
    },
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    refetchInterval: 30_000,
    staleTime: 30_000,
    initialPageParam: null,
  });
}

export function useEventsHeartbeat() {
  return useQuery<EventsHeartbeatResponse, Error>({
    queryKey: ["eventsHeartbeat"],
    queryFn: fetchEventsHeartbeat,
    refetchInterval: 30_000,
    staleTime: 30_000,
  });
}
