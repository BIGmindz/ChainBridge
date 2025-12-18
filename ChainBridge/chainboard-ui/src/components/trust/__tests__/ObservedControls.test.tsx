/**
 * Observed Controls Tests — PAC-SONNY-TRUST-UI-REDUCTION-01
 *
 * Tests for stripped-down Observed Controls component.
 *
 * @see PAC-SONNY-TRUST-UI-REDUCTION-01
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ObservedControls } from '../ObservedControls';

describe('ObservedControls', () => {
  it('renders artifact label', () => {
    render(<ObservedControls />);
    expect(screen.getByText('Observed Controls')).toBeInTheDocument();
  });

  it('renders what this shows', () => {
    render(<ObservedControls />);
    expect(screen.getByText('Controls where code exists and tests pass.')).toBeInTheDocument();
  });

  it('renders default controls', () => {
    render(<ObservedControls />);
    expect(screen.getByText('Identity enforcement')).toBeInTheDocument();
    expect(screen.getByText('Scope enforcement')).toBeInTheDocument();
    expect(screen.getByText('Artifact verification')).toBeInTheDocument();
    expect(screen.getByText('Drift detection')).toBeInTheDocument();
  });

  it('shows presence status as "present" not "Enforced"', () => {
    render(<ObservedControls />);
    // Should show "present", not "Enforced", "Active", etc.
    expect(screen.getAllByText('present')).toHaveLength(4);
    expect(screen.queryByText('Enforced')).toBeNull();
    expect(screen.queryByText('Active')).toBeNull();
    expect(screen.queryByText('Enabled')).toBeNull();
  });

  it('shows test suite paths', () => {
    render(<ObservedControls />);
    expect(screen.getByText('tests/governance/test_acm_evaluator.py')).toBeInTheDocument();
    expect(screen.getByText('tests/governance/test_atlas_scope.py')).toBeInTheDocument();
  });

  it('has no icons', () => {
    const { container } = render(<ObservedControls />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('shows absent for inactive controls', () => {
    const controls = [
      { id: 'test', name: 'Test Control', test_suite: 'tests/test.py', present: false },
    ];
    render(<ObservedControls controls={controls} />);
    expect(screen.getByText('absent')).toBeInTheDocument();
  });
});
