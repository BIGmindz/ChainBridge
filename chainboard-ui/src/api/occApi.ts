/**
 * OCC (Operator Control Center) API Client
 * 
 * PAC Reference: PAC-BENSON-P42 — OCC Operationalization
 * Agent: SONNY (GID-02) — UI
 * Effective Date: 2026-01-02
 * 
 * INVARIANTS:
 *   INV-OCC-001: Dashboard reads are GET-only
 *   INV-OCC-002: Kill-switch mutations require auth token
 *   INV-OCC-003: Auth endpoints manage session tokens
 * 
 * This client provides access to:
 *   - /occ/dashboard/* (GET-only, read operations)
 *   - /occ/kill-switch/* (Mutations, require auth)
 *   - /occ/auth/* (Session management)
 */

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface AgentStateResponse {
  gid: string;
  name: string;
  state: 'ACTIVE' | 'IDLE' | 'SUSPENDED' | 'TERMINATED' | 'UNKNOWN';
  health: 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'UNKNOWN';
  last_heartbeat: string | null;
  current_pac: string | null;
  current_task: string | null;
  metadata: Record<string, unknown>;
}

export interface PDOSummary {
  pdo_id: string;
  outcome: string;
  source_system: string;
  actor: string;
  recorded_at: string;
  classification: 'shadow' | 'production';
}

export interface PDOListResponse {
  pdos: PDOSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface KillSwitchStatusResponse {
  state: 'DISARMED' | 'ARMED' | 'ENGAGED' | 'COOLDOWN';
  armed_by: string | null;
  armed_at: string | null;
  engaged_by: string | null;
  engaged_at: string | null;
  reason: string | null;
  affected_agents: string[];
  cooldown_until: string | null;
}

export interface KillSwitchAuditEntry {
  timestamp: string;
  action: string;
  actor: string;
  reason: string | null;
  previous_state: string;
  new_state: string;
}

export interface OperatorSession {
  session_id: string;
  operator_id: string;
  operator_name: string;
  mode: 'JEFFREY_INTERNAL' | 'PRODUCTION' | 'READONLY';
  permissions: string[];
  created_at: string;
  expires_at: string;
  is_valid: boolean;
}

export interface OperatorModeInfo {
  mode: string;
  description: string;
  permissions: string[];
  can_create_production_pdo: boolean;
  can_engage_kill_switch: boolean;
}

export interface OCCHealthResponse {
  status: 'ok' | 'degraded' | 'unhealthy';
  timestamp: string;
  components: {
    agent_store: boolean;
    pdo_store: boolean;
    kill_switch: boolean;
    auth_service: boolean;
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// GOD-VIEW TYPES (PAC-OCC-P23)
// ═══════════════════════════════════════════════════════════════════════════════

export interface PolicyInfo {
  name: string;
  hash: string;
  full_hash: string;
}

export interface GodViewResponse {
  system_status: 'LIVE' | 'KILLED';
  kill_switch_active: boolean;
  active_agents: number;
  active_policies: PolicyInfo[];
  timestamp: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

// Session token storage
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HTTP HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

export class OCCAPIError extends Error {
  constructor(
    public statusCode: number,
    public errorCode: string,
    message: string,
  ) {
    super(message);
    this.name = 'OCCAPIError';
  }
}

async function occGet<T>(path: string, params?: Record<string, string | number | boolean>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  
  const response = await fetch(url.toString(), {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ message: response.statusText }));
    throw new OCCAPIError(
      response.status,
      errorBody.error || 'OCC_API_ERROR',
      errorBody.message || `HTTP ${response.status}`,
    );
  }
  
  return response.json();
}

async function occPost<T>(path: string, body?: Record<string, unknown>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  
  const response = await fetch(url.toString(), {
    method: 'POST',
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ message: response.statusText }));
    throw new OCCAPIError(
      response.status,
      errorBody.error || 'OCC_API_ERROR',
      errorBody.message || `HTTP ${response.status}`,
    );
  }
  
  return response.json();
}

// ═══════════════════════════════════════════════════════════════════════════════
// DASHBOARD API (GET-only — INV-OCC-001)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * PAC-OCC-P23: God-View Aggregator
 * 
 * Single endpoint for complete system state.
 * Returns: system_status, active_agents, active_policies
 */
export async function getGodView(): Promise<GodViewResponse> {
  return occGet<GodViewResponse>('/dashboard');
}

/**
 * Get OCC health status
 */
export async function getOCCHealth(): Promise<OCCHealthResponse> {
  return occGet<OCCHealthResponse>('/occ/dashboard/health');
}

/**
 * Get all agent states
 */
export async function getAgentStates(): Promise<AgentStateResponse[]> {
  return occGet<AgentStateResponse[]>('/occ/dashboard/agents');
}

/**
 * Get specific agent state
 */
export async function getAgentState(gid: string): Promise<AgentStateResponse> {
  return occGet<AgentStateResponse>(`/occ/dashboard/agents/${gid}`);
}

/**
 * Get PDO list with pagination
 */
export async function getPDOList(
  offset: number = 0,
  limit: number = 50,
  classification?: 'shadow' | 'production',
): Promise<PDOListResponse> {
  const params: Record<string, string | number> = { offset, limit };
  if (classification) {
    params.classification = classification;
  }
  return occGet<PDOListResponse>('/occ/dashboard/pdos', params);
}

/**
 * Get kill switch status
 */
export async function getKillSwitchStatus(): Promise<KillSwitchStatusResponse> {
  return occGet<KillSwitchStatusResponse>('/occ/dashboard/kill-switch/status');
}

// ═══════════════════════════════════════════════════════════════════════════════
// KILL SWITCH API (Mutations — INV-OCC-002)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Arm the kill switch (requires auth)
 */
export async function armKillSwitch(reason?: string): Promise<KillSwitchStatusResponse> {
  return occPost<KillSwitchStatusResponse>('/occ/kill-switch/arm', { reason });
}

/**
 * Engage the kill switch (requires auth + ARMED state)
 */
export async function engageKillSwitch(reason: string): Promise<KillSwitchStatusResponse> {
  return occPost<KillSwitchStatusResponse>('/occ/kill-switch/engage', { reason });
}

/**
 * Disengage the kill switch (requires auth)
 */
export async function disengageKillSwitch(reason?: string): Promise<KillSwitchStatusResponse> {
  return occPost<KillSwitchStatusResponse>('/occ/kill-switch/disengage', { reason });
}

/**
 * Disarm the kill switch (requires auth)
 */
export async function disarmKillSwitch(reason?: string): Promise<KillSwitchStatusResponse> {
  return occPost<KillSwitchStatusResponse>('/occ/kill-switch/disarm', { reason });
}

/**
 * Get kill switch audit log
 */
export async function getKillSwitchAudit(limit: number = 100): Promise<KillSwitchAuditEntry[]> {
  return occGet<KillSwitchAuditEntry[]>('/occ/kill-switch/audit', { limit });
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUTH API (Session Management — INV-OCC-003)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Login as operator
 */
export async function operatorLogin(
  operatorId: string,
  password: string,
  mode: 'JEFFREY_INTERNAL' | 'PRODUCTION' | 'READONLY' = 'JEFFREY_INTERNAL',
): Promise<OperatorSession> {
  const response = await occPost<OperatorSession>('/occ/auth/login', {
    operator_id: operatorId,
    password,
    mode,
  });
  
  // Store the session token
  if (response.session_id) {
    setAuthToken(response.session_id);
  }
  
  return response;
}

/**
 * Logout current operator
 */
export async function operatorLogout(): Promise<{ success: boolean }> {
  const response = await occPost<{ success: boolean }>('/occ/auth/logout');
  setAuthToken(null);
  return response;
}

/**
 * Get current session
 */
export async function getCurrentSession(): Promise<OperatorSession | null> {
  try {
    return await occGet<OperatorSession>('/occ/auth/session');
  } catch (e) {
    if (e instanceof OCCAPIError && e.statusCode === 401) {
      return null;
    }
    throw e;
  }
}

/**
 * Get available operator modes
 */
export async function getOperatorModes(): Promise<OperatorModeInfo[]> {
  return occGet<OperatorModeInfo[]>('/occ/auth/modes');
}
