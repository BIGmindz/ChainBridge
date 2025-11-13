/**
 * Real API Client
 *
 * Fetches data from real FastAPI backend endpoints.
 * Designed to be swappable with MockApiClient via factory pattern.
 */

import {
  ProofPackResponse,
  ShipmentProofSummary,
  CreateProofPackPayload,
} from "../types";
import { config } from "../config/env";

/**
 * Helper to fetch JSON from API endpoint with error handling
 */
async function fetchJson<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${config.apiBaseUrl}${endpoint}`;

  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...((options?.headers as Record<string, string>) || {}),
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(
        `API error: ${response.status} ${response.statusText} at ${endpoint}`
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to fetch ${endpoint}: ${message}`);
  }
}

/**
 * Map ProofPackResponse (from backend) → ShipmentProofSummary (for UI)
 */
export function mapProofPackResponseToUI(
  response: ProofPackResponse
): ShipmentProofSummary {
  return {
    packId: response.pack_id,
    shipmentId: response.shipment_id,
    manifestHash: response.manifest_hash,
    generatedAt: response.generated_at,
    status: response.status,
    message: response.message,
    signatureStatus: response.signature_status,
    events: response.events,
  };
}

/**
 * Real API Client - connects to FastAPI backend
 *
 * Methods:
 * - getProofPack(packId): GET /proofpacks/{pack_id}
 * - createProofPack(payload): POST /proofpacks/run
 */
export class RealApiClient {
  /**
   * Fetch a single proof pack by ID
   *
   * GET /proofpacks/{pack_id}
   *
   * @param packId - The proof pack ID (e.g., "pp_abc123")
   * @returns ProofPackResponse from backend
   * @throws Error if API call fails
   */
  async getProofPack(packId: string): Promise<ProofPackResponse> {
    console.log(`📡 Fetching proof pack: ${packId} from ${config.apiBaseUrl}`);

    const response = await fetchJson<ProofPackResponse>(
      `/proofpacks/${packId}`
    );

    console.log(`✅ Proof pack retrieved: ${packId}`);
    return response;
  }

  /**
   * Create a new proof pack
   *
   * POST /proofpacks/run
   *
   * @param payload - Proof pack creation payload
   * @returns ProofPackResponse from backend
   * @throws Error if API call fails
   */
  async createProofPack(
    payload: CreateProofPackPayload
  ): Promise<ProofPackResponse> {
    console.log(`📡 Creating proof pack for shipment: ${payload.shipment_id}`);

    const response = await fetchJson<ProofPackResponse>("/proofpacks/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    console.log(`✅ Proof pack created: ${response.pack_id}`);
    return response;
  }

  /**
   * Test connectivity to backend
   * Useful for health checks
   */
  async healthCheck(): Promise<boolean> {
    try {
      await fetch(`${config.apiBaseUrl}/docs`, { method: "HEAD" });
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const realApiClient = new RealApiClient();
