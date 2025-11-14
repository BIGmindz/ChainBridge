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

import {
  Shipment,
  ShipmentStatus,
  ExceptionRow,

  NetworkVitals,
  ShipmentEvent,
  RiskAssessment,
  PaymentMilestone,
  PaymentState,
  ProofPackSummary,
  ProofPackResponse,
  CreateProofPackPayload,
} from "../types";
import type { GlobalSummary, CorridorMetrics } from "../lib/metrics";
import type { IoTHealthSummary, ShipmentIoTSnapshot } from "../lib/iot";
import { realApiClient } from "./realApiClient";
import { config } from "../config/env";

export interface MetricsApi {
  getGlobalSummary(): Promise<GlobalSummary>;
  getCorridorMetrics(): Promise<CorridorMetrics[]>;
  getIoTHealthSummary(): Promise<IoTHealthSummary>;
  getShipmentIoTSnapshot(shipmentId: string): Promise<ShipmentIoTSnapshot | null>;
}

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

function generateEvents(hoursAgo: number): ShipmentEvent[] {
  const events = [
    { event_type: "order_placed", offset: hoursAgo },
    { event_type: "pickup_scheduled", offset: hoursAgo - 12 },
    { event_type: "pickup_confirmed", offset: hoursAgo - 10 },
    { event_type: "in_transit", offset: hoursAgo - 6 },
  ];

  if (hoursAgo < 2) {
    events.push({ event_type: "delivery_attempted", offset: 1 });
  }

  return events.map((e) => ({
    event_type: e.event_type,
    timestamp: new Date(Date.now() - e.offset * 3600000).toISOString(),
  }));
}

function generateRiskAssessment(riskScore?: number): RiskAssessment {
  const score = riskScore ?? randomInt(10, 95);
  let category: "low" | "medium" | "high";

  if (score < 35) category = "low";
  else if (score < 70) category = "medium";
  else category = "high";

  return {
    risk_score: score,
    risk_category: category,
    recommended_action:
      category === "high"
        ? "Hold for manual review"
        : category === "medium"
          ? "Monitor closely"
          : "Proceed normally",
    confidence: randomInt(75, 99),
  };
}

function generatePaymentSchedule(): PaymentMilestone[] {
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

function generateProofPack(): ProofPackSummary {
  return {
    pack_id: generateProofPackId(),
    manifest_hash: generateManifestHash(),
    signature_status: Math.random() > 0.05 ? "VERIFIED" : "FAILED",
    created_at: new Date(Date.now() - 48 * 3600000).toISOString(),
  };
}

/**
 * Generate a mock shipment with realistic data distribution
 */
function generateShipment(overrides?: Partial<Shipment>): Shipment {
  const hoursAgo = randomInt(0, 168); // 0-7 days
  const riskScore = randomInt(10, 95);

  return {
    shipment_id: generateShipmentId(),
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
    created_at: new Date(Date.now() - (hoursAgo + 24) * 3600000).toISOString(),
    events: generateEvents(hoursAgo),
    risk: generateRiskAssessment(riskScore),
    payment_state: ["not_started", "in_progress", "partially_paid", "completed"][
      randomInt(0, 3)
    ] as PaymentState,
    payment_schedule: generatePaymentSchedule(),
    total_value_usd: randomInt(5000, 50000),
    proofpack: generateProofPack(),
    ...overrides,
  };
}

/**
 * Convert Shipment to ExceptionRow for exceptions view
 */
function shipmentToExceptionRow(shipment: Shipment): ExceptionRow {
  const hoursAgo =
    (Date.now() - new Date(shipment.last_update_timestamp).getTime()) / 3600000;

  return {
    shipment_id: shipment.shipment_id,
    lane: `${shipment.origin} → ${shipment.destination}`,
    current_status: shipment.current_status,
    risk_score: shipment.risk.risk_score,
    payment_state: shipment.payment_state,
    age_of_issue: formatAge(hoursAgo),
    issue_types: [],
    last_update: new Date(shipment.last_update_timestamp).toLocaleString(),
  };
}

function formatAge(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

// ============================================================================
// API CLIENT CLASS
// ============================================================================

class MockApiClient {
  private mockShipments: Map<string, Shipment> = new Map();
  private mockExceptions: ExceptionRow[] = [];

  constructor() {
    this.initializeMockData();
  }

  private initializeMockData(): void {
    // Generate 50 shipments with realistic distribution
    const shipments: Shipment[] = Array.from({ length: 50 }, () => generateShipment());

    shipments.forEach((ship) => {
      this.mockShipments.set(ship.shipment_id, ship);
    });

    // Generate exceptions (shipments with risk or payment issues)
    this.mockExceptions = shipments
      .filter((s) => s.risk.risk_score > 70 || s.payment_state === "blocked")
      .map(shipmentToExceptionRow);
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

    const atRiskShipments = allShipments.filter((s) => s.risk.risk_score >= 70);
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
        const minOk = filters.risk_min === undefined || e.risk_score >= filters.risk_min;
        const maxOk = filters.risk_max === undefined || e.risk_score <= filters.risk_max;
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
  }): Promise<Shipment[]> {
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
        const minOk = filters.risk_min === undefined || s.risk.risk_score >= filters.risk_min;
        const maxOk = filters.risk_max === undefined || s.risk.risk_score <= filters.risk_max;
        return minOk && maxOk;
      });
    }

    return results;
  }

  /**
   * GET /shipments/:id - Get single shipment detail
   */
  async getShipmentDetail(shipmentId: string): Promise<Shipment | null> {
    await this.delay(200);
    return this.mockShipments.get(shipmentId) || null;
  }

  /**
   * POST /proofpacks/run - Create a new proof pack
   */
  async createProofPack(payload: {
    shipment_id: string;
    events: ShipmentEvent[];
    risk_score?: number;
    policy_version?: string;
  }): Promise<ProofPackResponse> {
    await this.delay(300);

    const mockProofPack: ProofPackResponse = {
      pack_id: `pp_${Math.random().toString(36).substr(2, 9)}`,
      shipment_id: payload.shipment_id,
      generated_at: new Date().toISOString(),
      manifest_hash: `0x${Math.random().toString(16).substr(2, 64)}`,
      status: "SUCCESS",
      message: "Proof pack generated successfully",
      signature_status: "VERIFIED",
      events: payload.events,
    };

    console.log(`✅ Mock: Created proof pack ${mockProofPack.pack_id}`);
    return mockProofPack;
  }

  /**
   * GET /proofpacks/{pack_id} - Get a proof pack by ID
   */
  async getProofPack(packId: string): Promise<ProofPackResponse> {
    await this.delay(200);

    // Return a realistic mock proof pack
    const mockProofPack: ProofPackResponse = {
      pack_id: packId,
      shipment_id: `ship_${Math.random().toString(36).substr(2, 9)}`,
      generated_at: new Date(Date.now() - Math.random() * 86400000).toISOString(),
      manifest_hash: `0x${Math.random().toString(16).substr(2, 64)}`,
      status: Math.random() > 0.1 ? "SUCCESS" : "PENDING",
      message:
        Math.random() > 0.1
          ? "Proof pack verified"
          : "Awaiting blockchain confirmation",
      signature_status: Math.random() > 0.05 ? "VERIFIED" : "PENDING",
      events: [
        {
          event_type: "pickup",
          timestamp: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          event_type: "in_transit",
          timestamp: new Date(Date.now() - 43200000).toISOString(),
        },
        {
          event_type: "delivery",
          timestamp: new Date(Date.now() - 3600000).toISOString(),
        },
      ],
    };

    console.log(`✅ Mock: Retrieved proof pack ${packId}`);
    return mockProofPack;
  }

  /**
   * Simulate network delay
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

// Export singleton instance


// Export singleton instances
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
  }): Promise<Shipment[]>;

  // Single shipment detail
  getShipmentDetail(shipmentId: string): Promise<Shipment | null>;

  // Proof pack operations
  getProofPack(packId: string): Promise<ProofPackResponse>;
  createProofPack(payload: CreateProofPackPayload): Promise<ProofPackResponse>;
}

// ============================================================================
// API CLIENT FACTORY - SWITCHES BETWEEN MOCK AND REAL
// ============================================================================



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
  if (config.useMocks) {
    if (import.meta.env.DEV) {
      console.log("🎭 Using mock API client (VITE_USE_MOCKS=true)");
    }
    return mockApiClient;
  }

  if (import.meta.env.DEV) {
    console.log(`🔌 Using real API client (${config.apiBaseUrl})`);
  }
  return realApiClient as unknown as ApiClientType;
}

// Default export: prefer real API, fallback to mocks if it fails
export const apiClient: ApiClientType = getApiClient();
