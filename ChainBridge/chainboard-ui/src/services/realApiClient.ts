// src/services/realApiClient.ts
// Strongly-typed client for the ChainBoard FastAPI backend.

import { IoTHealthSummary, ShipmentIoTSnapshot } from "../lib/iot";
import { GlobalSummary, CorridorMetrics } from "../lib/metrics";
import type { RiskOverviewSummary } from "../lib/risk";
import { Shipment, RiskCategory, PaymentState, ExceptionRow } from "../lib/types";

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

function ensureChainboardBase(url: string): string {
  const normalized = url.endsWith("/") ? url.slice(0, -1) : url;
  if (normalized.endsWith("/chainboard")) {
    return normalized;
  }
  if (normalized.endsWith("/api")) {
    return `${normalized}/chainboard`;
  }
  if (normalized.includes("/chainboard")) {
    return normalized;
  }
  return `${normalized}/api/chainboard`;
}

const API_BASE_URL = ensureChainboardBase(RAW_BASE_URL);

if (import.meta.env.DEV) {
  console.log(`[realApiClient] Targeting ChainBoard API at ${API_BASE_URL}`);
}

type ShipmentsFilter = {
  corridor?: string;
  riskCategory?: RiskCategory;
  paymentState?: PaymentState;
  hasIoT?: boolean;
};

type ExceptionsFilter = {
  corridorId?: string;
  severity?: RiskCategory;
  acknowledged?: boolean;
};

function mapShipmentsFiltersToBackend(filters: ShipmentsFilter): Record<string, string | string[]> {
  const params: Record<string, string | string[]> = {};

  if (filters.corridor) {
    params["corridor"] = filters.corridor;
  }

  if (filters.riskCategory) {
    // Backend expects risk as List[RiskCategory], so send as array
    params["risk"] = [filters.riskCategory];
  }

  // Backend also supports status + search, which aren't exposed yet in ShipmentsFilter.
  return params;
}

function buildQuery(params: Record<string, string | string[]>): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;

    if (Array.isArray(value)) {
      // Backend expects repeated params for lists: ?risk=high&risk=medium
      value.forEach((v) => search.append(key, String(v)));
    } else {
      search.append(key, String(value));
    }
  }

  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!res.ok) {
    let body = "";
    try {
      body = await res.text();
    } catch {
      // ignore
    }
    throw new Error(
      `[realApiClient] Request failed ${res.status} ${res.statusText}: ${body}`
    );
  }

  return (await res.json()) as T;
}

interface GlobalSummaryEnvelope {
  summary: GlobalSummary;
  generatedAt: string;
}

interface CorridorMetricsEnvelope {
  corridors: CorridorMetrics[];
  total: number;
}

interface IoTHealthSummaryEnvelope {
  iot_health: IoTHealthSummary;
  generatedAt: string;
}

interface ShipmentIoTSnapshotEnvelope {
  snapshot: ShipmentIoTSnapshot;
  retrieved_at: string;
}

interface ShipmentsEnvelope {
  shipments: Shipment[];
  total: number;
  filtered: boolean;
}

interface ExceptionsEnvelope {
  exceptions: ExceptionRow[];
  total: number;
  criticalCount: number;
}

interface RiskOverviewEnvelope {
  overview: RiskOverviewSummary;
  generatedAt: string;
}

// -------- Metrics / Overview --------

export async function fetchGlobalSummary(): Promise<GlobalSummary> {
  const envelope = await request<GlobalSummaryEnvelope>("/metrics/summary");
  return envelope.summary;
}

export async function fetchCorridorMetrics(): Promise<CorridorMetrics[]> {
  const envelope = await request<CorridorMetricsEnvelope>("/metrics/corridors");
  return envelope.corridors;
}

export async function fetchIoTHealthSummary(): Promise<IoTHealthSummary> {
  try {
    const payload = await request<IoTHealthSummaryEnvelope>("/iot/health");
    return payload.iot_health;
  } catch (error) {
    const isNotFound =
      error instanceof Error && /404/.test(error.message ?? "");
    if (!isNotFound) {
      throw error;
    }

    const fallback = await request<IoTHealthSummaryEnvelope>("/metrics/iot/summary");
    return fallback.iot_health;
  }
}

export async function fetchShipmentIoTSnapshot(
  shipmentId: string
): Promise<ShipmentIoTSnapshot> {
  const envelope = await request<ShipmentIoTSnapshotEnvelope>(
    `/metrics/iot/shipments/${encodeURIComponent(shipmentId)}`
  );
  return envelope.snapshot;
}

// -------- Shipments & Exceptions --------

export async function fetchShipments(
  filters: ShipmentsFilter = {}
): Promise<ShipmentsEnvelope> {
  const backendFilters = mapShipmentsFiltersToBackend(filters);
  const qs = buildQuery(backendFilters);
  const path = `/shipments${qs}`;

  if (import.meta.env.DEV) {
    console.log(`[realApiClient] Fetching shipments: ${path}`);
  }

  const envelope = await request<ShipmentsEnvelope>(path);

  if (import.meta.env.DEV) {
    console.log(`[realApiClient] Received ${envelope.shipments.length} shipments (total: ${envelope.total})`);
  }

  return envelope;
}

export async function fetchShipmentById(id: string): Promise<Shipment> {
  return request<Shipment>(`/shipments/${encodeURIComponent(id)}`);
}

export async function fetchExceptions(
  _filters: ExceptionsFilter = {}
): Promise<ExceptionRow[]> {
  const qs = buildQuery({});
  const envelope = await request<ExceptionsEnvelope>(`/exceptions${qs}`);
  return envelope.exceptions;
}

export async function fetchRiskOverview(): Promise<RiskOverviewSummary> {
  const envelope = await request<RiskOverviewEnvelope>("/risk/overview");
  return envelope.overview;
}
