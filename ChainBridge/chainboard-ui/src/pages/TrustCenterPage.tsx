/**
 * Trust Center Page — PAC-SONNY-TRUST-HARDEN-01
 *
 * Hardened evidence registry. Read-only. Evidence-only.
 * No interpretation. No summaries. No claims.
 *
 * This is infrastructure, not UX.
 *
 * Sections (strict chronological order):
 * 1. Governance Fingerprint (hash, timestamp, schema)
 * 2. Audit Bundle (ID, hash, recorded timestamp)
 * 3. PDO Artifacts (ID, refs, source, recorded timestamp)
 * 4. Adversarial Testing (count, recorded timestamp, location)
 * 5. Non-Claims (verbatim, permanent, non-dismissible)
 *
 * @see PAC-SONNY-TRUST-HARDEN-01 — Trust Center Evidence-Only Hardening
 */

import {
  GovernanceArtifact,
  AuditBundle,
  AdversarialTesting,
  NonClaims,
  PDOArtifacts,
} from '../components/trust';
import type { GovernanceFingerprint, AuditBundleMetadata } from '../types/trust';
import type { PDORecord } from '../components/trust/PDOArtifacts';

/**
 * UNLINKED / DEMO DATA — Hardcoded fingerprint.
 * In production, this must be fetched from backend.
 */
const FINGERPRINT: GovernanceFingerprint = {
  fingerprint_hash: 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  timestamp: '2025-12-17T00:00:00Z',
  schema_version: '1.0.0',
};

/**
 * UNLINKED / DEMO DATA — Hardcoded audit bundle.
 * In production, this must be fetched from backend.
 */
const AUDIT_BUNDLE: AuditBundleMetadata = {
  bundle_id: 'audit-bundle-2025-12-17-001',
  created_at: '2025-12-17T10:00:00Z',
  bundle_hash: 'sha256:a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a',
  status: 'offline-verifiable',
};

/**
 * UNLINKED / DEMO DATA — Hardcoded PDO records.
 * In production, these must be fetched from backend.
 */
const PDO_RECORDS: PDORecord[] = [
  {
    pdo_id: 'pdo-2025-12-17-001',
    input_refs: ['artifact-input-001', 'artifact-input-002'],
    decision_ref: 'decision-ref-001',
    outcome_ref: 'outcome-ref-001',
    recorded_at: '2025-12-17T09:30:00Z',
    source_system: 'chainiq',
  },
  {
    pdo_id: 'pdo-2025-12-17-002',
    input_refs: ['artifact-input-003'],
    decision_ref: 'decision-ref-002',
    outcome_ref: 'outcome-ref-002',
    recorded_at: '2025-12-17T11:45:00Z',
    source_system: 'oc',
  },
];

/**
 * Trust Center Page.
 * Read-only evidence registry. No controls. No interpretation.
 */
export function TrustCenterPage(): JSX.Element {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100" data-testid="trust-center">
      {/* Header — minimal, no marketing */}
      <header className="border-b border-slate-800/50">
        <div className="max-w-2xl mx-auto px-6 py-4">
          <h1 className="text-sm font-medium text-slate-300 font-mono">
            Trust Center — Evidence Registry
          </h1>
          <p className="text-xs text-slate-600 mt-1 font-mono">
            Read-only. Evidence presented as recorded.
          </p>
        </div>
      </header>

      {/* Main content — strict chronological order, no controls */}
      <main className="max-w-2xl mx-auto px-6 py-4 space-y-3">
        {/* UNLINKED warning — demo data notice */}
        <div className="border border-slate-600 bg-slate-900/80 px-4 py-3 text-xs text-slate-400 font-mono">
          UNLINKED / DEMO DATA — Artifacts below are not linked to live backend
        </div>

        {/* Non-Claims FIRST — legal hard stop, always visible */}
        <NonClaims />

        {/* Evidence artifacts in chronological order */}
        <GovernanceArtifact fingerprint={FINGERPRINT} />
        <AuditBundle bundle={AUDIT_BUNDLE} />
        <PDOArtifacts pdos={PDO_RECORDS} />
        <AdversarialTesting testCount={133} lastRun="2025-12-17T12:00:00Z" />
      </main>

      {/* Footer — tamper-evident signal without claims */}
      <footer className="border-t border-slate-800/50 mt-8">
        <div className="max-w-2xl mx-auto px-6 py-4">
          <p className="text-xs text-slate-600 font-mono">
            All timestamps are UTC. All hashes are SHA-256. Evidence is append-only.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default TrustCenterPage;
