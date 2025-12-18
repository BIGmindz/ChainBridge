/**
 * Customer Trust Center Page — PAC-SONNY-TRUST-MIN-UI-01
 *
 * Evidence index. Literal data only.
 * No interpretation. No summaries. No adjectives.
 *
 * @see PAC-SONNY-TRUST-MIN-UI-01
 */

import {
  GovernanceArtifact,
  AuditBundle,
  AdversarialTesting,
  NonClaims,
} from '../components/trust';
import type { GovernanceFingerprint, AuditBundleMetadata } from '../types/trust';

const FINGERPRINT: GovernanceFingerprint = {
  fingerprint_hash: 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  timestamp: '2025-12-17T00:00:00Z',
  schema_version: '1.0.0',
};

const AUDIT_BUNDLE: AuditBundleMetadata = {
  bundle_id: 'audit-bundle-2025-12-17-001',
  created_at: '2025-12-17T10:00:00Z',
  bundle_hash: 'sha256:a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a',
  status: 'offline-verifiable',
};

export function CustomerTrustCenterPage(): JSX.Element {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800/50">
        <div className="max-w-2xl mx-auto px-6 py-4">
          <h1 className="text-sm font-medium text-slate-300">Trust Center</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-4 space-y-3">
        <GovernanceArtifact fingerprint={FINGERPRINT} />
        <AuditBundle bundle={AUDIT_BUNDLE} />
        <AdversarialTesting testCount={133} lastRun="2025-12-17T12:00:00Z" />
        <NonClaims />
      </main>
    </div>
  );
}

export default CustomerTrustCenterPage;
