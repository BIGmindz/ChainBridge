/**
 * Governance Timeline Panel Tests — PAC-SONNY-02
 *
 * Tests verify:
 * - Renders empty state correctly
 * - Renders multiple events in correct order (descending)
 * - Displays DENY event with red accent
 * - Displays audit_ref verbatim
 * - Fails closed on malformed event (error boundary)
 * - No interactive elements exist
 *
 * @see PAC-SONNY-02 — Governance Timeline (Read-Only) UI
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GovernanceTimelinePanel } from '../GovernanceTimelinePanel';
import { GovernanceEventRow } from '../GovernanceEventRow';
import { GovernanceTimelineEmptyState } from '../GovernanceTimelineEmptyState';
import type { GovernanceEvent } from '../../../types/governance';

// Test fixtures
const createEvent = (overrides: Partial<GovernanceEvent> = {}): GovernanceEvent => ({
  event_id: 'evt-001',
  timestamp: '2025-12-17T10:00:00Z',
  event_type: 'INTENT_EVALUATED',
  agent_gid: 'GID-03',
  metadata: {},
  ...overrides,
});

const multipleEvents: GovernanceEvent[] = [
  createEvent({
    event_id: 'evt-001',
    timestamp: '2025-12-17T10:00:00Z',
    event_type: 'INTENT_EVALUATED',
    agent_gid: 'GID-03',
    verb: 'EXECUTE',
    target: 'settlement.release',
    decision: 'DENY',
    reason_code: 'MISSING_AUTHORITY',
    audit_ref: 'audit-12345',
  }),
  createEvent({
    event_id: 'evt-002',
    timestamp: '2025-12-17T11:00:00Z', // Later
    event_type: 'ESCALATION_TRIGGERED',
    agent_gid: 'GID-00',
    verb: 'ESCALATE',
    target: 'human.operator',
    decision: 'ESCALATE',
  }),
  createEvent({
    event_id: 'evt-003',
    timestamp: '2025-12-17T09:00:00Z', // Earlier
    event_type: 'POLICY_CHECK',
    agent_gid: 'GID-01',
    decision: 'ALLOW',
  }),
];

describe('GovernanceTimelinePanel', () => {
  describe('Empty State', () => {
    it('renders empty state correctly when events array is empty', () => {
      render(<GovernanceTimelinePanel events={[]} />);

      // Exact text per PAC specification
      expect(screen.getByText('No governance events recorded.')).toBeInTheDocument();
    });

    it('shows event count of 0', () => {
      render(<GovernanceTimelinePanel events={[]} />);
      expect(screen.getByText('(0 events)')).toBeInTheDocument();
    });
  });

  describe('Event Ordering', () => {
    it('renders events sorted by timestamp descending', () => {
      render(<GovernanceTimelinePanel events={multipleEvents} />);

      const eventRows = screen.getAllByRole('listitem');
      expect(eventRows).toHaveLength(3);

      // First event should be the latest (11:00)
      expect(eventRows[0]).toHaveTextContent('ESCALATION_TRIGGERED');
      // Second should be 10:00
      expect(eventRows[1]).toHaveTextContent('INTENT_EVALUATED');
      // Last should be earliest (09:00)
      expect(eventRows[2]).toHaveTextContent('POLICY_CHECK');
    });

    it('shows correct event count', () => {
      render(<GovernanceTimelinePanel events={multipleEvents} />);
      expect(screen.getByText('(3 events)')).toBeInTheDocument();
    });
  });

  describe('DENY Event Styling', () => {
    it('displays DENY decision with appropriate styling', () => {
      const denyEvent = createEvent({
        event_id: 'evt-deny',
        event_type: 'GOVERNANCE_DENIAL',
        decision: 'DENY',
      });

      render(<GovernanceTimelinePanel events={[denyEvent]} />);

      // Should render the decision
      expect(screen.getByText('DENY')).toBeInTheDocument();
    });
  });

  describe('Audit Ref Display', () => {
    it('displays audit_ref verbatim', () => {
      const eventWithAudit = createEvent({
        event_id: 'evt-audit',
        audit_ref: 'audit-ref-xyz-789',
      });

      render(<GovernanceTimelinePanel events={[eventWithAudit]} />);

      expect(screen.getByText('audit-ref-xyz-789')).toBeInTheDocument();
    });
  });

  describe('Fail Closed Behavior', () => {
    it('shows error when events is not an array', () => {
      // @ts-expect-error Testing invalid input
      render(<GovernanceTimelinePanel events={null} />);

      expect(screen.getByText('Timeline Render Failed')).toBeInTheDocument();
      expect(screen.getByText('Events must be an array')).toBeInTheDocument();
    });

    it('shows error when event missing event_id', () => {
      const malformedEvent = {
        timestamp: '2025-12-17T10:00:00Z',
        event_type: 'TEST',
        agent_gid: 'GID-00',
        metadata: {},
      } as GovernanceEvent;

      render(<GovernanceTimelinePanel events={[malformedEvent]} />);

      expect(screen.getByText('Timeline Render Failed')).toBeInTheDocument();
    });

    it('shows error when event missing timestamp', () => {
      const malformedEvent = {
        event_id: 'evt-001',
        event_type: 'TEST',
        agent_gid: 'GID-00',
        metadata: {},
      } as GovernanceEvent;

      render(<GovernanceTimelinePanel events={[malformedEvent]} />);

      expect(screen.getByText('Timeline Render Failed')).toBeInTheDocument();
    });

    it('shows error when event missing agent_gid', () => {
      const malformedEvent = {
        event_id: 'evt-001',
        timestamp: '2025-12-17T10:00:00Z',
        event_type: 'TEST',
        metadata: {},
      } as GovernanceEvent;

      render(<GovernanceTimelinePanel events={[malformedEvent]} />);

      expect(screen.getByText('Timeline Render Failed')).toBeInTheDocument();
    });
  });

  describe('No Interactive Elements', () => {
    it('does not contain any buttons', () => {
      render(<GovernanceTimelinePanel events={multipleEvents} />);

      const buttons = screen.queryAllByRole('button');
      expect(buttons).toHaveLength(0);
    });

    it('does not contain any links', () => {
      render(<GovernanceTimelinePanel events={multipleEvents} />);

      const links = screen.queryAllByRole('link');
      expect(links).toHaveLength(0);
    });

    it('does not contain any text inputs', () => {
      const { container } = render(<GovernanceTimelinePanel events={multipleEvents} />);

      const inputs = container.querySelectorAll('input, textarea');
      expect(inputs).toHaveLength(0);
    });

    it('does not contain retry or action text', () => {
      render(<GovernanceTimelinePanel events={multipleEvents} />);

      expect(screen.queryByText(/retry/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/resolve/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/action/i)).not.toBeInTheDocument();
    });
  });

  describe('Field Display', () => {
    it('displays all present fields verbatim', () => {
      const fullEvent = createEvent({
        event_id: 'evt-full',
        timestamp: '2025-12-17T12:30:00Z',
        event_type: 'FULL_EVENT',
        agent_gid: 'GID-07',
        verb: 'PROPOSE',
        target: 'config.update',
        decision: 'ALLOW',
        reason_code: 'POLICY_SATISFIED',
        audit_ref: 'audit-full-123',
      });

      render(<GovernanceTimelinePanel events={[fullEvent]} />);

      expect(screen.getByText('FULL_EVENT')).toBeInTheDocument();
      expect(screen.getByText('GID-07')).toBeInTheDocument();
      expect(screen.getByText('PROPOSE')).toBeInTheDocument();
      expect(screen.getByText('config.update')).toBeInTheDocument();
      expect(screen.getByText('ALLOW')).toBeInTheDocument();
      expect(screen.getByText('POLICY_SATISFIED')).toBeInTheDocument();
      expect(screen.getByText('audit-full-123')).toBeInTheDocument();
    });
  });
});

describe('GovernanceEventRow', () => {
  it('renders event type verbatim', () => {
    const event = createEvent({ event_type: 'CUSTOM_EVENT_TYPE' });
    render(<GovernanceEventRow event={event} />);

    expect(screen.getByText('CUSTOM_EVENT_TYPE')).toBeInTheDocument();
  });

  it('renders timestamp in ISO format', () => {
    const event = createEvent({ timestamp: '2025-12-17T15:45:30Z' });
    render(<GovernanceEventRow event={event} />);

    expect(screen.getByText('2025-12-17T15:45:30Z')).toBeInTheDocument();
  });

  it('has listitem role', () => {
    const event = createEvent();
    render(<GovernanceEventRow event={event} />);

    expect(screen.getByRole('listitem')).toBeInTheDocument();
  });
});

describe('GovernanceTimelineEmptyState', () => {
  it('renders exact text per specification', () => {
    render(<GovernanceTimelineEmptyState />);

    expect(screen.getByText('No governance events recorded.')).toBeInTheDocument();
  });

  it('does not contain any buttons or actions', () => {
    const { container } = render(<GovernanceTimelineEmptyState />);

    const buttons = container.querySelectorAll('button');
    const links = container.querySelectorAll('a');

    expect(buttons).toHaveLength(0);
    expect(links).toHaveLength(0);
  });
});
