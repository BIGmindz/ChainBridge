// ═══════════════════════════════════════════════════════════════════════════════
// ChainBridge Governance Page
// PAC-012: Governance Hardening — ORDER 3 (Sonny GID-05)
// ═══════════════════════════════════════════════════════════════════════════════

import React, { useEffect, useState } from 'react';
import { AcknowledgmentView } from './AcknowledgmentView';
import { DependencyGraphView } from './DependencyGraphView';
import { NonCapabilitiesBanner } from './NonCapabilitiesBanner';
import { FailureSemanticsView } from './FailureSemanticsView';
import type {
  AcknowledgmentListDTO,
  DependencyGraphDTO,
  NonCapabilitiesListDTO,
  FailureSemanticsDTO,
  GovernanceSummaryDTO,
} from '../../types/governance';
import {
  getAcknowledgments,
  getDependencyGraph,
  getNonCapabilities,
  getFailureSemantics,
  getGovernanceSummary,
} from '../../api/governanceApi';

interface GovernancePageProps {
  pacId: string;
}

/**
 * Loading spinner component.
 */
const LoadingSpinner: React.FC = () => (
  <div className="flex items-center justify-center p-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
  </div>
);

/**
 * Error display component.
 */
const ErrorDisplay: React.FC<{ message: string }> = ({ message }) => (
  <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
    <strong>Error:</strong> {message}
  </div>
);

/**
 * Governance summary card.
 */
const SummaryCard: React.FC<{ summary: GovernanceSummaryDTO }> = ({ summary }) => (
  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
    <h3 className="text-lg font-semibold text-gray-900 mb-3">Governance Summary</h3>
    <div className="grid grid-cols-4 gap-4">
      <div className="text-center">
        <div className="text-2xl font-bold text-blue-600">
          {summary.total_acknowledgments}
        </div>
        <div className="text-xs text-gray-600">Acknowledgments</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-green-600">
          {summary.total_dependencies}
        </div>
        <div className="text-xs text-gray-600">Dependencies</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-purple-600">
          {summary.total_causality_links}
        </div>
        <div className="text-xs text-gray-600">Causality Links</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-red-600">
          {summary.total_non_capabilities}
        </div>
        <div className="text-xs text-gray-600">Non-Capabilities</div>
      </div>
    </div>
    
    {/* Invariants list */}
    <div className="mt-4 pt-4 border-t border-blue-200">
      <h4 className="text-sm font-medium text-gray-700 mb-2">Governance Invariants</h4>
      <div className="grid grid-cols-2 gap-1">
        {summary.governance_invariants.map((inv, i) => (
          <div
            key={i}
            className="text-xs bg-white/50 px-2 py-1 rounded border border-blue-100"
          >
            {inv}
          </div>
        ))}
      </div>
    </div>
  </div>
);

/**
 * Main governance page component.
 */
export const GovernancePage: React.FC<GovernancePageProps> = ({ pacId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonCapExpanded, setNonCapExpanded] = useState(false);

  // Data state
  const [acknowledgments, setAcknowledgments] = useState<AcknowledgmentListDTO | null>(null);
  const [dependencyGraph, setDependencyGraph] = useState<DependencyGraphDTO | null>(null);
  const [nonCapabilities, setNonCapabilities] = useState<NonCapabilitiesListDTO | null>(null);
  const [failureSemantics, setFailureSemantics] = useState<FailureSemanticsDTO | null>(null);
  const [summary, setSummary] = useState<GovernanceSummaryDTO | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const [acks, deps, nonCaps, semantics, sum] = await Promise.all([
          getAcknowledgments(pacId),
          getDependencyGraph(pacId),
          getNonCapabilities(),
          getFailureSemantics(),
          getGovernanceSummary(),
        ]);

        setAcknowledgments(acks);
        setDependencyGraph(deps);
        setNonCapabilities(nonCaps);
        setFailureSemantics(semantics);
        setSummary(sum);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load governance data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [pacId]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorDisplay message={error} />;
  }

  return (
    <div className="space-y-6 p-4">
      {/* Page header */}
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Governance Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          PAC: <span className="font-mono">{pacId}</span>
        </p>
      </div>

      {/* Summary */}
      {summary && <SummaryCard summary={summary} />}

      {/* Non-capabilities banner (always visible) */}
      {nonCapabilities && (
        <NonCapabilitiesBanner
          data={nonCapabilities}
          expanded={nonCapExpanded}
          onToggleExpand={() => setNonCapExpanded(!nonCapExpanded)}
        />
      )}

      {/* Main content grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Acknowledgments */}
        {acknowledgments && (
          <AcknowledgmentView
            acknowledgments={acknowledgments.acknowledgments}
            pacId={pacId}
          />
        )}

        {/* Dependencies */}
        {dependencyGraph && <DependencyGraphView graph={dependencyGraph} />}
      </div>

      {/* Failure semantics (full width) */}
      {failureSemantics && <FailureSemanticsView semantics={failureSemantics} />}
    </div>
  );
};

export default GovernancePage;
