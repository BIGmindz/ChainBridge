// ═══════════════════════════════════════════════════════════════════════════════
// ChainBridge Acknowledgment Status View
// PAC-012: Governance Hardening — ORDER 3 (Sonny GID-05)
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import type { AcknowledgmentDTO, AcknowledgmentStatus } from '../../types/governance';

interface AcknowledgmentViewProps {
  acknowledgments: AcknowledgmentDTO[];
  pacId: string;
}

/**
 * Get status color class.
 */
function getStatusColor(status: AcknowledgmentStatus): string {
  switch (status) {
    case 'ACKNOWLEDGED':
      return 'bg-green-100 text-green-800 border-green-300';
    case 'PENDING':
      return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    case 'REJECTED':
      return 'bg-red-100 text-red-800 border-red-300';
    case 'TIMEOUT':
      return 'bg-orange-100 text-orange-800 border-orange-300';
    case 'NOT_REQUIRED':
      return 'bg-gray-100 text-gray-600 border-gray-300';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300';
  }
}

/**
 * Get status icon.
 */
function getStatusIcon(status: AcknowledgmentStatus): string {
  switch (status) {
    case 'ACKNOWLEDGED':
      return '✓';
    case 'PENDING':
      return '⏳';
    case 'REJECTED':
      return '✗';
    case 'TIMEOUT':
      return '⏰';
    case 'NOT_REQUIRED':
      return '—';
    default:
      return '?';
  }
}

/**
 * Format timestamp for display.
 */
function formatTime(isoString?: string): string {
  if (!isoString) return '—';
  try {
    return new Date(isoString).toLocaleString();
  } catch {
    return isoString;
  }
}

/**
 * Acknowledgment status view component.
 */
export const AcknowledgmentView: React.FC<AcknowledgmentViewProps> = ({
  acknowledgments,
  pacId,
}) => {
  const acknowledged = acknowledgments.filter(a => a.status === 'ACKNOWLEDGED').length;
  const pending = acknowledgments.filter(a => a.status === 'PENDING').length;
  const rejected = acknowledgments.filter(a => a.status === 'REJECTED').length;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Agent Acknowledgments
        </h3>
        <span className="text-sm text-gray-500">PAC: {pacId}</span>
      </div>

      {/* Summary badges */}
      <div className="flex gap-2 mb-4">
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          ✓ {acknowledged} acknowledged
        </span>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          ⏳ {pending} pending
        </span>
        {rejected > 0 && (
          <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
            ✗ {rejected} rejected
          </span>
        )}
      </div>

      {/* Acknowledgment list */}
      <div className="space-y-2">
        {acknowledgments.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No acknowledgments recorded</p>
        ) : (
          acknowledgments.map((ack) => (
            <div
              key={ack.ack_id}
              className={`border rounded-md p-3 ${getStatusColor(ack.status)}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{getStatusIcon(ack.status)}</span>
                  <div>
                    <p className="font-medium text-sm">
                      {ack.agent_name} ({ack.agent_gid})
                    </p>
                    <p className="text-xs opacity-75">Order: {ack.order_id}</p>
                  </div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded bg-white/50">
                  {ack.ack_type}
                </span>
              </div>

              {/* Timestamps */}
              <div className="mt-2 text-xs grid grid-cols-2 gap-2">
                <div>
                  <span className="opacity-60">Requested:</span>{' '}
                  {formatTime(ack.requested_at)}
                </div>
                {ack.acknowledged_at && (
                  <div>
                    <span className="opacity-60">Acknowledged:</span>{' '}
                    {formatTime(ack.acknowledged_at)}
                  </div>
                )}
              </div>

              {/* Response or rejection reason */}
              {ack.response_message && (
                <p className="mt-2 text-xs italic">{ack.response_message}</p>
              )}
              {ack.rejection_reason && (
                <p className="mt-2 text-xs text-red-700">
                  Reason: {ack.rejection_reason}
                </p>
              )}
            </div>
          ))
        )}
      </div>

      {/* INV-GOV-001 notice */}
      <div className="mt-4 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
        <strong>INV-GOV-001:</strong> Explicit agent acknowledgment required before execution
      </div>
    </div>
  );
};

export default AcknowledgmentView;
