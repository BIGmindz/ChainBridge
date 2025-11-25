/**
 * API Routes Registry
 *
 * Centralized endpoint definitions for the ChainBoard Control Tower.
 * All API paths are defined here to ensure consistency and easy maintenance.
 */

export const API_ROUTES = {
  // Shipments & Manifest
  shipments: "/api/chainboard/shipments",
  shipmentById: (id: string) => `/api/chainboard/shipments/${encodeURIComponent(id)}`,

  // Events & Activity
  events: "/api/chainboard/events",
  eventsByShipment: (id: string) => `/api/chainboard/events/shipment/${encodeURIComponent(id)}`,

  // Timeline Events
  timelineEvents: "/api/chainboard/events",
  shipmentEvents: (reference: string) => `/api/chainboard/shipments/${encodeURIComponent(reference)}/events`,

  // Exceptions & Alerts
  exceptions: "/api/chainboard/exceptions",
  exceptionById: (id: string) => `/api/chainboard/exceptions/${encodeURIComponent(id)}`,

  // ChainIQ Risk Intelligence
  iqScores: "/api/chainboard/iq/scores",
  iqByShipment: (id: string) => `/api/chainboard/iq/scores/${encodeURIComponent(id)}`,
  riskOverview: "/api/chainboard/risk/overview",
  riskStories: "/api/chainboard/iq/risk-stories",

  // ChainPay Payment Intelligence
  paymentQueue: "/api/chainboard/pay/queue",
  payments: "/api/chainboard/payments",
  paymentsByShipment: (id: string) => `/api/chainboard/payments/shipment/${encodeURIComponent(id)}`,
  proofpack: (milestoneId: string) => `/api/chainboard/payments/proofpack/${encodeURIComponent(milestoneId)}`,

  // ChainSense IoT Telemetry
  iotHealth: "/api/chainboard/metrics/iot/summary",
  iotByShipment: (id: string) => `/api/chainboard/metrics/iot/shipments/${encodeURIComponent(id)}`,

  // Agent Health
  agentHealthStatus: "/api/agents/status",

  // Metrics & Overview
  globalSummary: "/api/chainboard/metrics/summary",
  corridorMetrics: "/api/chainboard/metrics/corridors",

  // Alerts & Triage
  alerts: "/api/chainboard/alerts",
  alertDetail: (id: string) => `/api/chainboard/alerts/${encodeURIComponent(id)}`,
  triageWorkQueue: "/api/chainboard/alerts/work-queue",
  alertAssign: (id: string) => `/api/chainboard/alerts/${encodeURIComponent(id)}/assign`,
  alertNotes: (id: string) => `/api/chainboard/alerts/${encodeURIComponent(id)}/notes`,
  alertStatus: (id: string) => `/api/chainboard/alerts/${encodeURIComponent(id)}/status`,

  // Settlement Actions
  settlementActions: {
    escalate: (milestoneId: string) => `/api/chainboard/settlements/${encodeURIComponent(milestoneId)}/actions/escalate`,
    markReviewed: (milestoneId: string) => `/api/chainboard/settlements/${encodeURIComponent(milestoneId)}/actions/mark-reviewed`,
    requestDocs: (milestoneId: string) => `/api/chainboard/settlements/${encodeURIComponent(milestoneId)}/actions/request-docs`,
    recent: (limit: number) => `/api/chainboard/settlements/actions/recent?limit=${limit}`,
  },
} as const;

/**
 * Helper to build query string from filters
 */
export function buildQueryString(params: Record<string, unknown> | { [key: string]: unknown } | object): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;

    if (Array.isArray(value)) {
      value.forEach((v) => search.append(key, String(v)));
    } else {
      search.append(key, String(value));
    }
  }

  const qs = search.toString();
  return qs ? `?${qs}` : "";
}
