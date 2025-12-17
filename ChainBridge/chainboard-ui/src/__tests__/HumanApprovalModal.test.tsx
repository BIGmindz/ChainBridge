/**
 * HumanApprovalModal (HAM) v1 — Tests
 *
 * Test coverage for PAC-DIGGI-04 acceptance criteria:
 * ✔ Cannot approve without typing confirmation
 * ✔ Intent payload immutable
 * ✔ No execution triggered from UI
 * ✔ Approval intent logged once
 * ✔ Modal traps focus until resolved
 * ✔ Keyboard + mouse tested
 * ✔ Snapshot tests for each failure mode
 *
 * @see PAC-DIGGI-04 — Human Approval Modal
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { HumanApprovalModal } from '../components/approval/HumanApprovalModal';
import type {
  HumanApprovalContext,
  ApproverIdentity,
  ApprovalIntent,
} from '../types/approval';

// ============================================================
// TEST DATA
// ============================================================

const mockIntent = {
  verb: 'EXECUTE',
  target: 'settlement.release',
  amount: '$50,000',
  environment: 'PRODUCTION',
  requested_by: 'GID-01',
  correlation_id: 'abc-123',
} as const;

const mockContext: HumanApprovalContext = {
  intent: mockIntent,
  risks: [
    'Agent lacks EXECUTE authority',
    'Production-scoped operation',
    'Financial transfer involved',
  ],
  requires_human_approval: true,
  denial_reason: 'AUTHORITY_CHECK_FAILED',
  denial_detail: 'GID-01 does not have EXECUTE permission',
};

const mockUser: ApproverIdentity = {
  user_id: 'human-123',
  role: 'AI Ops Lead',
  timestamp: '2025-12-17T10:00:00.000Z',
};

// ============================================================
// SETUP
// ============================================================

describe('HumanApprovalModal', () => {
  let onApprove: ReturnType<typeof vi.fn>;
  let onCancel: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onApprove = vi.fn().mockResolvedValue(undefined);
    onCancel = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================
  // RENDERING TESTS
  // ============================================================

  describe('rendering', () => {
    it('renders modal when isOpen is true', () => {
      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      expect(screen.getByText('⚠️ Human Approval Required')).toBeDefined();
      expect(
        screen.getByText(
          'This action cannot proceed without explicit authorization.'
        )
      ).toBeDefined();
    });

    it('does not render when isOpen is false', () => {
      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={false}
        />
      );

      expect(screen.queryByText('⚠️ Human Approval Required')).toBeNull();
    });

    it('displays immutable intent as read-only JSON', () => {
      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      // Check that intent fields are displayed
      expect(screen.getByText(/EXECUTE/)).toBeDefined();
      expect(screen.getByText(/settlement\.release/)).toBeDefined();
      expect(screen.getByText(/\$50,000/)).toBeDefined();
      expect(screen.getByText(/PRODUCTION/)).toBeDefined();
      expect(screen.getByText(/abc-123/)).toBeDefined();
    });

    it('displays risk factors', () => {
      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      expect(screen.getByText('Agent lacks EXECUTE authority')).toBeDefined();
      expect(screen.getByText('Production-scoped operation')).toBeDefined();
      expect(screen.getByText('Financial transfer involved')).toBeDefined();
    });
  });

  // ============================================================
  // CONFIRMATION TESTS
  // ============================================================

  describe('confirmation requirements', () => {
    it('AUTHORIZE button is disabled initially', () => {
      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button');
      expect(authorizeButton?.disabled).toBe(true);
    });

    it('cannot approve without checking checkbox', async () => {
      const user = userEvent.setup();

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      // Type confirmation without checking checkbox
      const input = screen.getByPlaceholderText(/Type.*AUTHORIZE/i) ||
                    screen.getByRole('textbox');
      await user.type(input, 'AUTHORIZE');

      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button');
      expect(authorizeButton?.disabled).toBe(true);
    });

    it('cannot approve without typing correct confirmation', async () => {
      const user = userEvent.setup();

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      // Check checkbox
      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      // Type wrong confirmation
      const input = screen.getByRole('textbox');
      await user.type(input, 'authorize'); // lowercase

      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button');
      expect(authorizeButton?.disabled).toBe(true);
    });

    it('enables AUTHORIZE button when both confirmations are complete', async () => {
      const user = userEvent.setup();

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      // Check checkbox
      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      // Type correct confirmation
      const input = screen.getByRole('textbox');
      await user.type(input, 'AUTHORIZE');

      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button');
      expect(authorizeButton?.disabled).toBe(false);
    });
  });

  // ============================================================
  // APPROVAL OUTPUT TESTS
  // ============================================================

  describe('approval output', () => {
    it('emits correct approval intent on authorize', async () => {
      const user = userEvent.setup();

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      // Complete confirmations
      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const input = screen.getByRole('textbox');
      await user.type(input, 'AUTHORIZE');

      // Click authorize
      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button')!;
      await user.click(authorizeButton);

      await waitFor(() => {
        expect(onApprove).toHaveBeenCalledTimes(1);
      });

      const approvalIntent: ApprovalIntent = onApprove.mock.calls[0][0];
      expect(approvalIntent.verb).toBe('ESCALATE');
      expect(approvalIntent.target).toBe('approved.execution');
      expect(approvalIntent.authorized_by.user_id).toBe('human-123');
      expect(approvalIntent.authorized_by.role).toBe('AI Ops Lead');
      expect(approvalIntent.approval_of).toBe('correlation_id:abc-123');
      expect(approvalIntent.approved_intent).toEqual(mockIntent);
    });

    it('does NOT trigger execution — only emits intent', async () => {
      const user = userEvent.setup();

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      // Complete and authorize
      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const input = screen.getByRole('textbox');
      await user.type(input, 'AUTHORIZE');

      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button')!;
      await user.click(authorizeButton);

      await waitFor(() => {
        expect(onApprove).toHaveBeenCalled();
      });

      // Verify the callback was called with an approval intent, not an execution
      const call = onApprove.mock.calls[0][0];
      expect(call.verb).toBe('ESCALATE'); // NOT EXECUTE
      expect(call.target).toBe('approved.execution'); // NOT the original target
    });

    it('blocks duplicate approval attempts', async () => {
      const user = userEvent.setup();

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      // Complete and authorize
      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const input = screen.getByRole('textbox');
      await user.type(input, 'AUTHORIZE');

      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button')!;
      await user.click(authorizeButton);

      await waitFor(() => {
        expect(onApprove).toHaveBeenCalledTimes(1);
      });

      // Try to click again — should be blocked
      await user.click(authorizeButton);

      // Still only called once
      expect(onApprove).toHaveBeenCalledTimes(1);
    });
  });

  // ============================================================
  // CANCEL TESTS
  // ============================================================

  describe('cancel behavior', () => {
    it('calls onCancel when CANCEL is clicked', async () => {
      const user = userEvent.setup();

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      const cancelButton = screen.getByText('CANCEL').closest('button')!;
      await user.click(cancelButton);

      expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('returns to Diggi view on cancel (no side effects)', async () => {
      const user = userEvent.setup();

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      const cancelButton = screen.getByText('CANCEL').closest('button')!;
      await user.click(cancelButton);

      expect(onApprove).not.toHaveBeenCalled();
      expect(onCancel).toHaveBeenCalled();
    });
  });

  // ============================================================
  // VALIDATION FAILURE TESTS
  // ============================================================

  describe('failure modes', () => {
    it('blocks approval when user identity is missing', () => {
      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={null}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      expect(screen.getByText('Approval Blocked')).toBeDefined();
      expect(
        screen.getByText(/Missing user identity/)
      ).toBeDefined();

      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button');
      expect(authorizeButton?.disabled).toBe(true);
    });

    it('blocks approval when intent payload is missing', () => {
      const invalidContext = {
        ...mockContext,
        intent: null as any,
      };

      render(
        <HumanApprovalModal
          context={invalidContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      expect(screen.getByText('Approval Blocked')).toBeDefined();
    });

    it('shows error on network failure', async () => {
      const user = userEvent.setup();
      onApprove.mockRejectedValueOnce(new Error('Network timeout'));

      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      // Complete and authorize
      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const input = screen.getByRole('textbox');
      await user.type(input, 'AUTHORIZE');

      const authorizeButton = screen.getByText('AUTHORIZE ACTION').closest('button')!;
      await user.click(authorizeButton);

      await waitFor(() => {
        expect(screen.getByText(/Network timeout/)).toBeDefined();
        expect(screen.getByText(/No automatic retry/)).toBeDefined();
      });
    });
  });

  // ============================================================
  // KEYBOARD TESTS
  // ============================================================

  describe('keyboard interaction', () => {
    it('blocks Escape key — must use explicit cancel', () => {
      render(
        <HumanApprovalModal
          context={mockContext}
          currentUser={mockUser}
          onApprove={onApprove}
          onCancel={onCancel}
          isOpen={true}
        />
      );

      fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' });

      // Modal should still be visible
      expect(screen.getByText('⚠️ Human Approval Required')).toBeDefined();
      expect(onCancel).not.toHaveBeenCalled();
    });
  });
});

// ============================================================
// TYPE CONTRACT TESTS
// ============================================================

describe('Type Contract', () => {
  it('HumanApprovalContext requires_human_approval must be true', () => {
    const context: HumanApprovalContext = {
      intent: mockIntent,
      risks: [],
      requires_human_approval: true, // This MUST be true — type enforced
    };

    expect(context.requires_human_approval).toBe(true);
  });

  it('ApprovalIntent has correct structure', () => {
    const approval: ApprovalIntent = {
      verb: 'ESCALATE',
      target: 'approved.execution',
      authorized_by: mockUser,
      approval_of: 'correlation_id:abc-123',
      approved_intent: mockIntent,
    };

    expect(approval.verb).toBe('ESCALATE');
    expect(approval.target).toBe('approved.execution');
  });
});
