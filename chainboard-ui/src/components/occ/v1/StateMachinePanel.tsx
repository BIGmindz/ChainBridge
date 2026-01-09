/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC v1.0 PDO State Machine Panel — State Visualization
 * PAC-JEFFREY-P03: OCC UI Execution
 * 
 * Displays the PDO state machine with:
 *   - State transition visualization
 *   - Override markers (permanent per INV-OVR-006)
 *   - Hash chain integrity display
 *   - Transition history
 * 
 * INVARIANTS:
 * - INV-OCC-UI-001: Read-only display, no mutations
 * - INV-OCC-008: State Determinism visualization
 * - INV-OVR-006: Override Marker Permanence display
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0, Article V
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useMemo } from 'react';
import type {
  PDOStateMachineState,
  PDORecord,
  PDOTransition,
  PDOState,
  TransitionType,
  StateMachineMetrics,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// STATE COLORS & CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

const STATE_CONFIG: Record<PDOState, { color: string; bg: string; category: string }> = {
  // Initial
  PENDING: { color: 'text-gray-400', bg: 'bg-gray-700', category: 'Initial' },
  SUBMITTED: { color: 'text-blue-400', bg: 'bg-blue-900/30', category: 'Initial' },
  // Agent
  AGENT_APPROVED: { color: 'text-green-400', bg: 'bg-green-900/30', category: 'Agent' },
  AGENT_BLOCKED: { color: 'text-red-400', bg: 'bg-red-900/30', category: 'Agent' },
  AGENT_FLAGGED: { color: 'text-yellow-400', bg: 'bg-yellow-900/30', category: 'Agent' },
  // Policy
  POLICY_APPROVED: { color: 'text-green-400', bg: 'bg-green-900/40', category: 'Policy' },
  POLICY_BLOCKED: { color: 'text-red-400', bg: 'bg-red-900/40', category: 'Policy' },
  // Operator (Override)
  OPERATOR_APPROVED: { color: 'text-emerald-400', bg: 'bg-emerald-900/30', category: 'Override' },
  OPERATOR_BLOCKED: { color: 'text-rose-400', bg: 'bg-rose-900/30', category: 'Override' },
  OPERATOR_MODIFIED: { color: 'text-amber-400', bg: 'bg-amber-900/30', category: 'Override' },
  // Processing
  IN_REVIEW: { color: 'text-purple-400', bg: 'bg-purple-900/30', category: 'Processing' },
  ESCALATED: { color: 'text-orange-400', bg: 'bg-orange-900/30', category: 'Processing' },
  // Terminal
  SETTLED: { color: 'text-green-500', bg: 'bg-green-900/50', category: 'Terminal' },
  REJECTED: { color: 'text-red-500', bg: 'bg-red-900/50', category: 'Terminal' },
  CANCELLED: { color: 'text-gray-500', bg: 'bg-gray-800', category: 'Terminal' },
  EXPIRED: { color: 'text-gray-600', bg: 'bg-gray-900', category: 'Terminal' },
};

const TRANSITION_TYPE_CONFIG: Record<TransitionType, { color: string; label: string }> = {
  AGENT: { color: 'text-cyan-400', label: 'Agent' },
  POLICY: { color: 'text-violet-400', label: 'Policy' },
  OPERATOR: { color: 'text-orange-400', label: 'Operator' },
  SYSTEM: { color: 'text-gray-400', label: 'System' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// METRICS PANEL
// ═══════════════════════════════════════════════════════════════════════════════

const MetricsPanel: React.FC<{ metrics: StateMachineMetrics }> = ({ metrics }) => (
  <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
    <h4 className="text-sm font-semibold text-gray-300 mb-3">State Machine Metrics</h4>
    <div className="grid grid-cols-2 gap-3 text-sm">
      <div>
        <span className="text-gray-500">PDOs:</span>
        <span className="ml-2 font-mono text-white">{metrics.pdoCount}</span>
      </div>
      <div>
        <span className="text-gray-500">Transitions:</span>
        <span className="ml-2 font-mono text-blue-400">{metrics.transitionCount}</span>
      </div>
      <div>
        <span className="text-gray-500">Overrides:</span>
        <span className="ml-2 font-mono text-orange-400">{metrics.overrideCount}</span>
      </div>
      <div>
        <span className="text-gray-500">Rejections:</span>
        <span className="ml-2 font-mono text-red-400">{metrics.rejectionCount}</span>
      </div>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// PDO CARD
// ═══════════════════════════════════════════════════════════════════════════════

interface PDOCardProps {
  pdo: PDORecord;
  selected: boolean;
  onSelect: (pdoId: string) => void;
}

const PDOCard: React.FC<PDOCardProps> = ({ pdo, selected, onSelect }) => {
  const stateConfig = STATE_CONFIG[pdo.currentState];
  
  return (
    <button
      onClick={() => onSelect(pdo.id)}
      className={`w-full text-left rounded-lg p-3 border transition-colors ${
        selected
          ? 'border-blue-500 bg-blue-900/20'
          : 'border-gray-700 bg-gray-800 hover:border-gray-600'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="font-mono text-sm text-white">{pdo.id}</span>
        {pdo.isOverridden && (
          <span
            className="px-1.5 py-0.5 text-[10px] bg-orange-900 text-orange-300 rounded"
            title={`Override ID: ${pdo.overrideId}`}
          >
            OVERRIDDEN
          </span>
        )}
      </div>
      
      <div className="flex items-center gap-2 mb-2">
        <span className={`px-2 py-0.5 text-xs rounded ${stateConfig.bg} ${stateConfig.color}`}>
          {pdo.currentState}
        </span>
        <span className="text-xs text-gray-500">{stateConfig.category}</span>
      </div>
      
      <div className="text-xs text-gray-400 space-y-1">
        <div>
          <span className="text-gray-500">Value:</span>
          <span className="ml-2 font-mono">{pdo.currency} {pdo.value.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-gray-500">Updated:</span>
          <span className="ml-2">{new Date(pdo.updatedAt).toLocaleString()}</span>
        </div>
        {pdo.originalDecision && (
          <div>
            <span className="text-gray-500">Original:</span>
            <span className="ml-2 text-gray-400">{pdo.originalDecision}</span>
          </div>
        )}
      </div>
    </button>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// TRANSITION TIMELINE
// ═══════════════════════════════════════════════════════════════════════════════

interface TransitionTimelineProps {
  transitions: PDOTransition[];
}

const TransitionTimeline: React.FC<TransitionTimelineProps> = ({ transitions }) => {
  if (transitions.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        Select a PDO to view transitions
      </div>
    );
  }
  
  return (
    <div className="space-y-0">
      {transitions.map((tr, index) => {
        const typeConfig = TRANSITION_TYPE_CONFIG[tr.transitionType];
        const fromConfig = STATE_CONFIG[tr.fromState];
        const toConfig = STATE_CONFIG[tr.toState];
        const isLast = index === transitions.length - 1;
        
        return (
          <div key={tr.id} className="relative">
            {/* Timeline line */}
            {!isLast && (
              <div className="absolute left-4 top-8 bottom-0 w-0.5 bg-gray-700" />
            )}
            
            {/* Transition node */}
            <div className="flex items-start gap-3 pb-4">
              {/* Node dot */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                tr.isOverride ? 'bg-orange-900 ring-2 ring-orange-500' : 'bg-gray-700'
              }`}>
                <span className="text-xs">
                  {tr.transitionType === 'AGENT' ? '🤖' :
                   tr.transitionType === 'POLICY' ? '📋' :
                   tr.transitionType === 'OPERATOR' ? '👤' : '⚙️'}
                </span>
              </div>
              
              {/* Transition content */}
              <div className="flex-1 bg-gray-800 rounded-lg p-3 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${typeConfig.color}`}>
                      {typeConfig.label}
                    </span>
                    {tr.isOverride && (
                      <span className="px-1.5 py-0.5 text-[10px] bg-orange-900 text-orange-300 rounded">
                        OVERRIDE
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(tr.timestamp).toLocaleString()}
                  </span>
                </div>
                
                {/* State transition */}
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-0.5 text-xs rounded ${fromConfig.bg} ${fromConfig.color}`}>
                    {tr.fromState}
                  </span>
                  <span className="text-gray-500">→</span>
                  <span className={`px-2 py-0.5 text-xs rounded ${toConfig.bg} ${toConfig.color}`}>
                    {tr.toState}
                  </span>
                </div>
                
                {/* Details */}
                <div className="text-xs text-gray-400 space-y-1">
                  <div>
                    <span className="text-gray-500">Actor:</span>
                    <span className="ml-2 font-mono">{tr.actorId}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Reason:</span>
                    <span className="ml-2">{tr.reason}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Hash:</span>
                    <span className="ml-2 font-mono text-[10px]" title={tr.hashCurrent}>
                      {tr.hashCurrent.substring(0, 16)}...
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN STATE MACHINE PANEL
// ═══════════════════════════════════════════════════════════════════════════════

export interface StateMachinePanelProps {
  state: PDOStateMachineState;
  loading?: boolean;
  onRefresh?: () => void;
  onSelectPDO?: (pdoId: string) => void;
}

export const StateMachinePanel: React.FC<StateMachinePanelProps> = ({
  state,
  loading = false,
  onRefresh,
  onSelectPDO,
}) => {
  const [selectedPdoId, setSelectedPdoId] = useState<string | null>(null);
  
  const handleSelectPDO = (pdoId: string) => {
    setSelectedPdoId(pdoId);
    onSelectPDO?.(pdoId);
  };
  
  // Group PDOs by state category
  const pdosByCategory = useMemo(() => {
    const categories: Record<string, PDORecord[]> = {
      Initial: [],
      Agent: [],
      Policy: [],
      Override: [],
      Processing: [],
      Terminal: [],
    };
    
    state.pdos.forEach((pdo) => {
      const config = STATE_CONFIG[pdo.currentState];
      categories[config.category].push(pdo);
    });
    
    return categories;
  }, [state.pdos]);

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-white">PDO State Machine</h3>
          <span className="text-xs text-gray-500">
            INV-OCC-008: State Determinism
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            Last: {new Date(state.lastRefresh).toLocaleTimeString()}
          </span>
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded disabled:opacity-50"
              aria-label="Refresh state machine"
            >
              {loading ? '...' : '↻'}
            </button>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: PDO List */}
        <div className="space-y-4">
          <MetricsPanel metrics={state.metrics} />
          
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h4 className="text-sm font-semibold text-gray-300 mb-3">PDO Records</h4>
            
            {state.pdos.length === 0 ? (
              <div className="text-center text-gray-500 py-4">No PDOs</div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {state.pdos.map((pdo) => (
                  <PDOCard
                    key={pdo.id}
                    pdo={pdo}
                    selected={pdo.id === selectedPdoId}
                    onSelect={handleSelectPDO}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
        
        {/* Right: Transition Timeline */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">
            Transition History
            {selectedPdoId && (
              <span className="ml-2 font-mono text-xs text-gray-500">
                {selectedPdoId}
              </span>
            )}
          </h4>
          
          <div className="max-h-[500px] overflow-y-auto">
            <TransitionTimeline transitions={state.selectedPdoTransitions} />
          </div>
        </div>
      </div>
      
      {/* Footer */}
      <div className="bg-gray-800 px-4 py-2 border-t border-gray-700 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          📖 Read-only view • INV-OCC-UI-001 • INV-OVR-006: Override markers permanent
        </span>
        <span className="text-xs text-gray-500">
          {state.pdos.filter(p => p.isOverridden).length} overridden PDOs
        </span>
      </div>
    </div>
  );
};

export default StateMachinePanel;
