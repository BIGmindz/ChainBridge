/**
 * PDODetailPage
 * 
 * Full page view for PDO artifact details with navigation and history.
 * Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-PDO-STRESS-023.
 * 
 * Agent: GID-02 (Sonny) — Frontend Engineer
 */

import React, { useState, useEffect, useCallback } from 'react';
import { PDOInspector, PDOArtifact } from '../components/PDOInspector';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface PDODetailPageProps {
  pdoId?: string;
  onNavigateBack?: () => void;
  onNavigateToPDO?: (pdoId: string) => void;
  apiBaseUrl?: string;
}

interface PDOListItem {
  pdo_id: string;
  pac_id: string;
  outcome_status: 'ACCEPTED' | 'CORRECTIVE' | 'REJECTED';
  emitted_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// MOCK DATA (for development/testing)
// ═══════════════════════════════════════════════════════════════════════════════

const MOCK_PDO_LIST: PDOListItem[] = [
  {
    pdo_id: 'PDO-PAC-023-001',
    pac_id: 'PAC-023-A',
    outcome_status: 'ACCEPTED',
    emitted_at: new Date().toISOString(),
  },
  {
    pdo_id: 'PDO-PAC-023-002',
    pac_id: 'PAC-023-B',
    outcome_status: 'CORRECTIVE',
    emitted_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    pdo_id: 'PDO-PAC-023-003',
    pac_id: 'PAC-023-C',
    outcome_status: 'ACCEPTED',
    emitted_at: new Date(Date.now() - 7200000).toISOString(),
  },
];

const MOCK_PDO_DETAIL: PDOArtifact = {
  pdo_id: 'PDO-PAC-023-001',
  pac_id: 'PAC-023-A',
  wrap_id: 'WRAP-PAC-023-A',
  ber_id: 'BER-PAC-023-A',
  issuer: 'GID-00',
  proof_hash: 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678',
  decision_hash: 'b2c3d4e5f67890123456789012345678901234567890abcdef1234567890abcd',
  outcome_hash: 'c3d4e5f678901234567890123456789012345678901234567890abcdef123456',
  pdo_hash: 'd4e5f6789012345678901234567890123456789012345678901234567890abcdef',
  outcome_status: 'ACCEPTED',
  emitted_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
};

// ═══════════════════════════════════════════════════════════════════════════════
// PDO LIST ITEM COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface PDOListItemProps {
  item: PDOListItem;
  isSelected: boolean;
  onClick: () => void;
}

const PDOListItemComponent: React.FC<PDOListItemProps> = ({
  item,
  isSelected,
  onClick,
}) => {
  const statusColors: Record<string, string> = {
    ACCEPTED: '#22c55e',
    CORRECTIVE: '#f59e0b',
    REJECTED: '#ef4444',
  };

  return (
    <button
      onClick={onClick}
      style={{
        width: '100%',
        padding: '12px 16px',
        border: 'none',
        borderLeft: `4px solid ${statusColors[item.outcome_status]}`,
        backgroundColor: isSelected ? '#eff6ff' : 'white',
        cursor: 'pointer',
        textAlign: 'left',
        borderBottom: '1px solid #e5e7eb',
        transition: 'background-color 0.15s',
      }}
      aria-selected={isSelected}
      role="option"
    >
      <div style={{ 
        fontWeight: 600, 
        fontSize: '14px',
        marginBottom: '4px',
        color: '#1f2937',
      }}>
        {item.pdo_id}
      </div>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        fontSize: '12px',
        color: '#6b7280',
      }}>
        <span>{item.pac_id}</span>
        <span>{new Date(item.emitted_at).toLocaleTimeString()}</span>
      </div>
    </button>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const PDODetailPage: React.FC<PDODetailPageProps> = ({
  pdoId: initialPdoId,
  onNavigateBack,
  onNavigateToPDO,
  apiBaseUrl = '/api',
}) => {
  // State
  const [pdoList, setPdoList] = useState<PDOListItem[]>(MOCK_PDO_LIST);
  const [selectedPdoId, setSelectedPdoId] = useState<string | undefined>(
    initialPdoId
  );
  const [pdoDetail, setPdoDetail] = useState<PDOArtifact | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(false);

  // Fetch PDO list
  const fetchPDOList = useCallback(async () => {
    setListLoading(true);
    try {
      // In production, fetch from API
      // const response = await fetch(`${apiBaseUrl}/pdo/list`);
      // const data = await response.json();
      // setPdoList(data);
      
      // Using mock data for now
      await new Promise(resolve => setTimeout(resolve, 500));
      setPdoList(MOCK_PDO_LIST);
    } catch (err) {
      console.error('Failed to fetch PDO list:', err);
    } finally {
      setListLoading(false);
    }
  }, [apiBaseUrl]);

  // Fetch PDO detail
  const fetchPDODetail = useCallback(async (pdoId: string) => {
    setLoading(true);
    setError(null);
    try {
      // In production, fetch from API
      // const response = await fetch(`${apiBaseUrl}/pdo/${pdoId}`);
      // if (!response.ok) throw new Error('PDO not found');
      // const data = await response.json();
      // setPdoDetail(data);
      
      // Using mock data for now
      await new Promise(resolve => setTimeout(resolve, 300));
      setPdoDetail({ ...MOCK_PDO_DETAIL, pdo_id: pdoId });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load PDO');
      setPdoDetail(null);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl]);

  // Load list on mount
  useEffect(() => {
    fetchPDOList();
  }, [fetchPDOList]);

  // Load detail when selection changes
  useEffect(() => {
    if (selectedPdoId) {
      fetchPDODetail(selectedPdoId);
      onNavigateToPDO?.(selectedPdoId);
    } else {
      setPdoDetail(null);
    }
  }, [selectedPdoId, fetchPDODetail, onNavigateToPDO]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    if (selectedPdoId) {
      fetchPDODetail(selectedPdoId);
    }
  }, [selectedPdoId, fetchPDODetail]);

  // Page styles
  const pageStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    backgroundColor: '#f9fafb',
  };

  const headerStyle: React.CSSProperties = {
    padding: '16px 24px',
    backgroundColor: 'white',
    borderBottom: '1px solid #e5e7eb',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  };

  const contentStyle: React.CSSProperties = {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  };

  const sidebarStyle: React.CSSProperties = {
    width: '320px',
    backgroundColor: 'white',
    borderRight: '1px solid #e5e7eb',
    overflowY: 'auto',
  };

  const mainStyle: React.CSSProperties = {
    flex: 1,
    padding: '24px',
    overflowY: 'auto',
  };

  return (
    <div style={pageStyle}>
      {/* Header */}
      <header style={headerStyle}>
        {onNavigateBack && (
          <button
            onClick={onNavigateBack}
            style={{
              padding: '8px 12px',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              backgroundColor: 'white',
              cursor: 'pointer',
              fontSize: '14px',
            }}
            aria-label="Go back"
          >
            ← Back
          </button>
        )}
        <div>
          <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 600 }}>
            🧿 PDO Artifacts
          </h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: '#6b7280' }}>
            Proof → Decision → Outcome Chain
          </p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
          <button
            onClick={fetchPDOList}
            disabled={listLoading}
            style={{
              padding: '8px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              backgroundColor: 'white',
              cursor: listLoading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              opacity: listLoading ? 0.5 : 1,
            }}
          >
            {listLoading ? 'Loading...' : '🔄 Refresh List'}
          </button>
        </div>
      </header>

      {/* Content */}
      <div style={contentStyle}>
        {/* Sidebar - PDO List */}
        <aside style={sidebarStyle} role="listbox" aria-label="PDO list">
          <div style={{ 
            padding: '12px 16px', 
            borderBottom: '1px solid #e5e7eb',
            fontWeight: 600,
            fontSize: '14px',
            color: '#374151',
          }}>
            Recent PDOs ({pdoList.length})
          </div>
          {pdoList.map((item) => (
            <PDOListItemComponent
              key={item.pdo_id}
              item={item}
              isSelected={selectedPdoId === item.pdo_id}
              onClick={() => setSelectedPdoId(item.pdo_id)}
            />
          ))}
          {pdoList.length === 0 && !listLoading && (
            <div style={{ 
              padding: '24px', 
              textAlign: 'center', 
              color: '#6b7280',
              fontSize: '14px',
            }}>
              No PDOs found
            </div>
          )}
        </aside>

        {/* Main - PDO Detail */}
        <main style={mainStyle}>
          <PDOInspector
            pdo={pdoDetail}
            loading={loading}
            error={error}
            onRefresh={handleRefresh}
          />
          
          {/* Additional Info Section */}
          {pdoDetail && !loading && !error && (
            <div style={{ 
              marginTop: '24px',
              backgroundColor: 'white',
              borderRadius: '12px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
              padding: '16px 24px',
            }}>
              <h3 style={{ 
                margin: '0 0 16px 0', 
                fontSize: '14px', 
                fontWeight: 600,
                color: '#374151',
              }}>
                Related Artifacts
              </h3>
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '16px',
              }}>
                <a
                  href={`/pac/${pdoDetail.pac_id}`}
                  style={{
                    padding: '16px',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '8px',
                    textDecoration: 'none',
                    color: '#1f2937',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '24px', marginBottom: '8px' }}>📋</div>
                  <div style={{ fontWeight: 600 }}>PAC</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    {pdoDetail.pac_id}
                  </div>
                </a>
                <a
                  href={`/wrap/${pdoDetail.wrap_id}`}
                  style={{
                    padding: '16px',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '8px',
                    textDecoration: 'none',
                    color: '#1f2937',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '24px', marginBottom: '8px' }}>📦</div>
                  <div style={{ fontWeight: 600 }}>WRAP</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    {pdoDetail.wrap_id || '—'}
                  </div>
                </a>
                <a
                  href={`/ber/${pdoDetail.ber_id}`}
                  style={{
                    padding: '16px',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '8px',
                    textDecoration: 'none',
                    color: '#1f2937',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '24px', marginBottom: '8px' }}>📝</div>
                  <div style={{ fontWeight: 600 }}>BER</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    {pdoDetail.ber_id}
                  </div>
                </a>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default PDODetailPage;
