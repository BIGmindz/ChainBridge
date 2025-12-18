/**
 * Control Coverage Tests — PAC-TRUST-CENTER-UI-01
 *
 * Tests for customer-facing Control Coverage component.
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ControlCoverage } from '../ControlCoverage';
import type { ControlCoverageItem } from '../ControlCoverage';

describe('ControlCoverage', () => {
  it('renders control coverage title', () => {
    render(<ControlCoverage />);
    expect(screen.getByText('Control Coverage')).toBeInTheDocument();
  });

  it('renders default controls when no coverage provided', () => {
    render(<ControlCoverage />);
    expect(screen.getByText('Access Control (ACM)')).toBeInTheDocument();
    expect(screen.getByText('Decision Routing (DRCP)')).toBeInTheDocument();
    expect(screen.getByText('Agent Constraints (DIGGI)')).toBeInTheDocument();
    expect(screen.getByText('Artifact Verification')).toBeInTheDocument();
    expect(screen.getByText('Scope Enforcement')).toBeInTheDocument();
    expect(screen.getByText('Fail-Closed Execution')).toBeInTheDocument();
  });

  it('renders custom coverage items', () => {
    const customCoverage: ControlCoverageItem[] = [
      { id: 'custom1', name: 'Custom Control', status: 'Active', active: true },
    ];
    render(<ControlCoverage coverage={customCoverage} />);
    expect(screen.getByText('Custom Control')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('shows unavailable for inactive controls', () => {
    const inactiveCoverage: ControlCoverageItem[] = [
      { id: 'inactive', name: 'Inactive Control', status: 'Disabled', active: false },
    ];
    render(<ControlCoverage coverage={inactiveCoverage} />);
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<ControlCoverage className="test-class" />);
    expect(container.firstChild).toHaveClass('test-class');
  });
});
