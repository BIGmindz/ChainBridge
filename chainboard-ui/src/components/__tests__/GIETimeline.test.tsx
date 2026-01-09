/**
 * Test GIE Timeline Component
 * 
 * Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
 * Agent: GID-02 (Sonny) — Senior Frontend Engineer
 */

import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { GIETimeline, AgentCard, CheckpointMarker } from '../components/GIETimeline';
import type { AgentState, Checkpoint, CheckpointType, AgentStatus } from '../components/GIETimeline';

// ═══════════════════════════════════════════════════════════════════════════════
// TEST DATA
// ═══════════════════════════════════════════════════════════════════════════════

const mockAgents: AgentState[] = [
  {
    gid: 'GID-01',
    name: 'Cody',
    role: 'Senior Backend Engineer',
    status: 'COMPLETED',
    startedAt: '2025-12-26T10:00:00Z',
    completedAt: '2025-12-26T10:05:00Z',
    wrapHash: 'sha256:abc123def456',
    testCount: 54,
  },
  {
    gid: 'GID-02',
    name: 'Sonny',
    role: 'Senior Frontend Engineer',
    status: 'RUNNING',
    startedAt: '2025-12-26T10:01:00Z',
  },
  {
    gid: 'GID-03',
    name: 'Mira-R',
    role: 'Research Lead',
    status: 'PENDING',
  },
  {
    gid: 'GID-07',
    name: 'Dan',
    role: 'Data Engineer',
    status: 'FAILED',
    errorMessage: 'Connection timeout',
  },
];

const mockCheckpoints: Checkpoint[] = [
  {
    id: 'CP-001',
    type: 'PAC_RECEIVED',
    message: 'PAC-028 validated',
    timestamp: '2025-12-26T10:00:00Z',
  },
  {
    id: 'CP-002',
    type: 'AGENTS_DISPATCHED',
    message: '6 agents dispatched',
    timestamp: '2025-12-26T10:00:01Z',
  },
  {
    id: 'CP-003',
    type: 'AGENT_STARTED',
    message: 'GID-01 started',
    timestamp: '2025-12-26T10:00:02Z',
    agentGid: 'GID-01',
  },
  {
    id: 'CP-004',
    type: 'AGENT_COMPLETED',
    message: 'GID-01 completed — 54 tests',
    timestamp: '2025-12-26T10:05:00Z',
    agentGid: 'GID-01',
  },
  {
    id: 'CP-005',
    type: 'WRAP_HASH_RECEIVED',
    message: 'GID-01 WRAP received',
    timestamp: '2025-12-26T10:05:01Z',
    agentGid: 'GID-01',
    hashRef: 'sha256:abc123def456',
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: AgentCard Component
// ═══════════════════════════════════════════════════════════════════════════════

describe('AgentCard', () => {
  it('renders agent information', () => {
    render(<AgentCard agent={mockAgents[0]} />);
    
    expect(screen.getByText('GID-01')).toBeInTheDocument();
    expect(screen.getByText('Cody')).toBeInTheDocument();
    expect(screen.getByText('Senior Backend Engineer')).toBeInTheDocument();
  });

  it('shows WRAP hash when available', () => {
    render(<AgentCard agent={mockAgents[0]} />);
    
    expect(screen.getByText(/WRAP:/)).toBeInTheDocument();
  });

  it('shows test count for completed agents', () => {
    render(<AgentCard agent={mockAgents[0]} />);
    
    expect(screen.getByText('54 tests passed')).toBeInTheDocument();
  });

  it('shows error message for failed agents', () => {
    render(<AgentCard agent={mockAgents[3]} />);
    
    expect(screen.getByText(/Connection timeout/)).toBeInTheDocument();
  });

  it('applies active styling when isActive', () => {
    const { container } = render(<AgentCard agent={mockAgents[1]} isActive={true} />);
    
    const card = container.querySelector('.agent-card.active');
    expect(card).toBeInTheDocument();
  });

  it('displays correct status icon', () => {
    render(<AgentCard agent={mockAgents[0]} />);
    expect(screen.getByText('✓')).toBeInTheDocument();
    
    render(<AgentCard agent={mockAgents[1]} />);
    expect(screen.getByText('⏳')).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: CheckpointMarker Component
// ═══════════════════════════════════════════════════════════════════════════════

describe('CheckpointMarker', () => {
  it('renders checkpoint information', () => {
    render(<CheckpointMarker checkpoint={mockCheckpoints[0]} />);
    
    expect(screen.getByText('PAC RECEIVED')).toBeInTheDocument();
    expect(screen.getByText('PAC-028 validated')).toBeInTheDocument();
  });

  it('displays checkpoint icon', () => {
    render(<CheckpointMarker checkpoint={mockCheckpoints[0]} />);
    
    expect(screen.getByText('🟦')).toBeInTheDocument();
  });

  it('shows hash reference when available', () => {
    render(<CheckpointMarker checkpoint={mockCheckpoints[4]} />);
    
    expect(screen.getByText(/sha256:/)).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = jest.fn();
    render(<CheckpointMarker checkpoint={mockCheckpoints[0]} onClick={onClick} />);
    
    fireEvent.click(screen.getByTestId('checkpoint-CP-001'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('formats timestamp correctly', () => {
    render(<CheckpointMarker checkpoint={mockCheckpoints[0]} />);
    
    // Should show formatted time
    expect(screen.getByText(/10:00:00/)).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: GIETimeline Component
// ═══════════════════════════════════════════════════════════════════════════════

describe('GIETimeline', () => {
  it('renders timeline with PAC ID', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
      />
    );
    
    expect(screen.getByText('PAC-028')).toBeInTheDocument();
    expect(screen.getByText('GIE Execution Timeline')).toBeInTheDocument();
  });

  it('displays all agents', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
      />
    );
    
    expect(screen.getByTestId('agent-card-GID-01')).toBeInTheDocument();
    expect(screen.getByTestId('agent-card-GID-02')).toBeInTheDocument();
    expect(screen.getByTestId('agent-card-GID-03')).toBeInTheDocument();
    expect(screen.getByTestId('agent-card-GID-07')).toBeInTheDocument();
  });

  it('displays all checkpoints', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
      />
    );
    
    expect(screen.getByTestId('checkpoint-CP-001')).toBeInTheDocument();
    expect(screen.getByTestId('checkpoint-CP-002')).toBeInTheDocument();
  });

  it('shows correct agent count', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
      />
    );
    
    expect(screen.getByText('Agents (4)')).toBeInTheDocument();
  });

  it('shows correct checkpoint count', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
      />
    );
    
    expect(screen.getByText('Checkpoints (5)')).toBeInTheDocument();
  });

  it('shows phase badge', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
        phase="EXECUTING"
      />
    );
    
    expect(screen.getByTestId('phase-badge')).toHaveTextContent('EXECUTING');
  });

  it('shows COMPLETE phase with green styling', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
        phase="COMPLETE"
      />
    );
    
    const badge = screen.getByTestId('phase-badge');
    expect(badge).toHaveTextContent('COMPLETE');
  });

  it('calculates progress correctly', () => {
    // 2 of 4 agents completed (COMPLETED + FAILED)
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
      />
    );
    
    expect(screen.getByText('2/4 agents')).toBeInTheDocument();
  });

  it('shows read-only indicator by default', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
      />
    );
    
    expect(screen.getByText(/Read-only view/)).toBeInTheDocument();
  });

  it('respects maxVisible limit', () => {
    const manyCheckpoints: Checkpoint[] = Array.from({ length: 100 }, (_, i) => ({
      id: `CP-${i}`,
      type: 'CHECKPOINT_REACHED' as CheckpointType,
      message: `Checkpoint ${i}`,
      timestamp: new Date().toISOString(),
    }));
    
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={manyCheckpoints}
        maxVisible={10}
      />
    );
    
    expect(screen.getByText(/Showing last 10 of 100 checkpoints/)).toBeInTheDocument();
  });

  it('shows empty state when no checkpoints', () => {
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={[]}
      />
    );
    
    expect(screen.getByText('Awaiting checkpoints...')).toBeInTheDocument();
  });

  it('calls onCheckpointClick when checkpoint clicked in non-readonly mode', () => {
    const onClick = jest.fn();
    
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
        readOnly={false}
        onCheckpointClick={onClick}
      />
    );
    
    fireEvent.click(screen.getByTestId('checkpoint-CP-001'));
    expect(onClick).toHaveBeenCalledWith(mockCheckpoints[0]);
  });

  it('does not call onCheckpointClick in readonly mode', () => {
    const onClick = jest.fn();
    
    render(
      <GIETimeline
        pacId="PAC-028"
        agents={mockAgents}
        checkpoints={mockCheckpoints}
        readOnly={true}
        onCheckpointClick={onClick}
      />
    );
    
    fireEvent.click(screen.getByTestId('checkpoint-CP-001'));
    expect(onClick).not.toHaveBeenCalled();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: Agent Status States
// ═══════════════════════════════════════════════════════════════════════════════

describe('GIETimeline Agent Status', () => {
  const statusCases: AgentStatus[] = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED'];
  
  statusCases.forEach(status => {
    it(`correctly displays ${status} status`, () => {
      const agent: AgentState = {
        gid: 'GID-TEST',
        name: 'Test',
        role: 'Test Role',
        status,
      };
      
      render(
        <GIETimeline
          pacId="PAC-TEST"
          agents={[agent]}
          checkpoints={[]}
        />
      );
      
      expect(screen.getByTestId('agent-card-GID-TEST')).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: Checkpoint Types
// ═══════════════════════════════════════════════════════════════════════════════

describe('GIETimeline Checkpoint Types', () => {
  const checkpointTypes: CheckpointType[] = [
    'PAC_RECEIVED',
    'AGENTS_DISPATCHED',
    'AGENT_STARTED',
    'AGENT_COMPLETED',
    'WRAP_HASH_RECEIVED',
    'ALL_WRAPS_RECEIVED',
    'BER_ISSUED',
    'PDO_EMITTED',
    'ERROR_SIGNAL',
  ];
  
  checkpointTypes.forEach(type => {
    it(`renders ${type} checkpoint correctly`, () => {
      const checkpoint: Checkpoint = {
        id: `CP-${type}`,
        type,
        message: `Test ${type}`,
        timestamp: new Date().toISOString(),
      };
      
      render(
        <GIETimeline
          pacId="PAC-TEST"
          agents={[]}
          checkpoints={[checkpoint]}
        />
      );
      
      expect(screen.getByTestId(`checkpoint-CP-${type}`)).toBeInTheDocument();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: Progress Calculation
// ═══════════════════════════════════════════════════════════════════════════════

describe('Progress Calculation', () => {
  it('shows 0% with all pending agents', () => {
    const agents: AgentState[] = [
      { gid: 'A', name: 'A', role: 'R', status: 'PENDING' },
      { gid: 'B', name: 'B', role: 'R', status: 'PENDING' },
    ];
    
    render(
      <GIETimeline
        pacId="PAC-TEST"
        agents={agents}
        checkpoints={[]}
      />
    );
    
    expect(screen.getByText('0/2 agents')).toBeInTheDocument();
  });

  it('shows 100% with all completed agents', () => {
    const agents: AgentState[] = [
      { gid: 'A', name: 'A', role: 'R', status: 'COMPLETED' },
      { gid: 'B', name: 'B', role: 'R', status: 'COMPLETED' },
    ];
    
    render(
      <GIETimeline
        pacId="PAC-TEST"
        agents={agents}
        checkpoints={[]}
      />
    );
    
    expect(screen.getByText('2/2 agents')).toBeInTheDocument();
  });

  it('counts FAILED as completed for progress', () => {
    const agents: AgentState[] = [
      { gid: 'A', name: 'A', role: 'R', status: 'COMPLETED' },
      { gid: 'B', name: 'B', role: 'R', status: 'FAILED' },
    ];
    
    render(
      <GIETimeline
        pacId="PAC-TEST"
        agents={agents}
        checkpoints={[]}
      />
    );
    
    expect(screen.getByText('2/2 agents')).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST: Edge Cases
// ═══════════════════════════════════════════════════════════════════════════════

describe('Edge Cases', () => {
  it('handles empty agents array', () => {
    render(
      <GIETimeline
        pacId="PAC-TEST"
        agents={[]}
        checkpoints={mockCheckpoints}
      />
    );
    
    expect(screen.getByText('Agents (0)')).toBeInTheDocument();
  });

  it('handles custom className', () => {
    const { container } = render(
      <GIETimeline
        pacId="PAC-TEST"
        agents={[]}
        checkpoints={[]}
        className="custom-class"
      />
    );
    
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('truncates long hash values', () => {
    const checkpoint: Checkpoint = {
      id: 'CP-LONG',
      type: 'WRAP_HASH_RECEIVED',
      message: 'Long hash',
      timestamp: new Date().toISOString(),
      hashRef: 'sha256:abcdefghijklmnopqrstuvwxyz1234567890',
    };
    
    render(
      <GIETimeline
        pacId="PAC-TEST"
        agents={[]}
        checkpoints={[checkpoint]}
      />
    );
    
    // Hash should be truncated
    const hashElement = screen.getByText(/sha256:.*\.\.\./);
    expect(hashElement).toBeInTheDocument();
  });
});
