import { useQuery } from "@tanstack/react-query";

import {
    fetchPaymentIntents,
    fetchPaymentIntentSummary,
    type PaymentIntentListParams,
} from "../services/apiClient";

/**
 * Hook to fetch payment intents list with optional filters.
 * Polls every 15 seconds to keep Money View fresh.
 */
export function usePaymentIntents(params: PaymentIntentListParams = {}) {
  return useQuery({
    queryKey: ["payment-intents", params],
    queryFn: () => fetchPaymentIntents(params),
    refetchInterval: 15_000,
    staleTime: 10_000,
    retry: 3,
    retryDelay: 1000,
  });
}

/**
 * Hook to fetch payment intent summary KPIs.
 * Polls every 15 seconds to sync with payment intents list.
 */
export function usePaymentIntentSummary() {
  return useQuery({
    queryKey: ["payment-intents-summary"],
    queryFn: fetchPaymentIntentSummary,
    refetchInterval: 15_000,
    staleTime: 10_000,
    retry: 3,
    retryDelay: 1000,
  });
}
