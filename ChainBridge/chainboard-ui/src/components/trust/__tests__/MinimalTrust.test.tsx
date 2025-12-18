/**
 * Minimal Trust UI Tests — PAC-SONNY-TRUST-MIN-UI-01
 *
 * Tests for minimum evidence-only components.
 *
 * @see PAC-SONNY-TRUST-MIN-UI-01
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { GovernanceArtifact } from '../GovernanceArtifact';
import { AuditBundle } from '../AuditBundle';
import { AdversarialTesting } from '../AdversarialTesting';
import { NonClaims } from '../NonClaims';
import type { GovernanceFingerprint, AuditBundleMetadata } from '../../../types/trust';

const mockFingerprint: GovernanceFingerprint = {
  fingerprint_hash: 'sha256:abc123',
  timestamp: '2025-12-17T00:00:00Z',
  schema_version: '1.0.0',
};

const mockBundle: AuditBundleMetadata = {
  bundle_id: 'test-bundle',
  created_at: '2025-12-17T10:00:00Z',
  bundle_hash: 'sha256:def456',
  status: 'offline-verifiable',
};

describe('GovernanceArtifact', () => {
  it('renders section label', () => {
    render(<GovernanceArtifact />);
    expect(screen.getByText('Governance Fingerprint')).toBeInTheDocument();
  });

  it('renders literal data fields', () => {
    render(<GovernanceArtifact fingerprint={mockFingerprint} />);
    expect(screen.getByText('sha256:abc123')).toBeInTheDocument();
    expect(screen.getByText('2025-12-17T00:00:00Z')).toBeInTheDocument();
    expect(screen.getByText('1.0.0')).toBeInTheDocument();
  });

  it('has no icons', () => {
    const { container } = render(<GovernanceArtifact fingerprint={mockFingerprint} />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('has no interpretation text', () => {
    const { container } = render(<GovernanceArtifact fingerprint={mockFingerprint} />);
    const text = container.textContent || '';
    expect(text).not.toContain('shows');
    expect(text).not.toContain('means');
    expect(text).not.toContain('ensures');
  });
});

describe('AuditBundle', () => {
  it('renders section label', () => {
    render(<AuditBundle />);
    expect(screen.getByText('Audit Bundle')).toBeInTheDocument();
  });

  it('renders literal data fields', () => {
    render(<AuditBundle bundle={mockBundle} />);
    expect(screen.getByText('test-bundle')).toBeInTheDocument();
    expect(screen.getByText('sha256:def456')).toBeInTheDocument();
    expect(screen.getByText('2025-12-17T10:00:00Z')).toBeInTheDocument();
  });

  it('renders verification command', () => {
    render(<AuditBundle bundle={mockBundle} />);
    expect(screen.getByText('sha256sum proofpacks/audit_bundle.json')).toBeInTheDocument();
  });

  it('has no icons', () => {
    const { container } = render(<AuditBundle bundle={mockBundle} />);
    expect(container.querySelector('svg')).toBeNull();
  });
});

describe('AdversarialTesting', () => {
  it('renders section label', () => {
    render(<AdversarialTesting />);
    expect(screen.getByText('Adversarial Testing')).toBeInTheDocument();
  });

  it('renders literal data fields', () => {
    render(<AdversarialTesting testCount={100} lastRun="2025-12-17T12:00:00Z" />);
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('2025-12-17T12:00:00Z')).toBeInTheDocument();
  });

  it('renders suite location', () => {
    render(<AdversarialTesting />);
    expect(screen.getByText('tests/governance/gameday/')).toBeInTheDocument();
  });

  it('has no icons', () => {
    const { container } = render(<AdversarialTesting />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('has no summary language', () => {
    const { container } = render(<AdversarialTesting testCount={100} lastRun="2025-12-17" />);
    const text = container.textContent || '';
    expect(text).not.toContain('passed');
    expect(text).not.toContain('failed');
    expect(text).not.toContain('status');
    expect(text).not.toContain('validated');
  });
});

describe('NonClaims', () => {
  it('renders section label', () => {
    render(<NonClaims />);
    expect(screen.getByText('Non-Claims')).toBeInTheDocument();
  });

  it('renders source file', () => {
    render(<NonClaims />);
    expect(screen.getByText('docs/trust/TRUST_NON_CLAIMS.md')).toBeInTheDocument();
  });

  it('renders all 14 TNC IDs', () => {
    render(<NonClaims />);
    const tncIds = [
      'TNC-SEC-01:', 'TNC-SEC-02:', 'TNC-SEC-03:', 'TNC-SEC-04:',
      'TNC-COMP-01:', 'TNC-COMP-02:',
      'TNC-CORR-01:', 'TNC-CORR-02:',
      'TNC-CERT-01:', 'TNC-CERT-02:',
      'TNC-AVAIL-01:',
      'TNC-ATK-01:', 'TNC-ATK-02:', 'TNC-ATK-03:',
    ];
    tncIds.forEach((id) => {
      expect(screen.getByText(id)).toBeInTheDocument();
    });
  });

  it('has no icons', () => {
    const { container } = render(<NonClaims />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('has no interpretation text', () => {
    const { container } = render(<NonClaims />);
    const text = container.textContent || '';
    expect(text).not.toContain('What this');
    expect(text).not.toContain('shows');
  });
});
