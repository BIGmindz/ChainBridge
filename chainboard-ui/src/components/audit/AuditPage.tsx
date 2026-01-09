/**
 * AuditPage — Main audit dashboard for external auditors
 * ════════════════════════════════════════════════════════════════════════════════
 *
 * PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
 * Agent: Sonny (GID-02) — Audit UI
 * Order: ORDER 3
 * Effective Date: 2025-12-30
 *
 * PURPOSE:
 *   Main entry point for audit functionality in the Operator Console.
 *   Enables external auditors to:
 *   - Reconstruct Proof→Decision→Outcome chains
 *   - Verify hash integrity
 *   - Export audit data (JSON/CSV)
 *   - View regulatory summaries
 *
 * ════════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useEffect } from "react";
import ChainVisualization from "./ChainVisualization";
import AuditExportPanel from "./AuditExportPanel";
import RegulatorySummaryView from "./RegulatorySummaryView";
import {
  ChainReconstruction,
  RegulatorySummary,
  AuditMetadata,
  ChainVerificationResult,
} from "../../types/audit";
import {
  getChainReconstruction,
  verifyChain,
  listChains,
  exportAuditTrailJson,
  exportAuditTrailCsv,
  getRegulatorySummary,
  getAuditMetadata,
} from "../../api/auditApi";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

type TabId = "chains" | "export" | "regulatory" | "metadata";

interface TabConfig {
  id: TabId;
  label: string;
  icon: string;
}

const TABS: TabConfig[] = [
  { id: "chains", label: "Chain Reconstruction", icon: "🔗" },
  { id: "export", label: "Export Data", icon: "📤" },
  { id: "regulatory", label: "Regulatory Summary", icon: "📊" },
  { id: "metadata", label: "API Metadata", icon: "ℹ️" },
];

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function AuditPage(): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>("chains");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Chain state
  const [chainIds, setChainIds] = useState<string[]>([]);
  const [selectedChainId, setSelectedChainId] = useState<string | null>(null);
  const [currentChain, setCurrentChain] = useState<ChainReconstruction | null>(null);
  const [verificationResult, setVerificationResult] =
    useState<ChainVerificationResult | null>(null);

  // Regulatory summary state
  const [regulatorySummary, setRegulatorySummary] =
    useState<RegulatorySummary | null>(null);

  // Metadata state
  const [metadata, setMetadata] = useState<AuditMetadata | null>(null);

  // ─────────────────────────────────────────────────────────────────────────────
  // EFFECTS
  // ─────────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    // Load initial data
    loadChainIds();
    loadMetadata();
  }, []);

  useEffect(() => {
    if (activeTab === "regulatory" && !regulatorySummary) {
      loadRegulatorySummary();
    }
  }, [activeTab]);

  // ─────────────────────────────────────────────────────────────────────────────
  // DATA LOADING
  // ─────────────────────────────────────────────────────────────────────────────

  const loadChainIds = async () => {
    try {
      const ids = await listChains({ limit: 100 });
      setChainIds(ids);
      if (ids.length > 0 && !selectedChainId) {
        setSelectedChainId(ids[0]);
        loadChain(ids[0]);
      }
    } catch (err) {
      console.error("Failed to load chain IDs:", err);
    }
  };

  const loadChain = async (chainId: string) => {
    setLoading(true);
    setError(null);
    try {
      const chain = await getChainReconstruction(chainId);
      setCurrentChain(chain);
      setVerificationResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chain");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async (chainId: string) => {
    setLoading(true);
    try {
      const result = await verifyChain(chainId);
      setVerificationResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  const loadRegulatorySummary = async () => {
    setLoading(true);
    try {
      const summary = await getRegulatorySummary();
      setRegulatorySummary(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load summary");
    } finally {
      setLoading(false);
    }
  };

  const loadMetadata = async () => {
    try {
      const meta = await getAuditMetadata();
      setMetadata(meta);
    } catch (err) {
      console.error("Failed to load metadata:", err);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Audit Console
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                PAC-013A · Operator Console Audit Readiness
              </p>
            </div>
            <div className="flex items-center gap-4">
              <span className="px-3 py-1 bg-red-100 text-red-800 text-sm font-medium rounded-full">
                FAIL-CLOSED
              </span>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                READ-ONLY
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Error Display */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700">{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-sm text-red-600 hover:text-red-800"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Loading Indicator */}
        {loading && (
          <div className="flex justify-center py-8">
            <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
        )}

        {/* Tab Content */}
        {!loading && (
          <>
            {/* Chains Tab */}
            {activeTab === "chains" && (
              <div className="space-y-6">
                {/* Chain Selector */}
                <div className="bg-white rounded-lg shadow p-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Chain
                  </label>
                  <div className="flex gap-4">
                    <select
                      value={selectedChainId || ""}
                      onChange={(e) => {
                        setSelectedChainId(e.target.value);
                        loadChain(e.target.value);
                      }}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
                    >
                      {chainIds.map((id) => (
                        <option key={id} value={id}>
                          {id}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => selectedChainId && loadChain(selectedChainId)}
                      className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                    >
                      Reload
                    </button>
                  </div>
                </div>

                {/* Chain Visualization */}
                {currentChain && (
                  <ChainVisualization
                    chain={currentChain}
                    onVerify={handleVerifyChain}
                  />
                )}

                {/* Verification Result */}
                {verificationResult && (
                  <div
                    className={`p-4 rounded-lg border ${
                      verificationResult.verified
                        ? "bg-green-50 border-green-200"
                        : "bg-red-50 border-red-200"
                    }`}
                  >
                    <h4 className="font-semibold mb-2">
                      {verificationResult.verified
                        ? "✓ Chain Verified"
                        : "✗ Verification Failed"}
                    </h4>
                    <div className="text-sm">
                      <p>
                        Verified: {verificationResult.verified_links}/
                        {verificationResult.total_links} links
                      </p>
                      <p className="font-mono text-xs mt-1">
                        Integrity Hash: {verificationResult.integrity_hash}
                      </p>
                      {verificationResult.failed_links.length > 0 && (
                        <p className="text-red-700 mt-2">
                          Failed: {verificationResult.failed_links.join(", ")}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Export Tab */}
            {activeTab === "export" && (
              <AuditExportPanel
                onExportJson={exportAuditTrailJson}
                onExportCsv={exportAuditTrailCsv}
              />
            )}

            {/* Regulatory Tab */}
            {activeTab === "regulatory" && regulatorySummary && (
              <RegulatorySummaryView
                summary={regulatorySummary}
                onRefresh={loadRegulatorySummary}
              />
            )}

            {/* Metadata Tab */}
            {activeTab === "metadata" && metadata && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Audit API Metadata
                </h3>

                <div className="grid grid-cols-2 gap-6 mb-6">
                  <div>
                    <div className="text-sm text-gray-500">PAC Reference</div>
                    <div className="font-medium">{metadata.pac_reference}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Agent</div>
                    <div className="font-medium">{metadata.agent}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Governance Mode</div>
                    <div className="font-medium">{metadata.governance_mode}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Execution Lane</div>
                    <div className="font-medium">{metadata.execution_lane}</div>
                  </div>
                </div>

                <div className="mb-6">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Capabilities
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(metadata.capabilities).map(([key, value]) => (
                      <span
                        key={key}
                        className={`px-2 py-1 rounded text-xs ${
                          value
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {key}: {value ? "✓" : "✗"}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Invariants
                  </h4>
                  <div className="space-y-2">
                    {Object.entries(metadata.invariants).map(([key, value]) => (
                      <div key={key} className="p-2 bg-gray-50 rounded text-sm">
                        <span className="font-mono text-blue-600">{key}:</span>{" "}
                        {value}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-8 py-4 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center text-xs text-gray-500">
            <span>ChainBridge Operator Console · Audit Module</span>
            <span>
              API: {metadata?.api_version || "..."} · Runtime: {metadata?.runtime_id || "..."}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
