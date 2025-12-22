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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function pickNumber(record: Record<string, unknown>, keys: string[], fallback = 0): number {
  for (const key of keys) {
    const raw = record[key];
    if (typeof raw === "number" && !Number.isNaN(raw)) {
      return raw;
    }
    if (typeof raw === "string" && raw.trim()) {
      const parsed = Number(raw);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }
  }
  return fallback;
}

function pickString(record: Record<string, unknown>, keys: string[], fallback?: string): string | undefined {
  for (const key of keys) {
    const raw = record[key];
    if (typeof raw === "string" && raw.trim().length > 0) {
      return raw;
    }
  }
  return fallback;
}

function normalizeAnomalies(value: unknown): IoTHealthSummary["anomalies"] {
  if (!Array.isArray(value)) {
    return [];
  }

  const anomalies: IoTHealthSummary["anomalies"] = [];

  value.forEach((item) => {
    if (!isRecord(item)) {
      return;
    }

    const deviceId = pickString(item, ["deviceId", "device_id"], "UNKNOWN-DEVICE") ?? "UNKNOWN-DEVICE";
    const severityRaw = (pickString(item, ["severity"], "LOW") ?? "LOW").toUpperCase();
    const severity: IoTHealthSummary["anomalies"][number]["severity"] = [
      "LOW",
      "MEDIUM",
      "HIGH",
      "CRITICAL",
    ].includes(severityRaw as never)
      ? (severityRaw as IoTHealthSummary["anomalies"][number]["severity"])
      : "LOW";

    anomalies.push({
      deviceId,
      severity,
      label: pickString(item, ["label", "title", "description"], deviceId) ?? deviceId,
      lastSeen:
        pickString(item, ["lastSeen", "last_seen", "detected_at"], new Date().toISOString()) ??
        new Date().toISOString(),
      shipmentReference: pickString(item, ["shipmentReference", "shipment_reference", "shipmentId"]),
      lane: pickString(item, ["lane", "corridor", "route"]),
    });
  });

  return anomalies;
}

function normalizeIoTHealth(payload: unknown): IoTHealthSummary {
  const root = isRecord(payload) ? payload : {};
  const summaryCandidate = [
    root.summary,
    root.iot_health,
    root.health,
    root.data,
    root,
  ].find((entry) => isRecord(entry)) as Record<string, unknown> | undefined;

  const summary = summaryCandidate ?? {};

  const fleetId = pickString(summary, ["fleetId", "fleet_id"], "CHAINBOARD-FLEET") ?? "CHAINBOARD-FLEET";
  const asOf = pickString(summary, ["asOf", "as_of", "generatedAt", "generated_at"], new Date().toISOString()) ??
    new Date().toISOString();

  const online = pickNumber(summary, ["online", "device_count_active", "devices_online", "active_sensors"], 0);
  const offline = pickNumber(summary, ["offline", "device_count_offline", "devices_offline", "critical_alerts_last_24h"], 0);
  const degraded = pickNumber(
    summary,
    ["degraded", "devices_degraded", "devices_degraded_count", "devices_stale_env", "devices_stale_gps"],
    0
  );

  const deviceCount = pickNumber(
    summary,
    [
      "deviceCount",
      "device_count",
      "device_total",
      "total_devices",
      "device_count_total",
      "shipments_with_iot",
    ],
    online + offline + degraded
  );

  const latencySeconds = pickNumber(
    summary,
    ["latencySeconds", "latency_seconds", "latency", "last_ingest_age_seconds"],
    pickNumber(root, ["latencySeconds", "latency_seconds"], 0)
  );

  const anomalies = normalizeAnomalies(summary.anomalies ?? root.anomalies);

  return {
    fleetId,
    asOf,
    deviceCount,
    online,
    offline,
    degraded: degraded || Math.max(deviceCount - online - offline, 0),
    anomalies,
    latencySeconds: latencySeconds || undefined,
  };
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
  const endpoints = ["/iot/health-summary", "/iot/health", "/metrics/iot/summary"] as const;

  let lastError: unknown;

  for (const endpoint of endpoints) {
    try {
      const payload = await request<unknown>(endpoint);
      return normalizeIoTHealth(payload);
    } catch (error) {
      lastError = error;
      if (import.meta.env.DEV) {
        console.warn(`[realApiClient] IoT health request failed for ${endpoint}`, error);
      }
      continue;
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error("Unable to load IoT health summary from ChainBoard API.");
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
