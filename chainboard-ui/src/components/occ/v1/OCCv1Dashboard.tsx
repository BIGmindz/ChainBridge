/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC v1.0 Dashboard — Main Dashboard Layout
 * PAC-JEFFREY-P03: OCC UI Execution
 * PAC-BENSON-EXEC-P11: Live API Wiring (GAP-01, GAP-03 closure)
 * 
 * Integrates all OCC v1.0 panels:
 *   - Queue Panel
 *   - PDO State Machine Panel
 *   - Audit Trail Panel
 * 
 * INVARIANTS:
 * - INV-OCC-UI-001: All state is read-only from backend
 * - INV-OCC-UI-002: No mutation operations in UI
 * - INV-OCC-UI-003: Display-only, observer pattern
 * - INV-OCC-UI-004: No mock data in production (PAC-BENSON-EXEC-P11)
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import { QueuePanel } from './QueuePanel';
import { StateMachinePanel } from './StateMachinePanel';
import { AuditPanel } from './AuditPanel';
import { useOCCDashboard, useOCCTransitions } from './useOCCApi';
import type { QueueState, PDOStateMachineState, AuditLogState } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════

type TabId = 'queue' | 'state-machine' | 'audit';

interface Tab {
  id: TabId;
  label: string;
  icon: string;
  invariant: string;
}

const TABS: Tab[] = [
  { id: 'queue', label: 'Action Queue', icon: '📥', invariant: 'INV-OCC-006' },
  { id: 'state-machine', label: 'PDO States', icon: '🔄', invariant: 'INV-OCC-008' },
  { id: 'audit', label: 'Audit Trail', icon: '📜', invariant: 'INV-OCC-002' },
];

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN DASHBOARD COMPONENT
// PAC-BENSON-EXEC-P11: Wired to live APIs (GAP-01 closure)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Default empty state for fail-closed rendering.
 * INV-OCC-UI-002: No optimistic rendering — show empty on error.
 */
const EMPTY_QUEUE_STATE: QueueState = {
  items: [],
  metrics: { currentSize: 0, maxSize: 10000, enqueueCount: 0, dequeueCount: 0, rejectCount: 0, sequenceCounter: 0 },
  isClosed: false,
  lastRefresh: new Date().toISOString(),
};

const EMPTY_STATE_MACHINE: PDOStateMachineState = {
  pdos: [],
  selectedPdoTransitions: [],
  metrics: { pdoCount: 0, transitionCount: 0, overrideCount: 0, rejectionCount: 0 },
  lastRefresh: new Date().toISOString(),
};

const EMPTY_AUDIT_STATE: AuditLogState = {
  records: [],
  statistics: { totalRecords: 0, sequenceCounter: 0, recordsByType: {}, recordsByResult: { SUCCESS: 0, BLOCKED: 0, ERROR: 0 }, chainValid: true },
  filters: {},
  lastRefresh: new Date().toISOString(),
};

export const OCCv1Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('queue');
  
  // PAC-BENSON-EXEC-P11: Live API hooks (GAP-01, GAP-03 closure)
  // INV-OCC-UI-004: No mock data — wired to /occ/dashboard/state
  const { queue, stateMachine, auditLog, refreshAll } = useOCCDashboard({
    refreshInterval: 5000,
    autoRefresh: true,
  });
  
  // Transitions hook for PDO detail view
  const { transitions, fetchTransitions } = useOCCTransitions();
  
  // Derive state with fail-closed defaults (INV-OCC-UI-002)
  const queueState = queue.data ?? EMPTY_QUEUE_STATE;
  const stateMachineState = stateMachine.data ?? EMPTY_STATE_MACHINE;
  const auditLogState = auditLog.data ?? EMPTY_AUDIT_STATE;
  
  // Combined loading state
  const isLoading = queue.loading || stateMachine.loading || auditLog.loading;
  
  // Combined error state
  const hasError = queue.error || stateMachine.error || auditLog.error;
  
  // Refresh handlers
  const handleRefreshQueue = useCallback(() => {
    queue.refresh();
  }, [queue]);
  
  const handleRefreshStateMachine = useCallback(() => {
    stateMachine.refresh();
  }, [stateMachine]);
  
  const handleRefreshAudit = useCallback(() => {
    auditLog.refresh();
  }, [auditLog]);
  
  // PDO selection handler — fetches transitions from backend
  const handleSelectPDO = useCallback((pdoId: string) => {
    fetchTransitions(pdoId);
  }, [fetchTransitions]);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold">OCC v1.0</h1>
            <span className="px-2 py-1 text-xs bg-blue-900 text-blue-300 rounded">
              Operator Control Center
            </span>
            <span className="text-xs text-gray-500">
              Constitutional Authority: OCC_CONSTITUTION_v1.0
            </span>
          </div>
          
          <div className="flex items-center gap-3">
            {hasError ? (
              <span className="px-2 py-1 text-xs bg-red-900 text-red-300 rounded flex items-center gap-1">
                <span className="w-2 h-2 bg-red-400 rounded-full" />
                Error — Fail-Closed
              </span>
            ) : isLoading ? (
              <span className="px-2 py-1 text-xs bg-yellow-900 text-yellow-300 rounded flex items-center gap-1">
                <span className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
                Loading...
              </span>
            ) : (
              <span className="px-2 py-1 text-xs bg-green-900 text-green-300 rounded flex items-center gap-1">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                Live
              </span>
            )}
            <span className="text-xs text-gray-500">
              PAC-BENSON-EXEC-P11
            </span>
          </div>
        </div>
      </header>
      
      {/* Tab Navigation */}
      <nav className="bg-gray-900 border-b border-gray-800 px-6">
        <div className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium transition-colors relative ${
                activeTab === tab.id
                  ? 'text-white'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <span className="flex items-center gap-2">
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                <span className="text-[10px] text-gray-500">({tab.invariant})</span>
              </span>
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
              )}
            </button>
          ))}
        </div>
      </nav>
      
      {/* Content */}
      <main className="p-6">
        {activeTab === 'queue' && (
          <QueuePanel
            state={queueState}
            loading={queue.loading}
            onRefresh={handleRefreshQueue}
          />
        )}
        
        {activeTab === 'state-machine' && (
          <StateMachinePanel
            state={{
              ...stateMachineState,
              // Merge in fetched transitions
              selectedPdoTransitions: transitions.length > 0 ? transitions : stateMachineState.selectedPdoTransitions,
            }}
            loading={stateMachine.loading}
            onRefresh={handleRefreshStateMachine}
            onSelectPDO={handleSelectPDO}
          />
        )}
        
        {activeTab === 'audit' && (
          <AuditPanel
            state={auditLogState}
            loading={auditLog.loading}
            onRefresh={handleRefreshAudit}
          />
        )}
      </main>
      
      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-800 px-6 py-2">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span>📖 Read-only Observer Mode</span>
            <span>|</span>
            <span>INV-OCC-UI-001: No mutations</span>
            <span>|</span>
            <span>INV-OCC-UI-004: Live API (P11)</span>
          </div>
          <div>
            ChainBridge OCC v1.0 • PAC-BENSON-EXEC-P11
          </div>
        </div>
      </footer>
    </div>
  );
};

export default OCCv1Dashboard;
