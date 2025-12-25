/**
 * GovernanceUIParityShield Tests — PAC-SONNY-P30-GOVERNANCE-UI-PARITY-SHIELD-01
 *
 * Tests verifying terminal parity for governance UI components.
 *
 * Test Categories:
 * 1. GovernanceShield — Shield status derivation and rendering
 * 2. LastEvaluatedBadge — Timestamp freshness and display
 * 3. GovernanceStatusCard — Terminal glyph parity
 * 4. Integration — Component composition
 *
 * @see PAC-SONNY-P30-GOVERNANCE-UI-PARITY-SHIELD-01
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  GovernanceShield,
  GovernanceShieldBadge,
  GovernanceShieldIcon,
  deriveShieldStatus,
} from '../GovernanceShield';
import {
  LastEvaluatedBadge,
  LastEvaluatedCompact,
  calculateFreshness,
  formatTimestamp,
  formatRelativeTime,
} from '../LastEvaluatedBadge';
import {
  GovernanceStatusCard,
  GovernanceStatusStrip,
  deriveGlyphPattern,
} from '../GovernanceStatusCard';
import type { GovernanceSummary } from '../../../types/governanceLedger';

// Mock summary data factory
function createMockSummary(overrides: Partial<GovernanceSummary> = {}): GovernanceSummary {
  return {
    total_pacs: 10,
    active_pacs: 3,
    blocked_pacs: 0,
    correction_cycles: 0,
    positive_closures: 5,
    pending_ratifications: 0,
    system_healthy: true,
    last_activity: new Date().toISOString(),
    ...overrides,
  };
}

// ============================================================================
// GovernanceShield Tests
// ============================================================================
describe('GovernanceShield', () => {
  describe('deriveShieldStatus', () => {
    it('returns RED when summary is null (FAIL_CLOSED)', () => {
      expect(deriveShieldStatus(null)).toBe('RED');
    });

    it('returns RED when system is unhealthy', () => {
      const summary = createMockSummary({ system_healthy: false });
      expect(deriveShieldStatus(summary)).toBe('RED');
    });

    it('returns RED when blocked_pacs > 0', () => {
      const summary = createMockSummary({ blocked_pacs: 2 });
      expect(deriveShieldStatus(summary)).toBe('RED');
    });

    it('returns YELLOW when correction_cycles > 0', () => {
      const summary = createMockSummary({ correction_cycles: 1 });
      expect(deriveShieldStatus(summary)).toBe('YELLOW');
    });

    it('returns YELLOW when pending_ratifications > 0', () => {
      const summary = createMockSummary({ pending_ratifications: 2 });
      expect(deriveShieldStatus(summary)).toBe('YELLOW');
    });

    it('returns GREEN when all clear', () => {
      const summary = createMockSummary();
      expect(deriveShieldStatus(summary)).toBe('GREEN');
    });

    it('prioritizes RED over YELLOW', () => {
      const summary = createMockSummary({
        blocked_pacs: 1,
        correction_cycles: 3,
      });
      expect(deriveShieldStatus(summary)).toBe('RED');
    });
  });

  describe('GovernanceShield component', () => {
    it('renders with GREEN status', () => {
      const summary = createMockSummary();
      render(<GovernanceShield summary={summary} />);

      const shield = screen.getByTestId('governance-shield');
      expect(shield).toHaveAttribute('data-status', 'GREEN');
      expect(screen.getByTestId('governance-shield-label')).toHaveTextContent('COMPLIANT');
    });

    it('renders with YELLOW status', () => {
      const summary = createMockSummary({ correction_cycles: 1 });
      render(<GovernanceShield summary={summary} />);

      const shield = screen.getByTestId('governance-shield');
      expect(shield).toHaveAttribute('data-status', 'YELLOW');
      expect(screen.getByTestId('governance-shield-label')).toHaveTextContent('IN PROGRESS');
    });

    it('renders with RED status', () => {
      const summary = createMockSummary({ blocked_pacs: 1 });
      render(<GovernanceShield summary={summary} />);

      const shield = screen.getByTestId('governance-shield');
      expect(shield).toHaveAttribute('data-status', 'RED');
      expect(screen.getByTestId('governance-shield-label')).toHaveTextContent('BLOCKED');
    });

    it('renders RED when summary is null (FAIL_CLOSED)', () => {
      render(<GovernanceShield summary={null} />);

      const shield = screen.getByTestId('governance-shield');
      expect(shield).toHaveAttribute('data-status', 'RED');
    });

    it('respects overrideStatus prop', () => {
      const summary = createMockSummary(); // Would normally be GREEN
      render(<GovernanceShield summary={summary} overrideStatus="YELLOW" />);

      const shield = screen.getByTestId('governance-shield');
      expect(shield).toHaveAttribute('data-status', 'YELLOW');
    });

    it('hides label when showLabel is false', () => {
      const summary = createMockSummary();
      render(<GovernanceShield summary={summary} showLabel={false} />);

      expect(screen.queryByTestId('governance-shield-label')).not.toBeInTheDocument();
    });

    it('renders different sizes', () => {
      const summary = createMockSummary();
      const { rerender } = render(<GovernanceShield summary={summary} size="sm" />);
      expect(screen.getByTestId('governance-shield-indicator')).toBeInTheDocument();

      rerender(<GovernanceShield summary={summary} size="lg" />);
      expect(screen.getByTestId('governance-shield-indicator')).toBeInTheDocument();
    });
  });

  describe('GovernanceShieldBadge component', () => {
    it('renders as a badge with status', () => {
      const summary = createMockSummary();
      render(<GovernanceShieldBadge summary={summary} />);

      const badge = screen.getByTestId('governance-shield-badge');
      expect(badge).toHaveAttribute('data-status', 'GREEN');
      expect(badge).toHaveTextContent('COMPLIANT');
    });
  });

  describe('GovernanceShieldIcon component', () => {
    it('renders minimal icon', () => {
      const summary = createMockSummary();
      render(<GovernanceShieldIcon summary={summary} />);

      const icon = screen.getByTestId('governance-shield-icon');
      expect(icon).toHaveAttribute('data-status', 'GREEN');
    });
  });
});

// ============================================================================
// LastEvaluatedBadge Tests
// ============================================================================
describe('LastEvaluatedBadge', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-12-24T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('calculateFreshness', () => {
    it('returns OUTDATED for null timestamp', () => {
      expect(calculateFreshness(null)).toBe('OUTDATED');
    });

    it('returns FRESH for < 1 minute ago', () => {
      const timestamp = new Date(Date.now() - 30 * 1000).toISOString();
      expect(calculateFreshness(timestamp)).toBe('FRESH');
    });

    it('returns RECENT for 1-5 minutes ago', () => {
      const timestamp = new Date(Date.now() - 3 * 60 * 1000).toISOString();
      expect(calculateFreshness(timestamp)).toBe('RECENT');
    });

    it('returns STALE for 5-15 minutes ago', () => {
      const timestamp = new Date(Date.now() - 10 * 60 * 1000).toISOString();
      expect(calculateFreshness(timestamp)).toBe('STALE');
    });

    it('returns OUTDATED for > 15 minutes ago', () => {
      const timestamp = new Date(Date.now() - 20 * 60 * 1000).toISOString();
      expect(calculateFreshness(timestamp)).toBe('OUTDATED');
    });
  });

  describe('formatTimestamp', () => {
    it('returns "Never" for null', () => {
      expect(formatTimestamp(null)).toBe('Never');
    });

    it('formats timestamp correctly', () => {
      const timestamp = '2025-12-24T12:00:00Z';
      const result = formatTimestamp(timestamp);
      expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });
  });

  describe('formatRelativeTime', () => {
    it('returns "Unknown" for null', () => {
      expect(formatRelativeTime(null)).toBe('Unknown');
    });

    it('returns "Just now" for < 60 seconds', () => {
      const timestamp = new Date(Date.now() - 30 * 1000).toISOString();
      expect(formatRelativeTime(timestamp)).toBe('Just now');
    });

    it('returns minutes format for < 60 minutes', () => {
      const timestamp = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      expect(formatRelativeTime(timestamp)).toBe('5m ago');
    });

    it('returns hours format for < 24 hours', () => {
      const timestamp = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
      expect(formatRelativeTime(timestamp)).toBe('2h ago');
    });
  });

  describe('LastEvaluatedBadge component', () => {
    it('renders with freshness indicator', () => {
      const timestamp = new Date().toISOString();
      render(<LastEvaluatedBadge timestamp={timestamp} />);

      const badge = screen.getByTestId('last-evaluated-badge');
      expect(badge).toHaveAttribute('data-freshness', 'FRESH');
      expect(screen.getByTestId('freshness-indicator')).toBeInTheDocument();
    });

    it('shows OUTDATED for null timestamp', () => {
      render(<LastEvaluatedBadge timestamp={null} />);

      const badge = screen.getByTestId('last-evaluated-badge');
      expect(badge).toHaveAttribute('data-freshness', 'OUTDATED');
    });

    it('hides freshness indicator when disabled', () => {
      const timestamp = new Date().toISOString();
      render(<LastEvaluatedBadge timestamp={timestamp} showFreshnessIndicator={false} />);

      expect(screen.queryByTestId('freshness-indicator')).not.toBeInTheDocument();
    });

    it('shows relative time by default', () => {
      const timestamp = new Date().toISOString();
      render(<LastEvaluatedBadge timestamp={timestamp} />);

      expect(screen.getByTestId('timestamp-value')).toHaveTextContent('Just now');
    });

    it('shows absolute time when showRelative is false', () => {
      const timestamp = '2025-12-24T12:00:00Z';
      render(<LastEvaluatedBadge timestamp={timestamp} showRelative={false} />);

      const value = screen.getByTestId('timestamp-value');
      expect(value.textContent).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });
  });

  describe('LastEvaluatedCompact component', () => {
    it('renders compact version', () => {
      const timestamp = new Date().toISOString();
      render(<LastEvaluatedCompact timestamp={timestamp} />);

      const compact = screen.getByTestId('last-evaluated-compact');
      expect(compact).toHaveAttribute('data-freshness', 'FRESH');
    });
  });
});

// ============================================================================
// GovernanceStatusCard Tests
// ============================================================================
describe('GovernanceStatusCard', () => {
  describe('deriveGlyphPattern', () => {
    it('returns PENDING for null summary', () => {
      expect(deriveGlyphPattern(null)).toBe('PENDING');
    });

    it('returns BLOCKED when blocked_pacs > 0', () => {
      const summary = createMockSummary({ blocked_pacs: 1 });
      expect(deriveGlyphPattern(summary)).toBe('BLOCKED');
    });

    it('returns BLOCKED when system is unhealthy', () => {
      const summary = createMockSummary({ system_healthy: false });
      expect(deriveGlyphPattern(summary)).toBe('BLOCKED');
    });

    it('returns CORRECTION_IN_PROGRESS when correction_cycles > 0', () => {
      const summary = createMockSummary({ correction_cycles: 2 });
      expect(deriveGlyphPattern(summary)).toBe('CORRECTION_IN_PROGRESS');
    });

    it('returns CORRECTION_IN_PROGRESS when pending_ratifications > 0', () => {
      const summary = createMockSummary({ pending_ratifications: 1 });
      expect(deriveGlyphPattern(summary)).toBe('CORRECTION_IN_PROGRESS');
    });

    it('returns GOLD_STANDARD_COMPLIANT when all clear', () => {
      const summary = createMockSummary();
      expect(deriveGlyphPattern(summary)).toBe('GOLD_STANDARD_COMPLIANT');
    });
  });

  describe('GovernanceStatusCard component', () => {
    it('renders GOLD_STANDARD_COMPLIANT state', () => {
      const summary = createMockSummary();
      render(<GovernanceStatusCard summary={summary} />);

      const card = screen.getByTestId('governance-status-card');
      expect(card).toHaveAttribute('data-pattern', 'GOLD_STANDARD_COMPLIANT');
      expect(screen.getByTestId('glyph-banner')).toHaveTextContent('🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩');
      expect(screen.getByTestId('terminal-output')).toHaveTextContent('STATUS: 🟩 GOLD_STANDARD_COMPLIANT');
    });

    it('renders CORRECTION_IN_PROGRESS state', () => {
      const summary = createMockSummary({ correction_cycles: 1 });
      render(<GovernanceStatusCard summary={summary} />);

      const card = screen.getByTestId('governance-status-card');
      expect(card).toHaveAttribute('data-pattern', 'CORRECTION_IN_PROGRESS');
      expect(screen.getByTestId('glyph-banner')).toHaveTextContent('🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡');
      expect(screen.getByTestId('terminal-output')).toHaveTextContent('STATUS: 🟡 CORRECTION_IN_PROGRESS');
    });

    it('renders BLOCKED state', () => {
      const summary = createMockSummary({ blocked_pacs: 1 });
      render(<GovernanceStatusCard summary={summary} />);

      const card = screen.getByTestId('governance-status-card');
      expect(card).toHaveAttribute('data-pattern', 'BLOCKED');
      expect(screen.getByTestId('glyph-banner')).toHaveTextContent('🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴');
      expect(screen.getByTestId('terminal-output')).toHaveTextContent('STATUS: 🔴 BLOCKED — ACTION REQUIRED');
    });

    it('renders PENDING state for null summary', () => {
      render(<GovernanceStatusCard summary={null} />);

      const card = screen.getByTestId('governance-status-card');
      expect(card).toHaveAttribute('data-pattern', 'PENDING');
      expect(screen.getByTestId('glyph-banner')).toHaveTextContent('⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜');
    });

    it('shows loading skeleton when loading', () => {
      render(<GovernanceStatusCard summary={null} loading={true} />);

      expect(screen.queryByTestId('governance-status-card')).not.toBeInTheDocument();
      expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('shows error state when error is present', () => {
      const error = new Error('Test error');
      render(<GovernanceStatusCard summary={null} error={error} />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Governance Status Unavailable')).toBeInTheDocument();
      expect(screen.getByText('Test error')).toBeInTheDocument();
    });

    it('hides glyph banner when showGlyphBanner is false', () => {
      const summary = createMockSummary();
      render(<GovernanceStatusCard summary={summary} showGlyphBanner={false} />);

      expect(screen.queryByTestId('glyph-banner')).not.toBeInTheDocument();
    });

    it('hides shield when showShield is false', () => {
      const summary = createMockSummary();
      render(<GovernanceStatusCard summary={summary} showShield={false} />);

      expect(screen.queryByTestId('governance-shield')).not.toBeInTheDocument();
    });

    it('renders compact mode', () => {
      const summary = createMockSummary();
      render(<GovernanceStatusCard summary={summary} compact={true} />);

      expect(screen.queryByTestId('terminal-output')).not.toBeInTheDocument();
    });

    it('shows stats breakdown', () => {
      const summary = createMockSummary({
        total_pacs: 10,
        active_pacs: 3,
        positive_closures: 5,
      });
      render(<GovernanceStatusCard summary={summary} />);

      expect(screen.getByText('Total')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
      expect(screen.getByText('Active')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('Closures')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('shows corrections stat when correction_cycles > 0', () => {
      const summary = createMockSummary({ correction_cycles: 2 });
      render(<GovernanceStatusCard summary={summary} />);

      expect(screen.getByText('Corrections')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('shows blocked stat when blocked_pacs > 0', () => {
      const summary = createMockSummary({ blocked_pacs: 1 });
      render(<GovernanceStatusCard summary={summary} />);

      expect(screen.getByText('Blocked')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
    });
  });

  describe('GovernanceStatusStrip component', () => {
    it('renders strip variant', () => {
      const summary = createMockSummary();
      render(<GovernanceStatusStrip summary={summary} />);

      const strip = screen.getByTestId('governance-status-strip');
      expect(strip).toHaveAttribute('data-pattern', 'GOLD_STANDARD_COMPLIANT');
      expect(strip).toHaveTextContent('GOLD STANDARD COMPLIANT');
    });

    it('shows timestamp in strip', () => {
      const summary = createMockSummary();
      render(<GovernanceStatusStrip summary={summary} />);

      expect(screen.getByTestId('last-evaluated-compact')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// Integration Tests — Terminal Parity
// ============================================================================
describe('Terminal Parity Integration', () => {
  it('all components agree on GREEN/COMPLIANT state', () => {
    const summary = createMockSummary();

    const { rerender } = render(<GovernanceShield summary={summary} />);
    expect(screen.getByTestId('governance-shield')).toHaveAttribute('data-status', 'GREEN');

    rerender(<GovernanceStatusCard summary={summary} />);
    expect(screen.getByTestId('governance-status-card')).toHaveAttribute('data-pattern', 'GOLD_STANDARD_COMPLIANT');

    expect(deriveShieldStatus(summary)).toBe('GREEN');
    expect(deriveGlyphPattern(summary)).toBe('GOLD_STANDARD_COMPLIANT');
  });

  it('all components agree on YELLOW/CORRECTION state', () => {
    const summary = createMockSummary({ correction_cycles: 1 });

    const { rerender } = render(<GovernanceShield summary={summary} />);
    expect(screen.getByTestId('governance-shield')).toHaveAttribute('data-status', 'YELLOW');

    rerender(<GovernanceStatusCard summary={summary} />);
    expect(screen.getByTestId('governance-status-card')).toHaveAttribute('data-pattern', 'CORRECTION_IN_PROGRESS');

    expect(deriveShieldStatus(summary)).toBe('YELLOW');
    expect(deriveGlyphPattern(summary)).toBe('CORRECTION_IN_PROGRESS');
  });

  it('all components agree on RED/BLOCKED state', () => {
    const summary = createMockSummary({ blocked_pacs: 1 });

    const { rerender } = render(<GovernanceShield summary={summary} />);
    expect(screen.getByTestId('governance-shield')).toHaveAttribute('data-status', 'RED');

    rerender(<GovernanceStatusCard summary={summary} />);
    expect(screen.getByTestId('governance-status-card')).toHaveAttribute('data-pattern', 'BLOCKED');

    expect(deriveShieldStatus(summary)).toBe('RED');
    expect(deriveGlyphPattern(summary)).toBe('BLOCKED');
  });

  it('FAIL_CLOSED: null summary maps to RED/PENDING (most restrictive)', () => {
    const { rerender } = render(<GovernanceShield summary={null} />);
    expect(screen.getByTestId('governance-shield')).toHaveAttribute('data-status', 'RED');

    rerender(<GovernanceStatusCard summary={null} />);
    expect(screen.getByTestId('governance-status-card')).toHaveAttribute('data-pattern', 'PENDING');

    // Shield returns RED (FAIL_CLOSED)
    expect(deriveShieldStatus(null)).toBe('RED');
    // Pattern returns PENDING (unknown state)
    expect(deriveGlyphPattern(null)).toBe('PENDING');
  });
});

// ============================================================================
// Accessibility Tests
// ============================================================================
describe('Accessibility', () => {
  it('GovernanceShield has proper aria-label', () => {
    const summary = createMockSummary();
    render(<GovernanceShield summary={summary} />);

    const shield = screen.getByTestId('governance-shield');
    expect(shield).toHaveAttribute('aria-label', 'Governance status: COMPLIANT');
  });

  it('LastEvaluatedBadge has proper aria-label', () => {
    const timestamp = new Date().toISOString();
    render(<LastEvaluatedBadge timestamp={timestamp} />);

    const badge = screen.getByTestId('last-evaluated-badge');
    expect(badge).toHaveAttribute('aria-label');
    expect(badge.getAttribute('aria-label')).toContain('Last evaluated:');
  });

  it('GovernanceStatusCard has proper role', () => {
    const summary = createMockSummary();
    render(<GovernanceStatusCard summary={summary} />);

    const card = screen.getByTestId('governance-status-card');
    expect(card).toHaveAttribute('role', 'region');
    expect(card).toHaveAttribute('aria-label', 'Governance Status');
  });

  it('Error state has alert role', () => {
    const error = new Error('Test');
    render(<GovernanceStatusCard summary={null} error={error} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
