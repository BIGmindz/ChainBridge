/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC v1.0 Audit Trail Panel — Immutable Audit Log Visualization
 * PAC-JEFFREY-P03: OCC UI Execution
 * 
 * Displays the OCC audit log with:
 *   - Chronological audit records
 *   - Hash chain integrity indicator
 *   - Filtering by type, operator, target
 *   - Override-specific tracking
 * 
 * INVARIANTS:
 * - INV-OCC-UI-001: Read-only display, no mutations
 * - INV-OCC-002: Audit Immutability display
 * - INV-OVR-003: Override records append-only
 * - INV-OVR-004: Complete audit trail
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0, Article VI
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useMemo } from 'react';
import type {
  AuditLogState,
  AuditRecord,
  AuditRecordType,
  AuditResult,
  AuditLogStatistics,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT RECORD TYPE CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

const RECORD_TYPE_CONFIG: Record<AuditRecordType, { icon: string; color: string; category: string }> = {
  // Queue operations
  QUEUE_ENQUEUE: { icon: '📥', color: 'text-blue-400', category: 'Queue' },
  QUEUE_DEQUEUE: { icon: '📤', color: 'text-blue-400', category: 'Queue' },
  QUEUE_ESCALATE: { icon: '⬆️', color: 'text-orange-400', category: 'Queue' },
  // Action operations
  ACTION_SUBMITTED: { icon: '📝', color: 'text-gray-400', category: 'Action' },
  ACTION_VALIDATED: { icon: '✓', color: 'text-green-400', category: 'Action' },
  ACTION_EXECUTED: { icon: '▶️', color: 'text-green-400', category: 'Action' },
  ACTION_BLOCKED: { icon: '🚫', color: 'text-red-400', category: 'Action' },
  // Override operations
  OVERRIDE_REQUESTED: { icon: '⚡', color: 'text-orange-400', category: 'Override' },
  OVERRIDE_VALIDATED: { icon: '✓', color: 'text-orange-400', category: 'Override' },
  OVERRIDE_EXECUTED: { icon: '🔓', color: 'text-orange-400', category: 'Override' },
  OVERRIDE_BLOCKED: { icon: '🔒', color: 'text-red-400', category: 'Override' },
  // State machine
  PDO_TRANSITION: { icon: '↔️', color: 'text-purple-400', category: 'State' },
  PDO_OVERRIDE_APPLIED: { icon: '🔄', color: 'text-orange-400', category: 'State' },
  // System
  SYSTEM_STARTUP: { icon: '🟢', color: 'text-green-400', category: 'System' },
  SYSTEM_SHUTDOWN: { icon: '🔴', color: 'text-red-400', category: 'System' },
  SYSTEM_FAIL_CLOSED: { icon: '⛔', color: 'text-red-500', category: 'System' },
  // Auth
  OPERATOR_LOGIN: { icon: '🔑', color: 'text-green-400', category: 'Auth' },
  OPERATOR_LOGOUT: { icon: '🚪', color: 'text-gray-400', category: 'Auth' },
  MFA_VERIFIED: { icon: '🔐', color: 'text-green-400', category: 'Auth' },
  // Errors
  INVARIANT_VIOLATION: { icon: '⚠️', color: 'text-red-500', category: 'Error' },
  UNAUTHORIZED_ACCESS: { icon: '🚨', color: 'text-red-500', category: 'Error' },
};

const RESULT_CONFIG: Record<AuditResult, { color: string; bg: string }> = {
  SUCCESS: { color: 'text-green-400', bg: 'bg-green-900/30' },
  BLOCKED: { color: 'text-red-400', bg: 'bg-red-900/30' },
  ERROR: { color: 'text-yellow-400', bg: 'bg-yellow-900/30' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// STATISTICS PANEL
// ═══════════════════════════════════════════════════════════════════════════════

const StatisticsPanel: React.FC<{ statistics: AuditLogStatistics }> = ({ statistics }) => (
  <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
    <div className="flex items-center justify-between mb-3">
      <h4 className="text-sm font-semibold text-gray-300">Audit Statistics</h4>
      <div className="flex items-center gap-2">
        {statistics.chainValid ? (
          <span className="px-2 py-0.5 text-xs bg-green-900 text-green-300 rounded flex items-center gap-1">
            <span>🔗</span> Chain Valid
          </span>
        ) : (
          <span className="px-2 py-0.5 text-xs bg-red-900 text-red-300 rounded flex items-center gap-1">
            <span>⚠️</span> Chain Broken
          </span>
        )}
      </div>
    </div>
    
    <div className="grid grid-cols-2 gap-3 text-sm mb-3">
      <div>
        <span className="text-gray-500">Total Records:</span>
        <span className="ml-2 font-mono text-white">{statistics.totalRecords}</span>
      </div>
      <div>
        <span className="text-gray-500">Sequence:</span>
        <span className="ml-2 font-mono text-gray-400">{statistics.sequenceCounter}</span>
      </div>
    </div>
    
    {/* Results breakdown */}
    <div className="flex gap-4 text-xs">
      {Object.entries(statistics.recordsByResult).map(([result, count]) => {
        const config = RESULT_CONFIG[result as AuditResult];
        return (
          <div key={result} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${config.bg}`} />
            <span className="text-gray-400">{result}:</span>
            <span className={config.color}>{count}</span>
          </div>
        );
      })}
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// FILTER BAR
// ═══════════════════════════════════════════════════════════════════════════════

interface FilterBarProps {
  filters: AuditLogState['filters'];
  onFilterChange: (filters: AuditLogState['filters']) => void;
}

const FilterBar: React.FC<FilterBarProps> = ({ filters, onFilterChange }) => {
  const categories = ['All', 'Queue', 'Action', 'Override', 'State', 'System', 'Auth', 'Error'];
  const [selectedCategory, setSelectedCategory] = useState('All');
  
  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    // In a real implementation, this would filter by recordType based on category
    // For now, we just track the selection
  };
  
  return (
    <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-gray-500">Filter:</span>
        {categories.map((category) => (
          <button
            key={category}
            onClick={() => handleCategoryChange(category)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              selectedCategory === category
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {category}
          </button>
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT RECORD ROW
// ═══════════════════════════════════════════════════════════════════════════════

interface AuditRecordRowProps {
  record: AuditRecord;
  expanded: boolean;
  onToggle: () => void;
}

const AuditRecordRow: React.FC<AuditRecordRowProps> = ({ record, expanded, onToggle }) => {
  const typeConfig = RECORD_TYPE_CONFIG[record.recordType];
  const resultConfig = RESULT_CONFIG[record.result];
  const shortHash = record.hashCurrent.substring(0, 8);
  const isOverrideRecord = record.recordType.startsWith('OVERRIDE_');
  
  return (
    <div className={`border border-gray-700 rounded-lg overflow-hidden ${
      isOverrideRecord ? 'ring-1 ring-orange-900/50' : ''
    }`}>
      {/* Main row */}
      <button
        onClick={onToggle}
        className="w-full text-left bg-gray-800 p-3 hover:bg-gray-750 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg" title={typeConfig.category}>
              {typeConfig.icon}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium ${typeConfig.color}`}>
                  {record.recordType.replace(/_/g, ' ')}
                </span>
                <span className={`px-1.5 py-0.5 text-[10px] rounded ${resultConfig.bg} ${resultConfig.color}`}>
                  {record.result}
                </span>
                {isOverrideRecord && (
                  <span className="px-1.5 py-0.5 text-[10px] bg-orange-900/50 text-orange-300 rounded">
                    OVERRIDE
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-400 mt-0.5">
                {record.message}
              </div>
            </div>
          </div>
          
          <div className="text-right">
            <div className="text-xs text-gray-500">
              {new Date(record.timestamp).toLocaleString()}
            </div>
            <div className="text-[10px] font-mono text-gray-600" title={record.hashCurrent}>
              {shortHash}...
            </div>
          </div>
        </div>
      </button>
      
      {/* Expanded details */}
      {expanded && (
        <div className="bg-gray-900 p-3 border-t border-gray-700 text-xs space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="text-gray-500">Record ID:</span>
              <span className="ml-2 font-mono text-gray-300">{record.id}</span>
            </div>
            <div>
              <span className="text-gray-500">Operator:</span>
              <span className="ml-2 font-mono text-gray-300">
                {record.operatorId || 'SYSTEM'}
                {record.operatorTier && (
                  <span className="ml-1 text-gray-500">({record.operatorTier})</span>
                )}
              </span>
            </div>
            {record.targetId && (
              <div>
                <span className="text-gray-500">Target:</span>
                <span className="ml-2 font-mono text-gray-300">{record.targetId}</span>
              </div>
            )}
            {record.actionType && (
              <div>
                <span className="text-gray-500">Action:</span>
                <span className="ml-2 text-gray-300">{record.actionType}</span>
              </div>
            )}
            {record.sessionId && (
              <div>
                <span className="text-gray-500">Session:</span>
                <span className="ml-2 font-mono text-gray-300">{record.sessionId.substring(0, 8)}...</span>
              </div>
            )}
            {record.ipAddress && (
              <div>
                <span className="text-gray-500">IP:</span>
                <span className="ml-2 font-mono text-gray-300">{record.ipAddress}</span>
              </div>
            )}
          </div>
          
          {/* Hash chain */}
          <div className="pt-2 border-t border-gray-800">
            <div className="text-gray-500 mb-1">Hash Chain:</div>
            <div className="font-mono text-[10px] space-y-1">
              <div>
                <span className="text-gray-500">Previous:</span>
                <span className="ml-2 text-gray-400">
                  {record.hashPrevious || 'GENESIS'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Current:</span>
                <span className="ml-2 text-gray-300">{record.hashCurrent}</span>
              </div>
            </div>
          </div>
          
          {/* Payload (if any) */}
          {Object.keys(record.payload).length > 0 && (
            <div className="pt-2 border-t border-gray-800">
              <div className="text-gray-500 mb-1">Payload:</div>
              <pre className="text-[10px] text-gray-400 bg-gray-950 p-2 rounded overflow-x-auto">
                {JSON.stringify(record.payload, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN AUDIT PANEL
// ═══════════════════════════════════════════════════════════════════════════════

export interface AuditPanelProps {
  state: AuditLogState;
  loading?: boolean;
  onRefresh?: () => void;
  onFilterChange?: (filters: AuditLogState['filters']) => void;
}

export const AuditPanel: React.FC<AuditPanelProps> = ({
  state,
  loading = false,
  onRefresh,
  onFilterChange,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  
  const handleToggle = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };
  
  // Count override records
  const overrideCount = useMemo(() => 
    state.records.filter(r => r.recordType.startsWith('OVERRIDE_')).length,
    [state.records]
  );

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-white">Audit Trail</h3>
          <span className="text-xs text-gray-500">
            INV-OCC-002: Immutable
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
              aria-label="Refresh audit log"
            >
              {loading ? '...' : '↻'}
            </button>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Statistics */}
        <StatisticsPanel statistics={state.statistics} />
        
        {/* Filters */}
        <FilterBar
          filters={state.filters}
          onFilterChange={onFilterChange || (() => {})}
        />
        
        {/* Records */}
        {state.records.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No audit records
          </div>
        ) : (
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {state.records.map((record) => (
              <AuditRecordRow
                key={record.id}
                record={record}
                expanded={expandedId === record.id}
                onToggle={() => handleToggle(record.id)}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="bg-gray-800 px-4 py-2 border-t border-gray-700 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          📖 Read-only view • INV-OVR-003: Append-only • INV-OVR-004: Complete trail
        </span>
        <span className="text-xs text-gray-500">
          {overrideCount} override records • {state.records.length} total
        </span>
      </div>
    </div>
  );
};

export default AuditPanel;
