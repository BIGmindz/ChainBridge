/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Governance Trust Badge
 * PAC-BENSON-P34: Trust Center (Public Audit Interface)
 * 
 * Displays governance trust indicators for public verification.
 * 
 * DOCTRINE REFERENCES:
 * - Law 2: Cockpit Visibility (adapted for external)
 * - Law 6: Visual Invariants
 * - Law 16: ALEX Supremacy (governance indicators)
 * 
 * CONSTRAINTS:
 * - READ-ONLY display
 * - No sensitive data
 * - Public-safe indicators only
 * 
 * Author: SONNY (GID-02) — Trust Center UI
 * UX: LIRA (GID-09) — Public UX & Accessibility
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React from 'react';
import type { TrustFingerprint, TrustCoverage, GamedayResults } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// COVERAGE INDICATOR
// ═══════════════════════════════════════════════════════════════════════════════

interface CoverageItemProps {
  label: string;
  enabled: boolean;
  description: string;
}

const CoverageItem: React.FC<CoverageItemProps> = ({ label, enabled, description }) => (
  <div 
    className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0"
    title={description}
  >
    <span className="text-gray-300 text-sm">{label}</span>
    <span
      className={`
        flex items-center gap-1 text-sm font-medium
        ${enabled ? 'text-green-400' : 'text-gray-500'}
      `}
      role="status"
      aria-label={`${label}: ${enabled ? 'Enabled' : 'Disabled'}`}
    >
      <span aria-hidden="true">{enabled ? '✓' : '○'}</span>
      {enabled ? 'Enabled' : 'Disabled'}
    </span>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface GovernanceTrustBadgeProps {
  /** Governance fingerprint */
  fingerprint: TrustFingerprint | null;
  /** Governance coverage */
  coverage: TrustCoverage | null;
  /** Gameday results */
  gameday: GamedayResults | null;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Callback to refresh data */
  onRefresh: () => void;
}

export const GovernanceTrustBadge: React.FC<GovernanceTrustBadgeProps> = ({
  fingerprint,
  coverage,
  gameday,
  isLoading,
  error,
  onRefresh,
}) => {
  // Calculate overall trust score (simple presence-based)
  const coverageScore = coverage
    ? Object.values(coverage).filter(Boolean).length
    : 0;
  const totalCoverage = 6; // Number of coverage items
  const coveragePercent = Math.round((coverageScore / totalCoverage) * 100);

  // Determine overall status
  const overallStatus = 
    error ? 'error' :
    isLoading ? 'loading' :
    coveragePercent === 100 ? 'full' :
    coveragePercent >= 80 ? 'high' :
    coveragePercent >= 50 ? 'medium' :
    'low';

  const statusColors = {
    full: 'border-green-500 bg-green-500/10',
    high: 'border-green-400 bg-green-400/10',
    medium: 'border-yellow-500 bg-yellow-500/10',
    low: 'border-red-500 bg-red-500/10',
    error: 'border-red-700 bg-red-700/10',
    loading: 'border-gray-500 bg-gray-500/10',
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Loading State
  // ═══════════════════════════════════════════════════════════════════════════
  if (isLoading && !fingerprint) {
    return (
      <div 
        className="bg-gray-900 border border-gray-700 rounded-lg p-6"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <span className="animate-spin">⟳</span>
          <span>Loading governance trust data...</span>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Error State
  // ═══════════════════════════════════════════════════════════════════════════
  if (error && !fingerprint) {
    return (
      <div 
        className="bg-red-900/20 border border-red-700 rounded-lg p-6"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-400">
            <span>✗</span>
            <span>Trust data unavailable: {error}</span>
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
      className={`bg-gray-900 border-2 ${statusColors[overallStatus]} rounded-lg overflow-hidden`}
      aria-labelledby="trust-badge-title"
    >
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Trust Shield Icon */}
            <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
              <span className="text-xl" aria-hidden="true">🛡️</span>
            </div>
            <div>
              <h2 id="trust-badge-title" className="text-lg font-semibold text-gray-100">
                Governance Trust
              </h2>
              <span className="text-xs text-gray-400">ChainBridge Verified</span>
            </div>
          </div>

          {/* Coverage Score */}
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-100">
              {coveragePercent}%
            </div>
            <div className="text-xs text-gray-400">
              Coverage ({coverageScore}/{totalCoverage})
            </div>
          </div>
        </div>
      </header>

      {/* Fingerprint Section */}
      {fingerprint && (
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="text-xs text-gray-500 mb-1">Governance Fingerprint</div>
          <code className="text-xs text-blue-400 font-mono break-all">
            {fingerprint.fingerprintHash}
          </code>
          <div className="text-xs text-gray-500 mt-1">
            Generated: {new Date(fingerprint.generatedAt).toLocaleString()}
          </div>
        </div>
      )}

      {/* Coverage Grid */}
      {coverage && (
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="text-sm text-gray-400 mb-2">Governance Coverage</div>
          <CoverageItem 
            label="Access Control Matrix"
            enabled={coverage.acmEnforced}
            description="ACM enforcement protects resource access"
          />
          <CoverageItem 
            label="Fail-Closed Execution"
            enabled={coverage.failClosedExecution}
            description="System fails safely on errors"
          />
          <CoverageItem 
            label="Artifact Verification"
            enabled={coverage.artifactVerification}
            description="Build artifacts are cryptographically verified"
          />
          <CoverageItem 
            label="Scope Guard"
            enabled={coverage.scopeGuard}
            description="Repository scope is enforced"
          />
          <CoverageItem 
            label="DRCP Active"
            enabled={coverage.drcpActive}
            description="Denial Rejection Correction Protocol active"
          />
          <CoverageItem 
            label="Diggi Enabled"
            enabled={coverage.diggiEnabled}
            description="Diggi bounded correction enabled"
          />
        </div>
      )}

      {/* Gameday Results */}
      {gameday && (
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="text-sm text-gray-400 mb-2">Adversarial Testing (Gameday)</div>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-xl font-bold text-gray-100">{gameday.scenariosTested}</div>
              <div className="text-xs text-gray-500">Scenarios</div>
            </div>
            <div>
              <div className={`text-xl font-bold ${gameday.silentFailures === 0 ? 'text-green-400' : 'text-red-400'}`}>
                {gameday.silentFailures}
              </div>
              <div className="text-xs text-gray-500">Silent Failures</div>
            </div>
            <div>
              <div className={`text-xl font-bold ${gameday.failClosed ? 'text-green-400' : 'text-red-400'}`}>
                {gameday.failClosed ? '✓' : '✗'}
              </div>
              <div className="text-xs text-gray-500">Fail-Closed</div>
            </div>
          </div>
          <div className="text-xs text-gray-500 mt-2 text-center">
            Last Run: {new Date(gameday.lastRun).toLocaleDateString()}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-gray-850 px-4 py-2">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Trust data is read-only and publicly verifiable</span>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
            aria-label="Refresh trust data"
          >
            {isLoading ? '⟳' : '↻'} Refresh
          </button>
        </div>
      </footer>
    </section>
  );
};

export default GovernanceTrustBadge;
