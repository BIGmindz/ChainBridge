/**
 * TraceGapIndicators Component
 * PAC-009: Full End-to-End Traceability — ORDER 4 (Sonny GID-02)
 * 
 * Visual indicators for missing trace links.
 * 
 * GOVERNANCE INVARIANTS:
 * - INV-TRACE-005: Missing links are explicit and non-silent
 */

import React from 'react';
import type { TraceGap, TraceViewStatus } from '../../types/trace';

// ═══════════════════════════════════════════════════════════════════════════════
// PROPS
// ═══════════════════════════════════════════════════════════════════════════════

interface TraceGapIndicatorsProps {
  gaps: TraceGap[];
  completenessScore: number;
  status: TraceViewStatus;
  pdoId: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS COLORS
// ═══════════════════════════════════════════════════════════════════════════════

const STATUS_STYLES: Record<TraceViewStatus, { bg: string; text: string; icon: string }> = {
  COMPLETE: { bg: 'bg-green-50', text: 'text-green-800', icon: '✓' },
  INCOMPLETE: { bg: 'bg-amber-50', text: 'text-amber-800', icon: '⚠️' },
  ERROR: { bg: 'bg-red-50', text: 'text-red-800', icon: '✗' },
};

const GAP_TYPE_STYLES: Record<string, { bg: string; text: string; icon: string }> = {
  DOMAIN_NOT_LINKED: { bg: 'bg-orange-100', text: 'text-orange-800', icon: '🔗' },
  LINK_MISSING: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: '❓' },
  DATA_UNAVAILABLE: { bg: 'bg-gray-100', text: 'text-gray-800', icon: '📭' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPLETENESS BAR
// ═══════════════════════════════════════════════════════════════════════════════

interface CompletenessBarProps {
  score: number;
}

const CompletenessBar: React.FC<CompletenessBarProps> = ({ score }) => {
  const percentage = Math.round(score * 100);
  
  let barColor = 'bg-red-500';
  if (percentage >= 75) barColor = 'bg-green-500';
  else if (percentage >= 50) barColor = 'bg-amber-500';
  else if (percentage >= 25) barColor = 'bg-orange-500';

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span>Trace Completeness</span>
        <span className="font-medium">{percentage}%</span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// GAP ITEM
// ═══════════════════════════════════════════════════════════════════════════════

interface GapItemProps {
  gap: TraceGap;
}

const GapItem: React.FC<GapItemProps> = ({ gap }) => {
  const styles = GAP_TYPE_STYLES[gap.gap_type] || GAP_TYPE_STYLES.DATA_UNAVAILABLE;

  return (
    <div className={`p-3 rounded-lg ${styles.bg} border border-opacity-20`}>
      <div className="flex items-start gap-2">
        <span className="text-lg">{styles.icon}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium px-2 py-0.5 rounded ${styles.text} bg-white bg-opacity-50`}>
              {gap.gap_type.replace(/_/g, ' ')}
            </span>
          </div>
          <p className={`mt-1 text-sm ${styles.text}`}>
            {gap.message}
          </p>
          {(gap.from_domain || gap.to_domain) && (
            <div className="mt-1 text-xs text-gray-600 flex gap-2">
              {gap.from_domain && (
                <span>From: <code className="bg-white bg-opacity-50 px-1 rounded">{gap.from_domain}</code></span>
              )}
              {gap.from_domain && gap.to_domain && <span>→</span>}
              {gap.to_domain && (
                <span>To: <code className="bg-white bg-opacity-50 px-1 rounded">{gap.to_domain}</code></span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const TraceGapIndicators: React.FC<TraceGapIndicatorsProps> = ({
  gaps,
  completenessScore,
  status,
  pdoId,
}) => {
  const statusStyles = STATUS_STYLES[status];

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className={`px-4 py-3 border-b ${statusStyles.bg}`}>
        <div className="flex items-center justify-between">
          <h3 className={`text-sm font-semibold ${statusStyles.text}`}>
            <span className="mr-2">{statusStyles.icon}</span>
            Trace Status: {status}
          </h3>
          <span className="text-xs text-gray-500">
            PDO: {pdoId}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Completeness Bar */}
        <CompletenessBar score={completenessScore} />

        {/* Gap Summary */}
        {gaps.length > 0 ? (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-700">
                Missing Links
              </h4>
              <span className="text-xs px-2 py-1 bg-amber-100 text-amber-800 rounded-full">
                {gaps.length} gap{gaps.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="space-y-2">
              {gaps.map((gap) => (
                <GapItem key={gap.gap_id} gap={gap} />
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <span className="text-2xl">✅</span>
            <p className="mt-2 text-sm text-green-600 font-medium">
              Full trace chain complete
            </p>
            <p className="text-xs text-gray-500">
              All links from PDO to Ledger are present
            </p>
          </div>
        )}

        {/* INV-TRACE-005 Notice */}
        <div className="text-xs text-gray-400 text-center border-t pt-3">
          INV-TRACE-005: Missing links are explicit and non-silent
        </div>
      </div>
    </div>
  );
};

export default TraceGapIndicators;
