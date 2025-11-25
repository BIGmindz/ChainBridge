/**
 * Shadow Pilot API Client
 *
 * Client service for fetching Shadow Pilot commercial impact analysis data.
 * Follows ChainBridge API patterns with proper error handling and React Query integration.
 */

import type {
    ShadowPilotFilters,
    ShadowPilotRun,
    ShadowPilotShipmentResult,
    ShadowPilotSummary
} from '../types/shadowPilot';

const BASE_URL = '/api/shadow-pilot';

class ShadowPilotAPIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ShadowPilotAPIError';
  }
}

async function apiRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ShadowPilotAPIError(
        errorData.message || `HTTP ${response.status}`,
        response.status,
        errorData.code
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ShadowPilotAPIError) {
      throw error;
    }
    throw new ShadowPilotAPIError(
      'Network error or invalid JSON response',
      0
    );
  }
}

/**
 * Fetch all available Shadow Pilot runs
 */
export async function fetchShadowPilotRuns(filters?: ShadowPilotFilters): Promise<ShadowPilotRun[]> {
  const queryParams = new URLSearchParams();

  if (filters?.prospect) queryParams.set('prospect', filters.prospect);
  if (filters?.corridor) queryParams.set('corridor', filters.corridor);
  if (filters?.status) queryParams.set('status', filters.status);
  if (filters?.period_months) queryParams.set('period_months', filters.period_months.toString());

  const endpoint = `/runs${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return apiRequest<ShadowPilotRun[]>(endpoint);
}

/**
 * Fetch summary for a specific Shadow Pilot run
 */
export async function fetchShadowPilotSummary(runId: string): Promise<ShadowPilotSummary> {
  return apiRequest<ShadowPilotSummary>(`/summaries/${runId}`);
}

/**
 * Fetch detailed shipment results for a specific run
 */
export async function fetchShadowPilotShipments(
  runId: string,
  limit?: number,
  offset?: number
): Promise<ShadowPilotShipmentResult[]> {
  const queryParams = new URLSearchParams();
  if (limit) queryParams.set('limit', limit.toString());
  if (offset) queryParams.set('offset', offset.toString());

  const endpoint = `/runs/${runId}/shipments${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return apiRequest<ShadowPilotShipmentResult[]>(endpoint);
}

/**
 * Trigger a new Shadow Pilot run
 */
export async function createShadowPilotRun(params: {
  prospect_name: string;
  corridor?: string;
  period_start: string;
  period_end: string;
}): Promise<ShadowPilotRun> {
  return apiRequest<ShadowPilotRun>('/runs', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * Export Shadow Pilot results as CSV
 */
export async function exportShadowPilotResults(
  runId: string,
  format: 'csv' | 'xlsx' = 'csv'
): Promise<Blob> {
  const response = await fetch(`${BASE_URL}/runs/${runId}/export?format=${format}`, {
    method: 'GET',
    headers: {
      'Accept': format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    },
  });

  if (!response.ok) {
    throw new ShadowPilotAPIError(
      `Export failed: ${response.statusText}`,
      response.status
    );
  }

  return response.blob();
}

/**
 * Get list of available prospects for filtering
 */
export async function fetchAvailableProspects(): Promise<string[]> {
  return apiRequest<string[]>('/prospects');
}

/**
 * Get list of available corridors for filtering
 */
export async function fetchAvailableCorridors(): Promise<string[]> {
  return apiRequest<string[]>('/corridors');
}
