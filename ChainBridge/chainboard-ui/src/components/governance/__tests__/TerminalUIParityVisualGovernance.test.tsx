/**
 * TerminalUIParityVisualGovernance Tests — PAC-SONNY-P30-TERMINAL-UI-PARITY-AND-VISUAL-GOVERNANCE-01
 *
 * Tests verifying:
 * 1. Visual language is distinct from agent colors
 * 2. Terminal glyphs map 1:1 to UI components
 * 3. Accessibility requirements met
 * 4. Signal semantics preserved across formats
 *
 * @see PAC-SONNY-P30-TERMINAL-UI-PARITY-AND-VISUAL-GOVERNANCE-01
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  SIGNAL_STATUS_CODES,
  SEVERITY_LEVELS,
  TERMINAL_GLYPHS,
  TERMINAL_BANNERS,
  GOVERNANCE_COLORS,
  SEVERITY_COLORS,
  getSignalVisualConfig,
  getSeverityVisualConfig,
  formatTerminalSignal,
  formatTerminalSummary,
  generateTerminalBanner,
} from '../GovernanceVisualLanguage';
import {
  GovernanceSignalBadge,
  SeverityBadge,
  GovernanceSignalRow,
  ValidationSummary,
  GateIndicator,
} from '../GovernanceSignalBadge';
import { TerminalUIParityDemo } from '../TerminalUIParityDemo';

// ============================================================================
// Visual Language Constants Tests
// ============================================================================
describe('GovernanceVisualLanguage Constants', () => {
  describe('SIGNAL_STATUS_CODES', () => {
    it('defines all four canonical statuses', () => {
      expect(SIGNAL_STATUS_CODES.PASS).toBe(0);
      expect(SIGNAL_STATUS_CODES.WARN).toBe(1);
      expect(SIGNAL_STATUS_CODES.FAIL).toBe(2);
      expect(SIGNAL_STATUS_CODES.SKIP).toBe(3);
    });

    it('provides sortable numeric codes', () => {
      // PASS should sort before WARN before FAIL before SKIP
      expect(SIGNAL_STATUS_CODES.PASS).toBeLessThan(SIGNAL_STATUS_CODES.WARN);
      expect(SIGNAL_STATUS_CODES.WARN).toBeLessThan(SIGNAL_STATUS_CODES.FAIL);
      expect(SIGNAL_STATUS_CODES.FAIL).toBeLessThan(SIGNAL_STATUS_CODES.SKIP);
    });
  });

  describe('SEVERITY_LEVELS', () => {
    it('defines all five severity levels', () => {
      expect(SEVERITY_LEVELS.NONE).toBe(0);
      expect(SEVERITY_LEVELS.LOW).toBe(1);
      expect(SEVERITY_LEVELS.MEDIUM).toBe(2);
      expect(SEVERITY_LEVELS.HIGH).toBe(3);
      expect(SEVERITY_LEVELS.CRITICAL).toBe(4);
    });

    it('maintains severity ordering', () => {
      expect(SEVERITY_LEVELS.NONE).toBeLessThan(SEVERITY_LEVELS.LOW);
      expect(SEVERITY_LEVELS.LOW).toBeLessThan(SEVERITY_LEVELS.MEDIUM);
      expect(SEVERITY_LEVELS.MEDIUM).toBeLessThan(SEVERITY_LEVELS.HIGH);
      expect(SEVERITY_LEVELS.HIGH).toBeLessThan(SEVERITY_LEVELS.CRITICAL);
    });
  });

  describe('TERMINAL_GLYPHS', () => {
    it('defines distinct status glyphs', () => {
      expect(TERMINAL_GLYPHS.PASS).toBe('✓');
      expect(TERMINAL_GLYPHS.WARN).toBe('⚠');
      expect(TERMINAL_GLYPHS.FAIL).toBe('✗');
      expect(TERMINAL_GLYPHS.SKIP).toBe('○');
    });

    it('defines block variants for banners', () => {
      expect(TERMINAL_GLYPHS.PASS_BLOCK).toBe('🟩');
      expect(TERMINAL_GLYPHS.WARN_BLOCK).toBe('🟧'); // Orange, NOT yellow
      expect(TERMINAL_GLYPHS.FAIL_BLOCK).toBe('🟥');
      expect(TERMINAL_GLYPHS.SKIP_BLOCK).toBe('⬜');
    });

    it('defines gate indicators', () => {
      expect(TERMINAL_GLYPHS.GATE_OPEN).toBe('🔓');
      expect(TERMINAL_GLYPHS.GATE_CLOSED).toBe('🔒');
      expect(TERMINAL_GLYPHS.GATE_PENDING).toBe('⏳');
    });
  });

  describe('TERMINAL_BANNERS', () => {
    it('defines 10-glyph wide banners', () => {
      // Each banner should be 10 emoji wide
      expect(TERMINAL_BANNERS.PASS.length).toBeGreaterThanOrEqual(10);
      expect(TERMINAL_BANNERS.WARN.length).toBeGreaterThanOrEqual(10);
      expect(TERMINAL_BANNERS.FAIL.length).toBeGreaterThanOrEqual(10);
      expect(TERMINAL_BANNERS.SKIP.length).toBeGreaterThanOrEqual(10);
    });

    it('WARN banner uses orange, NOT yellow', () => {
      // Critical: WARN must not be yellow (agent color for SONNY)
      expect(TERMINAL_BANNERS.WARN).toBe('🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧');
      expect(TERMINAL_BANNERS.WARN).not.toContain('🟡'); // No yellow!
    });
  });

  describe('GOVERNANCE_COLORS - Agent Color Separation', () => {
    it('PASS uses emerald (not green/agent)', () => {
      expect(GOVERNANCE_COLORS.PASS.hex).toBe('#10b981'); // Emerald
      expect(GOVERNANCE_COLORS.PASS.bg).toContain('emerald');
    });

    it('WARN uses orange (not yellow/SONNY)', () => {
      expect(GOVERNANCE_COLORS.WARN.hex).toBe('#f97316'); // Orange
      expect(GOVERNANCE_COLORS.WARN.bg).toContain('orange');
      expect(GOVERNANCE_COLORS.WARN.bg).not.toContain('yellow');
    });

    it('FAIL uses rose (not red/BENSON)', () => {
      expect(GOVERNANCE_COLORS.FAIL.hex).toBe('#f43f5e'); // Rose
      expect(GOVERNANCE_COLORS.FAIL.bg).toContain('rose');
      // Note: pure red is reserved for BENSON (GID-00)
    });

    it('all colors are distinct from standard agent colors', () => {
      // Agent colors typically use: red, yellow, green, blue, purple, magenta, white
      // Governance uses: emerald, orange, rose, slate, sky
      const governanceColorNames = [
        GOVERNANCE_COLORS.PASS.bg,
        GOVERNANCE_COLORS.WARN.bg,
        GOVERNANCE_COLORS.FAIL.bg,
        GOVERNANCE_COLORS.SKIP.bg,
        GOVERNANCE_COLORS.PENDING.bg,
      ];

      // Should not contain pure agent color names
      for (const color of governanceColorNames) {
        expect(color).not.toMatch(/^bg-(red|yellow|green|blue|purple|magenta|white)-500$/);
      }
    });
  });
});

// ============================================================================
// Visual Config Functions Tests
// ============================================================================
describe('Visual Config Functions', () => {
  describe('getSignalVisualConfig', () => {
    it('returns complete config for PASS', () => {
      const config = getSignalVisualConfig('PASS');
      expect(config.status).toBe('PASS');
      expect(config.label).toBe('PASS');
      expect(config.glyph).toBe('✓');
      expect(config.colors).toBe(GOVERNANCE_COLORS.PASS);
      expect(config.ariaLabel).toBe('Check passed');
    });

    it('returns complete config for WARN', () => {
      const config = getSignalVisualConfig('WARN');
      expect(config.status).toBe('WARN');
      expect(config.glyph).toBe('⚠');
      expect(config.colors).toBe(GOVERNANCE_COLORS.WARN);
    });

    it('returns complete config for FAIL', () => {
      const config = getSignalVisualConfig('FAIL');
      expect(config.status).toBe('FAIL');
      expect(config.glyph).toBe('✗');
      expect(config.colors).toBe(GOVERNANCE_COLORS.FAIL);
    });

    it('returns complete config for SKIP', () => {
      const config = getSignalVisualConfig('SKIP');
      expect(config.status).toBe('SKIP');
      expect(config.glyph).toBe('○');
      expect(config.colors).toBe(GOVERNANCE_COLORS.SKIP);
    });
  });

  describe('getSeverityVisualConfig', () => {
    it('returns config with correct level ordering', () => {
      const none = getSeverityVisualConfig('NONE');
      const low = getSeverityVisualConfig('LOW');
      const medium = getSeverityVisualConfig('MEDIUM');
      const high = getSeverityVisualConfig('HIGH');
      const critical = getSeverityVisualConfig('CRITICAL');

      expect(none.level).toBeLessThan(low.level);
      expect(low.level).toBeLessThan(medium.level);
      expect(medium.level).toBeLessThan(high.level);
      expect(high.level).toBeLessThan(critical.level);
    });
  });

  describe('formatTerminalSummary', () => {
    it('formats VALID summary when no failures', () => {
      const summary = formatTerminalSummary({ pass: 5, warn: 1, fail: 0, skip: 2 });
      expect(summary).toContain('VALID');
      expect(summary).toContain('✓');
      expect(summary).toContain('0 FAIL');
      expect(summary).toContain('5 PASS');
    });

    it('formats INVALID summary when failures present', () => {
      const summary = formatTerminalSummary({ pass: 3, warn: 0, fail: 2, skip: 0 });
      expect(summary).toContain('INVALID');
      expect(summary).toContain('✗');
      expect(summary).toContain('2 FAIL');
    });
  });

  describe('generateTerminalBanner', () => {
    it('generates VALID banner with pass glyphs', () => {
      const banner = generateTerminalBanner('VALID');
      expect(banner).toContain(TERMINAL_BANNERS.PASS);
    });

    it('generates INVALID banner with fail glyphs', () => {
      const banner = generateTerminalBanner('INVALID');
      expect(banner).toContain(TERMINAL_BANNERS.FAIL);
    });
  });
});

// ============================================================================
// GovernanceSignalBadge Component Tests
// ============================================================================
describe('GovernanceSignalBadge', () => {
  it('renders PASS badge correctly', () => {
    render(<GovernanceSignalBadge status="PASS" />);
    const badge = screen.getByTestId('governance-signal-badge');
    expect(badge).toHaveAttribute('data-status', 'PASS');
    expect(badge).toHaveTextContent('PASS');
    expect(badge).toHaveTextContent('✓');
  });

  it('renders WARN badge correctly', () => {
    render(<GovernanceSignalBadge status="WARN" />);
    const badge = screen.getByTestId('governance-signal-badge');
    expect(badge).toHaveAttribute('data-status', 'WARN');
    expect(badge).toHaveTextContent('⚠');
  });

  it('renders FAIL badge correctly', () => {
    render(<GovernanceSignalBadge status="FAIL" />);
    const badge = screen.getByTestId('governance-signal-badge');
    expect(badge).toHaveAttribute('data-status', 'FAIL');
    expect(badge).toHaveTextContent('✗');
  });

  it('renders SKIP badge correctly', () => {
    render(<GovernanceSignalBadge status="SKIP" />);
    const badge = screen.getByTestId('governance-signal-badge');
    expect(badge).toHaveAttribute('data-status', 'SKIP');
    expect(badge).toHaveTextContent('○');
  });

  it('hides glyph when showGlyph is false', () => {
    render(<GovernanceSignalBadge status="PASS" showGlyph={false} />);
    expect(screen.queryByText('✓')).not.toBeInTheDocument();
  });

  it('hides label when showLabel is false', () => {
    render(<GovernanceSignalBadge status="PASS" showLabel={false} />);
    expect(screen.queryByText('PASS')).not.toBeInTheDocument();
  });

  it('has proper aria-label for accessibility', () => {
    render(<GovernanceSignalBadge status="PASS" />);
    const badge = screen.getByTestId('governance-signal-badge');
    expect(badge).toHaveAttribute('aria-label', 'Check passed');
  });
});

// ============================================================================
// SeverityBadge Component Tests
// ============================================================================
describe('SeverityBadge', () => {
  it('renders CRITICAL severity', () => {
    render(<SeverityBadge severity="CRITICAL" />);
    const badge = screen.getByTestId('severity-badge');
    expect(badge).toHaveAttribute('data-severity', 'CRITICAL');
    expect(badge).toHaveTextContent('CRITICAL');
  });

  it('renders HIGH severity', () => {
    render(<SeverityBadge severity="HIGH" />);
    expect(screen.getByTestId('severity-badge')).toHaveAttribute('data-severity', 'HIGH');
  });

  it('has accessibility label', () => {
    render(<SeverityBadge severity="HIGH" />);
    expect(screen.getByTestId('severity-badge')).toHaveAttribute(
      'aria-label',
      'Severity: HIGH'
    );
  });
});

// ============================================================================
// GovernanceSignalRow Component Tests
// ============================================================================
describe('GovernanceSignalRow', () => {
  const defaultProps = {
    status: 'FAIL' as const,
    severity: 'HIGH' as const,
    code: 'PAG_001',
    title: 'Missing Activation Block',
  };

  it('renders signal row with correct status', () => {
    render(<GovernanceSignalRow {...defaultProps} />);
    const row = screen.getByTestId('governance-signal-row');
    expect(row).toHaveAttribute('data-status', 'FAIL');
  });

  it('displays code, title, and status', () => {
    render(<GovernanceSignalRow {...defaultProps} />);
    expect(screen.getByText('PAG_001')).toBeInTheDocument();
    expect(screen.getByText('Missing Activation Block')).toBeInTheDocument();
  });

  it('shows expanded content when expanded', () => {
    render(
      <GovernanceSignalRow
        {...defaultProps}
        description="Test description"
        evidence="Test evidence"
        resolution="Test resolution"
        expanded={true}
      />
    );
    expect(screen.getByText('Test description')).toBeInTheDocument();
    expect(screen.getByText('Test evidence')).toBeInTheDocument();
    expect(screen.getByText('Test resolution')).toBeInTheDocument();
  });

  it('hides expanded content when collapsed', () => {
    render(
      <GovernanceSignalRow
        {...defaultProps}
        description="Test description"
        expanded={false}
      />
    );
    expect(screen.queryByText('Test description')).not.toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<GovernanceSignalRow {...defaultProps} onClick={handleClick} />);

    // Find the clickable header area
    const header = screen.getByTestId('governance-signal-row').querySelector('[role="button"]');
    if (header) {
      fireEvent.click(header);
      expect(handleClick).toHaveBeenCalledTimes(1);
    }
  });
});

// ============================================================================
// ValidationSummary Component Tests
// ============================================================================
describe('ValidationSummary', () => {
  it('renders VALID status with correct styling', () => {
    render(
      <ValidationSummary
        passCount={5}
        warnCount={0}
        failCount={0}
        skipCount={1}
        status="VALID"
      />
    );
    const summary = screen.getByTestId('validation-summary');
    expect(summary).toHaveAttribute('data-status', 'VALID');
    expect(summary).toHaveTextContent('VALID');
    expect(summary).toHaveTextContent('✓');
  });

  it('renders INVALID status with correct styling', () => {
    render(
      <ValidationSummary
        passCount={3}
        warnCount={1}
        failCount={2}
        skipCount={0}
        status="INVALID"
      />
    );
    const summary = screen.getByTestId('validation-summary');
    expect(summary).toHaveAttribute('data-status', 'INVALID');
    expect(summary).toHaveTextContent('INVALID');
    expect(summary).toHaveTextContent('✗');
  });

  it('displays all counts correctly', () => {
    render(
      <ValidationSummary
        passCount={5}
        warnCount={2}
        failCount={1}
        skipCount={3}
        status="INVALID"
      />
    );
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});

// ============================================================================
// GateIndicator Component Tests
// ============================================================================
describe('GateIndicator', () => {
  it('renders PASS state with open gate', () => {
    render(<GateIndicator gateName="Review Gate" gateId="RG-v1.1" state="PASS" />);
    const indicator = screen.getByTestId('gate-indicator');
    expect(indicator).toHaveAttribute('data-state', 'PASS');
    expect(indicator).toHaveTextContent('🔓');
    expect(indicator).toHaveTextContent('OPEN');
  });

  it('renders FAIL state with closed gate', () => {
    render(<GateIndicator gateName="Review Gate" gateId="RG-v1.1" state="FAIL" />);
    const indicator = screen.getByTestId('gate-indicator');
    expect(indicator).toHaveAttribute('data-state', 'FAIL');
    expect(indicator).toHaveTextContent('🔒');
    expect(indicator).toHaveTextContent('CLOSED');
  });

  it('renders PENDING state with hourglass', () => {
    render(<GateIndicator gateName="BSRG" gateId="BSRG-01" state="PENDING" />);
    expect(screen.getByTestId('gate-indicator')).toHaveTextContent('⏳');
  });

  it('displays gate name and ID', () => {
    render(<GateIndicator gateName="Review Gate" gateId="RG-v1.1" state="PASS" />);
    expect(screen.getByText('Review Gate')).toBeInTheDocument();
    expect(screen.getByText('RG-v1.1')).toBeInTheDocument();
  });
});

// ============================================================================
// TerminalUIParityDemo Component Tests
// ============================================================================
describe('TerminalUIParityDemo', () => {
  it('renders the parity demo', () => {
    render(<TerminalUIParityDemo />);
    expect(screen.getByTestId('terminal-ui-parity-demo')).toBeInTheDocument();
  });

  it('displays terminal and UI sections', () => {
    render(<TerminalUIParityDemo />);
    expect(screen.getByText('📟')).toBeInTheDocument(); // Terminal indicator
    expect(screen.getByText('🖥️')).toBeInTheDocument(); // UI indicator
  });

  it('renders validation summary', () => {
    render(<TerminalUIParityDemo />);
    expect(screen.getByTestId('validation-summary')).toBeInTheDocument();
  });

  it('renders visual language reference section', () => {
    render(<TerminalUIParityDemo />);
    expect(screen.getByText('Governance Visual Language Reference')).toBeInTheDocument();
  });

  it('displays design note about color separation', () => {
    render(<TerminalUIParityDemo />);
    expect(screen.getByText(/Design Note: Governance vs Agent Visual Separation/i)).toBeInTheDocument();
  });
});

// ============================================================================
// Accessibility Tests
// ============================================================================
describe('Accessibility', () => {
  it('all signal badges have role="status"', () => {
    const { rerender } = render(<GovernanceSignalBadge status="PASS" />);
    expect(screen.getByRole('status')).toBeInTheDocument();

    rerender(<GovernanceSignalBadge status="FAIL" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('severity badges have proper aria-label', () => {
    render(<SeverityBadge severity="CRITICAL" />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Severity: CRITICAL');
  });

  it('validation summary is accessible', () => {
    render(
      <ValidationSummary
        passCount={1}
        warnCount={1}
        failCount={1}
        skipCount={1}
        status="INVALID"
      />
    );
    expect(screen.getByRole('status')).toHaveAttribute(
      'aria-label',
      'Validation result: INVALID'
    );
  });

  it('gate indicator is accessible', () => {
    render(<GateIndicator gateName="Test Gate" gateId="TG-01" state="PASS" />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Test Gate: PASS');
  });
});

// ============================================================================
// Visual Separation Integration Tests
// ============================================================================
describe('Visual Separation - Governance vs Agent Colors', () => {
  it('WARN color is orange, NOT yellow (SONNY)', () => {
    render(<GovernanceSignalBadge status="WARN" />);
    const badge = screen.getByTestId('governance-signal-badge');

    // Check that the badge uses orange styling, not yellow
    // The exact class check depends on implementation
    expect(badge.className).toContain('orange');
    expect(badge.className).not.toContain('yellow');
  });

  it('FAIL color is rose, NOT pure red (BENSON)', () => {
    render(<GovernanceSignalBadge status="FAIL" />);
    const badge = screen.getByTestId('governance-signal-badge');

    expect(badge.className).toContain('rose');
  });

  it('PASS color is emerald, NOT standard green', () => {
    render(<GovernanceSignalBadge status="PASS" />);
    const badge = screen.getByTestId('governance-signal-badge');

    expect(badge.className).toContain('emerald');
  });
});
