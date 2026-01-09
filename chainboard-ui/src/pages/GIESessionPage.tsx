/**
 * GIE Session Page
 * 
 * Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
 * Agent: GID-02 (Sonny) — Frontend / Operator Console
 * 
 * REAL WORK MODE — Production-grade session management page.
 * 
 * Features:
 * - Session overview
 * - Checkpoint timeline integration
 * - BER/PDO display
 * - Read-only operator view
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  GIECheckpointTimeline,
  Checkpoint,
  AgentStatus,
  CheckpointType,
} from '../components/GIECheckpointTimeline';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface BERSummary {
  berId: string;
  pacId: string;
  status: 'APPROVE' | 'REJECT' | 'ESCALATE' | 'PENDING';
  issuedAt?: string;
  wrapCount: number;
  passedCount: number;
  failedCount: number;
}

export interface PDOSummary {
  pdoId: string;
  pacId: string;
  contentHash: string;
  sealedAt: string;
  agentCount: number;
}

export interface SessionData {
  sessionId: string;
  pacId: string;
  startedAt: string;
  completedAt?: string;
  phase: string;
  checkpoints: Checkpoint[];
  agents: AgentStatus[];
  ber?: BERSummary;
  pdo?: PDOSummary;
}

export interface GIESessionPageProps {
  sessionId: string;
  initialData?: SessionData;
  onRefresh?: () => Promise<SessionData>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface SessionHeaderProps {
  sessionId: string;
  pacId: string;
  startedAt: string;
  completedAt?: string;
  phase: string;
}

const SessionHeader: React.FC<SessionHeaderProps> = ({
  sessionId,
  pacId,
  startedAt,
  completedAt,
  phase,
}) => {
  const formatDateTime = (iso: string): string => {
    const date = new Date(iso);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const calculateDuration = (start: string, end?: string): string => {
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
    const diffMs = endTime - startTime;
    
    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    }
    return `${seconds}s`;
  };

  const isComplete = !!completedAt;

  return (
    <header
      style={{
        backgroundColor: '#FFFFFF',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <div>
          <h1
            style={{
              margin: '0 0 8px 0',
              fontSize: '24px',
              fontWeight: 700,
              color: '#111827',
            }}
          >
            GIE Session
          </h1>
          <p
            style={{
              margin: 0,
              fontSize: '14px',
              color: '#6B7280',
              fontFamily: 'monospace',
            }}
          >
            {sessionId}
          </p>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <span
            style={{
              padding: '6px 16px',
              backgroundColor: isComplete ? '#DCFCE7' : '#DBEAFE',
              color: isComplete ? '#166534' : '#1E40AF',
              borderRadius: '9999px',
              fontSize: '14px',
              fontWeight: 600,
            }}
          >
            {phase}
          </span>
        </div>
      </div>

      <div
        style={{
          marginTop: '20px',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '16px',
        }}
      >
        <InfoBlock label="PAC" value={pacId} />
        <InfoBlock label="Started" value={formatDateTime(startedAt)} />
        <InfoBlock
          label="Completed"
          value={completedAt ? formatDateTime(completedAt) : '—'}
        />
        <InfoBlock
          label="Duration"
          value={calculateDuration(startedAt, completedAt)}
        />
      </div>
    </header>
  );
};

interface InfoBlockProps {
  label: string;
  value: string;
}

const InfoBlock: React.FC<InfoBlockProps> = ({ label, value }) => (
  <div>
    <dt
      style={{
        fontSize: '12px',
        fontWeight: 500,
        color: '#6B7280',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: '4px',
      }}
    >
      {label}
    </dt>
    <dd
      style={{
        margin: 0,
        fontSize: '14px',
        fontWeight: 600,
        color: '#111827',
      }}
    >
      {value}
    </dd>
  </div>
);

interface BERCardProps {
  ber: BERSummary;
}

const BERCard: React.FC<BERCardProps> = ({ ber }) => {
  const statusColors: Record<string, { bg: string; text: string }> = {
    APPROVE: { bg: '#DCFCE7', text: '#166534' },
    REJECT: { bg: '#FEE2E2', text: '#991B1B' },
    ESCALATE: { bg: '#FEF3C7', text: '#92400E' },
    PENDING: { bg: '#F3F4F6', text: '#374151' },
  };

  const colors = statusColors[ber.status] || statusColors.PENDING;

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: '16px',
            fontWeight: 600,
            color: '#111827',
          }}
        >
          Benson Execution Review
        </h3>
        <span
          style={{
            padding: '4px 12px',
            backgroundColor: colors.bg,
            color: colors.text,
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: 600,
          }}
        >
          {ber.status}
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '12px',
          fontSize: '13px',
        }}
      >
        <div>
          <span style={{ color: '#6B7280' }}>WRAPs:</span>{' '}
          <strong>{ber.wrapCount}</strong>
        </div>
        <div>
          <span style={{ color: '#6B7280' }}>Passed:</span>{' '}
          <strong style={{ color: '#16A34A' }}>{ber.passedCount}</strong>
        </div>
        <div>
          <span style={{ color: '#6B7280' }}>Failed:</span>{' '}
          <strong style={{ color: '#DC2626' }}>{ber.failedCount}</strong>
        </div>
      </div>

      {ber.issuedAt && (
        <p
          style={{
            margin: '12px 0 0 0',
            fontSize: '12px',
            color: '#9CA3AF',
          }}
        >
          Issued: {new Date(ber.issuedAt).toLocaleString()}
        </p>
      )}
    </div>
  );
};

interface PDOCardProps {
  pdo: PDOSummary;
}

const PDOCard: React.FC<PDOCardProps> = ({ pdo }) => {
  const truncateHash = (hash: string): string => {
    if (hash.length <= 24) return hash;
    return `${hash.slice(0, 14)}...${hash.slice(-10)}`;
  };

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        borderLeft: '4px solid #14B8A6',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: '16px',
            fontWeight: 600,
            color: '#111827',
          }}
        >
          🔒 Proof of Determined Outcome
        </h3>
        <span
          style={{
            padding: '4px 12px',
            backgroundColor: '#CCFBF1',
            color: '#0F766E',
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: 600,
          }}
        >
          SEALED
        </span>
      </div>

      <div
        style={{
          padding: '12px',
          backgroundColor: '#F9FAFB',
          borderRadius: '8px',
          fontFamily: 'monospace',
          fontSize: '12px',
        }}
      >
        <div style={{ marginBottom: '8px' }}>
          <span style={{ color: '#6B7280' }}>PDO ID:</span>{' '}
          <span style={{ color: '#111827' }}>{pdo.pdoId}</span>
        </div>
        <div style={{ marginBottom: '8px' }}>
          <span style={{ color: '#6B7280' }}>Hash:</span>{' '}
          <span style={{ color: '#059669' }} title={pdo.contentHash}>
            {truncateHash(pdo.contentHash)}
          </span>
        </div>
        <div>
          <span style={{ color: '#6B7280' }}>Agents:</span>{' '}
          <span style={{ color: '#111827' }}>{pdo.agentCount}</span>
        </div>
      </div>

      <p
        style={{
          margin: '12px 0 0 0',
          fontSize: '12px',
          color: '#9CA3AF',
        }}
      >
        Sealed: {new Date(pdo.sealedAt).toLocaleString()}
      </p>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const GIESessionPage: React.FC<GIESessionPageProps> = ({
  sessionId,
  initialData,
  onRefresh,
}) => {
  const [data, setData] = useState<SessionData | null>(initialData || null);
  const [isLoading, setIsLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);

  // Load initial data if not provided
  useEffect(() => {
    if (!initialData && onRefresh) {
      setIsLoading(true);
      onRefresh()
        .then(setData)
        .catch(err => setError(err.message))
        .finally(() => setIsLoading(false));
    }
  }, [initialData, onRefresh]);

  const handleRefresh = useCallback(async () => {
    if (!onRefresh) return;

    setIsLoading(true);
    try {
      const newData = await onRefresh();
      setData(newData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh');
    } finally {
      setIsLoading(false);
    }
  }, [onRefresh]);

  const handleCheckpointClick = useCallback((checkpoint: Checkpoint) => {
    console.log('Checkpoint clicked:', checkpoint);
  }, []);

  const isComplete = useMemo(() => {
    if (!data) return false;
    return data.phase === 'COMPLETE' || !!data.completedAt;
  }, [data]);

  if (isLoading && !data) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
          color: '#6B7280',
        }}
      >
        Loading session data...
      </div>
    );
  }

  if (error && !data) {
    return (
      <div
        style={{
          padding: '24px',
          backgroundColor: '#FEF2F2',
          borderRadius: '12px',
          color: '#991B1B',
        }}
      >
        <h3 style={{ margin: '0 0 8px 0' }}>Error Loading Session</h3>
        <p style={{ margin: 0 }}>{error}</p>
        {onRefresh && (
          <button
            onClick={handleRefresh}
            style={{
              marginTop: '16px',
              padding: '8px 16px',
              backgroundColor: '#DC2626',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: '24px', color: '#6B7280' }}>
        No session data available
      </div>
    );
  }

  return (
    <div
      className="gie-session-page"
      style={{
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        padding: '24px',
        backgroundColor: '#F3F4F6',
        minHeight: '100vh',
      }}
    >
      {/* Header */}
      <SessionHeader
        sessionId={data.sessionId}
        pacId={data.pacId}
        startedAt={data.startedAt}
        completedAt={data.completedAt}
        phase={data.phase}
      />

      {/* Main Content Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 400px',
          gap: '24px',
        }}
      >
        {/* Timeline */}
        <div>
          <GIECheckpointTimeline
            pacId={data.pacId}
            checkpoints={data.checkpoints}
            agents={data.agents}
            currentPhase={data.phase}
            isComplete={isComplete}
            onCheckpointClick={handleCheckpointClick}
          />
        </div>

        {/* Sidebar */}
        <aside
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {/* BER Card */}
          {data.ber && <BERCard ber={data.ber} />}

          {/* PDO Card */}
          {data.pdo && <PDOCard pdo={data.pdo} />}

          {/* Refresh Button */}
          {onRefresh && (
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              style={{
                padding: '12px 24px',
                backgroundColor: isLoading ? '#9CA3AF' : '#3B82F6',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 500,
                cursor: isLoading ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.2s',
              }}
            >
              {isLoading ? 'Refreshing...' : 'Refresh Session'}
            </button>
          )}
        </aside>
      </div>
    </div>
  );
};

export default GIESessionPage;
