/**
 * Sample Shipment Payloads for ChainIQ Lab
 *
 * Provides pre-configured feature vectors for testing and demonstration.
 * These payloads satisfy the ShipmentFeaturesV0 schema with realistic values.
 *
 * @module features/chainiq/samplePayloads
 */

import type { ShipmentFeaturesV0Like } from "../../api/chainiq";

/**
 * Sample 1: Pharma cold-chain shipment (US-MX corridor)
 * High-value, high-risk scenario with IoT monitoring and documentation requirements.
 */
export const sampleShipmentPharmaUsMx: ShipmentFeaturesV0Like = {
  // Identifiers & Context
  shipment_id: "DEMO-PHARMA-US-MX-001",
  corridor: "US-MX",
  origin_country: "US",
  destination_country: "MX",
  mode: "road",
  commodity_category: "pharma_cold_chain",
  financing_type: "inventory_in_transit",
  counterparty_risk_bucket: "MEDIUM",

  // Operational / Transit
  planned_transit_hours: 48.0,
  actual_transit_hours: null, // Still in transit
  eta_deviation_hours: 4.5, // Running 4.5 hours late
  num_route_deviations: 1,
  max_route_deviation_km: 12.3,
  total_dwell_hours: 6.0,
  max_single_dwell_hours: 3.5,
  handoff_count: 2,
  max_custody_gap_hours: 0.5,
  delay_flag: 1, // Delayed

  // IoT / Condition Monitoring
  has_iot_telemetry: 1, // IoT sensors present
  temp_mean: 5.2, // °C
  temp_std: 0.8,
  temp_min: 3.1,
  temp_max: 7.9,
  temp_out_of_range_pct: 2.3, // 2.3% out of range
  sensor_uptime_pct: 98.5,

  // Documentation / Collateral
  doc_count: 8,
  missing_required_docs: 1, // Missing one required doc
  duplicate_doc_flag: 0,
  doc_inconsistency_flag: 0,
  doc_age_days: 2.1,
  collateral_value: 125000.0,
  collateral_value_bucket: "high",

  // Historical / Entity Behavior
  shipper_on_time_pct_90d: 0.87,
  carrier_on_time_pct_90d: 0.92,
  corridor_disruption_index_90d: 0.42,
  prior_exceptions_count_180d: 3,
  prior_losses_flag: 0,

  // Lane Risk & Sentiment
  lane_risk_score: 0.45,
  lane_sentiment_score: 0.62,
  recent_corridor_loss_rate_90d: 0.02,

  // Currency & Value
  financing_amount_usd: 95000.0,
  estimated_market_value_usd: 110000.0,
};

/**
 * Sample 2: Generic electronics shipment (CN-NL corridor)
 * Lower risk, ocean freight, standard documentation.
 */
export const sampleShipmentGenericCnNl: ShipmentFeaturesV0Like = {
  // Identifiers & Context
  shipment_id: "DEMO-GENERIC-CN-NL-002",
  corridor: "CN-NL",
  origin_country: "CN",
  destination_country: "NL",
  mode: "ocean",
  commodity_category: "electronics",
  financing_type: "inventory_in_transit",
  counterparty_risk_bucket: "LOW",

  // Operational / Transit
  planned_transit_hours: 720.0, // 30 days
  actual_transit_hours: 715.0, // Completed, slightly early
  eta_deviation_hours: -5.0, // 5 hours early
  num_route_deviations: 0,
  max_route_deviation_km: 0.0,
  total_dwell_hours: 48.0,
  max_single_dwell_hours: 18.0,
  handoff_count: 4,
  max_custody_gap_hours: 1.2,
  delay_flag: 0, // On time

  // IoT / Condition Monitoring
  has_iot_telemetry: 0, // No IoT
  temp_mean: null,
  temp_std: null,
  temp_min: null,
  temp_max: null,
  temp_out_of_range_pct: null,
  sensor_uptime_pct: null,

  // Documentation / Collateral
  doc_count: 12,
  missing_required_docs: 0,
  duplicate_doc_flag: 0,
  doc_inconsistency_flag: 0,
  doc_age_days: 1.5,
  collateral_value: 75000.0,
  collateral_value_bucket: "medium",

  // Historical / Entity Behavior
  shipper_on_time_pct_90d: 0.95,
  carrier_on_time_pct_90d: 0.89,
  corridor_disruption_index_90d: 0.18,
  prior_exceptions_count_180d: 0,
  prior_losses_flag: 0,

  // Lane Risk & Sentiment
  lane_risk_score: 0.22,
  lane_sentiment_score: 0.78,
  recent_corridor_loss_rate_90d: 0.005,

  // Currency & Value
  financing_amount_usd: 58000.0,
  estimated_market_value_usd: 72000.0,
};

/**
 * Sample 3: High-risk automotive parts shipment (MX-US corridor)
 * Border crossing complications, multiple delays, missing documentation.
 */
export const sampleShipmentHighRiskMxUs: ShipmentFeaturesV0Like = {
  // Identifiers & Context
  shipment_id: "DEMO-HIGHRISK-MX-US-003",
  corridor: "MX-US",
  origin_country: "MX",
  destination_country: "US",
  mode: "road",
  commodity_category: "automotive_parts",
  financing_type: "open_account",
  counterparty_risk_bucket: "HIGH",

  // Operational / Transit
  planned_transit_hours: 36.0,
  actual_transit_hours: null, // Still in transit
  eta_deviation_hours: 18.0, // Running 18 hours late!
  num_route_deviations: 3,
  max_route_deviation_km: 45.0,
  total_dwell_hours: 28.0, // High dwell time
  max_single_dwell_hours: 14.0,
  handoff_count: 5,
  max_custody_gap_hours: 2.5,
  delay_flag: 1, // Delayed

  // IoT / Condition Monitoring
  has_iot_telemetry: 1,
  temp_mean: 28.5, // °C (ambient)
  temp_std: 3.2,
  temp_min: 21.0,
  temp_max: 35.0,
  temp_out_of_range_pct: 8.5, // 8.5% out of range
  sensor_uptime_pct: 92.0, // Some sensor dropouts

  // Documentation / Collateral
  doc_count: 6,
  missing_required_docs: 3, // Missing critical docs
  duplicate_doc_flag: 1, // Duplicate docs detected
  doc_inconsistency_flag: 1, // Inconsistencies detected
  doc_age_days: 5.2,
  collateral_value: 45000.0,
  collateral_value_bucket: "low",

  // Historical / Entity Behavior
  shipper_on_time_pct_90d: 0.68,
  carrier_on_time_pct_90d: 0.71,
  corridor_disruption_index_90d: 0.67,
  prior_exceptions_count_180d: 8,
  prior_losses_flag: 1, // Prior losses detected!

  // Lane Risk & Sentiment
  lane_risk_score: 0.72,
  lane_sentiment_score: 0.35,
  recent_corridor_loss_rate_90d: 0.08,

  // Currency & Value
  financing_amount_usd: 32000.0,
  estimated_market_value_usd: 38000.0,
};

/**
 * All available sample payloads with descriptive labels.
 */
export const SAMPLE_PAYLOADS = [
  {
    label: "Pharma Cold-Chain (US-MX) - Medium Risk",
    payload: sampleShipmentPharmaUsMx,
  },
  {
    label: "Electronics (CN-NL) - Low Risk",
    payload: sampleShipmentGenericCnNl,
  },
  {
    label: "Automotive Parts (MX-US) - High Risk",
    payload: sampleShipmentHighRiskMxUs,
  },
] as const;
