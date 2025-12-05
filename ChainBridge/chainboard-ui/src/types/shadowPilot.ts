/**
 * Shadow Pilot Types
 *
 * TypeScript definitions for Shadow Pilot commercial impact analysis.
 * These mirror Cody's backend API contract for pilot run results.
 */

export interface ShadowPilotSummary {
  run_id: string;
  prospect_name: string;
  period_months: number;
  total_gmv_usd: number;
  financeable_gmv_usd: number;
  financed_gmv_usd: number;
  protocolRevenueUsd: number;
  working_capital_saved_usd: number;
  losses_avoided_usd: number;
  salvageRevenueUsd: number;
  average_daysPulledForward: number;
  shipments_evaluated: number;
  shipments_financeable: number;
  createdAt: string;
}

export interface ShadowPilotRun {
  run_id: string;
  prospect_name: string;
  corridor?: string;
  period_start: string;
  period_end: string;
  status: 'running' | 'completed' | 'failed';
  createdAt: string;
  completed_at?: string;
}

export interface ShadowPilotShipmentResult {
  shipmentId: string;
  original_gmv_usd: number;
  financeable_amount_usd: number;
  financedAmountUsd: number;
  protocol_fee_usd: number;
  working_capital_saved_usd: number;
  daysPulledForward: number;
  riskScore: number;
  financing_applied: boolean;
  reason?: string;
}

export interface ShadowPilotFilters {
  prospect?: string;
  corridor?: string;
  period_months?: number;
  min_gmv?: number;
  status?: 'running' | 'completed' | 'failed';
}

export interface ShadowPilotExportData {
  summary: ShadowPilotSummary;
  shipments?: ShadowPilotShipmentResult[];
  export_timestamp: string;
  exported_by: string;
}

// Derived metrics for UI display
export interface ShadowPilotMetrics {
  total_commercial_impact: number;
  roi_percentage: number;
  financing_penetration: number;
  avg_capital_velocity: number;
  loss_prevention_rate: number;
}
