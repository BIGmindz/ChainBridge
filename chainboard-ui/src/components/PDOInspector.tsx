/**
 * PDOInspector Component
 * 
 * Displays detailed PDO (Proof → Decision → Outcome) artifact information.
 * Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-PDO-STRESS-023.
 * 
 * Agent: GID-02 (Sonny) — Frontend Engineer
 */

import React, { useMemo } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface PDOArtifact {
  pdo_id: string;
  pac_id: string;
  wrap_id: string;
  ber_id: string;
  issuer: string;
  proof_hash: string;
  decision_hash: string;
  outcome_hash: string;
  pdo_hash: string;
  outcome_status: 'ACCEPTED' | 'CORRECTIVE' | 'REJECTED';
  emitted_at: string;
  created_at: string;
}

export interface PDOInspectorProps {
  pdo: PDOArtifact | null;
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  className?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface StatusBadgeProps {
  status: PDOArtifact['outcome_status'];
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const styles: Record<string, React.CSSProperties> = {
    ACCEPTED: {
      backgroundColor: '#dcfce7',
      color: '#166534',
      border: '1px solid #86efac',
    },
    CORRECTIVE: {
      backgroundColor: '#fef3c7',
      color: '#92400e',
      border: '1px solid #fcd34d',
    },
    REJECTED: {
      backgroundColor: '#fee2e2',
      color: '#991b1b',
      border: '1px solid #fca5a5',
    },
  };

  const icons: Record<string, string> = {
    ACCEPTED: '✅',
    CORRECTIVE: '⚠️',
    REJECTED: '❌',
  };

  return (
    <span
      style={{
        padding: '4px 12px',
        borderRadius: '9999px',
        fontSize: '14px',
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        ...styles[status],
      }}
      role="status"
      aria-label={`Outcome status: ${status}`}
    >
      <span aria-hidden="true">{icons[status]}</span>
      {status}
    </span>
  );
};

interface HashDisplayProps {
  label: string;
  hash: string;
  truncate?: boolean;
}

const HashDisplay: React.FC<HashDisplayProps> = ({ 
  label, 
  hash, 
  truncate = true 
}) => {
  const displayHash = truncate && hash.length > 16 
    ? `${hash.slice(0, 8)}...${hash.slice(-8)}`
    : hash;

  return (
    <div style={{ marginBottom: '12px' }}>
      <div style={{ 
        fontSize: '12px', 
        color: '#6b7280', 
        marginBottom: '4px',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
      }}>
        {label}
      </div>
      <code
        style={{
          fontFamily: 'monospace',
          fontSize: '13px',
          backgroundColor: '#f3f4f6',
          padding: '6px 10px',
          borderRadius: '4px',
          display: 'block',
          wordBreak: 'break-all',
        }}
        title={hash}
      >
        {displayHash || '—'}
      </code>
    </div>
  );
};

interface InfoRowProps {
  label: string;
  value: string | React.ReactNode;
}

const InfoRow: React.FC<InfoRowProps> = ({ label, value }) => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'space-between',
    padding: '8px 0',
    borderBottom: '1px solid #e5e7eb',
  }}>
    <span style={{ color: '#6b7280', fontSize: '14px' }}>{label}</span>
    <span style={{ fontWeight: 500, fontSize: '14px' }}>{value}</span>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// LOADING STATE
// ═══════════════════════════════════════════════════════════════════════════════

const LoadingSkeleton: React.FC = () => (
  <div 
    style={{ padding: '24px' }}
    role="status"
    aria-label="Loading PDO data"
  >
    <div style={{ 
      height: '24px', 
      backgroundColor: '#e5e7eb', 
      borderRadius: '4px',
      marginBottom: '16px',
      animation: 'pulse 2s infinite',
    }} />
    <div style={{ 
      height: '100px', 
      backgroundColor: '#e5e7eb', 
      borderRadius: '4px',
      marginBottom: '16px',
      animation: 'pulse 2s infinite',
    }} />
    <div style={{ 
      height: '200px', 
      backgroundColor: '#e5e7eb', 
      borderRadius: '4px',
      animation: 'pulse 2s infinite',
    }} />
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR STATE
// ═══════════════════════════════════════════════════════════════════════════════

interface ErrorDisplayProps {
  message: string;
  onRetry?: () => void;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ message, onRetry }) => (
  <div
    style={{
      padding: '24px',
      backgroundColor: '#fee2e2',
      borderRadius: '8px',
      textAlign: 'center',
    }}
    role="alert"
  >
    <div style={{ fontSize: '24px', marginBottom: '8px' }}>❌</div>
    <div style={{ color: '#991b1b', fontWeight: 500, marginBottom: '16px' }}>
      {message}
    </div>
    {onRetry && (
      <button
        onClick={onRetry}
        style={{
          padding: '8px 16px',
          backgroundColor: '#991b1b',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
        }}
      >
        Retry
      </button>
    )}
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// EMPTY STATE
// ═══════════════════════════════════════════════════════════════════════════════

const EmptyState: React.FC = () => (
  <div
    style={{
      padding: '48px 24px',
      textAlign: 'center',
      color: '#6b7280',
    }}
  >
    <div style={{ fontSize: '48px', marginBottom: '16px' }}>🧿</div>
    <div style={{ fontSize: '16px' }}>No PDO selected</div>
    <div style={{ fontSize: '14px', marginTop: '8px' }}>
      Select a PDO from the list to view details
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const PDOInspector: React.FC<PDOInspectorProps> = ({
  pdo,
  loading = false,
  error = null,
  onRefresh,
  className,
}) => {
  // Format timestamp for display
  const formattedTimestamp = useMemo(() => {
    if (!pdo?.emitted_at) return '—';
    try {
      return new Date(pdo.emitted_at).toLocaleString();
    } catch {
      return pdo.emitted_at;
    }
  }, [pdo?.emitted_at]);

  // Verify hash chain (simplified frontend check)
  const hashChainValid = useMemo(() => {
    if (!pdo) return false;
    return !!(
      pdo.proof_hash &&
      pdo.decision_hash &&
      pdo.outcome_hash &&
      pdo.pdo_hash
    );
  }, [pdo]);

  // Container styles
  const containerStyle: React.CSSProperties = {
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    overflow: 'hidden',
  };

  // Handle loading state
  if (loading) {
    return (
      <div style={containerStyle} className={className}>
        <LoadingSkeleton />
      </div>
    );
  }

  // Handle error state
  if (error) {
    return (
      <div style={containerStyle} className={className}>
        <ErrorDisplay message={error} onRetry={onRefresh} />
      </div>
    );
  }

  // Handle empty state
  if (!pdo) {
    return (
      <div style={containerStyle} className={className}>
        <EmptyState />
      </div>
    );
  }

  return (
    <div style={containerStyle} className={className}>
      {/* Header */}
      <div
        style={{
          padding: '16px 24px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>
            🧿 PDO Inspector
          </h2>
          <div style={{ color: '#6b7280', fontSize: '13px', marginTop: '4px' }}>
            Proof → Decision → Outcome
          </div>
        </div>
        <StatusBadge status={pdo.outcome_status} />
      </div>

      {/* Identity Section */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #e5e7eb' }}>
        <h3 style={{ 
          margin: '0 0 12px 0', 
          fontSize: '14px', 
          fontWeight: 600,
          color: '#374151',
        }}>
          Identity
        </h3>
        <InfoRow label="PDO ID" value={pdo.pdo_id} />
        <InfoRow label="PAC ID" value={pdo.pac_id} />
        <InfoRow label="WRAP ID" value={pdo.wrap_id || '—'} />
        <InfoRow label="BER ID" value={pdo.ber_id} />
        <InfoRow label="Issuer" value={pdo.issuer} />
        <InfoRow label="Emitted At" value={formattedTimestamp} />
      </div>

      {/* Hash Chain Section */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #e5e7eb' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}>
          <h3 style={{ 
            margin: 0, 
            fontSize: '14px', 
            fontWeight: 600,
            color: '#374151',
          }}>
            Hash Chain
          </h3>
          <span
            style={{
              fontSize: '12px',
              color: hashChainValid ? '#166534' : '#991b1b',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            {hashChainValid ? '✓ Valid' : '✗ Invalid'}
          </span>
        </div>

        {/* Hash Chain Visualization */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column',
          gap: '8px',
        }}>
          <HashDisplay label="1. Proof Hash" hash={pdo.proof_hash} />
          <div style={{ 
            textAlign: 'center', 
            color: '#9ca3af',
            fontSize: '20px',
          }}>
            ↓
          </div>
          <HashDisplay label="2. Decision Hash" hash={pdo.decision_hash} />
          <div style={{ 
            textAlign: 'center', 
            color: '#9ca3af',
            fontSize: '20px',
          }}>
            ↓
          </div>
          <HashDisplay label="3. Outcome Hash" hash={pdo.outcome_hash} />
          <div style={{ 
            textAlign: 'center', 
            color: '#9ca3af',
            fontSize: '20px',
          }}>
            ↓
          </div>
          <HashDisplay label="4. PDO Hash (Final)" hash={pdo.pdo_hash} />
        </div>
      </div>

      {/* Actions */}
      {onRefresh && (
        <div style={{ padding: '16px 24px' }}>
          <button
            onClick={onRefresh}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: '#f3f4f6',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 500,
              color: '#374151',
            }}
          >
            🔄 Refresh
          </button>
        </div>
      )}
    </div>
  );
};

export default PDOInspector;
