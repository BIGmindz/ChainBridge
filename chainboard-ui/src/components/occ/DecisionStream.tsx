/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Decision Stream Component — PDO Cards + BER Actions
 * PAC-BENSON-P21-C: OCC Intensive Multi-Agent Execution
 * 
 * Displays a chronological stream of governance decisions:
 * - PDO (Payment/Disbursement Orders) cards
 * - BER (Benson Execution Report) actions
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display, no mutation
 * - INV-OCC-002: No optimistic state rendering
 * - INV-BER-001: BER actions are display-only
 * 
 * Author: SONNY (GID-02) — Frontend
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useCallback } from 'react';
import type {
  DecisionStreamItem,
  PDOCard,
  BERCard,
  PDOOutcome,
  BERClassification,
  BERState,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const PDO_OUTCOME_CONFIG: Record<PDOOutcome, { color: string; bgColor: string; label: string; icon: string }> = {
  APPROVED: { color: 'text-green-400', bgColor: 'bg-green-900/30', label: 'Approved', icon: '✓' },
  REJECTED: { color: 'text-red-400', bgColor: 'bg-red-900/30', label: 'Rejected', icon: '✗' },
  PENDING: { color: 'text-yellow-400', bgColor: 'bg-yellow-900/30', label: 'Pending', icon: '⏳' },
};

const BER_CLASSIFICATION_CONFIG: Record<BERClassification, { color: string; label: string }> = {
  PROVISIONAL: { color: 'text-yellow-400', label: 'Provisional' },
  FINAL: { color: 'text-green-400', label: 'Final' },
  BINDING: { color: 'text-blue-400', label: 'Binding' },
};

const BER_STATE_CONFIG: Record<BERState, { color: string; bgColor: string; label: string }> = {
  PENDING: { color: 'text-gray-400', bgColor: 'bg-gray-800', label: 'Pending' },
  ISSUED: { color: 'text-blue-400', bgColor: 'bg-blue-900/30', label: 'Issued' },
  SETTLED: { color: 'text-green-400', bgColor: 'bg-green-900/30', label: 'Settled' },
  BLOCKED: { color: 'text-red-400', bgColor: 'bg-red-900/30', label: 'Blocked' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// PDO CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface PDOCardDisplayProps {
  pdo: PDOCard;
  onViewDetails?: (pdoId: string) => void;
}

const PDOCardDisplay: React.FC<PDOCardDisplayProps> = ({ pdo, onViewDetails }) => {
  const outcomeConfig = PDO_OUTCOME_CONFIG[pdo.outcome];

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.key === 'Enter' || e.key === ' ') && onViewDetails) {
        e.preventDefault();
        onViewDetails(pdo.pdoId);
      }
    },
    [pdo.pdoId, onViewDetails]
  );

  return (
    <article
      className={`
        bg-gray-800 border border-gray-700 rounded-lg p-4
        ${onViewDetails ? 'cursor-pointer hover:bg-gray-750 focus:outline-none focus:ring-2 focus:ring-blue-500' : ''}
        transition-colors duration-150
      `}
      role="article"
      aria-label={`PDO ${pdo.pdoId}: ${outcomeConfig.label}`}
      tabIndex={onViewDetails ? 0 : -1}
      onClick={() => onViewDetails?.(pdo.pdoId)}
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            className={`text-lg ${outcomeConfig.color}`}
            aria-hidden="true"
          >
            📋
          </span>
          <div>
            <span className="font-mono text-sm text-gray-300">{pdo.pdoId}</span>
            <div className="text-xs text-gray-500">PDO Decision</div>
          </div>
        </div>
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${outcomeConfig.color} ${outcomeConfig.bgColor}`}
          role="status"
        >
          {outcomeConfig.icon} {outcomeConfig.label}
        </span>
      </div>

      {/* PAC Reference */}
      <div className="mb-2">
        <span className="text-xs text-gray-500">PAC: </span>
        <span className="text-xs text-blue-400 font-mono">{pdo.pacId}</span>
      </div>

      {/* Amount (if applicable) */}
      {pdo.amount !== null && (
        <div className="mb-2">
          <span className="text-lg font-bold text-gray-100">
            {pdo.currency} {pdo.amount.toLocaleString()}
          </span>
        </div>
      )}

      {/* Reasons (truncated) */}
      {pdo.reasons.length > 0 && (
        <div className="mb-2">
          <p className="text-sm text-gray-400 line-clamp-2">
            {pdo.reasons.join('; ')}
          </p>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-700">
        <span>By {pdo.issuedBy}</span>
        <span title={pdo.createdAt}>{formatTimestamp(pdo.createdAt)}</span>
      </div>

      {/* Hash (collapsed) */}
      <div className="mt-2">
        <span
          className="text-xs text-gray-600 font-mono truncate block"
          title={`Hash: ${pdo.pdoHash}`}
        >
          {pdo.pdoHash.substring(0, 16)}...
        </span>
      </div>
    </article>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// BER CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface BERCardDisplayProps {
  ber: BERCard;
  onViewDetails?: (berId: string) => void;
}

const BERCardDisplay: React.FC<BERCardDisplayProps> = ({ ber, onViewDetails }) => {
  const classificationConfig = BER_CLASSIFICATION_CONFIG[ber.classification];
  const stateConfig = BER_STATE_CONFIG[ber.state];

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.key === 'Enter' || e.key === ' ') && onViewDetails) {
        e.preventDefault();
        onViewDetails(ber.berId);
      }
    },
    [ber.berId, onViewDetails]
  );

  return (
    <article
      className={`
        bg-gray-800 border border-gray-700 rounded-lg p-4
        border-l-4 border-l-purple-500
        ${onViewDetails ? 'cursor-pointer hover:bg-gray-750 focus:outline-none focus:ring-2 focus:ring-purple-500' : ''}
        transition-colors duration-150
      `}
      role="article"
      aria-label={`BER ${ber.berId}: ${stateConfig.label}`}
      tabIndex={onViewDetails ? 0 : -1}
      onClick={() => onViewDetails?.(ber.berId)}
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg text-purple-400" aria-hidden="true">📜</span>
          <div>
            <span className="font-mono text-sm text-gray-300">{ber.berId}</span>
            <div className="text-xs text-gray-500">Benson Execution Report</div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={`px-2 py-0.5 rounded text-xs font-medium ${classificationConfig.color} bg-gray-700`}
          >
            {classificationConfig.label}
          </span>
          <span
            className={`px-2 py-0.5 rounded text-xs font-medium ${stateConfig.color} ${stateConfig.bgColor}`}
            role="status"
          >
            {stateConfig.label}
          </span>
        </div>
      </div>

      {/* PAC Reference */}
      <div className="mb-2">
        <span className="text-xs text-gray-500">PAC: </span>
        <span className="text-xs text-blue-400 font-mono">{ber.pacId}</span>
      </div>

      {/* Execution Binding */}
      <div className="flex items-center gap-4 mb-2 text-xs">
        <span className={ber.executionBinding ? 'text-green-400' : 'text-gray-500'}>
          {ber.executionBinding ? '🔗 Binding' : '○ Non-binding'}
        </span>
        <span className={ber.settlementEffect === 'BINDING' ? 'text-green-400' : 'text-gray-500'}>
          Settlement: {ber.settlementEffect}
        </span>
      </div>

      {/* WRAPs Progress */}
      <div className="mb-2">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-gray-500">WRAPs Collected</span>
          <span className="text-gray-300">
            {ber.wrapsCollected}/{ber.wrapsRequired}
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-1.5">
          <div
            className="bg-purple-500 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${(ber.wrapsCollected / ber.wrapsRequired) * 100}%` }}
            role="progressbar"
            aria-valuenow={ber.wrapsCollected}
            aria-valuemin={0}
            aria-valuemax={ber.wrapsRequired}
            aria-label={`${ber.wrapsCollected} of ${ber.wrapsRequired} WRAPs collected`}
          />
        </div>
      </div>

      {/* Training Signals */}
      {ber.trainingSignalsCount > 0 && (
        <div className="mb-2 text-xs text-gray-500">
          <span className="text-cyan-400">📊 {ber.trainingSignalsCount}</span> training signals
        </div>
      )}

      {/* Ledger Hash (if committed) */}
      {ber.ledgerCommitHash && (
        <div className="mb-2">
          <span className="text-xs text-gray-500">Ledger: </span>
          <span
            className="text-xs text-green-400 font-mono"
            title={ber.ledgerCommitHash}
          >
            {ber.ledgerCommitHash.substring(0, 16)}...
          </span>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-700">
        <span>By {ber.issuedBy}</span>
        <span title={ber.issuedAt}>{formatTimestamp(ber.issuedAt)}</span>
      </div>
    </article>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// DECISION STREAM COMPONENT (MAIN EXPORT)
// ═══════════════════════════════════════════════════════════════════════════════

interface DecisionStreamProps {
  /** Stream items */
  items: DecisionStreamItem[];
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
  /** Callback when PDO is selected */
  onSelectPDO?: (pdoId: string) => void;
  /** Callback when BER is selected */
  onSelectBER?: (berId: string) => void;
  /** Maximum items to display */
  maxItems?: number;
  /** Show "load more" button */
  hasMore?: boolean;
  /** Callback for loading more items */
  onLoadMore?: () => void;
}

export const DecisionStream: React.FC<DecisionStreamProps> = ({
  items,
  loading = false,
  error = null,
  onSelectPDO,
  onSelectBER,
  maxItems = 50,
  hasMore = false,
  onLoadMore,
}) => {
  // Sort items by timestamp (newest first)
  const sortedItems = React.useMemo(() => {
    return [...items]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, maxItems);
  }, [items, maxItems]);

  // Calculate stats
  const stats = React.useMemo(() => {
    const pdoCount = items.filter((i) => i.type === 'PDO').length;
    const berCount = items.filter((i) => i.type === 'BER').length;
    const approvedPDOs = items.filter(
      (i) => i.type === 'PDO' && i.pdo?.outcome === 'APPROVED'
    ).length;
    const settledBERs = items.filter(
      (i) => i.type === 'BER' && i.ber?.state === 'SETTLED'
    ).length;
    return { pdoCount, berCount, approvedPDOs, settledBERs };
  }, [items]);

  if (error) {
    return (
      <div
        className="bg-gray-800 border border-red-700 rounded-lg p-4"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <span aria-hidden="true">🛑</span>
          <span className="font-medium">Decision Stream Error</span>
        </div>
        <p className="text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg"
      aria-label="Decision Stream"
    >
      {/* Header */}
      <div className="border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg" aria-hidden="true">📊</span>
            <div>
              <h2 className="text-lg font-bold text-gray-100">Decision Stream</h2>
              <p className="text-xs text-gray-500">
                PDO decisions and BER execution reports
              </p>
            </div>
          </div>

          {/* Stats */}
          <div
            className="flex items-center gap-4 text-xs"
            role="status"
            aria-label="Decision statistics"
          >
            <span className="text-blue-400">
              📋 {stats.pdoCount} PDOs ({stats.approvedPDOs} approved)
            </span>
            <span className="text-purple-400">
              📜 {stats.berCount} BERs ({stats.settledBERs} settled)
            </span>
          </div>
        </div>
      </div>

      {/* Stream Content */}
      <div className="p-4 max-h-[600px] overflow-y-auto">
        {loading && items.length === 0 ? (
          <div
            className="flex items-center justify-center py-8"
            role="status"
            aria-label="Loading decisions"
          >
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
            <span className="sr-only">Loading decision stream...</span>
          </div>
        ) : sortedItems.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <span aria-hidden="true">📭</span>
            <p className="mt-2">No decisions recorded</p>
          </div>
        ) : (
          <div
            className="space-y-3"
            role="feed"
            aria-label="Decision items"
          >
            {sortedItems.map((item) => (
              <div key={item.id} role="article">
                {item.type === 'PDO' && item.pdo && (
                  <PDOCardDisplay
                    pdo={item.pdo}
                    onViewDetails={onSelectPDO}
                  />
                )}
                {item.type === 'BER' && item.ber && (
                  <BERCardDisplay
                    ber={item.ber}
                    onViewDetails={onSelectBER}
                  />
                )}
              </div>
            ))}

            {/* Load More */}
            {hasMore && onLoadMore && (
              <button
                onClick={onLoadMore}
                disabled={loading}
                className={`
                  w-full py-2 rounded-lg text-sm font-medium transition-colors
                  ${loading
                    ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }
                `}
              >
                {loading ? 'Loading...' : 'Load More'}
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function formatTimestamp(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
  
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default DecisionStream;
