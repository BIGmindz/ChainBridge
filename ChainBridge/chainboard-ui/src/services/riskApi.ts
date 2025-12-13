/**
 * ChainIQ Risk API Client
 *
 * API service for fetching risk assessments from the ChainIQ Risk API.
 * All calls go through the main API gateway (Cody's routes).
 *
 * Endpoints:
 * - POST /api/v1/risk/score
 * - POST /api/v1/risk/simulation
 * - GET /api/v1/risk/health
 */

import type {
  BackendRiskScoreResponse,
  RiskHealthResponse,
  ShipmentRiskAssessment,
  ShipmentRiskContext,
} from "../types/risk";
import { mapBackendAssessment, mapContextToBackend } from "../types/risk";

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
const API_BASE_URL = RAW_BASE_URL || "http://localhost:8001";
const DEFAULT_TIMEOUT_MS = 15_000;

// =============================================================================
// ERROR HANDLING
// =============================================================================

class RiskApiError extends Error {
  status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "RiskApiError";
    this.status = status;
  }
}

async function safeReadError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (payload?.detail) {
      return typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    }
    if (payload?.message) {
      return payload.message;
    }
  } catch {
    // Ignore JSON parse errors
  }
  return `Request failed with status ${response.status}`;
}

// =============================================================================
// HTTP HELPERS
// =============================================================================

async function httpPost<T>(
  path: string,
  body: unknown,
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = `${API_BASE_URL}${path}`;
    console.log(`[riskApi] POST ${path}`, { source: "api" });

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      const message = await safeReadError(response);
      throw new RiskApiError(message, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof RiskApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new RiskApiError("Request timed out while contacting ChainIQ Risk API.");
    }
    throw new RiskApiError(error instanceof Error ? error.message : "Network request failed.");
  } finally {
    clearTimeout(timeout);
  }
}

async function httpGet<T>(
  path: string,
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = `${API_BASE_URL}${path}`;
    console.log(`[riskApi] GET ${path}`, { source: "api" });

    const response = await fetch(url, {
      headers: {
        Accept: "application/json",
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      const message = await safeReadError(response);
      throw new RiskApiError(message, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof RiskApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new RiskApiError("Request timed out while contacting ChainIQ Risk API.");
    }
    throw new RiskApiError(error instanceof Error ? error.message : "Network request failed.");
  } finally {
    clearTimeout(timeout);
  }
}

// =============================================================================
// RISK API FUNCTIONS
// =============================================================================

/**
 * Score a single shipment's risk using ChainIQ
 *
 * @param context - Shipment context for risk scoring
 * @returns Risk assessment with score, decision, factors, and tags
 */
export async function fetchShipmentRisk(
  context: ShipmentRiskContext
): Promise<ShipmentRiskAssessment> {
  const payload = {
    shipments: [mapContextToBackend(context)],
    include_factors: true,
    max_factors: 3,
  };

  const response = await httpPost<BackendRiskScoreResponse>("/api/v1/risk/score", payload);

  if (!response.assessments || response.assessments.length === 0) {
    throw new RiskApiError("No risk assessment returned from ChainIQ");
  }

  return mapBackendAssessment(response.assessments[0]);
}

/**
 * Score multiple shipments' risk in batch
 *
 * @param contexts - Array of shipment contexts
 * @param maxFactors - Maximum number of factors to include per assessment
 * @returns Array of risk assessments
 */
export async function fetchBatchShipmentRisk(
  contexts: ShipmentRiskContext[],
  maxFactors: number = 3
): Promise<ShipmentRiskAssessment[]> {
  const payload = {
    shipments: contexts.map(mapContextToBackend),
    include_factors: true,
    max_factors: maxFactors,
  };

  const response = await httpPost<BackendRiskScoreResponse>("/api/v1/risk/score", payload);

  if (!response.assessments) {
    throw new RiskApiError("No risk assessments returned from ChainIQ");
  }

  return response.assessments.map(mapBackendAssessment);
}

/**
 * Check ChainIQ Risk API health status
 *
 * @returns Health status including model version and status
 */
export async function fetchRiskHealth(): Promise<RiskHealthResponse> {
  return httpGet<RiskHealthResponse>("/api/v1/risk/health");
}

// =============================================================================
// SIMULATION API (TODO)
// =============================================================================

/**
 * Run what-if simulation comparing carriers/routes/timing
 * TODO: Implement when simulation endpoint is ready
 */
export async function fetchRiskSimulation(
  _baseContext: ShipmentRiskContext,
  _scenarios: Array<Partial<ShipmentRiskContext>>
): Promise<ShipmentRiskAssessment[]> {
  // TODO: Wire to POST /api/v1/risk/simulation when available
  throw new RiskApiError("Risk simulation not yet implemented");
}
