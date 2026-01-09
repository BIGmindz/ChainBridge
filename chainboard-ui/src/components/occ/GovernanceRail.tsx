/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Governance Rail Component — Active Invariants Display
 * PAC-BENSON-P21-C: OCC Intensive Multi-Agent Execution
 * 
 * Displays active governance invariants with:
 * - Rule IDs (e.g., INV-CP-001)
 * - Pass/fail status
 * - Invariant class (S/M/X/T/A/F/C-INV)
 * - Enforcement points
 * - Violation messages (if failing)
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display
 * - INV-ALEX-001: UI reflects invariant failures with rule IDs
 * - INV-ALEX-002: No bypass of backend gates
 * 
 * Author: SONNY (GID-02) — Frontend
 * Governance: ALEX (GID-08)
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import type {
  GovernanceRailState,
  InvariantDisplay,
  InvariantStatus,
  InvariantClass,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const INVARIANT_STATUS_CONFIG: Record<InvariantStatus, { color: string; bgColor: string; icon: string; label: string }> = {
  PASSING: { color: 'text-green-400', bgColor: 'bg-green-900/30', icon: '✓', label: 'Passing' },
  FAILING: { color: 'text-red-400', bgColor: 'bg-red-900/30', icon: '✗', label: 'Failing' },
  NOT_EVALUATED: { color: 'text-gray-400', bgColor: 'bg-gray-800', icon: '○', label: 'Not Evaluated' },
};

const INVARIANT_CLASS_CONFIG: Record<InvariantClass, { color: string; label: string; description: string }> = {
  'S-INV': { color: 'text-blue-400', label: 'Structural', description: 'Schema validation, required fields' },
  'M-INV': { color: 'text-purple-400', label: 'Semantic', description: 'Meaning/intent validation' },
  'X-INV': { color: 'text-cyan-400', label: 'Cross-Artifact', description: 'Inter-document consistency' },
  'T-INV': { color: 'text-orange-400', label: 'Temporal', description: 'Ordering, timestamps, sequences' },
  'A-INV': { color: 'text-yellow-400', label: 'Authority', description: 'GID/lane authorization' },
  'F-INV': { color: 'text-green-400', label: 'Finality', description: 'BER/settlement eligibility' },
  'C-INV': { color: 'text-pink-400', label: 'Training', description: 'Signal emission compliance' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// INVARIANT ROW COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface InvariantRowProps {
  invariant: InvariantDisplay;
  isExpanded: boolean;
  onToggle: () => void;
}

const InvariantRow: React.FC<InvariantRowProps> = ({
  invariant,
  isExpanded,
  onToggle,
}) => {
  const statusConfig = INVARIANT_STATUS_CONFIG[invariant.status];
  const classConfig = INVARIANT_CLASS_CONFIG[invariant.invariantClass];

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onToggle();
      }
    },
    [onToggle]
  );

  return (
    <div
      className={`
        border border-gray-700 rounded-lg overflow-hidden
        ${invariant.status === 'FAILING' ? 'border-l-4 border-l-red-500' : ''}
      `}
    >
      {/* Header Row */}
      <button
        className={`
          w-full flex items-center justify-between p-3
          bg-gray-800 hover:bg-gray-750 transition-colors
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset
        `}
        onClick={onToggle}
        onKeyDown={handleKeyDown}
        aria-expanded={isExpanded}
        aria-controls={`invariant-details-${invariant.invariantId}`}
      >
        <div className="flex items-center gap-3">
          {/* Status Icon */}
          <span
            className={`w-6 h-6 flex items-center justify-center rounded ${statusConfig.bgColor} ${statusConfig.color}`}
            aria-hidden="true"
          >
            {statusConfig.icon}
          </span>

          {/* ID & Name */}
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-gray-200">{invariant.invariantId}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${classConfig.color} bg-gray-700`}>
                {invariant.invariantClass}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">{invariant.name}</p>
          </div>
        </div>

        {/* Expand Icon */}
        <span
          className={`text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          aria-hidden="true"
        >
          ▼
        </span>
      </button>

      {/* Details Panel */}
      {isExpanded && (
        <div
          id={`invariant-details-${invariant.invariantId}`}
          className="p-3 bg-gray-850 border-t border-gray-700"
          role="region"
          aria-label={`Details for ${invariant.invariantId}`}
        >
          {/* Description */}
          <p className="text-sm text-gray-300 mb-3">{invariant.description}</p>

          {/* Class Info */}
          <div className="mb-3">
            <span className="text-xs text-gray-500">Class: </span>
            <span className={`text-xs ${classConfig.color}`}>
              {classConfig.label} — {classConfig.description}
            </span>
          </div>

          {/* Enforcement Points */}
          {invariant.enforcementPoints.length > 0 && (
            <div className="mb-3">
              <span className="text-xs text-gray-500 block mb-1">Enforcement Points:</span>
              <div className="flex flex-wrap gap-1">
                {invariant.enforcementPoints.map((point) => (
                  <span
                    key={point}
                    className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded"
                  >
                    {point}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Violation Message (if failing) */}
          {invariant.status === 'FAILING' && invariant.violationMessage && (
            <div
              className="p-2 bg-red-900/20 border border-red-700 rounded"
              role="alert"
            >
              <span className="text-xs text-red-400 font-medium">Violation: </span>
              <span className="text-xs text-gray-300">{invariant.violationMessage}</span>
            </div>
          )}

          {/* Last Evaluated */}
          {invariant.lastEvaluated && (
            <div className="mt-2 text-xs text-gray-600">
              Last evaluated: {new Date(invariant.lastEvaluated).toLocaleString()}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// GOVERNANCE SUMMARY BAR
// ═══════════════════════════════════════════════════════════════════════════════

interface GovernanceSummaryBarProps {
  rail: GovernanceRailState;
}

const GovernanceSummaryBar: React.FC<GovernanceSummaryBarProps> = ({ rail }) => {
  return (
    <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg mb-4">
      {/* System Status Indicators */}
      <div className="flex items-center gap-4 text-xs">
        <span
          className={`flex items-center gap-1 ${rail.lintV2Active ? 'text-green-400' : 'text-red-400'}`}
          title={rail.lintV2Active ? 'Lint v2 Active' : 'Lint v2 Inactive'}
        >
          {rail.lintV2Active ? '●' : '○'} Lint v2
        </span>
        <span
          className={`flex items-center gap-1 ${rail.schemaRegistryLocked ? 'text-green-400' : 'text-yellow-400'}`}
          title={rail.schemaRegistryLocked ? 'Schema Registry Locked' : 'Schema Registry Unlocked'}
        >
          {rail.schemaRegistryLocked ? '🔒' : '🔓'} Schema
        </span>
        <span
          className={`flex items-center gap-1 ${rail.failClosedEnabled ? 'text-green-400' : 'text-red-400'}`}
          title={rail.failClosedEnabled ? 'Fail-Closed Enabled' : 'Fail-Closed Disabled'}
        >
          {rail.failClosedEnabled ? '✓' : '✗'} Fail-Closed
        </span>
      </div>

      {/* Active PAC */}
      {rail.activePacId && (
        <div className="text-xs">
          <span className="text-gray-500">Active: </span>
          <span className="text-blue-400 font-mono">{rail.activePacId}</span>
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// GOVERNANCE RAIL COMPONENT (MAIN EXPORT)
// ═══════════════════════════════════════════════════════════════════════════════

interface GovernanceRailProps {
  /** Governance rail state */
  rail: GovernanceRailState | null;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
  /** Filter by status */
  filterStatus?: InvariantStatus | 'ALL';
  /** Filter by class */
  filterClass?: InvariantClass | 'ALL';
}

export const GovernanceRail: React.FC<GovernanceRailProps> = ({
  rail,
  loading = false,
  error = null,
  filterStatus = 'ALL',
  filterClass = 'ALL',
}) => {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [localFilterStatus, setLocalFilterStatus] = useState<InvariantStatus | 'ALL'>(filterStatus);
  const [localFilterClass, setLocalFilterClass] = useState<InvariantClass | 'ALL'>(filterClass);

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  // Filter invariants
  const filteredInvariants = React.useMemo(() => {
    if (!rail) return [];
    return rail.invariants.filter((inv) => {
      if (localFilterStatus !== 'ALL' && inv.status !== localFilterStatus) return false;
      if (localFilterClass !== 'ALL' && inv.invariantClass !== localFilterClass) return false;
      return true;
    });
  }, [rail, localFilterStatus, localFilterClass]);

  // Group by status for summary
  const statusGroups = React.useMemo(() => {
    if (!rail) return { passing: 0, failing: 0, notEvaluated: 0 };
    return {
      passing: rail.invariants.filter((i) => i.status === 'PASSING').length,
      failing: rail.invariants.filter((i) => i.status === 'FAILING').length,
      notEvaluated: rail.invariants.filter((i) => i.status === 'NOT_EVALUATED').length,
    };
  }, [rail]);

  if (error) {
    return (
      <div
        className="bg-gray-800 border border-red-700 rounded-lg p-4"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <span aria-hidden="true">🛑</span>
          <span className="font-medium">Governance Rail Error</span>
        </div>
        <p className="text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg"
      aria-label="Governance Rail"
    >
      {/* Header */}
      <div className="border-b border-gray-700 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-lg" aria-hidden="true">⚖️</span>
            <div>
              <h2 className="text-lg font-bold text-gray-100">Governance Rail</h2>
              <p className="text-xs text-gray-500">
                Active invariants and compliance status
              </p>
            </div>
          </div>

          {/* Status Summary */}
          <div
            className="flex items-center gap-3 text-xs"
            role="status"
            aria-label="Invariant summary"
          >
            <span className="text-green-400">✓ {statusGroups.passing}</span>
            {statusGroups.failing > 0 && (
              <span className="text-red-400 font-bold">✗ {statusGroups.failing}</span>
            )}
            <span className="text-gray-500">○ {statusGroups.notEvaluated}</span>
          </div>
        </div>

        {/* System Summary Bar */}
        {rail && <GovernanceSummaryBar rail={rail} />}

        {/* Filters */}
        <div className="flex items-center gap-4">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="filter-status" className="text-xs text-gray-500">
              Status:
            </label>
            <select
              id="filter-status"
              value={localFilterStatus}
              onChange={(e) => setLocalFilterStatus(e.target.value as InvariantStatus | 'ALL')}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">All</option>
              <option value="PASSING">Passing</option>
              <option value="FAILING">Failing</option>
              <option value="NOT_EVALUATED">Not Evaluated</option>
            </select>
          </div>

          {/* Class Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="filter-class" className="text-xs text-gray-500">
              Class:
            </label>
            <select
              id="filter-class"
              value={localFilterClass}
              onChange={(e) => setLocalFilterClass(e.target.value as InvariantClass | 'ALL')}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">All Classes</option>
              <option value="S-INV">S-INV (Structural)</option>
              <option value="M-INV">M-INV (Semantic)</option>
              <option value="X-INV">X-INV (Cross-Artifact)</option>
              <option value="T-INV">T-INV (Temporal)</option>
              <option value="A-INV">A-INV (Authority)</option>
              <option value="F-INV">F-INV (Finality)</option>
              <option value="C-INV">C-INV (Training)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Invariants List */}
      <div className="p-4 max-h-[500px] overflow-y-auto">
        {loading ? (
          <div
            className="flex items-center justify-center py-8"
            role="status"
            aria-label="Loading invariants"
          >
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-500" />
            <span className="sr-only">Loading governance data...</span>
          </div>
        ) : !rail ? (
          <div className="text-center py-8 text-gray-500">
            <span aria-hidden="true">📭</span>
            <p className="mt-2">No governance data available</p>
          </div>
        ) : filteredInvariants.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <span aria-hidden="true">🔍</span>
            <p className="mt-2">No invariants match filters</p>
          </div>
        ) : (
          <div
            className="space-y-2"
            role="list"
            aria-label="Invariant rules"
          >
            {filteredInvariants.map((invariant) => (
              <InvariantRow
                key={invariant.invariantId}
                invariant={invariant}
                isExpanded={expandedIds.has(invariant.invariantId)}
                onToggle={() => toggleExpanded(invariant.invariantId)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Last Sync Footer */}
      {rail && (
        <div className="border-t border-gray-700 px-4 py-2 text-xs text-gray-600">
          Last sync: {new Date(rail.lastSync).toLocaleString()}
        </div>
      )}
    </section>
  );
};

export default GovernanceRail;
