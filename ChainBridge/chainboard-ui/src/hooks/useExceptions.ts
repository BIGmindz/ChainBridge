/**
 * useExceptions Hook
 *
 * React Query hooks for exception data fetching in The OC.
 * Provides loading states, error handling, and cache management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import {
  fetchExceptions,
  fetchExceptionDetail,
  fetchExceptionStats,
  fetchDecisionRecords,
  fetchShipmentRiskSummary,
  fetchShipmentSettlementSummary,
  updateExceptionStatus,
} from "../services/exceptionsApi";
import type { ExceptionSeverity, ExceptionStatus } from "../types/exceptions";

// =============================================================================
// QUERY KEYS
// =============================================================================

export const exceptionKeys = {
  all: ["exceptions"] as const,
  lists: () => [...exceptionKeys.all, "list"] as const,
  list: (filters: { status?: ExceptionStatus; severity?: ExceptionSeverity }) =>
    [...exceptionKeys.lists(), filters] as const,
  details: () => [...exceptionKeys.all, "detail"] as const,
  detail: (id: string) => [...exceptionKeys.details(), id] as const,
  stats: () => [...exceptionKeys.all, "stats"] as const,
};

export const decisionKeys = {
  all: ["decisions"] as const,
  lists: () => [...decisionKeys.all, "list"] as const,
  list: (filters: { shipment_id?: string; exception_id?: string }) =>
    [...decisionKeys.lists(), filters] as const,
};

export const riskKeys = {
  all: ["risk"] as const,
  shipment: (shipmentId: string) => [...riskKeys.all, "shipment", shipmentId] as const,
};

export const settlementKeys = {
  all: ["settlement"] as const,
  shipment: (shipmentId: string) => [...settlementKeys.all, "shipment", shipmentId] as const,
};

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Fetch list of exceptions with optional filters
 */
export function useExceptions(filters?: {
  status?: ExceptionStatus;
  severity?: ExceptionSeverity;
}) {
  return useQuery({
    queryKey: exceptionKeys.list(filters ?? {}),
    queryFn: () => fetchExceptions(filters),
    staleTime: 30_000, // 30 seconds
    refetchInterval: 60_000, // Auto-refresh every minute
  });
}

/**
 * Fetch a single exception with related data
 */
export function useExceptionDetail(exceptionId: string | null) {
  return useQuery({
    queryKey: exceptionKeys.detail(exceptionId ?? ""),
    queryFn: () => fetchExceptionDetail(exceptionId!),
    enabled: !!exceptionId,
    staleTime: 15_000,
  });
}

/**
 * Fetch exception statistics for KPI display
 */
export function useExceptionStats() {
  return useQuery({
    queryKey: exceptionKeys.stats(),
    queryFn: fetchExceptionStats,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

/**
 * Fetch decision records with optional filters
 */
export function useDecisionRecords(filters?: {
  shipment_id?: string;
  exception_id?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: decisionKeys.list(filters ?? {}),
    queryFn: () => fetchDecisionRecords(filters),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

/**
 * Fetch risk summary for a shipment (ChainIQ)
 */
export function useShipmentRisk(shipmentId: string | null) {
  return useQuery({
    queryKey: riskKeys.shipment(shipmentId ?? ""),
    queryFn: () => fetchShipmentRiskSummary(shipmentId!),
    enabled: !!shipmentId,
    staleTime: 60_000,
  });
}

/**
 * Fetch settlement summary for a shipment (ChainPay)
 */
export function useShipmentSettlement(shipmentId: string | null) {
  return useQuery({
    queryKey: settlementKeys.shipment(shipmentId ?? ""),
    queryFn: () => fetchShipmentSettlementSummary(shipmentId!),
    enabled: !!shipmentId,
    staleTime: 60_000,
  });
}

/**
 * Mutation hook for updating exception status
 */
export function useUpdateExceptionStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ exceptionId, status }: { exceptionId: string; status: ExceptionStatus }) =>
      updateExceptionStatus(exceptionId, status),
    onSuccess: (_data, variables) => {
      // Invalidate and refetch related queries
      queryClient.invalidateQueries({ queryKey: exceptionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: exceptionKeys.detail(variables.exceptionId) });
      queryClient.invalidateQueries({ queryKey: exceptionKeys.stats() });
    },
  });
}
