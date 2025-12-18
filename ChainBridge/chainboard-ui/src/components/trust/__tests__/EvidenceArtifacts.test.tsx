/**
 * Evidence Artifacts Tests — PAC-SONNY-TRUST-UI-REDUCTION-01
 *
 * Tests for stripped-down Evidence Artifacts component.
 *
 * @see PAC-SONNY-TRUST-UI-REDUCTION-01
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { EvidenceArtifacts } from '../EvidenceArtifacts';
import type { AuditBundleMetadata } from '../../../types/trust';

const mockBundle: AuditBundleMetadata = {
  bundle_id: 'test-bundle-001',
  created_at: '2025-12-17T10:00:00Z',
  bundle_hash: 'sha256:abc123',
  status: 'offline-verifiable',
};

describe('EvidenceArtifacts', () => {
  it('renders artifact label', () => {
    render(<EvidenceArtifacts />);
    expect(screen.getByText('Audit Bundle')).toBeInTheDocument();
  });

  it('renders source path', () => {
    render(<EvidenceArtifacts />);
    expect(screen.getByText('proofpacks/audit_bundle.json')).toBeInTheDocument();
  });

  it('renders what this shows', () => {
    render(<EvidenceArtifacts />);
    expect(screen.getByText('Metadata for the latest generated audit bundle.')).toBeInTheDocument();
  });

  it('displays bundle data when provided', () => {
    render(<EvidenceArtifacts bundle={mockBundle} />);
    expect(screen.getByText('test-bundle-001')).toBeInTheDocument();
    expect(screen.getByText('sha256:abc123')).toBeInTheDocument();
    expect(screen.getByText('2025-12-17T10:00:00Z')).toBeInTheDocument();
  });

  it('shows dashes when no bundle', () => {
    render(<EvidenceArtifacts />);
    expect(screen.getAllByText('—')).toHaveLength(3);
  });

  it('renders verification instruction', () => {
    render(<EvidenceArtifacts />);
    expect(screen.getByText(/compute SHA-256/)).toBeInTheDocument();
  });

  it('has no icons', () => {
    const { container } = render(<EvidenceArtifacts bundle={mockBundle} />);
    expect(container.querySelector('svg')).toBeNull();
  });
});
