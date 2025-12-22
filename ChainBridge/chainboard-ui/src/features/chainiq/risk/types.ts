export type RiskBand = "LOW" | "MEDIUM" | "HIGH";

export interface FeaturesSnapshot {
  value_usd: number;
  is_hazmat: boolean;
  is_temp_control: boolean;
  iot_alert_count: number;
  recent_delay_events: number;
  lane_risk_index: number;
  border_crossing_count: number;
  carrier_incident_rate_90d?: number;
  carrier_tenure_days?: number;
}

export interface RiskEvaluationRecord {
  evaluation_id: string;
  timestamp: string; // ISO
  model_version: string;
  shipment_id: string;
  carrier_id: string;
  lane_id: string;
  risk_score: number;
  risk_band: RiskBand;
  primary_reasons: string[];
  features_snapshot: FeaturesSnapshot;
}

export interface RiskModelMetrics {
  id: string;
  model_version: string;
  evaluation_window_start: string; // ISO datetime
  evaluation_window_end: string; // ISO datetime
  eval_count: number;

  critical_incident_recall: number | null;
  high_risk_precision: number | null;
  ops_workload_percent: number | null;
  loss_value_coverage_pct: number | null;
  calibration_low_rate: number | null;
  calibration_high_rate: number | null;

  has_failures: boolean;
  has_warnings: boolean;
  fail_messages: string[];
  warning_messages: string[];

  created_at: string; // ISO datetime
}
