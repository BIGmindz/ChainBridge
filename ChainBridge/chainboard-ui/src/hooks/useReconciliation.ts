import { useMutation, useQueryClient } from "@tanstack/react-query";

import { reconcilePaymentIntent, type ReconciliationPayload } from "../services/apiClient";

/**
 * Hook to trigger reconciliation for a payment intent.
 * On success, invalidates payment intents queries to refresh UI.
 */
export function useReconcilePaymentIntent() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { paymentIntentId: string; payload?: ReconciliationPayload }>({
    mutationFn: async ({ paymentIntentId, payload }) => {
      return reconcilePaymentIntent(paymentIntentId, payload);
    },
    onSuccess: () => {
      // Invalidate payment intents list to refresh UI with new reconciliation data
      queryClient.invalidateQueries({
        queryKey: ["payment-intents"],
      });
      // Also invalidate summary KPIs if present
      queryClient.invalidateQueries({
        queryKey: ["payment-intents-summary"],
      });
    },
  });
}
