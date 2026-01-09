/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Trust Center Dashboard
 * PAC-BENSON-P34: Trust Center (Public Audit Interface)
 * 
 * Main public-facing dashboard for external verification and audit access.
 * Integrates all Trust Center components into a unified interface.
 * 
 * DOCTRINE REFERENCES:
 * - Law 2, §2.2: Visibility surfaces (public tier)
 * - Law 6: Visual Invariants
 * - Law 8: ProofPack Completeness
 * 
 * CONSTRAINTS:
 * - READ-ONLY access
 * - Public-safe data only
 * - No authentication required
 * - No private/sensitive information
 * 
 * Author: SONNY (GID-02) — Trust Center UI
 * UX: LIRA (GID-09) — Public UX & Accessibility
 * API: CODY (GID-01) — Public read-only APIs
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useEffect, useCallback } from 'react';
import { GovernanceTrustBadge } from './GovernanceTrustBadge';
import { ProofPackVerifier } from './ProofPackVerifier';
import { PublicAuditTimeline } from './PublicAuditTimeline';
import type { 
  TrustCenterState,
  TrustFingerprint,
  TrustCoverage,
  GamedayResults,
  AuditBundleMetadata,
  PublicAuditTimeline as PublicAuditTimelineData,
  PublicProofPackSummary,
  PublicVerificationResult,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// API ENDPOINTS (Public Trust API)
// ═══════════════════════════════════════════════════════════════════════════════

const TRUST_API = {
  FINGERPRINT: '/api/v1/trust/fingerprint',
  COVERAGE: '/api/v1/trust/coverage',
  GAMEDAY: '/api/v1/trust/gameday',
  AUDIT: '/api/v1/trust/audit/latest',
  TIMELINE: '/api/v1/trust/timeline',
  PROOFPACK_LOOKUP: '/api/v1/proofpack',
  PROOFPACK_VERIFY: '/api/v1/proofpack/{id}/verify',
  PROOFPACK_DOWNLOAD: '/api/v1/proofpack/{id}/download',
};

// ═══════════════════════════════════════════════════════════════════════════════
// TAB CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

type TabId = 'overview' | 'verify' | 'timeline';

interface TabConfig {
  id: TabId;
  label: string;
  icon: string;
  description: string;
}

const TABS: TabConfig[] = [
  {
    id: 'overview',
    label: 'Trust Overview',
    icon: '🛡',
    description: 'Governance health and coverage',
  },
  {
    id: 'verify',
    label: 'Verify ProofPack',
    icon: '✓',
    description: 'Verify integrity of audit artifacts',
  },
  {
    id: 'timeline',
    label: 'Audit Timeline',
    icon: '📜',
    description: 'Public audit history',
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export interface TrustCenterDashboardProps {
  /** Initial ProofPack ID to look up (optional) */
  initialProofPackId?: string;
  /** Initial tab to show */
  initialTab?: TabId;
  /** API base URL override */
  apiBaseUrl?: string;
}

export const TrustCenterDashboard: React.FC<TrustCenterDashboardProps> = ({
  initialProofPackId,
  initialTab = 'overview',
  apiBaseUrl = '',
}) => {
  // ═══════════════════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════════════════
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);
  const [state, setState] = useState<TrustCenterState>({
    isLoading: false,
    error: null,
    fingerprint: null,
    coverage: null,
    gamedayResults: null,
    latestAudit: null,
    timeline: null,
  });

  // Separate state for ProofPack verification
  const [proofPackLoading, setProofPackLoading] = useState(false);
  const [proofPackSummary, setProofPackSummary] = useState<PublicProofPackSummary | null>(null);
  const [verificationResult, setVerificationResult] = useState<PublicVerificationResult | null>(null);
  const [proofPackError, setProofPackError] = useState<string | null>(null);

  // ═══════════════════════════════════════════════════════════════════════════
  // DATA FETCHING
  // ═══════════════════════════════════════════════════════════════════════════
  const fetchTrustData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const [fingerprintRes, coverageRes, gamedayRes, auditRes] = await Promise.all([
        fetch(`${apiBaseUrl}${TRUST_API.FINGERPRINT}`),
        fetch(`${apiBaseUrl}${TRUST_API.COVERAGE}`),
        fetch(`${apiBaseUrl}${TRUST_API.GAMEDAY}`),
        fetch(`${apiBaseUrl}${TRUST_API.AUDIT}`),
      ]);

      const [fingerprint, coverage, gamedayResults, latestAudit] = await Promise.all([
        fingerprintRes.ok ? fingerprintRes.json() : null,
        coverageRes.ok ? coverageRes.json() : null,
        gamedayRes.ok ? gamedayRes.json() : null,
        auditRes.ok ? auditRes.json() : null,
      ]);

      setState((prev) => ({
        ...prev,
        isLoading: false,
        fingerprint,
        coverage,
        gamedayResults,
        latestAudit,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load trust data',
      }));
    }
  }, [apiBaseUrl]);

  const fetchTimeline = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      const res = await fetch(`${apiBaseUrl}${TRUST_API.TIMELINE}`);
      if (!res.ok) throw new Error('Timeline unavailable');
      
      const timeline = await res.json();
      setState((prev) => ({
        ...prev,
        isLoading: false,
        timeline,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load timeline',
      }));
    }
  }, [apiBaseUrl]);

  // ═══════════════════════════════════════════════════════════════════════════
  // PROOFPACK HANDLERS
  // ═══════════════════════════════════════════════════════════════════════════
  const handleLookup = useCallback(async (proofpackId: string) => {
    setProofPackLoading(true);
    setProofPackError(null);
    setProofPackSummary(null);
    setVerificationResult(null);

    try {
      const res = await fetch(`${apiBaseUrl}${TRUST_API.PROOFPACK_LOOKUP}/${proofpackId}`);
      if (!res.ok) {
        if (res.status === 404) throw new Error('ProofPack not found');
        throw new Error('Lookup failed');
      }
      
      const summary = await res.json();
      setProofPackSummary(summary);
    } catch (err) {
      setProofPackError(err instanceof Error ? err.message : 'Lookup failed');
    } finally {
      setProofPackLoading(false);
    }
  }, [apiBaseUrl]);

  const handleVerify = useCallback(async (proofpackId: string) => {
    setProofPackLoading(true);
    setProofPackError(null);
    setVerificationResult(null);

    try {
      const url = `${apiBaseUrl}${TRUST_API.PROOFPACK_VERIFY.replace('{id}', proofpackId)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Verification failed');
      
      const result = await res.json();
      setVerificationResult(result);
    } catch (err) {
      setProofPackError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setProofPackLoading(false);
    }
  }, [apiBaseUrl]);

  const handleDownload = useCallback(async (proofpackId: string) => {
    try {
      const url = `${apiBaseUrl}${TRUST_API.PROOFPACK_DOWNLOAD.replace('{id}', proofpackId)}`;
      window.open(url, '_blank');
    } catch (err) {
      setProofPackError('Download failed');
    }
  }, [apiBaseUrl]);

  // ═══════════════════════════════════════════════════════════════════════════
  // EFFECTS
  // ═══════════════════════════════════════════════════════════════════════════
  useEffect(() => {
    fetchTrustData();
  }, [fetchTrustData]);

  useEffect(() => {
    if (activeTab === 'timeline' && !state.timeline) {
      fetchTimeline();
    }
  }, [activeTab, state.timeline, fetchTimeline]);

  useEffect(() => {
    if (initialProofPackId) {
      setActiveTab('verify');
      handleLookup(initialProofPackId);
    }
  }, [initialProofPackId, handleLookup]);

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Tab Navigation
  // ═══════════════════════════════════════════════════════════════════════════
  const renderTabNav = () => (
    <nav 
      className="flex border-b border-gray-700 bg-gray-800"
      role="tablist"
      aria-label="Trust Center sections"
    >
      {TABS.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-controls={`panel-${tab.id}`}
          onClick={() => setActiveTab(tab.id)}
          className={`
            flex items-center gap-2 px-4 py-3 text-sm font-medium
            border-b-2 transition-colors
            ${activeTab === tab.id
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
            }
          `}
        >
          <span aria-hidden="true">{tab.icon}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </nav>
  );

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Tab Content
  // ═══════════════════════════════════════════════════════════════════════════
  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div 
            role="tabpanel" 
            id="panel-overview"
            aria-labelledby="tab-overview"
            className="p-6"
          >
            <div className="grid gap-6 md:grid-cols-2">
              {/* Governance Trust Badge */}
              <div className="md:col-span-2">
                <GovernanceTrustBadge
                  fingerprint={state.fingerprint}
                  coverage={state.coverage}
                  gamedayResults={state.gamedayResults}
                  isLoading={state.isLoading}
                  error={state.error}
                />
              </div>

              {/* Latest Audit Summary */}
              {state.latestAudit && (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-300 mb-2">
                    📋 Latest Audit Bundle
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Bundle ID:</dt>
                      <dd className="text-gray-200 font-mono text-xs">
                        {state.latestAudit.bundleId.substring(0, 12)}...
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Generated:</dt>
                      <dd className="text-gray-200">
                        {new Date(state.latestAudit.generatedAt).toLocaleDateString()}
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Items:</dt>
                      <dd className="text-gray-200">{state.latestAudit.itemCount}</dd>
                    </div>
                  </dl>
                </div>
              )}

              {/* Trust Statement */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300 mb-2">
                  🔒 Trust Statement
                </h3>
                <p className="text-xs text-gray-400 leading-relaxed">
                  ChainBridge operates under a formal governance framework with 
                  automated compliance verification. All decisions are recorded 
                  with cryptographic proof trails (ProofPacks) that can be 
                  independently verified.
                </p>
              </div>
            </div>
          </div>
        );

      case 'verify':
        return (
          <div 
            role="tabpanel" 
            id="panel-verify"
            aria-labelledby="tab-verify"
            className="p-6"
          >
            <ProofPackVerifier
              initialProofPackId={initialProofPackId}
              isLoading={proofPackLoading}
              proofpack={proofPackSummary}
              verificationResult={verificationResult}
              error={proofPackError}
              onLookup={handleLookup}
              onVerify={handleVerify}
              onDownload={handleDownload}
            />
          </div>
        );

      case 'timeline':
        return (
          <div 
            role="tabpanel" 
            id="panel-timeline"
            aria-labelledby="tab-timeline"
            className="p-6"
          >
            <PublicAuditTimeline
              timeline={state.timeline}
              isLoading={state.isLoading}
              error={state.error}
              onLoadMore={() => {/* TODO: pagination */}}
              onRefresh={fetchTimeline}
              onProofPackClick={(id) => {
                setActiveTab('verify');
                handleLookup(id);
              }}
            />
          </div>
        );

      default:
        return null;
    }
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // MAIN RENDER
  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-3xl" aria-hidden="true">🛡</div>
              <div>
                <h1 className="text-xl font-semibold text-gray-100">
                  ChainBridge Trust Center
                </h1>
                <p className="text-sm text-gray-400">
                  Public Verification & Audit Interface
                </p>
              </div>
            </div>

            {/* Status Indicator */}
            <div className="flex items-center gap-2">
              {state.isLoading ? (
                <span className="text-yellow-400 text-sm">⟳ Loading...</span>
              ) : state.error ? (
                <span className="text-red-400 text-sm">⚠ Error</span>
              ) : (
                <span className="text-green-400 text-sm">● Online</span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto">
        <div className="bg-gray-900 border-x border-b border-gray-800 rounded-b-lg overflow-hidden">
          {renderTabNav()}
          {renderTabContent()}
        </div>

        {/* Footer */}
        <footer className="text-center py-6 text-xs text-gray-500">
          <p>
            All data displayed is public-safe and read-only.
            Sensitive information has been redacted per governance policy.
          </p>
          <p className="mt-1">
            ChainBridge Trust Center • Operator Experience Doctrine v1.0.0
          </p>
        </footer>
      </main>
    </div>
  );
};

export default TrustCenterDashboard;
