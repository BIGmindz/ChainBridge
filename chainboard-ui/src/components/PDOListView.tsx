/**
 * PDOListView — Operator Console PDO List Component
 * 
 * PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
 * Agent: Sonny (GID-02) — UI
 * Effective Date: 2025-12-30
 * 
 * INVARIANTS:
 *   INV-OC-001: UI may not mutate PDO or settlement state (no action buttons)
 *   INV-OC-003: Ledger hash visible for final outcomes
 *   INV-OC-004: Missing data explicit (shows UNAVAILABLE)
 * 
 * This component is READ-ONLY. It displays PDO data but cannot modify it.
 */

import React, { useEffect, useState, useCallback } from 'react';
import type {
  OCPDOView,
  OCPDOListResponse,
  OCPDOFilters,
  PDOOutcomeStatus,
} from '../types/operatorConsole';
import { OUTCOME_STATUS_BG_COLORS, UNAVAILABLE_MARKER } from '../types/operatorConsole';
import { fetchPDOList } from '../api/operatorConsole';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface PDOListViewProps {
  onSelectPDO?: (pdoId: string) => void;
  selectedPDOId?: string | null;
  className?: string;
}

interface PDOListState {
  items: OCPDOView[];
  total: number;
  loading: boolean;
  error: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Status badge with color coding.
 */
const StatusBadge: React.FC<{ status: string | null | undefined }> = ({ status }) => {
  const safeStatus = (status || 'PENDING') as PDOOutcomeStatus;
  const colorClass = OUTCOME_STATUS_BG_COLORS[safeStatus] || 'bg-gray-100 text-gray-800';
  
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${colorClass}`}>
      {status || 'PENDING'}
    </span>
  );
};

/**
 * Hash display with truncation and explicit UNAVAILABLE handling (INV-OC-004).
 */
const HashDisplay: React.FC<{ hash: string; label?: string }> = ({ hash, label }) => {
  const isUnavailable = hash === UNAVAILABLE_MARKER || hash === 'UNAVAILABLE';
  
  if (isUnavailable) {
    return (
      <span className="text-xs text-amber-600 font-medium">
        {label ? `${label}: ` : ''}UNAVAILABLE
      </span>
    );
  }
  
  const truncated = hash.length > 16 ? `${hash.slice(0, 8)}...${hash.slice(-8)}` : hash;
  
  return (
    <span className="font-mono text-xs text-slate-500" title={hash}>
      {label ? `${label}: ` : ''}{truncated}
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// PDO LIST ITEM
// ═══════════════════════════════════════════════════════════════════════════════

interface PDOListItemProps {
  pdo: OCPDOView;
  isSelected: boolean;
  onClick: () => void;
}

/**
 * Single PDO list item. READ-ONLY: No action buttons (INV-OC-001).
 */
const PDOListItem: React.FC<PDOListItemProps> = ({ pdo, isSelected, onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        w-full text-left p-3 rounded-lg border transition-all duration-150
        ${isSelected 
          ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200' 
          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
        }
      `}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-sm font-medium text-slate-800">
          {pdo.pdo_id}
        </span>
        <StatusBadge status={pdo.outcome_status} />
      </div>
      
      {/* PAC ID */}
      {pdo.pac_id && (
        <div className="text-xs text-slate-500 mb-1">
          PAC: <span className="font-medium">{pdo.pac_id}</span>
        </div>
      )}
      
      {/* Ledger Hash (INV-OC-003: Must be visible) */}
      <div className="mb-1">
        <HashDisplay hash={pdo.ledger_entry_hash} label="Ledger" />
      </div>
      
      {/* Sequence and timestamp */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>
          Seq: {pdo.sequence_number === -1 ? 'N/A' : pdo.sequence_number}
        </span>
        <span>
          {new Date(pdo.timestamp).toLocaleString()}
        </span>
      </div>
      
      {/* Settlement linkage indicator */}
      {pdo.settlement_id && (
        <div className="mt-2 text-xs text-green-600">
          ✓ Settlement: {pdo.settlement_id}
        </div>
      )}
    </button>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * PDOListView — READ-ONLY PDO list for Operator Console.
 * 
 * INV-OC-001: No mutation actions available.
 * INV-OC-003: Ledger hash always visible.
 * INV-OC-004: Missing data shown as UNAVAILABLE.
 */
export const PDOListView: React.FC<PDOListViewProps> = ({
  onSelectPDO,
  selectedPDOId,
  className = '',
}) => {
  // State
  const [state, setState] = useState<PDOListState>({
    items: [],
    total: 0,
    loading: true,
    error: null,
  });
  
  const [filters, setFilters] = useState<OCPDOFilters>({
    limit: 50,
    offset: 0,
  });
  
  // Load PDOs
  const loadPDOs = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    
    try {
      const response = await fetchPDOList(filters);
      setState({
        items: response.items,
        total: response.total,
        loading: false,
        error: null,
      });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to load PDOs',
      }));
    }
  }, [filters]);
  
  useEffect(() => {
    loadPDOs();
  }, [loadPDOs]);
  
  // Filter handlers
  const handleStatusFilter = (status: string) => {
    setFilters((prev) => ({
      ...prev,
      outcome_status: status || undefined,
      offset: 0,
    }));
  };
  
  // Render
  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header — READ-ONLY indicator */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800">PDO Registry</h2>
          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
            READ-ONLY
          </span>
        </div>
        <span className="text-xs text-slate-500">
          {state.total} total
        </span>
      </div>
      
      {/* Filters */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-100">
        <select
          className="text-xs border border-slate-200 rounded px-2 py-1"
          value={filters.outcome_status || ''}
          onChange={(e) => handleStatusFilter(e.target.value)}
        >
          <option value="">All Outcomes</option>
          <option value="ACCEPTED">Accepted</option>
          <option value="CORRECTIVE">Corrective</option>
          <option value="REJECTED">Rejected</option>
          <option value="PENDING">Pending</option>
        </select>
        
        <button
          type="button"
          onClick={() => loadPDOs()}
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {state.loading && (
          <div className="text-center py-8 text-slate-500">
            Loading PDOs...
          </div>
        )}
        
        {state.error && (
          <div className="text-center py-8 text-red-500">
            Error: {state.error}
          </div>
        )}
        
        {!state.loading && !state.error && state.items.length === 0 && (
          <div className="text-center py-8 text-slate-400">
            No PDOs found
          </div>
        )}
        
        {!state.loading && state.items.map((pdo) => (
          <PDOListItem
            key={pdo.pdo_id}
            pdo={pdo}
            isSelected={selectedPDOId === pdo.pdo_id}
            onClick={() => onSelectPDO?.(pdo.pdo_id)}
          />
        ))}
      </div>
      
      {/* Footer with pagination info */}
      <div className="px-4 py-2 border-t border-slate-200 text-xs text-slate-500">
        Showing {state.items.length} of {state.total} • 
        <span className="ml-1 text-amber-600">
          Operator Console is read-only
        </span>
      </div>
    </div>
  );
};

export default PDOListView;
