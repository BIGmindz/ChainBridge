/**
 * PDOArtifacts Tests — PAC-SONNY-TRUST-HARDEN-01
 *
 * Tests for PDO Artifacts component.
 * Validates read-only evidence rendering.
 *
 * @see PAC-SONNY-TRUST-HARDEN-01 — Trust Center Evidence-Only Hardening
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PDOArtifacts, type PDORecord } from '../PDOArtifacts';

const SAMPLE_PDO: PDORecord = {
  pdo_id: 'pdo-test-001',
  input_refs: ['input-ref-001', 'input-ref-002'],
  decision_ref: 'decision-ref-001',
  outcome_ref: 'outcome-ref-001',
  recorded_at: '2025-12-17T10:00:00Z',
  source_system: 'chainiq',
};

describe('PDOArtifacts', () => {
  it('renders empty state when no PDOs provided', () => {
    render(<PDOArtifacts />);
    expect(screen.getByText('No PDO records available.')).toBeInTheDocument();
  });

  it('renders PDO ID in monospace font', () => {
    render(<PDOArtifacts pdos={[SAMPLE_PDO]} />);
    const pdoId = screen.getByText('pdo-test-001');
    expect(pdoId).toBeInTheDocument();
    expect(pdoId).toHaveClass('font-mono');
  });

  it('renders source system in uppercase', () => {
    render(<PDOArtifacts pdos={[SAMPLE_PDO]} />);
    expect(screen.getByText('CHAINIQ')).toBeInTheDocument();
  });

  it('renders all input references', () => {
    render(<PDOArtifacts pdos={[SAMPLE_PDO]} />);
    expect(screen.getByText('input-ref-001')).toBeInTheDocument();
    expect(screen.getByText('input-ref-002')).toBeInTheDocument();
  });

  it('renders decision and outcome references', () => {
    render(<PDOArtifacts pdos={[SAMPLE_PDO]} />);
    expect(screen.getByText('decision-ref-001')).toBeInTheDocument();
    expect(screen.getByText('outcome-ref-001')).toBeInTheDocument();
  });

  it('renders timestamp with UTC label', () => {
    render(<PDOArtifacts pdos={[SAMPLE_PDO]} />);
    expect(screen.getByText('Recorded At (UTC)')).toBeInTheDocument();
    expect(screen.getByText('2025-12-17T10:00:00Z')).toBeInTheDocument();
  });

  it('renders multiple PDOs', () => {
    const secondPdo: PDORecord = {
      ...SAMPLE_PDO,
      pdo_id: 'pdo-test-002',
      source_system: 'oc',
    };
    render(<PDOArtifacts pdos={[SAMPLE_PDO, secondPdo]} />);
    expect(screen.getByText('pdo-test-001')).toBeInTheDocument();
    expect(screen.getByText('pdo-test-002')).toBeInTheDocument();
  });

  it('has no editable controls', () => {
    const { container } = render(<PDOArtifacts pdos={[SAMPLE_PDO]} />);
    expect(container.querySelectorAll('input')).toHaveLength(0);
    expect(container.querySelectorAll('button')).toHaveLength(0);
    expect(container.querySelectorAll('select')).toHaveLength(0);
    expect(container.querySelectorAll('textarea')).toHaveLength(0);
  });
});
