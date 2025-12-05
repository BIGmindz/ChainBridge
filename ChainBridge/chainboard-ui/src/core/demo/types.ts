/**
 * Demo Walkthrough Types
 *
 * Step-by-step guided demo system for investor/operator presentations.
 */

export type DemoStepId =
  | "overview_kpis"
  | "overview_insights"
  | "shipments_view"
  | "shipments_hot_shipment"
  | "shipment_drawer_intel"
  | "shipment_timeline"
  | "risk_stories"
  | "payment_queue"
  | "iot_health"
  | "alerts_console"
  | "triage_playbook";

/**
 * Individual demo step with target route and optional UI highlight
 */
export interface DemoStep {
  id: DemoStepId;
  title: string;
  description: string;
  targetRoute: string;
  highlightKey?: string;
}

/**
 * Complete demo scenario with multiple steps
 */
export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  heroShipmentHint?: string; // e.g. corridor substring or risk tag
  steps: DemoStep[];
}
