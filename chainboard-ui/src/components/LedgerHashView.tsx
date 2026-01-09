/**
 * LedgerHashView — Operator Console Ledger Visibility Component
 * 
 * PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
 * Agent: Sonny (GID-02) — UI
 * Effective Date: 2025-12-30
 * 
 * INVARIANTS:
 *   INV-OC-003: Ledger hash visible for final outcomes
 *   INV-OC-004: Missing data explicit
 */

import React, { useEffect, useState, useCallback } from 'react';
import type {
  OCLedgerEntry,
  OCLedgerVerifyResponse,
} from '../types/operatorConsole';
import { fetchLedgerEntries, verifyLedgerChain } from '../api/operatorConsole';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface LedgerHashViewProps {
  onSelectEntry?: (entryId: string) => void;
  className?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEDGER ENTRY ROW
// ═══════════════════════════════════════════════════════════════════════════════

interface LedgerEntryRowProps {
  entry: OCLedgerEntry;
  onClick: () => void;
}

const LedgerEntryRow: React.FC<LedgerEntryRowProps> = ({ entry, onClick }) => {
  return (
    <tr
      className="hover:bg-slate-50 cursor-pointer border-b border-slate-100"
      onClick={onClick}
    >
      <td className="px-3 py-2 text-xs text-slate-500 font-mono">
        {entry.sequence_number}
      </td>
      <td className="px-3 py-2">
        <span className="text-xs px-2 py-0.5 bg-slate-100 rounded text-slate-700">
          {entry.entry_type}
        </span>
      </td>
      <td className="px-3 py-2 font-mono text-xs text-slate-600" title={entry.entry_hash}>
        {entry.entry_hash.slice(0, 8)}...{entry.entry_hash.slice(-8)}
      </td>
      <td className="px-3 py-2 font-mono text-xs text-slate-400" title={entry.previous_hash}>
        {entry.previous_hash.slice(0, 8)}...
      </td>
      <td className="px-3 py-2 text-xs text-slate-600 font-mono">
        {entry.reference_id}
      </td>
      <td className="px-3 py-2 text-xs text-slate-400">
        {new Date(entry.timestamp).toLocaleString()}
      </td>
    </tr>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// CHAIN STATUS BADGE
// ═══════════════════════════════════════════════════════════════════════════════

interface ChainStatusBadgeProps {
  verifyResult: OCLedgerVerifyResponse | null;
  loading: boolean;
}

const ChainStatusBadge: React.FC<ChainStatusBadgeProps> = ({ verifyResult, loading }) => {
  if (loading) {
    return (
      <span className="px-2 py-1 text-xs bg-slate-100 text-slate-600 rounded">
        Verifying...
      </span>
    );
  }
  
  if (!verifyResult) {
    return (
      <span className="px-2 py-1 text-xs bg-slate-100 text-slate-500 rounded">
        Not verified
      </span>
    );
  }
  
  if (verifyResult.chain_valid) {
    return (
      <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded flex items-center gap-1">
        <span>✓</span> Chain Valid ({verifyResult.entry_count} entries)
      </span>
    );
  }
  
  return (
    <span className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded flex items-center gap-1">
      <span>✗</span> Chain Broken: {verifyResult.error}
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * LedgerHashView — READ-ONLY ledger visibility (INV-OC-003).
 */
export const LedgerHashView: React.FC<LedgerHashViewProps> = ({
  onSelectEntry,
  className = '',
}) => {
  const [entries, setEntries] = useState<OCLedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<OCLedgerVerifyResponse | null>(null);
  const [verifying, setVerifying] = useState(false);
  
  // Load entries
  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchLedgerEntries(100, 0);
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ledger');
    } finally {
      setLoading(false);
    }
  }, []);
  
  // Verify chain
  const handleVerify = useCallback(async () => {
    setVerifying(true);
    try {
      const result = await verifyLedgerChain();
      setVerifyResult(result);
    } catch (err) {
      setVerifyResult({
        chain_valid: false,
        error: err instanceof Error ? err.message : 'Verification failed',
        entry_count: 0,
        verified_at: new Date().toISOString(),
      });
    } finally {
      setVerifying(false);
    }
  }, []);
  
  useEffect(() => {
    loadEntries();
  }, [loadEntries]);
  
  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-slate-800">Ledger Hash Chain</h2>
          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
            READ-ONLY
          </span>
        </div>
        
        <div className="flex items-center gap-3">
          <ChainStatusBadge verifyResult={verifyResult} loading={verifying} />
          <button
            type="button"
            onClick={handleVerify}
            disabled={verifying}
            className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
          >
            Verify Chain
          </button>
          <button
            type="button"
            onClick={loadEntries}
            disabled={loading}
            className="text-xs text-slate-600 hover:text-slate-800 disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-auto">
        {loading && (
          <div className="text-center py-8 text-slate-500">
            Loading ledger entries...
          </div>
        )}
        
        {error && (
          <div className="text-center py-8 text-red-500">
            Error: {error}
          </div>
        )}
        
        {!loading && !error && entries.length === 0 && (
          <div className="text-center py-8 text-slate-400">
            No ledger entries
          </div>
        )}
        
        {!loading && !error && entries.length > 0 && (
          <table className="w-full text-left">
            <thead className="bg-slate-100 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-xs font-medium text-slate-600">Seq</th>
                <th className="px-3 py-2 text-xs font-medium text-slate-600">Type</th>
                <th className="px-3 py-2 text-xs font-medium text-slate-600">Hash</th>
                <th className="px-3 py-2 text-xs font-medium text-slate-600">Prev</th>
                <th className="px-3 py-2 text-xs font-medium text-slate-600">Reference</th>
                <th className="px-3 py-2 text-xs font-medium text-slate-600">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <LedgerEntryRow
                  key={entry.entry_id}
                  entry={entry}
                  onClick={() => onSelectEntry?.(entry.entry_id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
      
      {/* Footer */}
      <div className="px-4 py-2 border-t border-slate-200 text-xs text-slate-500">
        {entries.length} entries • Hash chain provides tamper-evident audit trail
      </div>
    </div>
  );
};

export default LedgerHashView;
