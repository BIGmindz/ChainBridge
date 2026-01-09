/**
 * ClosureChecklistPanel — PAC-JEFFREY-P03 Section 10
 * 
 * Displays the positive closure checklist with pass/fail status for each item.
 * 
 * All items must PASS for valid positive closure.
 * 
 * Author: SONNY (GID-02) — Frontend Lane
 */

import React from 'react';
import type { PositiveClosureChecklistDTO } from '../../types/controlPlane';
import { formatTimestamp } from '../../types/controlPlane';

interface ClosureChecklistPanelProps {
  checklist: PositiveClosureChecklistDTO | null;
  loading?: boolean;
  error?: string | null;
}

const CHECKLIST_ITEMS = [
  { key: 'PAG-01_ACKS_COMPLETE', label: 'PAG-01 ACKs Complete', description: 'All required agent acknowledgments received' },
  { key: 'ALL_REQUIRED_WRAPS', label: 'All Required WRAPs', description: 'All executing agents submitted WRAPs' },
  { key: 'RG-01', label: 'RG-01 Review Gate', description: 'Review gate passed with training signals' },
  { key: 'BSRG-01', label: 'BSRG-01 Self-Review', description: 'Benson self-attestation complete' },
  { key: 'BER_ISSUED', label: 'BER Issued', description: 'Benson Execution Report generated' },
  { key: 'LEDGER_COMMIT', label: 'Ledger Commit', description: 'Governance ledger attestation' },
] as const;

const STATUS_STYLES: Record<string, { icon: string; bgColor: string; textColor: string }> = {
  PASS: { icon: '✓', bgColor: 'bg-green-900/50', textColor: 'text-green-400' },
  FAIL: { icon: '✗', bgColor: 'bg-red-900/50', textColor: 'text-red-400' },
  PROVISIONAL: { icon: '◐', bgColor: 'bg-yellow-900/50', textColor: 'text-yellow-400' },
  PENDING: { icon: '○', bgColor: 'bg-gray-800', textColor: 'text-gray-400' },
};

export const ClosureChecklistPanel: React.FC<ClosureChecklistPanelProps> = ({
  checklist,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <div className="animate-spin h-5 w-5 border-2 border-cyan-500 border-t-transparent rounded-full" />
          <h3 className="text-lg font-semibold text-gray-200">Loading Closure Checklist...</h3>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/30 rounded-lg p-4 border border-red-700">
        <h3 className="text-lg font-semibold text-red-400 mb-2">Checklist Error</h3>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  if (!checklist) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-400">No Closure Checklist</h3>
        <p className="text-gray-500 text-sm mt-2">Checklist not yet initialized.</p>
      </div>
    );
  }

  const overallStyle = STATUS_STYLES[checklist.overall_status] || STATUS_STYLES.PENDING;
  const passCount = Object.values(checklist.items).filter(v => v === 'PASS').length;
  const totalItems = Object.keys(checklist.items).length;

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📋</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-200">
              Positive Closure Checklist
            </h3>
            <p className="text-xs text-gray-500 font-mono">{checklist.checklist_id}</p>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-bold ${
          checklist.overall_status === 'PASS' 
            ? 'bg-green-600 text-white' 
            : checklist.overall_status === 'FAIL'
            ? 'bg-red-600 text-white'
            : 'bg-yellow-600 text-white'
        }`}>
          {checklist.overall_status}
        </div>
      </div>

      {/* Progress Summary */}
      <div className="mb-4 p-3 bg-gray-900/50 rounded">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-400">Checklist Progress</span>
          <span className="text-lg font-bold text-gray-200">{passCount} / {totalItems}</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${
              passCount === totalItems ? 'bg-green-500' : 'bg-cyan-500'
            }`}
            style={{ width: `${(passCount / totalItems) * 100}%` }}
          />
        </div>
      </div>

      {/* Checklist Items */}
      <div className="space-y-2">
        {CHECKLIST_ITEMS.map(({ key, label, description }) => {
          const status = checklist.items[key as keyof typeof checklist.items] || 'PENDING';
          const style = STATUS_STYLES[status] || STATUS_STYLES.PENDING;

          return (
            <div 
              key={key}
              className={`p-3 rounded border ${style.bgColor} border-gray-700 transition-all`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`text-xl font-bold ${style.textColor}`}>
                    {style.icon}
                  </span>
                  <div>
                    <p className="font-medium text-gray-200">{label}</p>
                    <p className="text-xs text-gray-500">{description}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-mono ${style.bgColor} ${style.textColor} border border-current/30`}>
                  {status}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-gray-700 flex justify-between text-xs text-gray-500">
        <span>
          {checklist.evaluated_at 
            ? `Evaluated: ${formatTimestamp(checklist.evaluated_at)}`
            : 'Not yet evaluated'
          }
        </span>
        <span>PAC: {checklist.pac_id}</span>
      </div>

      {/* Governance Note */}
      <div className="mt-3 p-2 bg-cyan-900/20 rounded border border-cyan-700/30">
        <p className="text-xs text-cyan-400">
          <span className="font-bold">PAC-JEFFREY-P03 §10:</span> All items must PASS for valid positive closure.
          LEDGER_COMMIT may be PROVISIONAL for non-final BERs.
        </p>
      </div>
    </div>
  );
};

export default ClosureChecklistPanel;
