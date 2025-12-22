const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// NOTE (SONNY/GID-02): Endpoint path to be aligned with Cody's IoT facade.
// Backend exposes /api/iot/health, so we align here.
export const IOT_HEALTH_PATH = '/api/iot/health';

export const IOT_HEALTH_URL = `${API_BASE_URL}${IOT_HEALTH_PATH}`;

export const OPERATOR_RISK_SNAPSHOT_PATH = (intentId: string) =>
  `/api/operator/settlements/${encodeURIComponent(intentId)}/risk_snapshot`;

export const operatorRiskSnapshotUrl = (intentId: string) =>
  `${API_BASE_URL}${OPERATOR_RISK_SNAPSHOT_PATH(intentId)}`;
