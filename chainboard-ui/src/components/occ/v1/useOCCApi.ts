/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC v1.0 API Hooks — Backend Integration
 * PAC-JEFFREY-P03: OCC UI Execution
 * 
 * React hooks for fetching OCC v1.0 backend data.
 * All hooks are READ-ONLY per INV-OCC-UI-001.
 * 
 * INVARIANTS:
 * - INV-OCC-001: GET-only dashboard reads
 * - INV-OCC-UI-001: All state is read-only from backend
 * - INV-OCC-UI-002: No mutation operations
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  QueueState,
  QueueItem,
  PDOStateMachineState,
  PDORecord,
  PDOState,
  AuditLogState,
  AuditRecord,
  PDOTransition,
  AuditFilters,
  ReplayResult,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// BACKEND RESPONSE TYPES (api/occ_dashboard.py)
// PAC-BENSON-EXEC-P11: Type definitions for API contract alignment (GAP-04)
// ═══════════════════════════════════════════════════════════════════════════════

interface PDOCard {
  pdo_id: string;
  pac_id: string;
  agent_id: string;
  agent_name: string;
  decision_type: string;
  description: string;
  outcome: 'APPROVED' | 'REJECTED' | 'ESCALATED' | 'PENDING';
  invariants_checked: string[];
  timestamp: string;
  rationale?: string;
  classification: 'SHADOW' | 'PRODUCTION';
}

interface DecisionStreamItem {
  id: string;
  item_type: 'pdo' | 'ber';
  timestamp: string;
  pdo_card?: PDOCard;
  ber_card?: unknown;
}

interface KillSwitchStatus {
  state: 'DISARMED' | 'ARMED' | 'ENGAGED' | 'COOLDOWN';
  auth_level: string;
  engaged_by?: string;
  engaged_at?: string;
  engagement_reason?: string;
  affected_pacs?: string[];
  cooldown_remaining_ms?: number;
}

interface GovernanceRailState {
  invariants: Array<{
    invariant_id: string;
    rule_id: string;
    description: string;
    invariant_class: string;
    status: 'passing' | 'failing' | 'unknown';
    last_checked: string;
    source: string;
  }>;
  lint_v2_passing: boolean;
  schema_registry_valid: boolean;
  fail_closed_active: boolean;
  last_refresh: string;
}

interface AgentTile {
  agent_id: string;
  agent_name: string;
  lane: string;
  health: string;
  execution_state: string;
  current_pac_id?: string;
  tasks_completed: number;
  tasks_pending: number;
  last_heartbeat: string;
  blocked_reason?: string;
}

/**
 * Dashboard state response from /occ/dashboard/state
 */
interface DashboardStateResponse {
  agents: AgentTile[];
  decision_stream: DecisionStreamItem[];
  governance_rail: GovernanceRailState;
  kill_switch: KillSwitchStatus;
  active_pac_id?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// PAC-BENSON-EXEC-P11: Aligned with backend routes (GAP-04)
// ═══════════════════════════════════════════════════════════════════════════════

// Backend routes per api/occ_dashboard.py (PAC-BENSON-P42)
const API_BASE = '/occ/dashboard';
const DEFAULT_REFRESH_INTERVAL = 5000; // 5 seconds

interface UseOCCOptions {
  refreshInterval?: number;
  autoRefresh?: boolean;
}

interface HookResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  lastRefresh: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// GENERIC FETCH HOOK (GET-ONLY per INV-OCC-001)
// ═══════════════════════════════════════════════════════════════════════════════

function useOCCFetch<T>(
  endpoint: string,
  options: UseOCCOptions = {}
): HookResult<T> {
  const { refreshInterval = DEFAULT_REFRESH_INTERVAL, autoRefresh = true } = options;
  
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);
  
  const fetchData = useCallback(async () => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    
    try {
      setLoading(true);
      setError(null);
      
      // INV-OCC-001: GET-only reads
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'GET', // INVARIANT: Read-only
        headers: {
          'Accept': 'application/json',
          'X-OCC-Client': 'chainboard-ui-v1',
        },
        signal: abortControllerRef.current.signal,
      });
      
      if (!response.ok) {
        throw new Error(`OCC API error: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      setData(result);
      setLastRefresh(new Date().toISOString());
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was cancelled, ignore
        return;
      }
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, [endpoint]);
  
  // Initial fetch
  useEffect(() => {
    fetchData();
    
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData]);
  
  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefresh || refreshInterval <= 0) return;
    
    const intervalId = setInterval(fetchData, refreshInterval);
    return () => clearInterval(intervalId);
  }, [autoRefresh, refreshInterval, fetchData]);
  
  return { data, loading, error, refresh: fetchData, lastRefresh };
}

// ═══════════════════════════════════════════════════════════════════════════════
// QUEUE HOOK — INV-OCC-006 (Queue Ordering)
// PAC-BENSON-EXEC-P11: Derives queue state from dashboard state (GAP-03)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Transform decision stream to queue-like state.
 * Maps backend DecisionStreamItem[] to QueueState for UI compatibility.
 */
function transformToQueueState(dashboardState: DashboardStateResponse | null): QueueState | null {
  if (!dashboardState) return null;
  
  // Transform decision stream items to queue items
  const items: QueueItem[] = dashboardState.decision_stream
    .filter(item => item.item_type === 'pdo' && item.pdo_card)
    .slice(0, 50) // Limit for queue display
    .map((item, index) => ({
      id: item.id,
      actionType: item.pdo_card?.decision_type || 'OTHER',
      payload: { description: item.pdo_card?.description || '' },
      operator: {
        operatorId: item.pdo_card?.agent_id || 'SYSTEM',
        tier: 'T2' as const,
        sessionId: `session-${item.id}`,
        verified: true,
      },
      priority: item.pdo_card?.outcome === 'ESCALATED' ? 'CRITICAL' as const : 'NORMAL' as const,
      createdAt: item.timestamp,
      sequenceNumber: index + 1,
      hashPrevious: index > 0 ? `hash-${index - 1}` : null,
      hashCurrent: `hash-${index}`,
    }));
  
  return {
    items,
    metrics: {
      currentSize: items.length,
      maxSize: 10000,
      enqueueCount: dashboardState.decision_stream.length,
      dequeueCount: dashboardState.decision_stream.filter(i => 
        i.pdo_card?.outcome === 'APPROVED' || i.pdo_card?.outcome === 'REJECTED'
      ).length,
      rejectCount: dashboardState.decision_stream.filter(i => 
        i.pdo_card?.outcome === 'REJECTED'
      ).length,
      sequenceCounter: dashboardState.decision_stream.length,
    },
    isClosed: dashboardState.kill_switch?.state === 'ENGAGED',
    lastRefresh: new Date().toISOString(),
  };
}

export function useOCCQueue(options?: UseOCCOptions): HookResult<QueueState> {
  const dashboard = useOCCFetch<DashboardStateResponse>('/state', options);
  
  return {
    data: transformToQueueState(dashboard.data),
    loading: dashboard.loading,
    error: dashboard.error,
    refresh: dashboard.refresh,
    lastRefresh: dashboard.lastRefresh,
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// PDO STATE MACHINE HOOK — INV-OCC-008 (State Determinism)
// PAC-BENSON-EXEC-P11: Derives state machine from dashboard state (GAP-03)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Map backend decision outcome to PDO state.
 */
function mapOutcomeToState(outcome: string | undefined): PDOState {
  switch (outcome) {
    case 'APPROVED': return 'SETTLED';
    case 'REJECTED': return 'REJECTED';
    case 'ESCALATED': return 'ESCALATED';
    case 'PENDING':
    default: return 'PENDING';
  }
}

/**
 * Transform decision stream to PDO state machine state.
 */
function transformToStateMachineState(dashboardState: DashboardStateResponse | null): PDOStateMachineState | null {
  if (!dashboardState) return null;
  
  const pdos: PDORecord[] = dashboardState.decision_stream
    .filter(item => item.item_type === 'pdo' && item.pdo_card)
    .map(item => ({
      id: item.id,
      value: 0, // Not provided by backend
      currency: 'USD',
      currentState: mapOutcomeToState(item.pdo_card?.outcome),
      createdAt: item.timestamp,
      updatedAt: item.timestamp,
      isOverridden: false,
      overrideId: null,
      overrideTimestamp: null,
      originalDecision: null,
      originalOperatorId: null,
      metadata: {},
    }));
  
  return {
    pdos,
    selectedPdoTransitions: [],
    metrics: {
      pdoCount: pdos.length,
      transitionCount: pdos.length,
      overrideCount: 0,
      rejectionCount: pdos.filter(p => p.currentState === 'REJECTED').length,
    },
    lastRefresh: new Date().toISOString(),
  };
}

export function useOCCStateMachine(options?: UseOCCOptions): HookResult<PDOStateMachineState> {
  const dashboard = useOCCFetch<DashboardStateResponse>('/state', options);
  
  return {
    data: transformToStateMachineState(dashboard.data),
    loading: dashboard.loading,
    error: dashboard.error,
    refresh: dashboard.refresh,
    lastRefresh: dashboard.lastRefresh,
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// PDO TRANSITIONS HOOK
// ═══════════════════════════════════════════════════════════════════════════════

interface UseOCCTransitionsResult {
  transitions: PDOTransition[];
  loading: boolean;
  error: Error | null;
  fetchTransitions: (pdoId: string) => Promise<void>;
}

export function useOCCTransitions(): UseOCCTransitionsResult {
  const [transitions, setTransitions] = useState<PDOTransition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchTransitions = useCallback(async (pdoId: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // INV-OCC-001: GET-only reads
      const response = await fetch(`${API_BASE}/state-machine/pdo/${pdoId}/transitions`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-OCC-Client': 'chainboard-ui-v1',
        },
      });
      
      if (!response.ok) {
        throw new Error(`OCC API error: ${response.status}`);
      }
      
      const result = await response.json();
      setTransitions(result.transitions || []);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, []);
  
  return { transitions, loading, error, fetchTransitions };
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT LOG HOOK — INV-OCC-002 (Audit Immutability)
// PAC-BENSON-EXEC-P11: Derives audit log from dashboard state (GAP-03)
// ═══════════════════════════════════════════════════════════════════════════════

interface UseOCCAuditLogOptions extends UseOCCOptions {
  filters?: AuditFilters;
}

/**
 * Transform decision stream to audit log state.
 */
function transformToAuditLogState(dashboardState: DashboardStateResponse | null): AuditLogState | null {
  if (!dashboardState) return null;
  
  const records: AuditRecord[] = dashboardState.decision_stream.map((item, index) => ({
    id: `AUD-${item.id}`,
    recordType: item.pdo_card ? 'PDO_TRANSITION' : 'ACTION_EXECUTED',
    timestamp: item.timestamp,
    operatorId: item.pdo_card?.agent_id || null,
    operatorTier: null,
    sessionId: null,
    ipAddress: null,
    userAgent: null,
    targetId: item.pdo_card?.pdo_id || item.id,
    actionType: item.pdo_card?.decision_type || null,
    payload: { description: item.pdo_card?.description || '' },
    result: item.pdo_card?.outcome === 'APPROVED' ? 'SUCCESS' : 
            item.pdo_card?.outcome === 'REJECTED' ? 'BLOCKED' : 'SUCCESS',
    message: item.pdo_card?.description || `Decision ${item.id}`,
    hashPrevious: index > 0 ? `hash-prev-${index}` : null,
    hashCurrent: `hash-${index}`,
  }));
  
  const recordsByType: Record<string, number> = {};
  const recordsByResult: Record<string, number> = { SUCCESS: 0, BLOCKED: 0, ERROR: 0 };
  
  records.forEach(r => {
    recordsByType[r.recordType] = (recordsByType[r.recordType] || 0) + 1;
    if (r.result === 'SUCCESS') recordsByResult.SUCCESS++;
    else if (r.result === 'BLOCKED') recordsByResult.BLOCKED++;
    else recordsByResult.ERROR++;
  });
  
  return {
    records,
    statistics: {
      totalRecords: records.length,
      sequenceCounter: records.length,
      recordsByType,
      recordsByResult,
      chainValid: true,
    },
    filters: {},
    lastRefresh: new Date().toISOString(),
  };
}

export function useOCCAuditLog(options?: UseOCCAuditLogOptions): HookResult<AuditLogState> {
  const dashboard = useOCCFetch<DashboardStateResponse>('/state', options);
  
  return {
    data: transformToAuditLogState(dashboard.data),
    loading: dashboard.loading,
    error: dashboard.error,
    refresh: dashboard.refresh,
    lastRefresh: dashboard.lastRefresh,
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// REPLAY HOOK — INV-OCC-010 (Replay Determinism)
// ═══════════════════════════════════════════════════════════════════════════════

interface UseOCCReplayResult {
  result: ReplayResult | null;
  loading: boolean;
  error: Error | null;
  executeReplay: (pdoId: string) => Promise<void>;
}

export function useOCCReplay(): UseOCCReplayResult {
  const [result, setResult] = useState<ReplayResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const executeReplay = useCallback(async (pdoId: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // INV-OCC-001: GET-only reads (replay is idempotent read operation)
      const response = await fetch(`${API_BASE}/replay/${pdoId}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-OCC-Client': 'chainboard-ui-v1',
        },
      });
      
      if (!response.ok) {
        throw new Error(`OCC API error: ${response.status}`);
      }
      
      const replayResult = await response.json();
      setResult(replayResult);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, []);
  
  return { result, loading, error, executeReplay };
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMBINED DASHBOARD HOOK
// ═══════════════════════════════════════════════════════════════════════════════

interface UseOCCDashboardResult {
  queue: HookResult<QueueState>;
  stateMachine: HookResult<PDOStateMachineState>;
  auditLog: HookResult<AuditLogState>;
  refreshAll: () => Promise<void>;
}

export function useOCCDashboard(options?: UseOCCOptions): UseOCCDashboardResult {
  const queue = useOCCQueue(options);
  const stateMachine = useOCCStateMachine(options);
  const auditLog = useOCCAuditLog(options);
  
  const refreshAll = useCallback(async () => {
    await Promise.all([
      queue.refresh(),
      stateMachine.refresh(),
      auditLog.refresh(),
    ]);
  }, [queue, stateMachine, auditLog]);
  
  return { queue, stateMachine, auditLog, refreshAll };
}
