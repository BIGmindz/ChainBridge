/**
 * OperatorConsolePage — Main Operator Console View
 * 
 * PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
 * Agent: Sonny (GID-02) — UI
 * Effective Date: 2025-12-30
 * 
 * INVARIANTS:
 *   INV-OC-001: UI may not mutate PDO or settlement state
 *   INV-OC-002: Every settlement links to PDO ID
 *   INV-OC-003: Ledger hash visible for final outcomes
 *   INV-OC-004: Missing data explicit (no silent gaps)
 *   INV-OC-005: Non-GET requests fail closed
 * 
 * This page is COMPLETELY READ-ONLY. No mutation actions exist.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { PDOListView } from '../components/PDOListView';
import { PDOTimelineView } from '../components/PDOTimelineView';
import { LedgerHashView } from '../components/LedgerHashView';
import type { OCHealthResponse } from '../types/operatorConsole';
import { fetchOCHealth } from '../api/operatorConsole';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

type ActiveTab = 'pdo' | 'settlements' | 'ledger';

// ═══════════════════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════

interface TabProps {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: string;
}

const Tab: React.FC<TabProps> = ({ active, onClick, label, icon }) => (
  <button
    type="button"
    onClick={onClick}
    className={`
      flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors
      ${active 
        ? 'border-blue-500 text-blue-700' 
        : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
      }
    `}
  >
    <span>{icon}</span>
    <span>{label}</span>
  </button>
);

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS BANNER
// ═══════════════════════════════════════════════════════════════════════════════

interface StatusBannerProps {
  health: OCHealthResponse | null;
  loading: boolean;
  error: string | null;
}

const StatusBanner: React.FC<StatusBannerProps> = ({ health, loading, error }) => {
  if (loading) {
    return (
      <div className="bg-slate-100 text-slate-600 px-4 py-2 text-sm">
        Connecting to Operator Console API...
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-red-100 text-red-700 px-4 py-2 text-sm">
        ⚠️ API Error: {error}
      </div>
    );
  }
  
  if (health) {
    return (
      <div className="bg-blue-50 text-blue-700 px-4 py-2 text-sm flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 bg-blue-100 rounded text-xs font-medium">
            READ-ONLY
          </span>
          <span>
            Operator Console is read-only. PDO and Settlement data cannot be modified from this interface.
          </span>
        </div>
        <span className="text-xs text-blue-500">
          API v{health.api_version}
        </span>
      </div>
    );
  }
  
  return null;
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * OperatorConsolePage — READ-ONLY console for PDO and Settlement visibility.
 * 
 * Layout:
 * - Left panel: PDO list or Settlements list
 * - Right panel: Timeline view
 * - Bottom panel: Ledger hash visibility
 * 
 * NO ACTION BUTTONS: This page cannot mutate any data (INV-OC-001).
 */
export const OperatorConsolePage: React.FC = () => {
  // State
  const [activeTab, setActiveTab] = useState<ActiveTab>('pdo');
  const [selectedPDOId, setSelectedPDOId] = useState<string | null>(null);
  const [selectedSettlementId, setSelectedSettlementId] = useState<string | null>(null);
  const [health, setHealth] = useState<OCHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  
  // Load health on mount
  useEffect(() => {
    const loadHealth = async () => {
      try {
        const response = await fetchOCHealth();
        setHealth(response);
        setHealthError(null);
      } catch (err) {
        setHealthError(err instanceof Error ? err.message : 'Failed to connect');
      } finally {
        setHealthLoading(false);
      }
    };
    
    loadHealth();
  }, []);
  
  // Handlers
  const handleSelectPDO = useCallback((pdoId: string) => {
    setSelectedPDOId(pdoId);
    setSelectedSettlementId(null);
  }, []);
  
  const handleSelectSettlement = useCallback((settlementId: string) => {
    setSelectedSettlementId(settlementId);
    setSelectedPDOId(null);
  }, []);
  
  return (
    <div className="flex flex-col h-screen bg-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-slate-800">
              Operator Console
            </h1>
            <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
              PDO & Settlement Visibility
            </span>
          </div>
          
          <div className="text-xs text-slate-500">
            PAC-007C • INV-OC-001 through INV-OC-005 Enforced
          </div>
        </div>
        
        {/* Read-only banner */}
        <StatusBanner health={health} loading={healthLoading} error={healthError} />
        
        {/* Tabs */}
        <div className="flex border-b border-slate-200 px-4">
          <Tab
            active={activeTab === 'pdo'}
            onClick={() => setActiveTab('pdo')}
            label="PDO Registry"
            icon="📄"
          />
          <Tab
            active={activeTab === 'settlements'}
            onClick={() => setActiveTab('settlements')}
            label="Settlements"
            icon="💰"
          />
          <Tab
            active={activeTab === 'ledger'}
            onClick={() => setActiveTab('ledger')}
            label="Ledger"
            icon="📒"
          />
        </div>
      </header>
      
      {/* Main content */}
      <main className="flex-1 overflow-hidden p-4">
        {activeTab === 'pdo' && (
          <div className="grid grid-cols-2 gap-4 h-full">
            {/* PDO List */}
            <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
              <PDOListView
                selectedPDOId={selectedPDOId}
                onSelectPDO={handleSelectPDO}
              />
            </div>
            
            {/* Timeline */}
            <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
              <PDOTimelineView
                pdoId={selectedPDOId}
                settlementId={selectedSettlementId}
              />
            </div>
          </div>
        )}
        
        {activeTab === 'settlements' && (
          <div className="grid grid-cols-2 gap-4 h-full">
            {/* Settlements placeholder */}
            <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
              <div className="p-4">
                <div className="flex items-center gap-2 mb-4">
                  <h2 className="text-sm font-semibold text-slate-800">Settlements</h2>
                  <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                    READ-ONLY
                  </span>
                </div>
                <div className="text-center py-8 text-slate-400">
                  Settlement visibility coming soon.
                  <br />
                  <span className="text-xs">
                    INV-OC-002: Every settlement will link to PDO ID
                  </span>
                </div>
              </div>
            </div>
            
            {/* Timeline */}
            <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
              <PDOTimelineView
                pdoId={selectedPDOId}
                settlementId={selectedSettlementId}
              />
            </div>
          </div>
        )}
        
        {activeTab === 'ledger' && (
          <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden h-full">
            <LedgerHashView />
          </div>
        )}
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 px-4 py-2 text-xs text-slate-500">
        <div className="flex items-center justify-between">
          <div>
            Operator Console • Read-Only Access • Ledger hash visibility enforced (INV-OC-003)
          </div>
          <div>
            No silent gaps (INV-OC-004) • Non-GET blocked (INV-OC-005)
          </div>
        </div>
      </footer>
    </div>
  );
};

export default OperatorConsolePage;
