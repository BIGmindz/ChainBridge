/**
 * Test GIE Checkpoint Timeline & Session Page
 * 
 * Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
 * Agent: GID-02 (Sonny) — Frontend / Operator Console
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  GIECheckpointTimeline,
  Checkpoint,
  AgentStatus,
} from '../components/GIECheckpointTimeline';
import {
  GIESessionPage,
  SessionData,
} from '../pages/GIESessionPage';

// ═══════════════════════════════════════════════════════════════════════════════
// TEST DATA
// ═══════════════════════════════════════════════════════════════════════════════

const mockCheckpoints: Checkpoint[] = [
  {
    id: 'cp-001',
    type: 'PAC_STARTED',
    timestamp: '2025-12-26T10:00:00Z',
    message: 'PAC-029 execution started',
  },
  {
    id: 'cp-002',
    type: 'AGENT_STARTED',
    timestamp: '2025-12-26T10:00:01Z',
    agentGid: 'GID-01',
    message: 'Agent GID-01 started execution',
  },
  {
    id: 'cp-003',
    type: 'WRAP_RECEIVED',
    timestamp: '2025-12-26T10:00:30Z',
    agentGid: 'GID-01',
    wrapHash: 'sha256:7c2d4e8f1a3b5c6d7e8f9a0b1c2d3e4f5a6b7c8d',
    message: 'WRAP received from GID-01',
  },
];

const mockAgents: AgentStatus[] = [
  {
    gid: 'GID-01',
    name: 'Cody',
    lane: 'BACKEND',
    state: 'COMPLETED',
    taskName: 'Execution Planner',
    wrapHash: 'sha256:7c2d4e8f...',
  },
  {
    gid: 'GID-02',
    name: 'Sonny',
    lane: 'FRONTEND',
    state: 'RUNNING',
    taskName: 'Checkpoint Timeline',
  },
  {
    gid: 'GID-03',
    name: 'Mira-R',
    lane: 'RESEARCH',
    state: 'PENDING',
    taskName: 'Competitive Analysis',
  },
];

const mockSessionData: SessionData = {
  sessionId: 'SESSION-029-001',
  pacId: 'PAC-029',
  startedAt: '2025-12-26T10:00:00Z',
  phase: 'EXECUTING',
  checkpoints: mockCheckpoints,
  agents: mockAgents,
};

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: GIECheckpointTimeline
// ═══════════════════════════════════════════════════════════════════════════════

describe('GIECheckpointTimeline', () => {
  it('renders the PAC ID', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="EXECUTING"
        isComplete={false}
      />
    );
    
    expect(screen.getByText('PAC-029')).toBeInTheDocument();
  });

  it('renders all checkpoints', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="EXECUTING"
        isComplete={false}
      />
    );
    
    expect(screen.getByText('PAC STARTED')).toBeInTheDocument();
    expect(screen.getByText('AGENT STARTED')).toBeInTheDocument();
    expect(screen.getByText('WRAP RECEIVED')).toBeInTheDocument();
  });

  it('renders agent cards', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="EXECUTING"
        isComplete={false}
      />
    );
    
    expect(screen.getByText('GID-01')).toBeInTheDocument();
    expect(screen.getByText('GID-02')).toBeInTheDocument();
    expect(screen.getByText('GID-03')).toBeInTheDocument();
  });

  it('shows agent states', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="EXECUTING"
        isComplete={false}
      />
    );
    
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('shows WRAP count progress', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="EXECUTING"
        isComplete={false}
      />
    );
    
    // 1 WRAP received out of 3 agents
    expect(screen.getByText('1/3 WRAPs')).toBeInTheDocument();
  });

  it('handles checkpoint click', () => {
    const handleClick = jest.fn();
    
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="EXECUTING"
        isComplete={false}
        onCheckpointClick={handleClick}
      />
    );
    
    // Click on a checkpoint
    fireEvent.click(screen.getByText('PAC STARTED'));
    
    expect(handleClick).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'PAC_STARTED' })
    );
  });

  it('displays WRAP hash on checkpoint', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="EXECUTING"
        isComplete={false}
      />
    );
    
    // Truncated hash should be visible
    expect(screen.getByText(/WRAP:.*sha256/)).toBeInTheDocument();
  });

  it('shows empty state when no checkpoints', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={[]}
        agents={mockAgents}
        currentPhase="STARTING"
        isComplete={false}
      />
    );
    
    expect(screen.getByText('No checkpoints yet')).toBeInTheDocument();
  });

  it('shows complete state styling', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="COMPLETE"
        isComplete={true}
      />
    );
    
    expect(screen.getByText('COMPLETE')).toBeInTheDocument();
  });

  it('has proper accessibility attributes', () => {
    render(
      <GIECheckpointTimeline
        pacId="PAC-029"
        checkpoints={mockCheckpoints}
        agents={mockAgents}
        currentPhase="EXECUTING"
        isComplete={false}
      />
    );
    
    expect(screen.getByRole('region', { name: /checkpoint timeline/i })).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByRole('list', { name: /checkpoint list/i })).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: GIESessionPage
// ═══════════════════════════════════════════════════════════════════════════════

describe('GIESessionPage', () => {
  it('renders session header', () => {
    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        initialData={mockSessionData}
      />
    );
    
    expect(screen.getByText('GIE Session')).toBeInTheDocument();
    expect(screen.getByText('SESSION-029-001')).toBeInTheDocument();
  });

  it('displays PAC ID', () => {
    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        initialData={mockSessionData}
      />
    );
    
    expect(screen.getAllByText('PAC-029').length).toBeGreaterThan(0);
  });

  it('shows session phase', () => {
    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        initialData={mockSessionData}
      />
    );
    
    expect(screen.getByText('EXECUTING')).toBeInTheDocument();
  });

  it('renders BER card when present', () => {
    const dataWithBER: SessionData = {
      ...mockSessionData,
      ber: {
        berId: 'BER-029',
        pacId: 'PAC-029',
        status: 'APPROVE',
        issuedAt: '2025-12-26T10:01:00Z',
        wrapCount: 6,
        passedCount: 6,
        failedCount: 0,
      },
    };

    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        initialData={dataWithBER}
      />
    );
    
    expect(screen.getByText('Benson Execution Review')).toBeInTheDocument();
    expect(screen.getByText('APPROVE')).toBeInTheDocument();
  });

  it('renders PDO card when present', () => {
    const dataWithPDO: SessionData = {
      ...mockSessionData,
      pdo: {
        pdoId: 'PDO-029',
        pacId: 'PAC-029',
        contentHash: 'sha256:d4a7e1f3b8c29a56...',
        sealedAt: '2025-12-26T10:02:00Z',
        agentCount: 6,
      },
    };

    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        initialData={dataWithPDO}
      />
    );
    
    expect(screen.getByText('🔒 Proof of Determined Outcome')).toBeInTheDocument();
    expect(screen.getByText('SEALED')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        onRefresh={() => new Promise(() => {})} // Never resolves
      />
    );
    
    expect(screen.getByText('Loading session data...')).toBeInTheDocument();
  });

  it('shows error state', async () => {
    const failingRefresh = jest.fn().mockRejectedValue(new Error('Network error'));
    
    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        onRefresh={failingRefresh}
      />
    );
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Session')).toBeInTheDocument();
    });
  });

  it('handles refresh button click', async () => {
    const mockRefresh = jest.fn().mockResolvedValue(mockSessionData);
    
    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        initialData={mockSessionData}
        onRefresh={mockRefresh}
      />
    );
    
    fireEvent.click(screen.getByText('Refresh Session'));
    
    await waitFor(() => {
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it('shows no data state', () => {
    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
      />
    );
    
    expect(screen.getByText('No session data available')).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: Integration
// ═══════════════════════════════════════════════════════════════════════════════

describe('Integration', () => {
  it('timeline renders correctly within session page', () => {
    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        initialData={mockSessionData}
      />
    );
    
    // Verify timeline components are present
    expect(screen.getByRole('region', { name: /checkpoint timeline/i })).toBeInTheDocument();
    expect(screen.getByText('Checkpoints')).toBeInTheDocument();
    expect(screen.getByText('Agents (3)')).toBeInTheDocument();
  });

  it('complete session shows all artifacts', () => {
    const completeData: SessionData = {
      ...mockSessionData,
      completedAt: '2025-12-26T10:05:00Z',
      phase: 'COMPLETE',
      ber: {
        berId: 'BER-029',
        pacId: 'PAC-029',
        status: 'APPROVE',
        issuedAt: '2025-12-26T10:04:00Z',
        wrapCount: 6,
        passedCount: 6,
        failedCount: 0,
      },
      pdo: {
        pdoId: 'PDO-029',
        pacId: 'PAC-029',
        contentHash: 'sha256:d4a7e1f3...',
        sealedAt: '2025-12-26T10:05:00Z',
        agentCount: 6,
      },
    };

    render(
      <GIESessionPage
        sessionId="SESSION-029-001"
        initialData={completeData}
      />
    );
    
    expect(screen.getByText('COMPLETE')).toBeInTheDocument();
    expect(screen.getByText('Benson Execution Review')).toBeInTheDocument();
    expect(screen.getByText('🔒 Proof of Determined Outcome')).toBeInTheDocument();
  });
});
