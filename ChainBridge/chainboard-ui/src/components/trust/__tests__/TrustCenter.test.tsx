/**
 * Trust Center Tests — PAC-TRUST-CENTER-01
 *
 * Tests verify:
 * - No interactive elements exist
 * - Empty states render correctly
 * - All sections display read-only data
 * - Non-claims section is present
 * - No buttons, toggles, filters, or controls
 *
 * @see PAC-TRUST-CENTER-01 — Public Trust Center (Read-Only)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TrustEmptyState } from '../TrustEmptyState';
import { TrustFingerprintCard } from '../TrustFingerprintCard';
import { TrustCoverageList } from '../TrustCoverageList';
import { TrustAuditBundleCard } from '../TrustAuditBundleCard';
import { TrustGamedaySummary } from '../TrustGamedaySummary';
import { TrustNonClaims } from '../TrustNonClaims';
import type {
  GovernanceFingerprint,
  AuditBundleMetadata,
  GamedaySummary,
} from '../../../types/trust';

// Test fixtures
const validFingerprint: GovernanceFingerprint = {
  fingerprint_hash: 'sha256:abc123def456',
  timestamp: '2025-12-17T10:00:00Z',
  schema_version: '1.0.0',
};

const validBundle: AuditBundleMetadata = {
  bundle_id: 'bundle-001',
  created_at: '2025-12-17T10:00:00Z',
  bundle_hash: 'sha256:xyz789',
  status: 'offline-verifiable',
};

const validGameday: GamedaySummary = {
  scenarios_tested: 133,
  silent_failures: 0,
  fail_closed_all: true,
};

describe('TrustEmptyState', () => {
  it('renders section name in empty state', () => {
    render(<TrustEmptyState section="Test Section" />);
    expect(screen.getByText('Test Section data unavailable')).toBeInTheDocument();
  });

  it('does not contain any interactive elements', () => {
    const { container } = render(<TrustEmptyState section="Test" />);

    const buttons = container.querySelectorAll('button, a, [role="button"]');
    const inputs = container.querySelectorAll('input, textarea, select');

    expect(buttons).toHaveLength(0);
    expect(inputs).toHaveLength(0);
  });
});

describe('TrustFingerprintCard', () => {
  it('renders fingerprint data when provided', () => {
    render(<TrustFingerprintCard fingerprint={validFingerprint} />);

    expect(screen.getByText('sha256:abc123def456')).toBeInTheDocument();
    expect(screen.getByText('2025-12-17T10:00:00Z')).toBeInTheDocument();
    expect(screen.getByText('1.0.0')).toBeInTheDocument();
  });

  it('renders exact copy text', () => {
    render(<TrustFingerprintCard fingerprint={validFingerprint} />);

    expect(screen.getByText(
      'This fingerprint represents the current governance configuration. Any change produces a new hash.'
    )).toBeInTheDocument();
  });

  it('renders empty state when fingerprint missing', () => {
    render(<TrustFingerprintCard fingerprint={undefined} />);

    expect(screen.getByText('Governance Fingerprint data unavailable')).toBeInTheDocument();
  });

  it('does not contain any interactive elements', () => {
    const { container } = render(<TrustFingerprintCard fingerprint={validFingerprint} />);

    const buttons = container.querySelectorAll('button, a, [role="button"]');
    const inputs = container.querySelectorAll('input, textarea, select');

    expect(buttons).toHaveLength(0);
    expect(inputs).toHaveLength(0);
  });
});

describe('TrustCoverageList', () => {
  it('renders default coverage items', () => {
    render(<TrustCoverageList />);

    expect(screen.getByText('ACM enforcement')).toBeInTheDocument();
    expect(screen.getByText('DRCP escalation')).toBeInTheDocument();
    expect(screen.getByText('Diggi corrections')).toBeInTheDocument();
    expect(screen.getByText('Artifact integrity verification')).toBeInTheDocument();
    expect(screen.getByText('Scope guard enforcement')).toBeInTheDocument();
    expect(screen.getByText('Fail-closed execution binding')).toBeInTheDocument();
  });

  it('shows presence indicators only — no metrics', () => {
    render(<TrustCoverageList />);

    // Should have "present" text for presence indication
    const presentIndicators = screen.getAllByText('present');
    expect(presentIndicators.length).toBeGreaterThan(0);
  });

  it('renders empty state for empty array', () => {
    render(<TrustCoverageList coverage={[]} />);

    expect(screen.getByText('Governance Coverage data unavailable')).toBeInTheDocument();
  });

  it('does not contain any interactive elements', () => {
    const { container } = render(<TrustCoverageList />);

    const buttons = container.querySelectorAll('button, a, [role="button"]');
    const inputs = container.querySelectorAll('input, textarea, select');

    expect(buttons).toHaveLength(0);
    expect(inputs).toHaveLength(0);
  });
});

describe('TrustAuditBundleCard', () => {
  it('renders bundle data when provided', () => {
    render(<TrustAuditBundleCard bundle={validBundle} />);

    expect(screen.getByText('bundle-001')).toBeInTheDocument();
    expect(screen.getByText('sha256:xyz789')).toBeInTheDocument();
    expect(screen.getByText('Offline-verifiable')).toBeInTheDocument();
  });

  it('renders verification command snippet', () => {
    render(<TrustAuditBundleCard bundle={validBundle} />);

    expect(screen.getByText(/python verify_audit_bundle.py/)).toBeInTheDocument();
  });

  it('renders empty state when bundle missing', () => {
    render(<TrustAuditBundleCard bundle={undefined} />);

    expect(screen.getByText('Audit Bundle data unavailable')).toBeInTheDocument();
  });

  it('does not contain any interactive elements', () => {
    const { container } = render(<TrustAuditBundleCard bundle={validBundle} />);

    const buttons = container.querySelectorAll('button, a, [role="button"]');
    const inputs = container.querySelectorAll('input, textarea, select');

    expect(buttons).toHaveLength(0);
    expect(inputs).toHaveLength(0);
  });
});

describe('TrustGamedaySummary', () => {
  it('renders gameday data as text', () => {
    render(<TrustGamedaySummary gameday={validGameday} />);

    expect(screen.getByText('133 adversarial scenarios tested')).toBeInTheDocument();
    expect(screen.getByText('0 silent failures')).toBeInTheDocument();
    expect(screen.getByText('Fail-closed in all cases')).toBeInTheDocument();
  });

  it('renders source reference', () => {
    render(<TrustGamedaySummary gameday={validGameday} />);

    expect(screen.getByText('Source: PAC-GOV-GAMEDAY-01')).toBeInTheDocument();
  });

  it('renders empty state when gameday missing', () => {
    render(<TrustGamedaySummary gameday={undefined} />);

    expect(screen.getByText('Adversarial Testing data unavailable')).toBeInTheDocument();
  });

  it('does not contain any interactive elements', () => {
    const { container } = render(<TrustGamedaySummary gameday={validGameday} />);

    const buttons = container.querySelectorAll('button, a, [role="button"]');
    const inputs = container.querySelectorAll('input, textarea, select');

    expect(buttons).toHaveLength(0);
    expect(inputs).toHaveLength(0);
  });

  it('does not contain charts or visualizations', () => {
    const { container } = render(<TrustGamedaySummary gameday={validGameday} />);

    const charts = container.querySelectorAll('svg[role="img"], canvas, .chart');
    // Only icons allowed, no chart elements
    expect(charts).toHaveLength(0);
  });
});

describe('TrustNonClaims', () => {
  it('renders all mandatory non-claim statements', () => {
    render(<TrustNonClaims />);

    expect(screen.getByText('This does not guarantee correctness')).toBeInTheDocument();
    expect(screen.getByText('This does not imply coverage completeness')).toBeInTheDocument();
    expect(screen.getByText('This is not external certification')).toBeInTheDocument();
  });

  it('renders Non-Claims header', () => {
    render(<TrustNonClaims />);

    expect(screen.getByText('Non-Claims')).toBeInTheDocument();
  });

  it('does not contain any interactive elements', () => {
    const { container } = render(<TrustNonClaims />);

    const buttons = container.querySelectorAll('button, a, [role="button"]');
    const inputs = container.querySelectorAll('input, textarea, select');

    expect(buttons).toHaveLength(0);
    expect(inputs).toHaveLength(0);
  });
});

describe('Trust Center — No Interactivity Verification', () => {
  it('no buttons exist across all components', () => {
    const { container } = render(
      <>
        <TrustFingerprintCard fingerprint={validFingerprint} />
        <TrustCoverageList />
        <TrustAuditBundleCard bundle={validBundle} />
        <TrustGamedaySummary gameday={validGameday} />
        <TrustNonClaims />
      </>
    );

    const buttons = container.querySelectorAll('button');
    expect(buttons).toHaveLength(0);
  });

  it('no links exist across all components', () => {
    const { container } = render(
      <>
        <TrustFingerprintCard fingerprint={validFingerprint} />
        <TrustCoverageList />
        <TrustAuditBundleCard bundle={validBundle} />
        <TrustGamedaySummary gameday={validGameday} />
        <TrustNonClaims />
      </>
    );

    const links = container.querySelectorAll('a');
    expect(links).toHaveLength(0);
  });

  it('no form inputs exist across all components', () => {
    const { container } = render(
      <>
        <TrustFingerprintCard fingerprint={validFingerprint} />
        <TrustCoverageList />
        <TrustAuditBundleCard bundle={validBundle} />
        <TrustGamedaySummary gameday={validGameday} />
        <TrustNonClaims />
      </>
    );

    const inputs = container.querySelectorAll('input, textarea, select');
    expect(inputs).toHaveLength(0);
  });

  it('no toggle or checkbox elements exist', () => {
    const { container } = render(
      <>
        <TrustFingerprintCard fingerprint={validFingerprint} />
        <TrustCoverageList />
        <TrustAuditBundleCard bundle={validBundle} />
        <TrustGamedaySummary gameday={validGameday} />
        <TrustNonClaims />
      </>
    );

    const toggles = container.querySelectorAll('[role="switch"], [role="checkbox"]');
    expect(toggles).toHaveLength(0);
  });
});
