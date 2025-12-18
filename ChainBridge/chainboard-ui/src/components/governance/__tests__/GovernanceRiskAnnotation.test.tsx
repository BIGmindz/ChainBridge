/**
 * Governance Risk Annotation Tests — PAC-SONNY-03
 *
 * Tests verify:
 * - No interactivity exists
 * - Governance decision renders unchanged when risk added
 * - Risk annotation never renders alone
 * - Malformed risk data → safe failure
 * - Risk shown as informational only
 * - Explicit empty/unavailable states
 *
 * @see PAC-SONNY-03 — Risk Annotation (Read-Only)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GovernanceRiskBadge, GovernanceRiskDisclaimer } from '../GovernanceRiskBadge';
import { GovernanceRiskEmptyState } from '../GovernanceRiskEmptyState';
import { GovernanceEventRow } from '../GovernanceEventRow';
import type { GovernanceEvent, RiskAnnotation } from '../../../types/governance';

// Test fixtures
const createEvent = (overrides: Partial<GovernanceEvent> = {}): GovernanceEvent => ({
  event_id: 'evt-001',
  timestamp: '2025-12-17T10:00:00Z',
  event_type: 'INTENT_EVALUATED',
  agent_gid: 'GID-03',
  metadata: {},
  ...overrides,
});

const validRiskAnnotation: RiskAnnotation = {
  category: 'COUNTERPARTY_RISK',
  rationale: 'Elevated exposure to high-risk corridor',
  confidence_interval: '0.85-0.92',
  source: 'ChainIQ-v2',
  assessed_at: '2025-12-17T09:59:00Z',
};

describe('GovernanceRiskBadge', () => {
  it('renders category verbatim', () => {
    render(<GovernanceRiskBadge category="SETTLEMENT_RISK" />);

    expect(screen.getByText('SETTLEMENT_RISK')).toBeInTheDocument();
    expect(screen.getByText('RISK SIGNAL')).toBeInTheDocument();
  });

  it('is not interactive — no button role', () => {
    const { container } = render(<GovernanceRiskBadge category="TEST" />);

    const buttons = container.querySelectorAll('button, [role="button"]');
    expect(buttons).toHaveLength(0);
  });

  it('has informational aria-label', () => {
    render(<GovernanceRiskBadge category="FRAUD_SIGNAL" />);

    expect(screen.getByLabelText('Risk signal: FRAUD_SIGNAL')).toBeInTheDocument();
  });
});

describe('GovernanceRiskDisclaimer', () => {
  it('renders exact disclaimer text', () => {
    render(<GovernanceRiskDisclaimer />);

    expect(screen.getByText('Informational — does not affect decision')).toBeInTheDocument();
  });
});

describe('GovernanceRiskEmptyState', () => {
  it('renders "No risk annotation available" for none status', () => {
    render(<GovernanceRiskEmptyState status="none" />);

    expect(screen.getByText('No risk annotation available')).toBeInTheDocument();
  });

  it('renders "Risk engine unavailable" for unavailable status', () => {
    render(<GovernanceRiskEmptyState status="unavailable" />);

    expect(screen.getByText('Risk engine unavailable')).toBeInTheDocument();
  });

  it('returns null for present status', () => {
    const { container } = render(<GovernanceRiskEmptyState status="present" />);

    expect(container.firstChild).toBeNull();
  });

  it('does not contain any buttons or actions', () => {
    const { container } = render(<GovernanceRiskEmptyState status="none" />);

    const buttons = container.querySelectorAll('button, a, [role="button"]');
    expect(buttons).toHaveLength(0);
  });
});

describe('GovernanceEventRow with Risk Annotation', () => {
  describe('Governance Decision Unchanged', () => {
    it('renders governance decision when risk annotation present', () => {
      const event = createEvent({
        decision: 'DENY',
        reason_code: 'MISSING_AUTHORITY',
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      // Governance decision still renders
      expect(screen.getByText('DENY')).toBeInTheDocument();
      expect(screen.getByText('MISSING_AUTHORITY')).toBeInTheDocument();
    });

    it('governance decision styling unchanged by risk', () => {
      const event = createEvent({
        decision: 'DENY',
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      // DENY should still have its styling
      const decisionText = screen.getByText('DENY');
      expect(decisionText).toHaveClass('text-rose-400');
    });

    it('event type and timestamp unchanged by risk', () => {
      const event = createEvent({
        event_type: 'GOVERNANCE_CHECK',
        timestamp: '2025-12-17T15:30:00Z',
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('GOVERNANCE_CHECK')).toBeInTheDocument();
      expect(screen.getByText('2025-12-17T15:30:00Z')).toBeInTheDocument();
    });
  });

  describe('Risk Shown as Informational Only', () => {
    it('renders risk badge with category', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('RISK SIGNAL')).toBeInTheDocument();
      expect(screen.getByText('COUNTERPARTY_RISK')).toBeInTheDocument();
    });

    it('renders informational disclaimer', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('Informational — does not affect decision')).toBeInTheDocument();
    });

    it('renders risk rationale verbatim', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('Elevated exposure to high-risk corridor')).toBeInTheDocument();
    });

    it('renders confidence interval if present', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('0.85-0.92')).toBeInTheDocument();
    });

    it('renders source if present', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('ChainIQ-v2')).toBeInTheDocument();
    });
  });

  describe('Risk Annotation Never Renders Alone', () => {
    it('event always has governance fields even with risk', () => {
      const event = createEvent({
        event_type: 'POLICY_CHECK',
        agent_gid: 'GID-01',
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      // Governance fields present
      expect(screen.getByText('POLICY_CHECK')).toBeInTheDocument();
      expect(screen.getByText('GID-01')).toBeInTheDocument();

      // Risk is secondary
      expect(screen.getByText('RISK SIGNAL')).toBeInTheDocument();
    });
  });

  describe('Malformed Risk Data Handling', () => {
    it('shows unavailable state when status is present but annotation missing', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: undefined,
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('Risk engine unavailable')).toBeInTheDocument();
    });

    it('shows none state when status is none', () => {
      const event = createEvent({
        risk_annotation_status: 'none',
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('No risk annotation available')).toBeInTheDocument();
    });

    it('shows unavailable state when status is unavailable', () => {
      const event = createEvent({
        risk_annotation_status: 'unavailable',
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('Risk engine unavailable')).toBeInTheDocument();
    });

    it('defaults to none when no status provided', () => {
      const event = createEvent({
        // No risk_annotation_status
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.getByText('No risk annotation available')).toBeInTheDocument();
    });
  });

  describe('No Interactivity', () => {
    it('does not contain any buttons in risk section', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      const { container } = render(<GovernanceEventRow event={event} />);

      const buttons = container.querySelectorAll('button, [role="button"]');
      expect(buttons).toHaveLength(0);
    });

    it('does not contain any links in risk section', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      const { container } = render(<GovernanceEventRow event={event} />);

      const links = container.querySelectorAll('a');
      expect(links).toHaveLength(0);
    });

    it('does not contain any text inputs', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      const { container } = render(<GovernanceEventRow event={event} />);

      const inputs = container.querySelectorAll('input, textarea');
      expect(inputs).toHaveLength(0);
    });

    it('does not contain retry or action text', () => {
      const event = createEvent({
        risk_annotation_status: 'present',
        risk_annotation: validRiskAnnotation,
      });

      render(<GovernanceEventRow event={event} />);

      expect(screen.queryByText(/retry/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/override/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/dismiss/i)).not.toBeInTheDocument();
    });
  });
});
