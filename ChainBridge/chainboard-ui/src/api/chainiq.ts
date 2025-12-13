/**
 * ChainIQ API Client
 *
 * Handles communication with ChainIQ ML endpoints for risk and anomaly scoring.
 * Uses the existing apiClient infrastructure for consistent error handling and timeouts.
 *
 * @module api/chainiq
 */

import { httpGet, httpPost } from "../services/apiClient";

/**
 * Feature contribution explaining a score component.
 * Part of the glass-box explainability system.
 */
export interface FeatureContribution {
  /** Name of the feature (e.g., "eta_deviation_hours") */
  feature: string;
  /** Human-readable explanation of the feature's impact */
  reason: string;
}

/**
 * Response from risk scoring endpoint.
 */
export interface RiskScoreResult {
  /** Risk score between 0 (low risk) and 1 (high risk) */
  score: number;
  /** List of feature contributions explaining the score */
  explanation: FeatureContribution[];
  /** Version identifier of the risk scoring model */
  model_version: string;
}

/**
 * Response from anomaly detection endpoint.
 */
export interface AnomalyScoreResult {
  /** Anomaly score between 0 (normal) and 1 (highly anomalous) */
  score: number;
  /** List of feature contributions explaining the anomaly score */
  explanation: FeatureContribution[];
  /** Version identifier of the anomaly detection model */
  model_version: string;
}

/**
 * Shipment feature vector for ML scoring.
 * This is a simplified interface; extend as needed.
 *
 * For v0.1, we support the full ShipmentFeaturesV0 schema from ChainIQ.
 * Key fields are typed; additional fields can be added dynamically.
 */
export interface ShipmentFeaturesV0Like {
  // Required identifiers
  shipment_id: string;
  corridor: string;
  origin_country: string;
  destination_country: string;
  mode: string;
  commodity_category: string;
  financing_type: string;
  counterparty_risk_bucket: string;

  // Operational / Transit
  planned_transit_hours: number;
  actual_transit_hours?: number | null;
  eta_deviation_hours: number;
  num_route_deviations: number;
  max_route_deviation_km: number;
  total_dwell_hours: number;
  max_single_dwell_hours: number;
  handoff_count: number;
  max_custody_gap_hours: number;
  delay_flag: number; // 0 or 1

  // IoT / Condition Monitoring
  has_iot_telemetry: number; // 0 or 1
  temp_mean?: number | null;
  temp_std?: number | null;
  temp_min?: number | null;
  temp_max?: number | null;
  temp_out_of_range_pct?: number | null;
  sensor_uptime_pct?: number | null;

  // Documentation / Collateral
  doc_count: number;
  missing_required_docs: number;
  duplicate_doc_flag: number; // 0 or 1
  doc_inconsistency_flag: number; // 0 or 1
  doc_age_days: number;
  collateral_value: number;
  collateral_value_bucket: string;

  // Historical / Entity Behavior
  shipper_on_time_pct_90d: number;
  carrier_on_time_pct_90d: number;
  corridor_disruption_index_90d: number;
  prior_exceptions_count_180d: number;
  prior_losses_flag: number; // 0 or 1

  // Lane Risk & Sentiment
  lane_risk_score: number;
  lane_sentiment_score: number;
  recent_corridor_loss_rate_90d: number;

  // Currency & Value
  financing_amount_usd: number;
  estimated_market_value_usd: number;

  // Flexible additional fields
  [key: string]: unknown;
}

/**
 * Fetch risk score for a shipment.
 *
 * @param features - Shipment feature vector
 * @returns Promise resolving to risk score result
 * @throws ApiError if request fails
 */
export async function fetchRiskScore(
  features: ShipmentFeaturesV0Like
): Promise<RiskScoreResult> {
  return httpPost<RiskScoreResult>("/iq/ml/risk-score", features);
}

/**
 * Fetch anomaly score for a shipment.
 *
 * @param features - Shipment feature vector
 * @returns Promise resolving to anomaly score result
 * @throws ApiError if request fails
 */
export async function fetchAnomalyScore(
  features: ShipmentFeaturesV0Like
): Promise<AnomalyScoreResult> {
  return httpPost<AnomalyScoreResult>("/iq/ml/anomaly", features);
}

/**
 * IQ ML metrics from observability endpoint.
 * Shows how many times each ML endpoint has been called.
 */
export interface IqMetrics {
  /** Total number of risk scoring calls */
  risk_calls_total: number;
  /** Total number of anomaly scoring calls */
  anomaly_calls_total: number;
}

/**
 * Fetch IQ ML metrics for observability.
 * Shows live call counts for risk and anomaly endpoints.
 *
 * @returns Promise resolving to IQ metrics
 * @throws ApiError if request fails
 */
export async function fetchIqMetrics(): Promise<IqMetrics> {
  return httpGet<IqMetrics>("/iq/ml/debug/metrics");
}
