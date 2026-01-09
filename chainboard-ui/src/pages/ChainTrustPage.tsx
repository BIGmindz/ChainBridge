// ═══════════════════════════════════════════════════════════════════════════════
// ChainTrust Page — External Trust Center
// PAC-JEFFREY-P19R: ChainTrust UI Implementation (Sonny GID-02)
//
// READ-ONLY governance visualization for external auditors and investors.
// Produces investor- and auditor-grade proof of control.
//
// FEATURES:
// 1. ChainTrust Overview — Governance status, invariant count, runtime mode
// 2. Agent Uniform Inspection — GID, role, scope, PAC/ACK/WRAP/BER indicators
// 3. PDO Lifecycle Viewer — Proof → Decision → Outcome timeline
// 4. Invariant Coverage Display — S/A/X/T/F/UNIFORM categories
// 5. External Audit Mode — Read-only, shareable, deterministic
//
// DATA SOURCE: lint_v2 / governance APIs (no inferred state)
// INVARIANT: INV-LINT-PLAT-003 — UI renders only lint-validated state
// ═══════════════════════════════════════════════════════════════════════════════

import React, { useEffect, useState, useCallback } from 'react';
import {
  GovernanceStatusPanel,
  AgentUniformPanel,
  PDOLifecycleViewer,
  InvariantCoveragePanel,
} from '../components/chaintrust';
import type {
  GovernanceStatusDTO,
  AgentUniformPanelDTO,
  PDOLifecycleViewerDTO,
  InvariantCoveragePanelDTO,
} from '../types/chaintrust';
import {
  getGovernanceStatus,
  getAgentUniformPanel,
  getPDOLifecycleViewer,
  getInvariantCoverage,
} from '../api/chaintrustApi';

/**
 * ChainTrust header with branding.
 */
const ChainTrustHeader: React.FC<{ lastUpdated: string | null; onRefresh: () => void }> = ({
  lastUpdated,
  onRefresh,
}) => (
  <div className="bg-gray-900 border-b border-gray-700 px-6 py-4">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">CT</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">ChainTrust</h1>
            <p className="text-xs text-gray-400">External Trust Center — Read-Only</p>
          </div>
        </div>
        <div className="flex items-center gap-2 ml-8">
          <span className="text-xs text-gray-500">Governance Surface</span>
          <span className="bg-green-900/30 text-green-400 text-xs px-2 py-1 rounded">
            AUDITOR GRADE
          </span>
        </div>
      </div>
      <div className="flex items-center gap-4">
        {lastUpdated && (
          <span className="text-xs text-gray-500">
            Last updated: {new Date(lastUpdated).toLocaleString()}
          </span>
        )}
        <button
          onClick={onRefresh}
          className="text-sm bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition-colors"
        >
          ↻ Refresh
        </button>
      </div>
    </div>
  </div>
);

/**
 * External Audit Mode banner.
 */
const AuditModeBanner: React.FC = () => (
  <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4 mb-6">
    <div className="flex items-center gap-3">
      <span className="text-blue-400 text-xl">🔒</span>
      <div>
        <h3 className="text-sm font-semibold text-blue-300">External Audit Mode</h3>
        <p className="text-xs text-blue-400">
          This view is read-only and deterministic. All data originates from lint_v2 governance APIs.
          No internal identifiers exposed. Shareable with auditors and investors.
        </p>
      </div>
    </div>
  </div>
);

/**
 * Loading state for initial page load.
 */
const PageLoading: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen bg-gray-950">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
      <p className="text-gray-400">Loading ChainTrust governance data...</p>
    </div>
  </div>
);

/**
 * ChainTrust Page — Main Trust Center Dashboard.
 */
export const ChainTrustPage: React.FC = () => {
  // Data state
  const [governanceStatus, setGovernanceStatus] = useState<GovernanceStatusDTO | null>(null);
  const [agentUniform, setAgentUniform] = useState<AgentUniformPanelDTO | null>(null);
  const [pdoLifecycle, setPdoLifecycle] = useState<PDOLifecycleViewerDTO | null>(null);
  const [invariantCoverage, setInvariantCoverage] = useState<InvariantCoveragePanelDTO | null>(null);
  
  // Loading states
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [loadingPdo, setLoadingPdo] = useState(true);
  const [loadingInvariants, setLoadingInvariants] = useState(true);
  
  // Error states
  const [errorStatus, setErrorStatus] = useState<string | null>(null);
  const [errorAgents, setErrorAgents] = useState<string | null>(null);
  const [errorPdo, setErrorPdo] = useState<string | null>(null);
  const [errorInvariants, setErrorInvariants] = useState<string | null>(null);
  
  // Last updated
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  /**
   * Fetch all data in parallel.
   */
  const fetchAllData = useCallback(async () => {
    setLastUpdated(new Date().toISOString());

    // Fetch governance status
    setLoadingStatus(true);
    setErrorStatus(null);
    try {
      const status = await getGovernanceStatus();
      setGovernanceStatus(status);
    } catch (err) {
      setErrorStatus(err instanceof Error ? err.message : 'Failed to load governance status');
    } finally {
      setLoadingStatus(false);
    }

    // Fetch agent uniform data
    setLoadingAgents(true);
    setErrorAgents(null);
    try {
      const agents = await getAgentUniformPanel();
      setAgentUniform(agents);
    } catch (err) {
      setErrorAgents(err instanceof Error ? err.message : 'Failed to load agent uniform data');
    } finally {
      setLoadingAgents(false);
    }

    // Fetch PDO lifecycle data
    setLoadingPdo(true);
    setErrorPdo(null);
    try {
      const pdo = await getPDOLifecycleViewer();
      setPdoLifecycle(pdo);
    } catch (err) {
      setErrorPdo(err instanceof Error ? err.message : 'Failed to load PDO lifecycle data');
    } finally {
      setLoadingPdo(false);
    }

    // Fetch invariant coverage data
    setLoadingInvariants(true);
    setErrorInvariants(null);
    try {
      const invariants = await getInvariantCoverage();
      setInvariantCoverage(invariants);
    } catch (err) {
      setErrorInvariants(err instanceof Error ? err.message : 'Failed to load invariant coverage');
    } finally {
      setLoadingInvariants(false);
    }
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Check if initial load is complete
  const isInitialLoading = loadingStatus && loadingAgents && loadingPdo && loadingInvariants;

  if (isInitialLoading) {
    return <PageLoading />;
  }

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <ChainTrustHeader lastUpdated={lastUpdated} onRefresh={fetchAllData} />

      {/* Main Content */}
      <div className="p-6">
        {/* Audit Mode Banner */}
        <AuditModeBanner />

        {/* Dashboard Grid */}
        <div className="grid grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-6">
            {/* Governance Status */}
            <GovernanceStatusPanel
              status={governanceStatus}
              loading={loadingStatus}
              error={errorStatus}
            />

            {/* PDO Lifecycle */}
            <PDOLifecycleViewer
              data={pdoLifecycle}
              loading={loadingPdo}
              error={errorPdo}
            />
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Agent Uniform */}
            <AgentUniformPanel
              data={agentUniform}
              loading={loadingAgents}
              error={errorAgents}
            />

            {/* Invariant Coverage */}
            <InvariantCoveragePanel
              data={invariantCoverage}
              loading={loadingInvariants}
              error={errorInvariants}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 pt-6 border-t border-gray-800 text-center">
          <p className="text-xs text-gray-600">
            ChainTrust External Trust Center · PAC-JEFFREY-P19R · Read-Only Governance Surface
          </p>
          <p className="text-xs text-gray-700 mt-1">
            All data sourced from lint_v2 governance APIs · No inferred or derived state
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChainTrustPage;
