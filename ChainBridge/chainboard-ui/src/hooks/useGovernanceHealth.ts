/**
 * useGovernanceHealth Hook — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * React hook for fetching and managing governance health data.
 * All operations are READ-ONLY.
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 */

import { useState, useEffect, useCallback } from 'react';
import type {
  GovernanceHealthMetrics,
  GovernanceHealthState,
  SettlementChain,
  EnterpriseComplianceSummary,
  SettlementStage,
} from '../types/governanceHealth';
import { fetchGovernanceSummary } from '../services/governanceLedgerApi';

/**
 * Mock data generator for governance health metrics.
 * In production, this would call the governance API.
 */
function generateMockMetrics(): GovernanceHealthMetrics {
  return {
    totalPacs: 58,
    activePacs: 12,
    blockedPacs: 2,
    positiveClosures: 41,

    totalBers: 45,
    pendingBers: 3,
    approvedBers: 42,

    totalPdos: 42,
    finalizedPdos: 40,

    totalWraps: 40,
    acceptedWraps: 38,

    settlementRate: 93.4,
    avgSettlementTimeMs: 245000, // ~4 minutes
    pendingSettlements: 5,

    ledgerIntegrity: 'HEALTHY',
    lastLedgerSync: new Date().toISOString(),
    sequenceGaps: 0,
  };
}

/**
 * Generate mock settlement chains.
 */
function generateMockChains(): SettlementChain[] {
  const now = new Date();

  return [
    {
      chainId: 'chain-001',
      pacId: 'PAC-BENSON-P58-GOVERNANCE-DOCTRINE-V1-1-PDO-CANONICALIZATION-01',
      berId: 'BER-BENSON-P58-20251226',
      pdoId: 'PDO-BENSON-P58-20251226',
      wrapId: 'WRAP-BENSON-P58-20251226',
      currentStage: 'LEDGER_COMMIT',
      status: 'COMPLETED',
      startedAt: new Date(now.getTime() - 3600000).toISOString(),
      completedAt: new Date().toISOString(),
      nodes: [
        { stage: 'PAC_DISPATCH', status: 'FINALIZED', artifactId: 'PAC-BENSON-P58', authority: 'BENSON (GID-00)' },
        { stage: 'AGENT_EXECUTION', status: 'FINALIZED' },
        { stage: 'BER_GENERATION', status: 'FINALIZED', artifactId: 'BER-BENSON-P58' },
        { stage: 'HUMAN_REVIEW', status: 'FINALIZED', authority: 'ALEX' },
        { stage: 'PDO_FINALIZATION', status: 'FINALIZED', artifactId: 'PDO-BENSON-P58' },
        { stage: 'WRAP_GENERATION', status: 'FINALIZED', artifactId: 'WRAP-BENSON-P58' },
        { stage: 'WRAP_ACCEPTED', status: 'FINALIZED' },
        { stage: 'LEDGER_COMMIT', status: 'FINALIZED' },
      ],
    },
    {
      chainId: 'chain-002',
      pacId: 'PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01',
      currentStage: 'AGENT_EXECUTION',
      status: 'IN_PROGRESS',
      startedAt: new Date().toISOString(),
      nodes: [
        { stage: 'PAC_DISPATCH', status: 'FINALIZED', artifactId: 'PAC-SONNY-P01', authority: 'BENSON (GID-00)' },
        { stage: 'AGENT_EXECUTION', status: 'ACTIVE' },
        { stage: 'BER_GENERATION', status: 'PENDING' },
        { stage: 'HUMAN_REVIEW', status: 'PENDING' },
        { stage: 'PDO_FINALIZATION', status: 'PENDING' },
        { stage: 'WRAP_GENERATION', status: 'PENDING' },
        { stage: 'WRAP_ACCEPTED', status: 'PENDING' },
        { stage: 'LEDGER_COMMIT', status: 'PENDING' },
      ],
    },
    {
      chainId: 'chain-003',
      pacId: 'PAC-DAN-P44-GOVERNANCE-CI-FAILURE-VISIBILITY-AUTO-REMEDIATION-01',
      berId: 'BER-DAN-P44-20251225',
      currentStage: 'HUMAN_REVIEW',
      status: 'IN_PROGRESS',
      startedAt: new Date(now.getTime() - 7200000).toISOString(),
      nodes: [
        { stage: 'PAC_DISPATCH', status: 'FINALIZED', artifactId: 'PAC-DAN-P44', authority: 'BENSON (GID-00)' },
        { stage: 'AGENT_EXECUTION', status: 'FINALIZED' },
        { stage: 'BER_GENERATION', status: 'FINALIZED', artifactId: 'BER-DAN-P44' },
        { stage: 'HUMAN_REVIEW', status: 'AWAITING_REVIEW', authority: 'ALEX (pending)' },
        { stage: 'PDO_FINALIZATION', status: 'PENDING' },
        { stage: 'WRAP_GENERATION', status: 'PENDING' },
        { stage: 'WRAP_ACCEPTED', status: 'PENDING' },
        { stage: 'LEDGER_COMMIT', status: 'PENDING' },
      ],
    },
  ];
}

/**
 * Generate mock enterprise compliance summary.
 */
function generateMockComplianceSummary(): EnterpriseComplianceSummary {
  return {
    mappings: [
      { framework: 'SOX', control: '§302', description: 'Scope Definition', artifact: 'PAC' },
      { framework: 'SOX', control: '§404', description: 'Assessment', artifact: 'BER' },
      { framework: 'SOX', control: '§802', description: 'Retention', artifact: 'LEDGER' },
      { framework: 'SOC2', control: 'CC6.1', description: 'Change Control', artifact: 'PAC' },
      { framework: 'SOC2', control: 'CC6.7', description: 'Testing', artifact: 'BER' },
      { framework: 'SOC2', control: 'CC7.2', description: 'Evidence', artifact: 'PDO' },
      { framework: 'SOC2', control: 'CC5.1', description: 'Sign-off', artifact: 'WRAP' },
      { framework: 'SOC2', control: 'CC8.1', description: 'Retention', artifact: 'LEDGER' },
      { framework: 'NIST_CSF', control: 'PR.IP-1', description: 'Configuration', artifact: 'PAC' },
      { framework: 'NIST_CSF', control: 'DE.CM-1', description: 'Monitoring', artifact: 'BER' },
      { framework: 'NIST_CSF', control: 'RS.AN-1', description: 'Analysis', artifact: 'PDO' },
      { framework: 'NIST_CSF', control: 'PR.IP-4', description: 'Review', artifact: 'WRAP' },
      { framework: 'NIST_CSF', control: 'PR.DS-1', description: 'Protection', artifact: 'LEDGER' },
      { framework: 'ISO_27001', control: 'A.12.1', description: 'Procedures', artifact: 'PAC' },
      { framework: 'ISO_27001', control: 'A.9.4', description: 'Access Control', artifact: 'BER' },
      { framework: 'ISO_27001', control: 'A.12.4', description: 'Logging', artifact: 'PDO' },
      { framework: 'ISO_27001', control: 'A.14.2', description: 'Change Control', artifact: 'WRAP' },
      { framework: 'ISO_27001', control: 'A.12.4.3', description: 'Audit Logs', artifact: 'LEDGER' },
    ],
    lastAuditDate: '2025-12-20',
    complianceScore: 96,
    frameworkCoverage: {
      sox: 100,
      soc2: 100,
      nist: 100,
      iso27001: 100,
    },
  };
}

/**
 * Hook for governance health data.
 */
export function useGovernanceHealth(refreshInterval = 30000): GovernanceHealthState {
  const [state, setState] = useState<GovernanceHealthState>({
    metrics: generateMockMetrics(),
    recentChains: generateMockChains(),
    complianceSummary: generateMockComplianceSummary(),
    isLoading: true,
    error: null,
    lastUpdated: new Date().toISOString(),
  });

  const fetchData = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      // In production, these would be real API calls
      // For now, use mock data with slight variations
      const metrics = generateMockMetrics();
      const chains = generateMockChains();
      const compliance = generateMockComplianceSummary();

      // Try to get real ledger data if available
      try {
        const ledgerSummary = await fetchGovernanceSummary();
        if (ledgerSummary) {
          metrics.totalPacs = ledgerSummary.total_pacs;
          metrics.activePacs = ledgerSummary.active_pacs;
          metrics.blockedPacs = ledgerSummary.blocked_pacs;
          metrics.positiveClosures = ledgerSummary.positive_closures;
        }
      } catch {
        // Use mock data if API fails
      }

      setState({
        metrics,
        recentChains: chains,
        complianceSummary: compliance,
        isLoading: false,
        error: null,
        lastUpdated: new Date().toISOString(),
      });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err : new Error('Failed to fetch governance health data'),
      }));
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Refresh interval
  useEffect(() => {
    if (refreshInterval > 0) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchData, refreshInterval]);

  return state;
}

/**
 * Get stage progress percentage.
 */
export function getStageProgress(currentStage: SettlementStage): number {
  const stages: SettlementStage[] = [
    'PAC_DISPATCH',
    'AGENT_EXECUTION',
    'BER_GENERATION',
    'HUMAN_REVIEW',
    'PDO_FINALIZATION',
    'WRAP_GENERATION',
    'WRAP_ACCEPTED',
    'LEDGER_COMMIT',
  ];

  const index = stages.indexOf(currentStage);
  return index >= 0 ? Math.round(((index + 1) / stages.length) * 100) : 0;
}

/**
 * Format settlement time for display.
 */
export function formatSettlementTime(ms: number): string {
  if (ms < 60000) {
    return `${Math.round(ms / 1000)}s`;
  }
  if (ms < 3600000) {
    return `${Math.round(ms / 60000)}m`;
  }
  return `${Math.round(ms / 3600000)}h`;
}
