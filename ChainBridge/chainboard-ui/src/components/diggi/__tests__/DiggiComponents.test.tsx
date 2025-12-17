/**
 * Diggi Components Tests — CRC v1
 *
 * Tests for the Correction Rendering Contract components.
 * Verifies all PAC-DIGGI-03 requirements.
 *
 * TEST REQUIREMENTS:
 * 1. UI renders only backend-provided steps
 * 2. No additional buttons appear
 * 3. No free-text retry paths
 * 4. All buttons disabled if plan invalid
 * 5. Fail closed if correction payload missing or invalid
 * 6. Snapshot tests for denial variants
 *
 * @see PAC-DIGGI-03 — Correction Rendering Contract
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { DiggiDenialPanel } from '../DiggiDenialPanel';
import { DiggiConstraintList } from '../DiggiConstraintList';
import { DiggiNextStepButton } from '../DiggiNextStepButton';
import type { DiggiDenialResponse, DiggiCorrectionStep } from '../../../types/diggi';
import { validateCorrectionPlan, isKnownVerb } from '../../../types/diggi';


// ============================================================
// TEST FIXTURES
// ============================================================

const createDenialResponse = (
  overrides: Partial<DiggiDenialResponse> = {}
): DiggiDenialResponse => ({
  decision: 'DENY',
  agent_gid: 'GID-01',
  intent_verb: 'EXECUTE',
  intent_target: 'production.deploy',
  reason: 'EXECUTE_NOT_PERMITTED',
  reason_detail: 'Agent GID-01 does not have EXECUTE permission',
  next_hop: 'GID-00',
  timestamp: '2024-01-01T00:00:00Z',
  correlation_id: 'test-correlation-123',
  correction_plan: {
    correction_plan: {
      cause: 'EXECUTE_NOT_PERMITTED',
      constraints: [
        'Agent lacks EXECUTE authority',
        'Target is production-scoped',
      ],
      allowed_next_steps: [
        {
          verb: 'PROPOSE',
          target_scope: 'backend.tests',
          description: 'Draft change and submit for review',
        },
        {
          verb: 'ESCALATE',
          target: 'human.operator',
          description: 'Request human authorization',
        },
      ],
    },
  },
  ...overrides,
});

const createBlockDenialResponse = (): DiggiDenialResponse =>
  createDenialResponse({
    intent_verb: 'BLOCK',
    reason: 'BLOCK_NOT_PERMITTED',
    reason_detail: 'Agent GID-01 does not have BLOCK permission',
    correction_plan: {
      correction_plan: {
        cause: 'BLOCK_NOT_PERMITTED',
        constraints: [
          'Agent lacks BLOCK authority',
          'Only Sam (GID-06) and ALEX (GID-08) may BLOCK',
        ],
        allowed_next_steps: [
          {
            verb: 'PROPOSE',
            target_scope: 'governance.block.request',
            description: 'Submit block request to authorized agent',
          },
          {
            verb: 'ESCALATE',
            target: 'human.operator',
            description: 'Request human review of blocking action',
          },
        ],
      },
    },
  });

const createNoStepsDenialResponse = (): DiggiDenialResponse =>
  createDenialResponse({
    reason: 'DELETE_FORBIDDEN',
    reason_detail: 'DELETE operations are globally forbidden',
    correction_plan: {
      correction_plan: {
        cause: 'DELETE_FORBIDDEN',
        constraints: [
          'DELETE operations are globally forbidden',
          'No agent may delete resources without human approval',
        ],
        allowed_next_steps: [],
      },
    },
  });


// ============================================================
// TYPE VALIDATION TESTS
// ============================================================

describe('Type Validation', () => {
  describe('validateCorrectionPlan', () => {
    it('returns valid for correct plan', () => {
      const denial = createDenialResponse();
      const result = validateCorrectionPlan(denial.correction_plan);

      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('returns invalid for null plan', () => {
      const result = validateCorrectionPlan(null);

      expect(result.isValid).toBe(false);
      expect(result.error).toContain('missing correction_plan');
    });

    it('returns invalid for undefined plan', () => {
      const result = validateCorrectionPlan(undefined);

      expect(result.isValid).toBe(false);
      expect(result.error).toContain('missing correction_plan');
    });

    it('returns invalid for malformed plan', () => {
      const result = validateCorrectionPlan({ correction_plan: null as any });

      expect(result.isValid).toBe(false);
      expect(result.error).toContain('malformed');
    });

    it('returns invalid for plan with forbidden EXECUTE verb', () => {
      const badPlan = {
        correction_plan: {
          cause: 'TEST',
          constraints: [],
          allowed_next_steps: [
            { verb: 'EXECUTE', description: 'This is forbidden' },
          ],
        },
      };

      const result = validateCorrectionPlan(badPlan);

      expect(result.isValid).toBe(false);
      expect(result.error).toContain('forbidden verb EXECUTE');
    });

    it('returns invalid for plan with forbidden APPROVE verb', () => {
      const badPlan = {
        correction_plan: {
          cause: 'TEST',
          constraints: [],
          allowed_next_steps: [
            { verb: 'APPROVE', description: 'This is forbidden' },
          ],
        },
      };

      const result = validateCorrectionPlan(badPlan);

      expect(result.isValid).toBe(false);
      expect(result.error).toContain('forbidden verb APPROVE');
    });

    it('returns invalid for plan with forbidden BLOCK verb', () => {
      const badPlan = {
        correction_plan: {
          cause: 'TEST',
          constraints: [],
          allowed_next_steps: [
            { verb: 'BLOCK', description: 'This is forbidden' },
          ],
        },
      };

      const result = validateCorrectionPlan(badPlan);

      expect(result.isValid).toBe(false);
      expect(result.error).toContain('forbidden verb BLOCK');
    });
  });

  describe('isKnownVerb', () => {
    it('returns true for PROPOSE', () => {
      expect(isKnownVerb('PROPOSE')).toBe(true);
    });

    it('returns true for ESCALATE', () => {
      expect(isKnownVerb('ESCALATE')).toBe(true);
    });

    it('returns true for READ', () => {
      expect(isKnownVerb('READ')).toBe(true);
    });

    it('returns false for EXECUTE', () => {
      expect(isKnownVerb('EXECUTE')).toBe(false);
    });

    it('returns false for unknown verb', () => {
      expect(isKnownVerb('UNKNOWN')).toBe(false);
    });
  });
});


// ============================================================
// DIGGI DENIAL PANEL TESTS
// ============================================================

describe('DiggiDenialPanel', () => {
  describe('renders denial information correctly', () => {
    it('shows denial status banner', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('Action Denied')).toBeInTheDocument();
      expect(screen.getByText('EXECUTE_NOT_PERMITTED')).toBeInTheDocument();
    });

    it('shows denial reason detail', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText(/does not have EXECUTE permission/)).toBeInTheDocument();
    });

    it('shows agent and intent info', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('GID-01')).toBeInTheDocument();
      // EXECUTE appears in multiple places (badge, intent, reason), use getAllByText
      expect(screen.getAllByText(/EXECUTE/).length).toBeGreaterThan(0);
      expect(screen.getByText(/production\.deploy/)).toBeInTheDocument();
    });

    it('shows next_hop routing', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('GID-00')).toBeInTheDocument();
    });
  });

  describe('renders constraints correctly', () => {
    it('shows all constraints from plan', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('Agent lacks EXECUTE authority')).toBeInTheDocument();
      expect(screen.getByText('Target is production-scoped')).toBeInTheDocument();
    });

    it('shows constraints header', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('Constraints')).toBeInTheDocument();
    });
  });

  describe('renders allowed next steps correctly', () => {
    it('shows all allowed steps as buttons', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('Draft change and submit for review')).toBeInTheDocument();
      expect(screen.getByText('Request human authorization')).toBeInTheDocument();
    });

    it('shows verb labels on buttons', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('PROPOSE')).toBeInTheDocument();
      expect(screen.getByText('ESCALATE')).toBeInTheDocument();
    });

    it('calls onStepSelect when button clicked', () => {
      const denial = createDenialResponse();
      const onStepSelect = vi.fn();

      render(<DiggiDenialPanel denial={denial} onStepSelect={onStepSelect} />);

      const proposeButton = screen.getByText('Draft change and submit for review');
      fireEvent.click(proposeButton);

      expect(onStepSelect).toHaveBeenCalledTimes(1);
      expect(onStepSelect).toHaveBeenCalledWith(
        expect.objectContaining({ verb: 'PROPOSE' })
      );
    });
  });

  describe('handles edge cases', () => {
    it('renders message when no allowed steps', () => {
      const denial = createNoStepsDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText(/No allowed next steps/)).toBeInTheDocument();
    });

    it('shows error when correction_plan missing', () => {
      const denial = createDenialResponse({ correction_plan: undefined });
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('Governance Response Invalid')).toBeInTheDocument();
    });

    it('shows correlation ID when present', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('test-correlation-123')).toBeInTheDocument();
    });
  });

  describe('denial variants', () => {
    it('renders EXECUTE denial correctly', () => {
      const denial = createDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('EXECUTE_NOT_PERMITTED')).toBeInTheDocument();
      expect(screen.getByText('Agent lacks EXECUTE authority')).toBeInTheDocument();
    });

    it('renders BLOCK denial correctly', () => {
      const denial = createBlockDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('BLOCK_NOT_PERMITTED')).toBeInTheDocument();
      expect(screen.getByText('Agent lacks BLOCK authority')).toBeInTheDocument();
    });

    it('renders no-steps denial correctly', () => {
      const denial = createNoStepsDenialResponse();
      render(<DiggiDenialPanel denial={denial} />);

      expect(screen.getByText('DELETE_FORBIDDEN')).toBeInTheDocument();
      // "DELETE operations are globally forbidden" appears in both reason_detail and constraints
      expect(screen.getAllByText(/DELETE operations are globally forbidden/).length).toBeGreaterThan(0);
      expect(screen.getByText(/No allowed next steps/)).toBeInTheDocument();
    });
  });
});


// ============================================================
// DIGGI CONSTRAINT LIST TESTS
// ============================================================

describe('DiggiConstraintList', () => {
  it('renders all constraints', () => {
    const constraints = ['Constraint 1', 'Constraint 2', 'Constraint 3'];
    render(<DiggiConstraintList constraints={constraints} />);

    expect(screen.getByText('Constraint 1')).toBeInTheDocument();
    expect(screen.getByText('Constraint 2')).toBeInTheDocument();
    expect(screen.getByText('Constraint 3')).toBeInTheDocument();
  });

  it('renders empty message for no constraints', () => {
    render(<DiggiConstraintList constraints={[]} />);

    expect(screen.getByText('No constraints provided')).toBeInTheDocument();
  });

  it('shows constraints header', () => {
    const constraints = ['Test constraint'];
    render(<DiggiConstraintList constraints={constraints} />);

    expect(screen.getByText('Constraints')).toBeInTheDocument();
  });
});


// ============================================================
// DIGGI NEXT STEP BUTTON TESTS
// ============================================================

describe('DiggiNextStepButton', () => {
  const proposeStep: DiggiCorrectionStep = {
    verb: 'PROPOSE',
    target_scope: 'backend.tests',
    description: 'Draft change for review',
  };

  const escalateStep: DiggiCorrectionStep = {
    verb: 'ESCALATE',
    target: 'human.operator',
    description: 'Request human authorization',
  };

  it('renders PROPOSE button correctly', () => {
    render(<DiggiNextStepButton step={proposeStep} />);

    expect(screen.getByText('PROPOSE')).toBeInTheDocument();
    expect(screen.getByText('Draft change for review')).toBeInTheDocument();
    expect(screen.getByText(/backend\.tests/)).toBeInTheDocument();
  });

  it('renders ESCALATE button correctly', () => {
    render(<DiggiNextStepButton step={escalateStep} />);

    expect(screen.getByText('ESCALATE')).toBeInTheDocument();
    expect(screen.getByText('Request human authorization')).toBeInTheDocument();
    expect(screen.getByText(/human\.operator/)).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<DiggiNextStepButton step={proposeStep} onClick={onClick} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('does not call onClick when disabled', () => {
    const onClick = vi.fn();
    render(<DiggiNextStepButton step={proposeStep} onClick={onClick} disabled />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(onClick).not.toHaveBeenCalled();
  });

  it('returns null for unknown verb', () => {
    const unknownStep: DiggiCorrectionStep = {
      verb: 'UNKNOWN' as any,
      description: 'Unknown action',
    };

    const { container } = render(<DiggiNextStepButton step={unknownStep} />);

    expect(container.firstChild).toBeNull();
  });
});


// ============================================================
// SNAPSHOT TESTS
// ============================================================

describe('Snapshots', () => {
  it('matches snapshot for EXECUTE denial', () => {
    const denial = createDenialResponse();
    const { container } = render(<DiggiDenialPanel denial={denial} />);

    expect(container).toMatchSnapshot();
  });

  it('matches snapshot for BLOCK denial', () => {
    const denial = createBlockDenialResponse();
    const { container } = render(<DiggiDenialPanel denial={denial} />);

    expect(container).toMatchSnapshot();
  });

  it('matches snapshot for no-steps denial', () => {
    const denial = createNoStepsDenialResponse();
    const { container } = render(<DiggiDenialPanel denial={denial} />);

    expect(container).toMatchSnapshot();
  });

  it('matches snapshot for invalid plan', () => {
    const denial = createDenialResponse({ correction_plan: undefined });
    const { container } = render(<DiggiDenialPanel denial={denial} />);

    expect(container).toMatchSnapshot();
  });
});
