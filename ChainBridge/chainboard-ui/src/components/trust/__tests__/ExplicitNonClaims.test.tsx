/**
 * Explicit Non-Claims Tests — PAC-SONNY-TRUST-UI-REDUCTION-01
 *
 * Tests for verbatim non-claims component.
 *
 * @see PAC-SONNY-TRUST-UI-REDUCTION-01
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ExplicitNonClaims } from '../ExplicitNonClaims';

describe('ExplicitNonClaims', () => {
  it('renders artifact label', () => {
    render(<ExplicitNonClaims />);
    expect(screen.getByText('Non-Claims')).toBeInTheDocument();
  });

  it('renders source path', () => {
    render(<ExplicitNonClaims />);
    expect(screen.getByText('docs/trust/TRUST_NON_CLAIMS.md')).toBeInTheDocument();
  });

  it('renders what this shows', () => {
    render(<ExplicitNonClaims />);
    expect(screen.getByText('Explicit statements of what ChainBridge does not claim.')).toBeInTheDocument();
  });

  it('renders verbatim non-claims with IDs', () => {
    render(<ExplicitNonClaims />);
    // Check TNC IDs are present
    expect(screen.getByText('TNC-SEC-01')).toBeInTheDocument();
    expect(screen.getByText('TNC-SEC-02')).toBeInTheDocument();
    expect(screen.getByText('TNC-CERT-01')).toBeInTheDocument();
  });

  it('renders verbatim non-claim text', () => {
    render(<ExplicitNonClaims />);
    expect(screen.getByText('ChainBridge does not secure infrastructure.')).toBeInTheDocument();
    expect(screen.getByText('ChainBridge governance is not externally certified.')).toBeInTheDocument();
    expect(screen.getByText('ChainBridge does not guarantee availability.')).toBeInTheDocument();
  });

  it('renders all 14 non-claims', () => {
    render(<ExplicitNonClaims />);
    const tncIds = [
      'TNC-SEC-01', 'TNC-SEC-02', 'TNC-SEC-03', 'TNC-SEC-04',
      'TNC-COMP-01', 'TNC-COMP-02',
      'TNC-CORR-01', 'TNC-CORR-02',
      'TNC-CERT-01', 'TNC-CERT-02',
      'TNC-AVAIL-01',
      'TNC-ATK-01', 'TNC-ATK-02', 'TNC-ATK-03',
    ];
    tncIds.forEach((id) => {
      expect(screen.getByText(id)).toBeInTheDocument();
    });
  });

  it('has no icons', () => {
    const { container } = render(<ExplicitNonClaims />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('does not contain forbidden words', () => {
    const { container } = render(<ExplicitNonClaims />);
    const text = container.textContent || '';
    // No security-implying adjectives
    expect(text).not.toContain('secure');
    expect(text).not.toContain('safe');
    expect(text).not.toContain('protected');
    expect(text).not.toContain('guaranteed');
  });
});
