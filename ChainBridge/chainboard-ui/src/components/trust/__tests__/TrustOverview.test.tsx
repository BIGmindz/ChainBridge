/**
 * Trust Overview Tests — PAC-TRUST-CENTER-UI-01
 *
 * Tests for customer-facing Trust Overview component.
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { TrustOverview } from '../TrustOverview';
import type { GovernanceFingerprint, AuditBundleMetadata, GamedaySummary } from '../../../types/trust';

const mockFingerprint: GovernanceFingerprint = {
  fingerprint_hash: 'sha256:abc123',
  timestamp: '2025-12-17T00:00:00Z',
  schema_version: '1.0.0',
};

const mockAuditBundle: AuditBundleMetadata = {
  bundle_id: 'test-bundle-001',
  created_at: '2025-12-17T10:00:00Z',
  bundle_hash: 'sha256:def456',
  status: 'offline-verifiable',
};

const mockGameday: GamedaySummary = {
  scenarios_tested: 100,
  silent_failures: 0,
  fail_closed_all: true,
};

describe('TrustOverview', () => {
  it('renders governance overview title', () => {
    render(<TrustOverview />);
    expect(screen.getByText('Governance Overview')).toBeInTheDocument();
  });

  it('renders static governance statement', () => {
    render(<TrustOverview />);
    expect(screen.getByText(/ChainBridge operates with enforced governance controls/)).toBeInTheDocument();
  });

  it('displays fingerprint hash when provided', () => {
    render(<TrustOverview fingerprint={mockFingerprint} />);
    expect(screen.getByText('sha256:abc123')).toBeInTheDocument();
  });

  it('displays bundle id when provided', () => {
    render(
      <TrustOverview
        fingerprint={mockFingerprint}
        auditBundle={mockAuditBundle}
      />
    );
    expect(screen.getByText('test-bundle-001')).toBeInTheDocument();
  });

  it('shows unavailable when no data', () => {
    render(<TrustOverview />);
    expect(screen.getAllByText('Unavailable')).toHaveLength(3);
  });

  it('shows completed when gameday present', () => {
    render(<TrustOverview gameday={mockGameday} />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<TrustOverview className="test-class" />);
    expect(container.firstChild).toHaveClass('test-class');
  });
});
