/**
 * Test Provenance Tests — PAC-SONNY-TRUST-UI-REDUCTION-01
 *
 * Tests for stripped-down Test Provenance component.
 *
 * @see PAC-SONNY-TRUST-UI-REDUCTION-01
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { TestProvenance } from '../TestProvenance';

describe('TestProvenance', () => {
  it('renders artifact label', () => {
    render(<TestProvenance />);
    expect(screen.getByText('Test Provenance')).toBeInTheDocument();
  });

  it('renders what this shows', () => {
    render(<TestProvenance />);
    expect(screen.getByText('Test suite pass status at build time.')).toBeInTheDocument();
  });

  it('renders default test suites', () => {
    render(<TestProvenance />);
    expect(screen.getByText('Governance')).toBeInTheDocument();
    expect(screen.getByText('Security')).toBeInTheDocument();
    expect(screen.getByText('Scope Guard')).toBeInTheDocument();
    expect(screen.getByText('OCC')).toBeInTheDocument();
    expect(screen.getByText('ChainBoard')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
  });

  it('shows boolean pass status only', () => {
    render(<TestProvenance />);
    // Should show "passed", not counts or percentages
    expect(screen.getAllByText('passed')).toHaveLength(6);
    expect(screen.queryByText(/\d+%/)).toBeNull(); // No percentages
    expect(screen.queryByText(/\d+ tests/)).toBeNull(); // No counts
  });

  it('shows test directory paths', () => {
    render(<TestProvenance />);
    expect(screen.getByText('tests/governance/')).toBeInTheDocument();
    expect(screen.getByText('tests/security/')).toBeInTheDocument();
  });

  it('has no icons', () => {
    const { container } = render(<TestProvenance />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('shows failed for failing suites', () => {
    const suites = [
      { name: 'Failing', path: 'tests/failing/', passed: false },
    ];
    render(<TestProvenance suites={suites} />);
    expect(screen.getByText('failed')).toBeInTheDocument();
  });
});
