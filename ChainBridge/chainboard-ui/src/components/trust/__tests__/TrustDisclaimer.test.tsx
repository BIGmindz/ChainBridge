/**
 * Trust Disclaimer Tests — PAC-TRUST-CENTER-UI-01
 *
 * Tests for customer-facing Trust Disclaimer component.
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { TrustDisclaimer } from '../TrustDisclaimer';

describe('TrustDisclaimer', () => {
  it('renders disclaimer text', () => {
    render(<TrustDisclaimer />);
    expect(
      screen.getByText(/This Trust Center does not grant access/)
    ).toBeInTheDocument();
  });

  it('includes read-only statement', () => {
    render(<TrustDisclaimer />);
    expect(
      screen.getByText(/All data shown is read-only and informational/)
    ).toBeInTheDocument();
  });

  it('has no interactive elements', () => {
    render(<TrustDisclaimer />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<TrustDisclaimer className="test-class" />);
    expect(container.firstChild).toHaveClass('test-class');
  });
});
