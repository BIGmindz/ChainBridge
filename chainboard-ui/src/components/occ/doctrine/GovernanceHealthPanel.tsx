/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Governance Health Panel (MANDATORY)
 * PAC-BENSON-P32: UI Implementation (Operator Experience Doctrine Apply)
 * 
 * DOCTRINE LAW 4, §4.4 — Governance Health Panel (MANDATORY)
 * DOCTRINE LAW 16-17: ALEX Rule Alignment
 * 
 * Displays governance health metrics:
 * - ALEX Rules count and violations
 * - Active PACs count
 * - Pending WRAPs count
 * - Open BERs count
 * - Drift status
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display
 * - INV-ALEX-001: ALEX supremacy displayed
 * 
 * Author: SONNY (GID-02) — UI Implementation Lead
 * Governance: ALEX (GID-08)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React from 'react';
import type { GovernanceHealthState } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS COLORS (LAW 6, §6.1)
// ═══════════════════════════════════════════════════════════════════════════════

const STATUS_COLORS = {
  GOVERNED: { bg: 'bg-green-900/30', border: 'border-green-700', text: 'text-green-400', icon: '✓' },
  WARNING: { bg: 'bg-yellow-900/30', border: 'border-yellow-700', text: 'text-yellow-400', icon: '⚠️' },
  CRITICAL: { bg: 'bg-red-900/30', border: 'border-red-700', text: 'text-red-400', icon: '✗' },
};

const DRIFT_COLORS = {
  ZERO: { bg: 'bg-green-900/30', text: 'text-green-400', label: 'ZERO' },
  DETECTED: { bg: 'bg-red-900/30', text: 'text-red-400', label: 'DETECTED' },
  UNKNOWN: { bg: 'bg-gray-800', text: 'text-gray-400', label: 'UNKNOWN' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// METRIC CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface MetricCardProps {
  label: string;
  value: number | string;
  subValue?: string;
  status?: 'good' | 'warning' | 'critical' | 'neutral';
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, subValue, status = 'neutral' }) => {
  const statusStyles = {
    good: 'border-green-700 bg-green-900/20',
    warning: 'border-yellow-700 bg-yellow-900/20',
    critical: 'border-red-700 bg-red-900/20',
    neutral: 'border-gray-700 bg-gray-800',
  };

  const valueStyles = {
    good: 'text-green-400',
    warning: 'text-yellow-400',
    critical: 'text-red-400',
    neutral: 'text-gray-200',
  };

  return (
    <div 
      className={`flex flex-col items-center p-4 rounded-lg border ${statusStyles[status]}`}
      role="group"
      aria-label={`${label}: ${value}${subValue ? ` (${subValue})` : ''}`}
    >
      <span className="text-xs text-gray-500 mb-1">{label}</span>
      <span className={`text-2xl font-bold ${valueStyles[status]}`}>{value}</span>
      {subValue && <span className="text-xs text-gray-500 mt-1">{subValue}</span>}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface GovernanceHealthPanelProps {
  /** Governance health state from backend */
  state: GovernanceHealthState | null;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Callback to refresh */
  onRefresh: () => void;
  /** Callback to view details */
  onViewDetails: () => void;
}

export const GovernanceHealthPanel: React.FC<GovernanceHealthPanelProps> = ({
  state,
  isLoading,
  error,
  onRefresh,
  onViewDetails,
}) => {
  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Loading State
  // ═══════════════════════════════════════════════════════════════════════════
  if (isLoading && !state) {
    return (
      <div 
        className="bg-gray-900 border border-gray-700 rounded-lg p-6"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <span className="animate-spin">⟳</span>
          <span>Loading governance health...</span>
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
        className="bg-red-900/20 border border-red-700 rounded-lg p-6"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-400">
            <span>✗</span>
            <span>Governance Error: {error}</span>
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

  // Default state for display
  const displayState: GovernanceHealthState = state ?? {
    alexRulesCount: 11,
    alexViolations: 0,
    activePacCount: 0,
    pendingWrapsCount: 0,
    openBersCount: 0,
    driftStatus: 'UNKNOWN',
    lastHealthCheck: new Date().toISOString(),
    overallStatus: 'GOVERNED',
  };

  const statusConfig = STATUS_COLORS[displayState.overallStatus];
  const driftConfig = DRIFT_COLORS[displayState.driftStatus];

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden"
      aria-labelledby="governance-health-title"
    >
      {/* Header with Overall Status */}
      <header className={`${statusConfig.bg} border-b ${statusConfig.border} px-4 py-3`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`text-xl ${statusConfig.text}`} aria-hidden="true">
              {statusConfig.icon}
            </span>
            <h2 id="governance-health-title" className={`text-lg font-semibold ${statusConfig.text}`}>
              Governance: {displayState.overallStatus}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            {displayState.lastHealthCheck && (
              <span className="text-xs text-gray-500">
                Last check: {new Date(displayState.lastHealthCheck).toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
              aria-label="Refresh governance health"
            >
              ⟳
            </button>
          </div>
        </div>
      </header>

      {/* Metrics Grid (Law 4, §4.4) */}
      <div className="p-4">
        <div className="grid grid-cols-3 gap-3 mb-4">
          {/* ALEX Rules */}
          <MetricCard
            label="ALEX Rules"
            value={displayState.alexRulesCount}
            status="neutral"
          />

          {/* Violations */}
          <MetricCard
            label="Violations"
            value={displayState.alexViolations}
            status={displayState.alexViolations === 0 ? 'good' : 'critical'}
          />

          {/* Drift Status */}
          <div 
            className={`flex flex-col items-center p-4 rounded-lg border border-gray-700 ${driftConfig.bg}`}
            role="group"
            aria-label={`Drift: ${driftConfig.label}`}
          >
            <span className="text-xs text-gray-500 mb-1">Drift</span>
            <span className={`text-lg font-bold ${driftConfig.text}`}>{driftConfig.label}</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          {/* Active PACs */}
          <MetricCard
            label="Active PACs"
            value={displayState.activePacCount}
            status="neutral"
          />

          {/* Pending WRAPs */}
          <MetricCard
            label="Pending WRAPs"
            value={displayState.pendingWrapsCount}
            status={displayState.pendingWrapsCount > 0 ? 'warning' : 'good'}
          />

          {/* Open BERs */}
          <MetricCard
            label="Open BERs"
            value={displayState.openBersCount}
            status="neutral"
          />
        </div>
      </div>

      {/* ALEX Supremacy Notice (Law 16, §16.2) */}
      <div className="px-4 pb-4">
        <div className="p-3 bg-purple-900/20 border border-purple-700 rounded-lg text-center">
          <span className="text-xs text-purple-400">
            🔒 ALEX Governance Active — All operations subject to 11 hard constraints
          </span>
        </div>
      </div>

      {/* View Details Button */}
      <footer className="bg-gray-800 border-t border-gray-700 px-4 py-3">
        <button
          onClick={onViewDetails}
          className="w-full px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
        >
          View Full Governance Details →
        </button>
      </footer>
    </section>
  );
};

export default GovernanceHealthPanel;
