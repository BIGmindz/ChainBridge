/**
 * Gameday Status Tests — PAC-TRUST-CENTER-UI-01
 *
 * Tests for customer-facing Gameday Status component.
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { GamedayStatus } from '../GamedayStatus';
import type { GamedaySummary } from '../../../types/trust';

const mockGameday: GamedaySummary = {
  scenarios_tested: 133,
  silent_failures: 0,
  fail_closed_all: true,
};

describe('GamedayStatus', () => {
  it('renders adversarial testing title', () => {
    render(<GamedayStatus />);
    expect(screen.getByText('Adversarial Testing')).toBeInTheDocument();
  });

  it('renders customer-safe statement', () => {
    render(<GamedayStatus />);
    expect(
      screen.getByText(/governance controls are continuously validated/)
    ).toBeInTheDocument();
  });

  it('displays scenarios tested count', () => {
    render(<GamedayStatus gameday={mockGameday} />);
    expect(screen.getByText('133')).toBeInTheDocument();
    expect(screen.getByText('Scenarios Tested')).toBeInTheDocument();
  });

  it('displays silent failures count', () => {
    render(<GamedayStatus gameday={mockGameday} />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('Silent Failures')).toBeInTheDocument();
  });

  it('displays fail-closed status', () => {
    render(<GamedayStatus gameday={mockGameday} />);
    expect(screen.getByText('Yes')).toBeInTheDocument();
    expect(screen.getByText('Fail-Closed')).toBeInTheDocument();
  });

  it('shows dashes when no gameday data', () => {
    render(<GamedayStatus />);
    expect(screen.getAllByText('—')).toHaveLength(3);
  });

  it('applies custom className', () => {
    const { container } = render(<GamedayStatus className="test-class" />);
    expect(container.firstChild).toHaveClass('test-class');
  });
});
