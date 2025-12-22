/**
 * Diggi Correction Panel Tests — PAC-DIGGI-05-FE
 *
 * Tests verify:
 * - Steps are read-only
 * - Human ACK required before step interaction
 * - Button labels match backend schema exactly
 * - Fail closed on missing data
 * - No retry buttons
 * - No free-text inputs
 *
 * @see PAC-DIGGI-05-FE — Diggi Operator UX
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DiggiCorrectionPanel } from '../DiggiCorrectionPanel';
import type { DiggiCorrectionPlan } from '../../../types/diggi';

// Valid test correction plan
const validCorrectionPlan: DiggiCorrectionPlan = {
  cause: 'MISSING_AUTHORITY',
  constraints: ['Agent lacks EXECUTE permission', 'Production scope not allowed'],
  allowed_next_steps: [
    {
      verb: 'ESCALATE',
      target: 'human.operator',
      description: 'Request human approval for this action',
    },
    {
      verb: 'PROPOSE',
      target_scope: 'staging',
      description: 'Propose action in staging environment',
    },
    {
      verb: 'READ',
      description: 'View related governance policies',
    },
  ],
};

describe('DiggiCorrectionPanel', () => {
  describe('Read-Only Behavior', () => {
    it('renders all correction steps as read-only', () => {
      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
        />
      );

      // All steps should be visible
      expect(screen.getByText('Request human approval for this action')).toBeInTheDocument();
      expect(screen.getByText('Propose action in staging environment')).toBeInTheDocument();
      expect(screen.getByText('View related governance policies')).toBeInTheDocument();

      // READ-ONLY badge should be visible
      expect(screen.getByText('READ-ONLY')).toBeInTheDocument();
    });

    it('labels steps as "Proposed by Diggi"', () => {
      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
        />
      );

      // "Proposed by Diggi" labels should appear
      const diggiLabels = screen.getAllByText('Proposed by Diggi');
      expect(diggiLabels.length).toBeGreaterThan(0);
    });

    it('does not contain any text input fields', () => {
      const { container } = render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
        />
      );

      // No text inputs should exist
      const textInputs = container.querySelectorAll('input[type="text"], textarea');
      expect(textInputs.length).toBe(0);
    });

    it('does not contain any retry buttons', () => {
      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
        />
      );

      // No retry button should exist
      expect(screen.queryByText(/retry/i)).not.toBeInTheDocument();
    });
  });

  describe('Human Acknowledgement', () => {
    it('disables steps when human ACK is required but not given', () => {
      const onStepSelect = vi.fn();

      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={true}
          onStepSelect={onStepSelect}
        />
      );

      // ACK warning should be visible
      expect(screen.getByText(/Human acknowledgement required/)).toBeInTheDocument();

      // ACK button should be visible with exact text
      expect(screen.getByText('ACKNOWLEDGE GOVERNANCE DECISION')).toBeInTheDocument();

      // Try clicking a step — should not fire callback (steps disabled)
      const stepButton = screen.getByText('Request human approval for this action');
      fireEvent.click(stepButton);
      expect(onStepSelect).not.toHaveBeenCalled();
    });

    it('enables steps after human ACK', () => {
      const onStepSelect = vi.fn();
      const onAcknowledge = vi.fn();

      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={true}
          onStepSelect={onStepSelect}
          onAcknowledge={onAcknowledge}
        />
      );

      // Click ACK button
      const ackButton = screen.getByText('ACKNOWLEDGE GOVERNANCE DECISION');
      fireEvent.click(ackButton);

      expect(onAcknowledge).toHaveBeenCalledTimes(1);

      // ACK confirmation should appear
      expect(screen.getByText('Governance decision acknowledged')).toBeInTheDocument();

      // Now clicking a step should work
      const stepButton = screen.getByText('Request human approval for this action');
      fireEvent.click(stepButton);
      expect(onStepSelect).toHaveBeenCalledTimes(1);
    });

    it('button text matches backend schema exactly', () => {
      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={true}
        />
      );

      // Exact button text — no alternative wording
      const ackButton = screen.getByRole('button', { name: 'ACKNOWLEDGE GOVERNANCE DECISION' });
      expect(ackButton).toBeInTheDocument();
    });

    it('does not require ACK when requiresHumanAck is false', () => {
      const onStepSelect = vi.fn();

      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
          onStepSelect={onStepSelect}
        />
      );

      // No ACK warning
      expect(screen.queryByText(/Human acknowledgement required/)).not.toBeInTheDocument();

      // Steps should be interactive
      const stepButton = screen.getByText('Request human approval for this action');
      fireEvent.click(stepButton);
      expect(onStepSelect).toHaveBeenCalledTimes(1);
    });
  });

  describe('Fail Closed Behavior', () => {
    it('renders error state when correction plan is null', () => {
      render(
        <DiggiCorrectionPanel
          correctionPlan={null as unknown as DiggiCorrectionPlan}
          requiresHumanAck={false}
        />
      );

      expect(screen.getByText(/Correction plan data missing/)).toBeInTheDocument();
    });

    it('renders error state when correction plan is undefined', () => {
      render(
        <DiggiCorrectionPanel
          correctionPlan={undefined as unknown as DiggiCorrectionPlan}
          requiresHumanAck={false}
        />
      );

      expect(screen.getByText(/Correction plan data missing/)).toBeInTheDocument();
    });

    it('renders message when no correction steps available', () => {
      const emptyCorrectionPlan: DiggiCorrectionPlan = {
        cause: 'UNKNOWN',
        constraints: [],
        allowed_next_steps: [],
      };

      render(
        <DiggiCorrectionPanel
          correctionPlan={emptyCorrectionPlan}
          requiresHumanAck={false}
        />
      );

      expect(screen.getByText(/No correction steps available/)).toBeInTheDocument();
    });
  });

  describe('Audit Trail', () => {
    it('displays correlation ID when provided', () => {
      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
          correlationId="audit-12345"
        />
      );

      expect(screen.getByText('audit-12345')).toBeInTheDocument();
    });

    it('displays cause from backend verbatim', () => {
      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
        />
      );

      expect(screen.getByText('MISSING_AUTHORITY')).toBeInTheDocument();
    });
  });

  describe('Step Selection', () => {
    it('fires onStepSelect with correct step data', () => {
      const onStepSelect = vi.fn();

      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
          onStepSelect={onStepSelect}
        />
      );

      // Click the ESCALATE step
      fireEvent.click(screen.getByText('Request human approval for this action'));

      expect(onStepSelect).toHaveBeenCalledWith({
        verb: 'ESCALATE',
        target: 'human.operator',
        description: 'Request human approval for this action',
      });
    });

    it('supports keyboard navigation', () => {
      const onStepSelect = vi.fn();

      render(
        <DiggiCorrectionPanel
          correctionPlan={validCorrectionPlan}
          requiresHumanAck={false}
          onStepSelect={onStepSelect}
        />
      );

      // Find step and trigger Enter key
      const stepElement = screen.getByText('Request human approval for this action').closest('li');
      if (stepElement) {
        fireEvent.keyDown(stepElement, { key: 'Enter' });
        expect(onStepSelect).toHaveBeenCalledTimes(1);
      }
    });
  });
});
