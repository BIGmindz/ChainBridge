/**
 * Unified ChainBoard API Client
 *
 * Production-grade façade over the ChainBoard Control Tower backend.
 * Provides strongly-typed methods for all ChainBoard modules:
 * - ChainFreight (Shipments, Events)
 * - ChainIQ (Risk Intelligence)
 * - ChainPay (Payment Intelligence)
 * - ChainSense (IoT Telemetry)
 */

import type { CorridorMetrics, GlobalSummary } from "../../lib/metrics";
import type {
    ExceptionRow,
    Shipment,
    ShipmentIoTSnapshot,
} from "../../lib/types";
import type { AgentHealthResponse, AgentHealthSummary } from "../types/agents";
import type { TimelineEventEnvelope } from "../types/events";
import type { IoTHealthEnvelope, ShipmentIoTSnapshotEnvelope } from "../types/iot";
import type { RiskOverviewEnvelope, RiskStoryEnvelope } from "../types/iq";
import type { PaymentQueueEnvelope } from "../types/payments";
import type { ProofPack } from "../types/proofpack";
import type {
    SettlementActionKind,
    SettlementActionRequest,
    SettlementActionResponse
} from "../types/settlements";

import { httpClient } from "./http";
import { API_ROUTES, buildQueryString } from "./routes";

// ============================================================================
// Request/Response Types
// ============================================================================

export interface ShipmentFilter {
  corridor?: string;
  risk?: string | string[];
  status?: string | string[];
  search?: string;
  hasIoT?: boolean;
}

export interface ShipmentsEnvelope {
  shipments: Shipment[];
  total: number;
  filtered: boolean;
}

export interface ExceptionFilter {
  corridor?: string;
  severity?: string;
  acknowledged?: boolean;
}

export interface ExceptionsEnvelope {
  exceptions: ExceptionRow[];
  total: number;
  criticalCount: number;
}

export interface GlobalSummaryEnvelope {
  summary: GlobalSummary;
  generatedAt: string;
}

export interface CorridorMetricsEnvelope {
  corridors: CorridorMetrics[];
  total: number;
}

export interface ShipmentIoTEnvelope {
  snapshot: ShipmentIoTSnapshot;
  retrieved_at: string;
}

// ============================================================================
// Unified ChainBoard API
// ============================================================================

export const ChainboardAPI = {
  // -------------------------------------------------------------------------
  // Shipments & Manifest
  // -------------------------------------------------------------------------

  /**
   * List all shipments with optional filtering.
   */
  async listShipments(filters?: ShipmentFilter): Promise<ShipmentsEnvelope> {
    const qs = filters ? buildQueryString(filters) : "";
    return httpClient.get<ShipmentsEnvelope>(`${API_ROUTES.shipments}${qs}`);
  },

  /**
   * Get a single shipment by ID.
   */
  async getShipmentById(id: string): Promise<Shipment> {
    return httpClient.get<Shipment>(API_ROUTES.shipmentById(id));
  },

  // -------------------------------------------------------------------------
  // Events & Activity
  // -------------------------------------------------------------------------

  /**
   * List events for a specific shipment.
   */
  async listEvents(shipmentId: string): Promise<unknown> {
    return httpClient.get(API_ROUTES.eventsByShipment(shipmentId));
  },

  // -------------------------------------------------------------------------
  // Exceptions & Alerts
  // -------------------------------------------------------------------------

  /**
   * List all exceptions with optional filtering.
   */
  async listExceptions(filters?: ExceptionFilter): Promise<ExceptionsEnvelope> {
    const qs = filters ? buildQueryString(filters) : "";
    return httpClient.get<ExceptionsEnvelope>(`${API_ROUTES.exceptions}${qs}`);
  },

  // -------------------------------------------------------------------------
  // ChainIQ Risk Intelligence
  // -------------------------------------------------------------------------

  /**
   * Get ChainIQ risk overview summary.
   * Matches backend RiskOverviewResponse from api/schemas/chainboard.py
   */
  async getRiskOverview(): Promise<RiskOverviewEnvelope> {
    return httpClient.get<RiskOverviewEnvelope>(API_ROUTES.riskOverview);
  },

  /**
   * Get ChainIQ risk stories - human-readable narratives.
   * Matches backend RiskStoryResponse from api/schemas/chainboard.py
   */
  async getRiskStories(limit: number = 20): Promise<RiskStoryEnvelope> {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));

    const url = `${API_ROUTES.riskStories}?${params.toString()}`;
    return httpClient.get<RiskStoryEnvelope>(url);
  },

  /**
   * Get ChainIQ risk score for a specific shipment.
   */
  async getChainIQScore(shipmentId: string): Promise<unknown> {
    return httpClient.get(API_ROUTES.iqByShipment(shipmentId));
  },

  // -------------------------------------------------------------------------
  // ChainPay Payment Intelligence
  // -------------------------------------------------------------------------

  /**
   * Get ChainPay payment queue with holds.
   * Matches backend PaymentQueueResponse from api/schemas/chainboard.py
   */
  async getPaymentQueue(limit: number = 20): Promise<PaymentQueueEnvelope> {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));

    const url = `${API_ROUTES.paymentQueue}?${params.toString()}`;
    return httpClient.get<PaymentQueueEnvelope>(url);
  },

  /**
   * List payments for a specific shipment.
   */
  async listPayments(shipmentId: string): Promise<unknown> {
    return httpClient.get(API_ROUTES.paymentsByShipment(shipmentId));
  },

  /**
   * Get ProofPack evidence bundle for a payment milestone.
   * Contains documents, IoT signals, risk assessment, and audit trail.
   *
   * @param milestoneId - The unique milestone identifier
   * @returns ProofPack with comprehensive evidence data
   * @throws Error if milestone not found or API fails
   */
  async getProofPack(milestoneId: string): Promise<ProofPack> {
    if (!milestoneId) {
      throw new Error("milestoneId is required");
    }

    try {
      return await httpClient.get<ProofPack>(API_ROUTES.proofpack(milestoneId));
    } catch (error: unknown) {
      // Re-throw with context
      const err = error as { response?: { status?: number }; message?: string };
      if (err.response?.status === 404) {
        throw new Error(`ProofPack not found for milestone: ${milestoneId}`);
      }
      throw new Error(
        `Failed to fetch ProofPack for ${milestoneId}: ${err.message || "Unknown error"}`
      );
    }
  },

  // -------------------------------------------------------------------------
  // ChainSense IoT Telemetry
  // -------------------------------------------------------------------------

  /**
   * Get ChainSense IoT health summary.
   * Matches backend IoTHealthSummaryResponse from api/schemas/chainboard.py
   */
  async getIoTHealth(): Promise<IoTHealthEnvelope> {
    return httpClient.get<IoTHealthEnvelope>(API_ROUTES.iotHealth);
  },

  /**
   * Get IoT telemetry snapshot for a specific shipment.
   * Matches backend ShipmentIoTSnapshotResponse
   */
  async getIoTSnapshot(shipmentId: string): Promise<ShipmentIoTSnapshot | null> {
    try {
      const envelope = await httpClient.get<ShipmentIoTSnapshotEnvelope>(
        API_ROUTES.iotByShipment(shipmentId)
      );
      return envelope.snapshot;
    } catch (error: unknown) {
      // Return null if 404 (no IoT data for shipment)
      if ((error as {response?: {status?: number}})?.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  // -------------------------------------------------------------------------
  // Metrics & Overview
  // -------------------------------------------------------------------------

  /**
   * Get global summary metrics.
   */
  async getGlobalSummary(): Promise<GlobalSummary> {
    const envelope = await httpClient.get<GlobalSummaryEnvelope>(API_ROUTES.globalSummary);
    return envelope.summary;
  },

  /**
   * Get corridor-level metrics.
   */
  async getCorridorMetrics(): Promise<CorridorMetrics[]> {
    const envelope = await httpClient.get<CorridorMetricsEnvelope>(API_ROUTES.corridorMetrics);
    return envelope.corridors;
  },

  // -------------------------------------------------------------------------
  // Agent Health
  // -------------------------------------------------------------------------

  async getAgentHealthSummary(): Promise<AgentHealthSummary> {
    const payload = await httpClient.get<AgentHealthResponse>(API_ROUTES.agentHealthStatus);
    return {
      total: payload.total,
      valid: payload.valid,
      invalid: payload.invalid,
      invalidRoles: payload.invalid_roles ?? [],
    };
  },

  // -------------------------------------------------------------------------
  // Timeline Events
  // -------------------------------------------------------------------------

  /**
   * List global timeline events feed.
   * Matches backend TimelineEventResponse from api/schemas/chainboard.py
   */
  async listTimelineEvents(limit: number = 50): Promise<TimelineEventEnvelope> {
    const params = new URLSearchParams();
    params.set("limit", String(limit));

    const url = `${API_ROUTES.timelineEvents}?${params.toString()}`;
    return httpClient.get<TimelineEventEnvelope>(url);
  },

  /**
   * Get timeline events for a specific shipment by reference.
   * Matches backend /shipments/{reference}/events endpoint
   */
  async getShipmentEvents(reference: string, limit: number = 50): Promise<TimelineEventEnvelope> {
    const params = new URLSearchParams();
    params.set("limit", String(limit));

    const url = `${API_ROUTES.shipmentEvents(reference)}?${params.toString()}`;
    return httpClient.get<TimelineEventEnvelope>(url);
  },

  // -------------------------------------------------------------------------
  // Alerts & Triage
  // -------------------------------------------------------------------------

  /**
   * List alerts with optional filtering by status, source, and severity.
   * Returns alerts sorted by createdAt descending (most recent first).
   */
  async listAlerts(params?: {
    status?: import("../types/alerts").AlertStatus;
    source?: import("../types/alerts").AlertSource;
    severity?: import("../types/alerts").AlertSeverity;
    limit?: number;
  }): Promise<import("../types/alerts").AlertsEnvelope> {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.source) search.set("source", params.source);
    if (params?.severity) search.set("severity", params.severity);
    if (params?.limit) search.set("limit", String(params.limit));

    const qs = search.toString();
    const path = qs ? `${API_ROUTES.alerts}?${qs}` : API_ROUTES.alerts;

    return httpClient.get<import("../types/alerts").AlertsEnvelope>(path);
  },

  /**
   * Get a single alert by ID.
   */
  async getAlert(alertId: string): Promise<import("../types/alerts").ControlTowerAlert> {
    const res = await httpClient.get<{ alert: import("../types/alerts").ControlTowerAlert }>(
      API_ROUTES.alertDetail(alertId)
    );
    return res.alert;
  },

  // -------------------------------------------------------------------------
  // Work Queue & Triage
  // -------------------------------------------------------------------------

  /**
   * Get alert work queue with optional filters.
   * Returns alerts enriched with triage context (owner, notes, actions).
   */
  async getAlertWorkQueue(params?: {
    ownerId?: string;
    status?: import("../types/alerts").AlertStatus;
    source?: import("../types/alerts").AlertSource;
    severity?: import("../types/alerts").AlertSeverity;
    limit?: number;
  }): Promise<import("../types/alerts").AlertWorkQueueResponse> {
    const search = new URLSearchParams();
    if (params?.ownerId) search.set("owner_id", params.ownerId);
    if (params?.status) search.set("status", params.status);
    if (params?.source) search.set("source", params.source);
    if (params?.severity) search.set("severity", params.severity);
    if (params?.limit) search.set("limit", String(params.limit));

    const qs = search.toString();
    const path = qs ? `${API_ROUTES.triageWorkQueue}?${qs}` : API_ROUTES.triageWorkQueue;

    return httpClient.get<import("../types/alerts").AlertWorkQueueResponse>(path);
  },

  /**
   * Assign or unassign an alert to an owner.
   */
  async assignAlert(
    id: string,
    body: {
      ownerId?: string | null;
      ownerName?: string | null;
      ownerEmail?: string | null;
      ownerTeam?: string | null;
    }
  ): Promise<import("../types/alerts").AlertWorkItem> {
    return httpClient.post<import("../types/alerts").AlertWorkItem>(
      API_ROUTES.alertAssign(id),
      {
        owner_id: body.ownerId,
        owner_name: body.ownerName,
        owner_email: body.ownerEmail,
        owner_team: body.ownerTeam,
      }
    );
  },

  /**
   * Add a note to an alert.
   */
  async addAlertNote(
    id: string,
    body: {
      message: string;
      authorId: string;
      authorName: string;
      authorEmail?: string;
      authorTeam?: string;
    }
  ): Promise<import("../types/alerts").AlertWorkItem> {
    return httpClient.post<import("../types/alerts").AlertWorkItem>(
      API_ROUTES.alertNotes(id),
      {
        message: body.message,
        author_id: body.authorId,
        author_name: body.authorName,
        author_email: body.authorEmail,
        author_team: body.authorTeam,
      }
    );
  },

  /**
   * Update alert status (acknowledge, resolve, etc.).
   */
  async updateAlertStatus(
    id: string,
    body: {
      status: import("../types/alerts").AlertStatus;
      actorId: string;
      actorName: string;
      actorEmail?: string;
      actorTeam?: string;
    }
  ): Promise<import("../types/alerts").AlertWorkItem> {
    return httpClient.post<import("../types/alerts").AlertWorkItem>(
      API_ROUTES.alertStatus(id),
      {
        status: body.status,
        actor_id: body.actorId,
        actor_name: body.actorName,
        actor_email: body.actorEmail,
        actor_team: body.actorTeam,
      }
    );
  },

  // -------------------------------------------------------------------------
  // Settlement Actions
  // -------------------------------------------------------------------------

  /**
   * Post a settlement operator action
   *
   * Executes an operator action on a payment milestone (escalate, review, request docs).
   * Returns acceptance confirmation from backend.
   */
  async postSettlementAction(
    milestoneId: string,
    action: SettlementActionKind,
    body: SettlementActionRequest
  ): Promise<SettlementActionResponse> {
    const urlMap = {
      escalate_to_risk: API_ROUTES.settlementActions.escalate(milestoneId),
      mark_manually_reviewed: API_ROUTES.settlementActions.markReviewed(milestoneId),
      request_documentation: API_ROUTES.settlementActions.requestDocs(milestoneId),
    } as const;

    const url = urlMap[action];

    return httpClient.post<SettlementActionResponse>(url, {
      reason: body.reason,
      requested_by: body.requestedBy,
    });
  },

  /**
   * Get recent settlement actions
   *
   * Retrieves the most recent operator actions for audit trail display.
   */
  async getRecentSettlementActions(limit: number = 20): Promise<SettlementActionResponse[]> {
    return httpClient.get<SettlementActionResponse[]>(
      API_ROUTES.settlementActions.recent(limit)
    );
  },
};
