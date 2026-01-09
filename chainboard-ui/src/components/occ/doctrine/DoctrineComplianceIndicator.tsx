/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Doctrine Compliance Indicator (MANDATORY)
 * PAC-BENSON-P32: UI Implementation (Operator Experience Doctrine Apply)
 * 
 * DOCTRINE LAW 6 — Visual Invariants
 * 
 * Status Display Semantics:
 * - §6.1: GREEN = Healthy/Compliant/Active
 * - §6.1: YELLOW = Warning/Pending/Review
 * - §6.1: RED = Error/Violation/Blocked
 * 
 * Motion Semantics:
 * - §6.2: PULSING = Live/Active process
 * - §6.2: STATIC = Idle/Completed
 * - §6.2: SPINNING = Loading/Processing
 * 
 * Provides visual compliance summary for Doctrine Laws 1-17.
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display
 * - INV-DOC-LAW-6: All status colors follow §6.1 semantics
 * 
 * Author: CODY (GID-01) — Doctrine Compliance Lead
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// LAW 6 COLOR SEMANTICS (§6.1)
// ═══════════════════════════════════════════════════════════════════════════════

type ComplianceLevel = 'COMPLIANT' | 'WARNING' | 'VIOLATION' | 'UNKNOWN';

const COMPLIANCE_COLORS: Record<
  ComplianceLevel,
  { bg: string; text: string; border: string; glow: string }
> = {
  COMPLIANT: {
    bg: 'bg-green-500',
    text: 'text-green-400',
    border: 'border-green-500',
    glow: 'shadow-green-500/50',
  },
  WARNING: {
    bg: 'bg-yellow-500',
    text: 'text-yellow-400',
    border: 'border-yellow-500',
    glow: 'shadow-yellow-500/50',
  },
  VIOLATION: {
    bg: 'bg-red-500',
    text: 'text-red-400',
    border: 'border-red-500',
    glow: 'shadow-red-500/50',
  },
  UNKNOWN: {
    bg: 'bg-gray-500',
    text: 'text-gray-400',
    border: 'border-gray-500',
    glow: 'shadow-gray-500/50',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// DOCTRINE LAWS REGISTRY
// ═══════════════════════════════════════════════════════════════════════════════

interface DoctrineLaw {
  id: number;
  title: string;
  description: string;
  category: 'VISIBILITY' | 'GOVERNANCE' | 'SECURITY' | 'AUDIT';
}

const DOCTRINE_LAWS: DoctrineLaw[] = [
  { id: 1, title: 'Flight Recorder Mandate', description: 'All decisions logged with full context', category: 'AUDIT' },
  { id: 2, title: 'Cockpit Visibility', description: 'Operator sees all system state', category: 'VISIBILITY' },
  { id: 3, title: 'Glass-Box Operations', description: 'No hidden logic or black boxes', category: 'VISIBILITY' },
  { id: 4, title: 'Mandatory Surfaces', description: 'Required UI components present', category: 'VISIBILITY' },
  { id: 5, title: 'Forbidden Patterns', description: 'No auto-approve, silent fail, hidden override', category: 'GOVERNANCE' },
  { id: 6, title: 'Visual Invariants', description: 'Consistent color/motion semantics', category: 'VISIBILITY' },
  { id: 7, title: 'Audit Trail Immutability', description: 'Logs append-only, hash-chained', category: 'AUDIT' },
  { id: 8, title: 'ProofPack Completeness', description: 'Every decision has verifiable proof', category: 'AUDIT' },
  { id: 9, title: 'Trust Score Display', description: 'Trust indicators always visible', category: 'VISIBILITY' },
  { id: 10, title: 'Agent Accountability', description: 'Every action traced to agent GID', category: 'GOVERNANCE' },
  { id: 11, title: 'Quantum-Safe Readiness', description: 'Cryptographic primitives upgradeable', category: 'SECURITY' },
  { id: 12, title: 'PAC Governance', description: 'Pack Admission Control enforced', category: 'GOVERNANCE' },
  { id: 13, title: 'WRAP Requirements', description: 'Work Result Attestation Protocol', category: 'GOVERNANCE' },
  { id: 14, title: 'BER Finality', description: 'Benson Execution Report closes PAC', category: 'GOVERNANCE' },
  { id: 15, title: 'Kill Switch Presence', description: 'Emergency halt always accessible', category: 'SECURITY' },
  { id: 16, title: 'ALEX Supremacy', description: 'ALEX governance rules override all', category: 'GOVERNANCE' },
  { id: 17, title: 'No Silent Degradation', description: 'All failures visible to operator', category: 'SECURITY' },
];

// ═══════════════════════════════════════════════════════════════════════════════
// LAW COMPLIANCE ENTRY
// ═══════════════════════════════════════════════════════════════════════════════

interface LawComplianceStatus {
  lawId: number;
  level: ComplianceLevel;
  message?: string;
  lastChecked?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LAW ROW COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface LawRowProps {
  law: DoctrineLaw;
  status: LawComplianceStatus | undefined;
}

const LawRow: React.FC<LawRowProps> = ({ law, status }) => {
  const level = status?.level ?? 'UNKNOWN';
  const colors = COMPLIANCE_COLORS[level];

  return (
    <div className="flex items-center justify-between py-2 px-3 border-b border-gray-700 hover:bg-gray-800 transition-colors">
      <div className="flex items-center gap-3">
        {/* Status Dot (Law 6, §6.2 - static for completed checks) */}
        <span
          className={`w-2 h-2 rounded-full ${colors.bg}`}
          aria-hidden="true"
        />
        
        {/* Law Info */}
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-200">Law {law.id}</span>
            <span className="text-gray-400">—</span>
            <span className="text-gray-300">{law.title}</span>
          </div>
          <span className="text-xs text-gray-500">{law.description}</span>
        </div>
      </div>

      {/* Compliance Badge */}
      <div className="flex items-center gap-2">
        {status?.message && (
          <span className="text-xs text-gray-500 max-w-[200px] truncate" title={status.message}>
            {status.message}
          </span>
        )}
        <span
          className={`px-2 py-0.5 text-xs rounded font-medium ${colors.text} bg-opacity-20 ${
            level === 'COMPLIANT' ? 'bg-green-500' :
            level === 'WARNING' ? 'bg-yellow-500' :
            level === 'VIOLATION' ? 'bg-red-500' :
            'bg-gray-500'
          } bg-opacity-20`}
          role="status"
          aria-label={`Law ${law.id} compliance: ${level}`}
        >
          {level}
        </span>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface DoctrineComplianceIndicatorProps {
  /** Compliance status for each law */
  complianceStatuses: LawComplianceStatus[];
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Callback to refresh */
  onRefresh: () => void;
}

export const DoctrineComplianceIndicator: React.FC<DoctrineComplianceIndicatorProps> = ({
  complianceStatuses,
  isLoading,
  error,
  onRefresh,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Calculate summary
  const statusMap = new Map(complianceStatuses.map((s) => [s.lawId, s]));
  const compliantCount = complianceStatuses.filter((s) => s.level === 'COMPLIANT').length;
  const warningCount = complianceStatuses.filter((s) => s.level === 'WARNING').length;
  const violationCount = complianceStatuses.filter((s) => s.level === 'VIOLATION').length;
  
  // Determine overall status
  const overallLevel: ComplianceLevel = 
    violationCount > 0 ? 'VIOLATION' :
    warningCount > 0 ? 'WARNING' :
    compliantCount === DOCTRINE_LAWS.length ? 'COMPLIANT' :
    'UNKNOWN';
  
  const overallColors = COMPLIANCE_COLORS[overallLevel];

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Loading State
  // ═══════════════════════════════════════════════════════════════════════════
  if (isLoading && complianceStatuses.length === 0) {
    return (
      <div 
        className="bg-gray-900 border border-gray-700 rounded-lg p-4"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center gap-2 text-gray-400">
          {/* Law 6, §6.2 - spinning for loading */}
          <span className="animate-spin">⟳</span>
          <span>Checking doctrine compliance...</span>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Error State
  // ═══════════════════════════════════════════════════════════════════════════
  if (error) {
    return (
      <div 
        className="bg-red-900/20 border border-red-700 rounded-lg p-4"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-400">
            <span>✗</span>
            <span>Doctrine Compliance Error: {error}</span>
          </div>
          <button
            onClick={onRefresh}
            className="px-3 py-1 bg-red-700 hover:bg-red-600 text-white text-sm rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <section
      className={`bg-gray-900 border ${overallColors.border} rounded-lg overflow-hidden shadow-lg ${overallColors.glow}`}
      aria-labelledby="compliance-title"
    >
      {/* Summary Header (always visible) */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-3 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
            aria-expanded={isExpanded}
            aria-controls="compliance-details"
          >
            {/* Overall Status Indicator (Law 6, §6.2 - pulsing if active check) */}
            <span
              className={`w-4 h-4 rounded-full ${overallColors.bg} ${
                isLoading ? 'animate-pulse' : ''
              }`}
              aria-hidden="true"
            />
            
            <h2 id="compliance-title" className="text-lg font-semibold text-gray-100">
              Doctrine Compliance
            </h2>
            
            <span 
              className={`px-2 py-0.5 rounded text-xs font-medium ${overallColors.text}`}
              role="status"
            >
              {overallLevel}
            </span>
            
            <span className={`text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
              ▼
            </span>
          </button>

          {/* Quick Stats */}
          <div className="flex items-center gap-4 text-xs">
            <span className="text-green-400">{compliantCount} compliant</span>
            {warningCount > 0 && <span className="text-yellow-400">{warningCount} warnings</span>}
            {violationCount > 0 && <span className="text-red-400">{violationCount} violations</span>}
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
              aria-label="Refresh compliance check"
            >
              {isLoading ? '⟳' : '↻'}
            </button>
          </div>
        </div>
      </header>

      {/* Law Details (expandable) */}
      {isExpanded && (
        <div id="compliance-details" className="max-h-[400px] overflow-y-auto">
          {DOCTRINE_LAWS.map((law) => (
            <LawRow 
              key={law.id} 
              law={law} 
              status={statusMap.get(law.id)} 
            />
          ))}
        </div>
      )}

      {/* Footer with version */}
      <footer className="bg-gray-850 border-t border-gray-700 px-4 py-2">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Operator Experience Doctrine v1.0.0</span>
          <span>17 Laws | ALEX-Enforced</span>
        </div>
      </footer>
    </section>
  );
};

export default DoctrineComplianceIndicator;
