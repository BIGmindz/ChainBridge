/**
 * Governance Locked Banner Tests — PAC-DIGGI-05-FE
 *
 * Tests verify:
 * - All status types render correctly
 * - Messages displayed verbatim (no rewording)
 * - Read-only display (no actions)
 * - No retry buttons
 * - Proper accessibility attributes
 *
 * @see PAC-DIGGI-05-FE — Diggi Operator UX
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  GovernanceLockedBanner,
  GovernanceDenyBanner,
  GovernanceLockBanner,
  GovernanceProposeBanner,
} from '../GovernanceLockedBanner';

describe('GovernanceLockedBanner', () => {
  describe('Status Types', () => {
    it('renders DENIED status correctly', () => {
      render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Action was denied by governance"
        />
      );

      expect(screen.getByText('DENY')).toBeInTheDocument();
      expect(screen.getByText('Action was denied by governance')).toBeInTheDocument();
    });

    it('renders LOCKED status correctly', () => {
      render(
        <GovernanceLockedBanner
          status="LOCKED"
          message="This resource is governance locked"
        />
      );

      expect(screen.getByText('GOVERNANCE LOCKED')).toBeInTheDocument();
      expect(screen.getByText('This resource is governance locked')).toBeInTheDocument();
    });

    it('renders PROPOSED status correctly', () => {
      render(
        <GovernanceLockedBanner
          status="PROPOSED"
          message="Awaiting governance review"
        />
      );

      expect(screen.getByText('PROPOSE')).toBeInTheDocument();
      expect(screen.getByText('Awaiting governance review')).toBeInTheDocument();
    });

    it('renders INFO status correctly', () => {
      render(
        <GovernanceLockedBanner
          status="INFO"
          message="Informational notice from governance"
        />
      );

      expect(screen.getByText('INFO')).toBeInTheDocument();
      expect(screen.getByText('Informational notice from governance')).toBeInTheDocument();
    });
  });

  describe('Verbatim Display', () => {
    it('displays message verbatim without modification', () => {
      const exactMessage = 'Agent GID-03 lacks EXECUTE authority on production.settlement';

      render(
        <GovernanceLockedBanner
          status="DENIED"
          message={exactMessage}
        />
      );

      expect(screen.getByText(exactMessage)).toBeInTheDocument();
    });

    it('displays detail verbatim without modification', () => {
      const exactDetail = 'Policy ALEX-RULE-001 requires human approval for amounts > $10,000';

      render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
          detail={exactDetail}
        />
      );

      expect(screen.getByText(exactDetail)).toBeInTheDocument();
    });

    it('displays rule violated verbatim', () => {
      render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
          ruleViolated="ALEX-RULE-042"
        />
      );

      expect(screen.getByText('ALEX-RULE-042')).toBeInTheDocument();
    });
  });

  describe('Read-Only Behavior', () => {
    it('does not contain any buttons', () => {
      const { container } = render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
        />
      );

      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBe(0);
    });

    it('does not contain any text inputs', () => {
      const { container } = render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
        />
      );

      const inputs = container.querySelectorAll('input, textarea');
      expect(inputs.length).toBe(0);
    });

    it('does not contain retry text', () => {
      render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
        />
      );

      expect(screen.queryByText(/retry/i)).not.toBeInTheDocument();
    });
  });

  describe('Metadata Display', () => {
    it('displays agent GID when provided', () => {
      render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
          agentGid="GID-03"
        />
      );

      expect(screen.getByText(/Agent: GID-03/)).toBeInTheDocument();
    });

    it('displays timestamp when provided', () => {
      render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
          timestamp="2025-12-17T10:30:00Z"
        />
      );

      expect(screen.getByText(/Time: 2025-12-17T10:30:00Z/)).toBeInTheDocument();
    });

    it('displays correlation ID when provided', () => {
      render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
          correlationId="corr-12345-abc"
        />
      );

      expect(screen.getByText('corr-12345-abc')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has alert role', () => {
      render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
        />
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('has aria-live polite', () => {
      const { container } = render(
        <GovernanceLockedBanner
          status="DENIED"
          message="Denied"
        />
      );

      const banner = container.querySelector('[aria-live="polite"]');
      expect(banner).toBeInTheDocument();
    });
  });

  describe('Shorthand Components', () => {
    it('GovernanceDenyBanner renders DENIED status', () => {
      render(<GovernanceDenyBanner message="Denied by policy" />);
      expect(screen.getByText('DENY')).toBeInTheDocument();
    });

    it('GovernanceLockBanner renders LOCKED status', () => {
      render(<GovernanceLockBanner message="Locked by governance" />);
      expect(screen.getByText('GOVERNANCE LOCKED')).toBeInTheDocument();
    });

    it('GovernanceProposeBanner renders PROPOSED status', () => {
      render(<GovernanceProposeBanner message="Proposal pending" />);
      expect(screen.getByText('PROPOSE')).toBeInTheDocument();
    });
  });
});
