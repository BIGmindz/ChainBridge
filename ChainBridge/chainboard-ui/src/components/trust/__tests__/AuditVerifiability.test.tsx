/**
 * Audit Verifiability Tests — PAC-TRUST-CENTER-UI-01
 *
 * Tests for customer-facing Audit Verifiability component.
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { AuditVerifiability } from '../AuditVerifiability';
import type { AuditBundleMetadata } from '../../../types/trust';

const mockAuditBundle: AuditBundleMetadata = {
  bundle_id: 'test-bundle-001',
  created_at: '2025-12-17T10:00:00Z',
  bundle_hash: 'sha256:abc123def456',
  status: 'offline-verifiable',
};

describe('AuditVerifiability', () => {
  beforeEach(() => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it('renders audit verifiability title', () => {
    render(<AuditVerifiability />);
    expect(screen.getByText('Audit Verifiability')).toBeInTheDocument();
  });

  it('displays bundle hash when provided', () => {
    render(<AuditVerifiability auditBundle={mockAuditBundle} />);
    expect(screen.getByText('sha256:abc123def456')).toBeInTheDocument();
  });

  it('shows unavailable when no bundle', () => {
    render(<AuditVerifiability />);
    expect(screen.getAllByText('Unavailable')).toHaveLength(2);
  });

  it('renders copy button when hash available', () => {
    render(<AuditVerifiability auditBundle={mockAuditBundle} />);
    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument();
  });

  it('does not render copy button without hash', () => {
    render(<AuditVerifiability />);
    expect(screen.queryByRole('button', { name: /copy/i })).not.toBeInTheDocument();
  });

  it('copies hash to clipboard on click', async () => {
    render(<AuditVerifiability auditBundle={mockAuditBundle} />);
    const copyButton = screen.getByRole('button', { name: /copy/i });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('sha256:abc123def456');
    });
  });

  it('shows confirmation after copy', async () => {
    render(<AuditVerifiability auditBundle={mockAuditBundle} />);
    const copyButton = screen.getByRole('button', { name: /copy/i });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(screen.getByText('Copied')).toBeInTheDocument();
    });
  });

  it('displays offline verification status', () => {
    render(<AuditVerifiability auditBundle={mockAuditBundle} />);
    expect(screen.getByText('YES')).toBeInTheDocument();
  });

  it('displays schema version', () => {
    render(<AuditVerifiability schemaVersion="2.0.0" />);
    expect(screen.getByText('2.0.0')).toBeInTheDocument();
  });

  it('renders verification explanation', () => {
    render(<AuditVerifiability />);
    expect(
      screen.getByText(/Audit bundles can be independently verified/)
    ).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<AuditVerifiability className="test-class" />);
    expect(container.firstChild).toHaveClass('test-class');
  });
});
