/**
 * GovernanceLedgerPanel — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * Main panel for viewing the Governance Ledger and PAC Registry.
 * Provides operator-grade visibility into governance state.
 *
 * UX RULES (FAIL-CLOSED):
 * - blocked_means_disabled: Blocked PACs visually distinct
 * - closure_requires_badge: Every closure shows badge
 * - corrections_must_show_lineage: Correction history visible
 * - no_green_without_positive_closure: Only positive closure = green
 * - hover_explains_violation_codes: Tooltips explain violations
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import React, { useState } from 'react';
import type { PACRegistryEntry, GovernanceLedger } from '../../types/governanceLedger';
import { isPACBlocked, getStateStatus, getClosureLabel } from '../../types/governanceLedger';
import { PositiveClosureBadge } from './PositiveClosureBadge';
import { PacTimelineView } from './PacTimelineView';
import { CorrectionCycleStepper } from './CorrectionCycleStepper';
import { GovernanceStateSummaryCard } from './GovernanceStateSummaryCard';
import {
  useGovernanceLedger,
  usePACRegistry,
  useGovernanceSummary,
  usePACDetail,
} from '../../hooks/useGovernanceLedger';
import { ledgerToTimeline } from '../../services/governanceLedgerApi';

export interface GovernanceLedgerPanelProps {
  /** Poll interval in ms (default 30s) */
  pollInterval?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Tab type for panel navigation.
 */
type TabType = 'overview' | 'registry' | 'ledger';

/**
 * Tab button component.
 */
function TabButton({
  label,
  active,
  onClick,
  badge,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  badge?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        px-4 py-2 text-sm font-medium rounded-t-lg
        ${active
          ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
          : 'bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800'
        }
      `}
    >
      {label}
      {badge !== undefined && badge > 0 && (
        <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-red-500 text-white">
          {badge}
        </span>
      )}
    </button>
  );
}

/**
 * PAC list item component.
 */
function PACListItem({
  pac,
  selected,
  onClick,
}: {
  pac: PACRegistryEntry;
  selected: boolean;
  onClick: () => void;
}) {
  const isBlocked = isPACBlocked(pac.state);
  const status = getStateStatus(pac.state);

  const statusColors = {
    success: 'border-l-green-500',
    warning: 'border-l-amber-500',
    error: 'border-l-red-500',
    blocked: 'border-l-red-500',
    info: 'border-l-blue-500',
  };

  return (
    <button
      onClick={onClick}
      className={`
        w-full text-left p-3 border-l-4 ${statusColors[status]}
        ${selected
          ? 'bg-blue-50 dark:bg-blue-900/20'
          : 'bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750'
        }
        border-b border-gray-200 dark:border-gray-700
        transition-colors
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {pac.title}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
            {pac.pac_id}
          </p>
        </div>
        <PositiveClosureBadge
          closureType={pac.closure_type}
          state={pac.state}
          size="sm"
          showLabel={false}
        />
      </div>

      <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400">
        <AgentIndicator name={pac.owner_name} color={pac.owner_color} />
        <span>•</span>
        <span>{getClosureLabel(pac.closure_type)}</span>
        {pac.corrections.length > 0 && (
          <>
            <span>•</span>
            <span>{pac.corrections.length} corrections</span>
          </>
        )}
      </div>
    </button>
  );
}

/**
 * Agent indicator with color dot.
 */
function AgentIndicator({ name, color }: { name: string; color: string }) {
  const colorMap: Record<string, string> = {
    RED: 'bg-red-500',
    YELLOW: 'bg-yellow-500',
    GREEN: 'bg-green-500',
    BLUE: 'bg-blue-500',
    PURPLE: 'bg-purple-500',
    PINK: 'bg-pink-500',
    ORANGE: 'bg-orange-500',
    GRAY: 'bg-gray-500',
  };

  return (
    <span className="inline-flex items-center gap-1">
      <span className={`w-2 h-2 rounded-full ${colorMap[color] || 'bg-gray-500'}`} />
      <span>{name}</span>
    </span>
  );
}

/**
 * PAC detail view component.
 */
function PACDetailView({ pacId }: { pacId: string }) {
  const { pac, loading, error, timeline } = usePACDetail(pacId);

  if (loading) {
    return (
      <div className="p-4 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-2" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
      </div>
    );
  }

  if (error || !pac) {
    return (
      <div className="p-4 text-red-600 dark:text-red-400">
        Failed to load PAC details
      </div>
    );
  }

  return (
    <div className="p-4 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {pac.title}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">
              {pac.pac_id}
            </p>
          </div>
          <PositiveClosureBadge
            closureType={pac.closure_type}
            state={pac.state}
            size="md"
          />
        </div>

        <div className="flex items-center gap-4 mt-3 text-sm text-gray-600 dark:text-gray-400">
          <AgentIndicator name={pac.owner_name} color={pac.owner_color} />
          <span>•</span>
          <span>State: {pac.state}</span>
          {pac.closure_authority_name && (
            <>
              <span>•</span>
              <span>Closed by: {pac.closure_authority_name}</span>
            </>
          )}
        </div>
      </div>

      {/* Correction cycle */}
      {(pac.corrections.length > 0 || pac.active_violations.length > 0) && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
            Correction Cycle
          </h4>
          <CorrectionCycleStepper
            corrections={pac.corrections}
            activeViolations={pac.active_violations}
            orientation="vertical"
          />
        </div>
      )}

      {/* Timeline */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <PacTimelineView
          nodes={timeline}
          title="Lifecycle Timeline"
          showFilters={true}
          maxItems={20}
        />
      </div>
    </div>
  );
}

/**
 * Ledger entries view.
 */
function LedgerEntriesView({ ledger }: { ledger: GovernanceLedger }) {
  const timeline = ledgerToTimeline(ledger.entries);

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Governance Ledger
        </h3>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {ledger.total_entries} entries • Seq #{ledger.latest_sequence}
        </span>
      </div>
      <PacTimelineView
        nodes={timeline}
        title=""
        showFilters={true}
      />
    </div>
  );
}

/**
 * GovernanceLedgerPanel component.
 *
 * Main panel for operator visibility into governance state.
 */
export function GovernanceLedgerPanel({
  pollInterval = 30000,
  className = '',
}: GovernanceLedgerPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [selectedPacId, setSelectedPacId] = useState<string | null>(null);

  const { summary, loading: summaryLoading, error: summaryError } = useGovernanceSummary(pollInterval);
  const { registry, loading: registryLoading } = usePACRegistry(pollInterval);
  const { ledger, loading: ledgerLoading } = useGovernanceLedger(pollInterval);

  return (
    <div className={`flex flex-col h-full bg-gray-50 dark:bg-gray-900 ${className}`}>
      {/* Summary card */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <GovernanceStateSummaryCard
          summary={summary}
          loading={summaryLoading}
          error={summaryError}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-4 pt-4 bg-gray-100 dark:bg-gray-900">
        <TabButton
          label="Overview"
          active={activeTab === 'overview'}
          onClick={() => setActiveTab('overview')}
        />
        <TabButton
          label="PAC Registry"
          active={activeTab === 'registry'}
          onClick={() => setActiveTab('registry')}
          badge={registry?.blocked_pacs}
        />
        <TabButton
          label="Ledger"
          active={activeTab === 'ledger'}
          onClick={() => setActiveTab('ledger')}
        />
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden bg-white dark:bg-gray-800 border-t-0 border border-gray-200 dark:border-gray-700 rounded-b-lg mx-4 mb-4">
        {activeTab === 'overview' && (
          <div className="h-full overflow-auto p-4">
            {ledger && (
              <PacTimelineView
                nodes={ledgerToTimeline(ledger.entries)}
                title="Recent Activity"
                showFilters={false}
                maxItems={10}
              />
            )}
          </div>
        )}

        {activeTab === 'registry' && (
          <div className="h-full flex">
            {/* PAC list */}
            <div className="w-1/3 border-r border-gray-200 dark:border-gray-700 overflow-auto">
              {registryLoading && (
                <div className="p-4 animate-pulse space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded" />
                  ))}
                </div>
              )}
              {registry?.pacs.map((pac) => (
                <PACListItem
                  key={pac.pac_id}
                  pac={pac}
                  selected={selectedPacId === pac.pac_id}
                  onClick={() => setSelectedPacId(pac.pac_id)}
                />
              ))}
            </div>

            {/* PAC detail */}
            <div className="flex-1 overflow-auto">
              {selectedPacId ? (
                <PACDetailView pacId={selectedPacId} />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                  Select a PAC to view details
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'ledger' && (
          <div className="h-full overflow-auto">
            {ledgerLoading && (
              <div className="p-4 animate-pulse space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
                ))}
              </div>
            )}
            {ledger && <LedgerEntriesView ledger={ledger} />}
          </div>
        )}
      </div>
    </div>
  );
}

export default GovernanceLedgerPanel;
