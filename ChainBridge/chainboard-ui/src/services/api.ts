/**
 * Mock API Service
 *
 * Provides mocked data for development and testing.
 * This is designed to be easily replaced with real FastAPI endpoints later.
 *
 * Real API endpoints to implement:
 * - GET /vitals
 * - GET /exceptions?filters=...
 * - GET /shipments?filters=...
 * - GET /shipments/:id
 */

import { config } from "../config/env";
import type { ProofPackResponse, EntityHistoryResponse } from "../lib/apiClient";
import type {
  GlobalSummary,
  CorridorMetrics,
  ShipmentKpiSummary,
  PaymentHealthSummary,
  GovernanceHealthSummary,
} from "../lib/metrics";
import type {
  LegacyShipment,
  LegacyShipmentEvent,
  LegacyPaymentMilestone,
  LegacyProofPackSummary,
  LegacyRiskAssessment,
  CreateProofPackPayload,
} from "../lib/shipments";
import { legacyShipmentToExceptionRow } from "../lib/shipments";
import type {
  ShipmentStatus,
  ExceptionRow,
  NetworkVitals,
  PaymentState,
  IoTHealthSummary,
  ShipmentIoTSnapshot,
  IoTSensorReading,
} from "../lib/types";
import { classifyCorridor } from "../utils/corridors";

// ============================================================================
// MOCK DATA GENERATORS
// ============================================================================

const CARRIERS = ["FedEx", "UPS", "DHL", "XPO", "Schneider", "JB Hunt"];
const CUSTOMERS = ["Amazon", "Walmart", "Target", "Best Buy", "Home Depot"];
const ORIGINS = ["Shanghai", "Singapore", "Rotterdam", "Hamburg", "Los Angeles"];
const DESTINATIONS = ["Los Angeles", "New York", "Chicago", "Houston", "Dallas"];

function getRandomItem<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function generateShipmentId(): string {
  return `ship_${Math.random().toString(36).substr(2, 9)}`;
}

function generateTokenId(): string {
  return `ft_${Math.random().toString(36).substr(2, 9)}`;
}

function generateProofPackId(): string {
  return `pp_${Math.random().toString(36).substr(2, 9)}`;
}

function generateManifestHash(): string {
  return `0x${Math.random().toString(16).substr(2, 64)}`;
}

function generateEvents(hoursAgo: number): LegacyShipmentEvent[] {
  const events = [
    { eventType: "order_placed", offset: hoursAgo },
    { eventType: "pickup_scheduled", offset: hoursAgo - 12 },
    { eventType: "pickup_confirmed", offset: hoursAgo - 10 },
    { eventType: "in_transit", offset: hoursAgo - 6 },
  ];

  if (hoursAgo < 2) {
    events.push({ eventType: "delivery_attempted", offset: 1 });
  }

  return events.map((e) => ({
    eventType: e.eventType,
    timestamp: new Date(Date.now() - e.offset * 3600000).toISOString(),
  }));
}

function generateRiskAssessment(riskScore?: number): LegacyRiskAssessment {
  const score = riskScore ?? randomInt(10, 95);
  let category: "low" | "medium" | "high";

  if (score < 35) category = "low";
  else if (score < 70) category = "medium";
  else category = "high";

  return {
    riskScore: score,
    riskCategory: category,
    recommended_action:
      category === "high"
        ? "Hold for manual review"
        : category === "medium"
          ? "Monitor closely"
          : "Proceed normally",
    confidence: randomInt(75, 99),
  };
}

function generatePaymentSchedule(): LegacyPaymentMilestone[] {
  const statuses = ["released", "pending", "pending"] as const;
  return [
    {
      milestone: "Pickup confirmed",
      percentage: 20,
      status: statuses[0],
      amount_usd: 5000,
      released_at: new Date(Date.now() - 24 * 3600000).toISOString(),
    },
    {
      milestone: "In transit",
      percentage: 50,
      status: statuses[1],
      amount_usd: 12500,
    },
    {
      milestone: "Delivery confirmed",
      percentage: 30,
      status: statuses[2],
      amount_usd: 7500,
    },
  ];
}

function generateProofPack(): LegacyProofPackSummary {
  return {
    pack_id: generateProofPackId(),
    manifest_hash: generateManifestHash(),
    signature_status: Math.random() > 0.05 ? "VERIFIED" : "FAILED",
    createdAt: new Date(Date.now() - 48 * 3600000).toISOString(),
  };
}

/**
 * Generate a mock shipment with realistic data distribution
 */
function generateShipment(overrides?: Partial<LegacyShipment>): LegacyShipment {
  const hoursAgo = randomInt(0, 168); // 0-7 days
  const riskScore = randomInt(10, 95);

  return {
    shipmentId: generateShipmentId(),
    token_id: generateTokenId(),
    carrier: getRandomItem(CARRIERS),
    customer: getRandomItem(CUSTOMERS),
    origin: getRandomItem(ORIGINS),
    destination: getRandomItem(DESTINATIONS),
    current_status: ["pickup", "in_transit", "delivery", "delayed"][
      randomInt(0, 3)
    ] as ShipmentStatus,
    current_event: "in_transit",
    last_update_timestamp: new Date(Date.now() - hoursAgo * 3600000).toISOString(),
    createdAt: new Date(Date.now() - (hoursAgo + 24) * 3600000).toISOString(),
    events: generateEvents(hoursAgo),
    risk: generateRiskAssessment(riskScore),
    payment_state: ["not_started", "in_progress", "partially_paid", "completed"][
      randomInt(0, 3)
    ] as PaymentState,
    payment_schedule: generatePaymentSchedule(),
    total_valueUsd: randomInt(5000, 50000),
    proofpack: generateProofPack(),
    ...overrides,
  };
}

// ============================================================================
// API CLIENT CLASS
// ============================================================================

class MockApiClient {
  private mockShipments: Map<string, LegacyShipment> = new Map();
  private mockExceptions: ExceptionRow[] = [];

  constructor() {
    this.initializeMockData();
  }

  private initializeMockData(): void {
    // Generate 50 shipments with realistic distribution
    const shipments: LegacyShipment[] = Array.from({ length: 50 }, () => generateShipment());

    shipments.forEach((ship) => {
      this.mockShipments.set(ship.shipmentId, ship);
    });

    // Generate exceptions (shipments with risk or payment issues)
    this.mockExceptions = shipments
      .filter((s) => s.risk.riskScore > 70 || s.payment_state === "blocked")
      .map(legacyShipmentToExceptionRow);
  }

  /**
   * GET /vitals - Network vital signs KPIs
   */
  async getNetworkVitals(): Promise<NetworkVitals> {
    await this.delay(300);

    const allShipments = Array.from(this.mockShipments.values());
    const activeShipments = allShipments.filter((s) =>
      ["pickup", "in_transit", "delivery"].includes(s.current_status)
    );

    const onTimeShipments = activeShipments.filter((s) => {
      const ageHours =
        (Date.now() - new Date(s.last_update_timestamp).getTime()) / 3600000;
      return ageHours < 12; // Arbitrary: "on time" if updated in last 12h
    });

    const atRiskShipments = allShipments.filter((s) => s.risk.riskScore >= 70);
    const paymentHolds = allShipments.filter((s) => s.payment_state === "blocked");

    return {
      active_shipments: activeShipments.length,
      on_time_percent:
        activeShipments.length > 0
          ? Math.round((onTimeShipments.length / activeShipments.length) * 100)
          : 0,
      at_risk_shipments: atRiskShipments.length,
      open_payment_holds: paymentHolds.length,
    };
  }

  /**
   * GET /exceptions - Exception shipments with optional filtering
   */
  async getExceptions(filters?: {
    issue_types?: string[];
    risk_min?: number;
    risk_max?: number;
    time_window?: "2h" | "24h" | "7d";
  }): Promise<ExceptionRow[]> {
    await this.delay(200);

    let results = [...this.mockExceptions];

    if (filters?.risk_min !== undefined || filters?.risk_max !== undefined) {
      results = results.filter((e) => {
        const minOk = filters.risk_min === undefined || e.riskScore >= filters.risk_min;
        const maxOk = filters.risk_max === undefined || e.riskScore <= filters.risk_max;
        return minOk && maxOk;
      });
    }

    if (filters?.time_window) {
      const now = Date.now();
      const windowMs = {
        "2h": 2 * 3600000,
        "24h": 24 * 3600000,
        "7d": 7 * 24 * 3600000,
      }[filters.time_window];

      results = results.filter((e) => {
        const ageMs = now - new Date(e.last_update).getTime();
        return ageMs <= windowMs;
      });
    }

    return results;
  }

  /**
   * GET /shipments - List all shipments with filtering
   */
  async getShipments(filters?: {
    carrier?: string;
    customer?: string;
    status?: string;
    risk_min?: number;
    risk_max?: number;
  }): Promise<LegacyShipment[]> {
    await this.delay(250);

    let results = Array.from(this.mockShipments.values());

    if (filters?.carrier) {
      results = results.filter((s) => s.carrier === filters.carrier);
    }

    if (filters?.customer) {
      results = results.filter((s) => s.customer === filters.customer);
    }

    if (filters?.status) {
      results = results.filter((s) => s.current_status === filters.status);
    }

    if (filters?.risk_min !== undefined || filters?.risk_max !== undefined) {
      results = results.filter((s) => {
        const minOk = filters.risk_min === undefined || s.risk.riskScore >= filters.risk_min;
        const maxOk = filters.risk_max === undefined || s.risk.riskScore <= filters.risk_max;
        return minOk && maxOk;
      });
    }

    return results;
  }

  /**
   * GET /shipments/:id - Get single shipment detail
   */
  async getShipmentDetail(shipmentId: string): Promise<LegacyShipment | null> {
    await this.delay(200);
    return this.mockShipments.get(shipmentId) || null;
  }

  /**
   * POST /proofpacks/run - Create a new proof pack
   */
  async createProofPack(payload: CreateProofPackPayload): Promise<ProofPackResponse> {
    await this.delay(300);

    const mockProofPack: ProofPackResponse = {
      shipmentId: payload.shipmentId,
      version: "mock-1.0",
      generatedAt: new Date().toISOString(),
      risk_snapshot: {
        shipmentId: payload.shipmentId,
        riskScore: payload.riskScore ?? randomInt(10, 95),
        severity: payload.riskScore && payload.riskScore >= 70 ? "high" : "medium",
        recommended_action: "Monitor",
        reasonCodes: ["mock_generation"],
        last_scored_at: new Date().toISOString(),
      },
      history: buildMockHistory(payload.shipmentId, payload.events),
      payment_queue_entry: null,
      options_advisor: null,
    };

    console.log(`✅ Mock: Created proof pack for ${payload.shipmentId}`);
    return mockProofPack;
  }

  /**
   * GET /proofpacks/{pack_id} - Get a proof pack by ID
   */
  async getProofPack(packId: string): Promise<ProofPackResponse> {
    await this.delay(200);

    // Return a realistic mock proof pack
    const historicalEvents: LegacyShipmentEvent[] = [
      {
        eventType: "pickup",
        timestamp: new Date(Date.now() - 86400000).toISOString(),
      },
      {
        eventType: "in_transit",
        timestamp: new Date(Date.now() - 43200000).toISOString(),
      },
      {
        eventType: "delivery",
        timestamp: new Date(Date.now() - 3600000).toISOString(),
      },
    ];

    const mockProofPack: ProofPackResponse = {
      shipmentId: `ship_${Math.random().toString(36).substr(2, 9)}`,
      version: "mock-1.0",
      generatedAt: new Date(Date.now() - Math.random() * 86400000).toISOString(),
      risk_snapshot: {
        shipmentId: packId,
        riskScore: randomInt(20, 95),
        severity: "medium",
        recommended_action: "Monitor",
        reasonCodes: ["mock_data"],
        last_scored_at: new Date().toISOString(),
      },
      history: buildMockHistory(packId, historicalEvents),
      payment_queue_entry: null,
      options_advisor: null,
    };

    console.log(`✅ Mock: Retrieved proof pack ${packId}`);
    return mockProofPack;
  }

  // --------------------------------------------------------------------------
  // Dashboard + IoT helpers (legacy facade methods used by metrics/iot clients)
  // --------------------------------------------------------------------------

  async getMockGlobalSummary(): Promise<GlobalSummary> {
    await this.delay(120);
    const shipments = Array.from(this.mockShipments.values());
    const corridorMetrics = this.buildCorridorMetrics();
    const shipmentsSummary = this.buildShipmentSummary(shipments);
    const paymentsSummary = this.buildPaymentSummary(shipments);
    const governanceSummary = this.buildGovernanceSummary(shipments);

    return {
      threat_level: this.deriveThreatLevel(shipmentsSummary.high_risk_count),
      shipments: shipmentsSummary,
      payments: paymentsSummary,
      governance: governanceSummary,
      top_corridor: corridorMetrics[0] ?? null,
      iot: await this.getMockIoTHealthSummary(),
    };
  }

  async getMockCorridorMetrics(): Promise<CorridorMetrics[]> {
    await this.delay(150);
    return this.buildCorridorMetrics();
  }

  async getMockIoTHealthSummary(): Promise<IoTHealthSummary> {
    await this.delay(150);
    const shipments = Array.from(this.mockShipments.values());
    const shipmentsWithIoT = Math.round(shipments.length * 0.65);
    const alertsLastDay = randomInt(15, 45);
    const criticalAlerts = Math.round(alertsLastDay * 0.2);

    return {
      shipments_with_iot: shipmentsWithIoT,
      active_sensors: shipmentsWithIoT * randomInt(4, 8),
      alerts_last_24h: alertsLastDay,
      critical_alerts_last_24h: criticalAlerts,
      coverage_percent:
        shipments.length > 0
          ? Math.min(100, Math.round((shipmentsWithIoT / shipments.length) * 100))
          : 0,
    };
  }

  async getMockShipmentIoTSnapshot(
    shipmentId: string
  ): Promise<ShipmentIoTSnapshot | null> {
    await this.delay(160);
    if (!this.mockShipments.has(shipmentId)) {
      return null;
    }

    const readings = this.generateSensorReadings();
    const criticalAlerts = readings.filter((reading) => reading.status === "critical").length;

    return {
      shipmentId: shipmentId,
      latest_readings: readings,
      alert_count_24h: randomInt(0, 6) + criticalAlerts,
      critical_alerts_24h: criticalAlerts,
    };
  }

  private buildShipmentSummary(shipments: LegacyShipment[]): ShipmentKpiSummary {
    const total = shipments.length;
    const active = shipments.filter((s) => s.current_status !== "completed").length;
    const onTime = shipments.filter((s) => {
      const ageHours =
        (Date.now() - new Date(s.last_update_timestamp).getTime()) / 3600000;
      return ageHours < 12;
    }).length;
    const highRisk = shipments.filter((s) => s.risk.riskScore >= 70).length;
    const delayedOrBlocked = shipments.filter((s) =>
      ["delayed", "blocked"].includes(s.current_status)
    ).length;

    return {
      total_shipments: total,
      active_shipments: active,
      on_time_percent: total > 0 ? Math.round((onTime / total) * 100) : 0,
      exception_count: this.mockExceptions.length,
      high_risk_count: highRisk,
      delayed_or_blocked_count: delayedOrBlocked,
    };
  }

  private buildPaymentSummary(shipments: LegacyShipment[]): PaymentHealthSummary {
    const counts: Record<PaymentState, number> = {
      blocked: 0,
      completed: 0,
      in_progress: 0,
      not_started: 0,
      partially_paid: 0,
    };

    shipments.forEach((shipment) => {
      counts[shipment.payment_state] += 1;
    });

    const paymentHealthScore = Math.max(
      0,
      100 - counts.blocked * 5 - counts.partially_paid * 2
    );

    return {
      blocked_payments: counts.blocked,
      partially_paid: counts.partially_paid,
      completed: counts.completed,
      not_started: counts.not_started,
      in_progress: counts.in_progress,
      payment_health_score: paymentHealthScore,
      capital_locked_hours: counts.blocked * 12 + counts.partially_paid * 4,
    };
  }

  private buildGovernanceSummary(
    shipments: LegacyShipment[]
  ): GovernanceHealthSummary {
    const proofpackOk = shipments.filter(
      (shipment) => shipment.proofpack.signature_status === "VERIFIED"
    ).length;

    return {
      proofpack_ok_percent:
        shipments.length > 0 ? Math.round((proofpackOk / shipments.length) * 100) : 0,
      open_audits: Math.max(1, Math.round(this.mockExceptions.length / 4)),
      watchlisted_shipments: shipments.filter((s) => s.risk.riskCategory === "high").length,
    };
  }

  private buildCorridorMetrics(): CorridorMetrics[] {
    const stats: Map<
      string,
      {
        label: string;
        shipment_count: number;
        active_count: number;
        high_risk_count: number;
        blocked_payments: number;
        total_risk: number;
      }
    > = new Map();

    this.mockShipments.forEach((shipment) => {
      const { id, label } = classifyCorridor({
        origin: shipment.origin,
        destination: shipment.destination,
      });

      const entry = stats.get(id) ?? {
        label,
        shipment_count: 0,
        active_count: 0,
        high_risk_count: 0,
        blocked_payments: 0,
        total_risk: 0,
      };

      entry.shipment_count += 1;
      if (shipment.current_status !== "completed") {
        entry.active_count += 1;
      }
      if (shipment.risk.riskScore >= 70) {
        entry.high_risk_count += 1;
      }
      if (shipment.payment_state === "blocked") {
        entry.blocked_payments += 1;
      }
      entry.total_risk += shipment.risk.riskScore;
      stats.set(id, entry);
    });

    return Array.from(stats.entries())
      .map(([corridorId, value]) => {
        const riskAverage =
          value.shipment_count > 0
            ? Math.round(value.total_risk / value.shipment_count)
            : 0;

        return {
          corridorId: corridorId,
          label: value.label,
          shipment_count: value.shipment_count,
          active_count: value.active_count,
          high_risk_count: value.high_risk_count,
          blocked_payments: value.blocked_payments,
          avg_riskScore: riskAverage,
          trend:
            value.high_risk_count > value.shipment_count * 0.35
              ? "rising"
              : value.high_risk_count > value.shipment_count * 0.2
                ? "stable"
                : "improving",
        } satisfies CorridorMetrics;
      })
      .sort((a, b) => b.high_risk_count - a.high_risk_count);
  }

  private deriveThreatLevel(highRiskCount: number): GlobalSummary["threat_level"] {
    if (highRiskCount >= 15) {
      return "critical";
    }
    if (highRiskCount >= 6) {
      return "elevated";
    }
    return "normal";
  }

  private generateSensorReadings(): IoTSensorReading[] {
    const now = Date.now();
    return [
      {
        sensor_type: "temperature",
        value: (randomInt(2, 8) + Math.random()).toFixed(1),
        unit: "°C",
        timestamp: new Date(now - randomInt(5, 45) * 60000).toISOString(),
        status: "info",
      },
      {
        sensor_type: "humidity",
        value: randomInt(40, 60),
        unit: "%",
        timestamp: new Date(now - randomInt(10, 55) * 60000).toISOString(),
        status: "info",
      },
      {
        sensor_type: "door",
        value: Math.random() > 0.8 ? "open" : "closed",
        unit: null,
        timestamp: new Date(now - randomInt(1, 15) * 60000).toISOString(),
        status: Math.random() > 0.8 ? "warn" : "info",
      },
      {
        sensor_type: "shock",
        value: randomInt(0, 5),
        unit: "g",
        timestamp: new Date(now - randomInt(2, 20) * 60000).toISOString(),
        status: Math.random() > 0.9 ? "critical" : "info",
      },
      {
        sensor_type: "gps",
        value: "34.05° N, 118.24° W",
        unit: null,
        timestamp: new Date(now - randomInt(1, 5) * 60000).toISOString(),
        status: "info",
      },
    ];
  }


  /**
   * Simulate network delay
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

function buildMockHistory(
  shipmentId: string,
  events: LegacyShipmentEvent[]
): EntityHistoryResponse {
  return {
    entity_id: shipmentId,
    total_records: events.length,
    history: events.map((event, index) => ({
      timestamp: event.timestamp,
      score: randomInt(20, 95),
      severity: event.eventType === "delivery" ? "info" : "medium",
      recommended_action: event.eventType === "delivery" ? "Archive" : "Monitor",
      reasonCodes: ["mock_event"],
      payload: { eventType: event.eventType, order: index },
    })),
  };
}

// Export singleton instance
export const mockApiClient = new MockApiClient();

// ============================================================================
// API CLIENT INTERFACE - DEFINES ALL AVAILABLE METHODS
// ============================================================================

/**
 * Common interface for all API clients (Mock and Real)
 * Ensures type safety when switching between implementations
 */
export interface IApiClient {
  // Network vitals (KPI data)
  getNetworkVitals(): Promise<NetworkVitals>;

  // Exceptions with filtering
  getExceptions(filters?: {
    risk_min?: number;
    risk_max?: number;
    issue_types?: string[];
    time_window?: "2h" | "24h" | "7d";
  }): Promise<ExceptionRow[]>;

  // Shipments with filtering
  getShipments(filters?: {
    carrier?: string;
    customer?: string;
    status?: string;
    risk_min?: number;
    risk_max?: number;
  }): Promise<LegacyShipment[]>;

  // Single shipment detail
  getShipmentDetail(shipmentId: string): Promise<LegacyShipment | null>;

  // Proof pack operations
  getProofPack(packId: string): Promise<ProofPackResponse>;
  createProofPack(payload: CreateProofPackPayload): Promise<ProofPackResponse>;
}

// ============================================================================
// API CLIENT FACTORY - SWITCHES BETWEEN MOCK AND REAL
// ============================================================================



class HttpError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "HttpError";
  }
}

class RealApiClient implements IApiClient {
  constructor(private readonly baseUrl: string) {}

  private buildUrl(path: string): string {
    if (!path.startsWith("/")) {
      return `${this.baseUrl}/${path}`;
    }
    return `${this.baseUrl}${path}`;
  }

  private buildQuery(params: Record<string, unknown> | undefined): string {
    if (!params) {
      return "";
    }

    const search = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }

      if (Array.isArray(value)) {
        value.forEach((entry) => {
          search.append(key, String(entry));
        });
        return;
      }

      search.append(key, String(value));
    });

    const query = search.toString();
    return query ? `?${query}` : "";
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(this.buildUrl(path), {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });

    if (!response.ok) {
      let body = "";
      try {
        body = await response.text();
      } catch {
        // ignore body parsing failures
      }

      throw new HttpError(
        `[RealApiClient] ${response.status} ${response.statusText}: ${body}`,
        response.status
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  async getNetworkVitals(): Promise<NetworkVitals> {
    return this.request<NetworkVitals>("/vitals");
  }

  async getExceptions(filters?: {
    risk_min?: number;
    risk_max?: number;
    issue_types?: string[];
    time_window?: "2h" | "24h" | "7d";
  }): Promise<ExceptionRow[]> {
    const query = this.buildQuery(filters);
    const data = await this.request<ExceptionRow[] | { exceptions: ExceptionRow[] }>(
      `/exceptions${query}`
    );

    if (Array.isArray(data)) {
      return data;
    }
    if (data && Array.isArray((data as { exceptions?: ExceptionRow[] }).exceptions)) {
      return (data as { exceptions: ExceptionRow[] }).exceptions;
    }
    return [];
  }

  async getShipments(filters?: {
    carrier?: string;
    customer?: string;
    status?: string;
    risk_min?: number;
    risk_max?: number;
  }): Promise<LegacyShipment[]> {
    const query = this.buildQuery(filters);
    return this.request<LegacyShipment[]>(`/shipments${query}`);
  }

  async getShipmentDetail(shipmentId: string): Promise<LegacyShipment | null> {
    try {
      return await this.request<LegacyShipment>(`/shipments/${encodeURIComponent(shipmentId)}`);
    } catch (error) {
      if (error instanceof HttpError && error.status === 404) {
        return null;
      }
      throw error;
    }
  }

  async getProofPack(packId: string): Promise<ProofPackResponse> {
    return this.request<ProofPackResponse>(`/proofpacks/${encodeURIComponent(packId)}`);
  }

  async createProofPack(payload: CreateProofPackPayload): Promise<ProofPackResponse> {
    return this.request<ProofPackResponse>("/proofpacks/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}

function normalizeBaseUrl(url: string): string {
  if (!url) {
    return "";
  }
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

const normalizedBaseUrl = normalizeBaseUrl(config.apiBaseUrl);
const canUseRealApi = Boolean(normalizedBaseUrl);
const realApiClient: ApiClientType | null = canUseRealApi
  ? new RealApiClient(normalizedBaseUrl)
  : null;

/**
 * API Client Type - unified interface for both Mock and Real clients
 */
export type ApiClientType = IApiClient;

/**
 * Get the appropriate API client based on configuration
 *
 * Priority:
 * 1. If VITE_USE_MOCKS = "true" → always use MockApiClient
 * 2. Otherwise → use RealApiClient (requires backend at VITE_API_BASE_URL)
 *
 * Usage:
 *   const client = getApiClient();
 *   const proofPack = await client.getProofPack('pp_abc123');
 */
export function getApiClient(): ApiClientType {
  const shouldUseRealApi = !config.useMocks && realApiClient !== null;

  if (shouldUseRealApi) {
    if (import.meta.env.DEV) {
      console.log(`🔌 Using real API client (${normalizedBaseUrl})`);
    }
    return realApiClient as ApiClientType;
  }

  if (import.meta.env.DEV) {
    console.log(
      config.useMocks
        ? "🎭 Using mock API client (VITE_USE_MOCKS=true)"
        : "⚠️ Real API client unavailable, falling back to mock implementation"
    );
  }
  return mockApiClient;
}

// Default export: prefer real API, fallback to mocks if it fails
export const apiClient: ApiClientType = getApiClient();
