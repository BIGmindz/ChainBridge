/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * ProofPack Verifier
 * PAC-BENSON-P34: Trust Center (Public Audit Interface)
 * 
 * Public interface for verifying ProofPack integrity and signatures.
 * 
 * DOCTRINE REFERENCES:
 * - Law 4, §4.2: ProofPack with trust indicators (MANDATORY)
 * - Law 6: Visual Invariants
 * - Law 8: ProofPack Completeness
 * 
 * CONSTRAINTS:
 * - READ-ONLY verification
 * - No private data exposure
 * - Public-accessible without authentication
 * 
 * Author: SONNY (GID-02) — Trust Center UI
 * UX: LIRA (GID-09) — Public UX & Accessibility
 * Security: SAM (GID-06) — Public exposure review
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import { VerificationStatusBadge } from './VerificationStatusBadge';
import type { 
  PublicProofPackSummary, 
  PublicVerificationResult,
  VerificationStatus 
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// VERIFICATION RESULT DISPLAY
// ═══════════════════════════════════════════════════════════════════════════════

interface VerificationResultProps {
  result: PublicVerificationResult;
}

const VerificationResult: React.FC<VerificationResultProps> = ({ result }) => (
  <div className={`
    p-4 rounded-lg border
    ${result.verified 
      ? 'bg-green-900/20 border-green-500' 
      : 'bg-red-900/20 border-red-500'
    }
  `}>
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-lg font-semibold text-gray-100">
        Verification Result
      </h3>
      <VerificationStatusBadge status={result.status} size="lg" />
    </div>

    <p className={`text-sm mb-4 ${result.verified ? 'text-green-300' : 'text-red-300'}`}>
      {result.message}
    </p>

    <div className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <span className="text-gray-500">Hash Algorithm:</span>
        <span className="ml-2 text-gray-300">{result.hashAlgorithm}</span>
      </div>
      <div>
        <span className="text-gray-500">Verified At:</span>
        <span className="ml-2 text-gray-300">
          {new Date(result.verifiedAt).toLocaleString()}
        </span>
      </div>
      {result.signatureValid !== undefined && (
        <div>
          <span className="text-gray-500">Signature:</span>
          <span className={`ml-2 ${result.signatureValid ? 'text-green-400' : 'text-red-400'}`}>
            {result.signatureValid ? '✓ Valid' : '✗ Invalid'}
          </span>
        </div>
      )}
      {result.hashValid !== undefined && (
        <div>
          <span className="text-gray-500">Content Hash:</span>
          <span className={`ml-2 ${result.hashValid ? 'text-green-400' : 'text-red-400'}`}>
            {result.hashValid ? '✓ Valid' : '✗ Invalid'}
          </span>
        </div>
      )}
    </div>

    <div className="mt-4 pt-4 border-t border-gray-700">
      <div className="text-xs text-gray-500 mb-1">Manifest Hash</div>
      <code className="text-xs text-blue-400 font-mono break-all">
        {result.manifestHash}
      </code>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// PROOFPACK SUMMARY CARD
// ═══════════════════════════════════════════════════════════════════════════════

interface ProofPackCardProps {
  summary: PublicProofPackSummary;
  onVerify: () => void;
  onDownload: () => void;
  isVerifying: boolean;
}

const ProofPackCard: React.FC<ProofPackCardProps> = ({
  summary,
  onVerify,
  onDownload,
  isVerifying,
}) => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
    <div className="flex items-start justify-between mb-3">
      <div>
        <h4 className="text-sm font-semibold text-gray-100">ProofPack</h4>
        <code className="text-xs text-gray-400 font-mono">
          {summary.proofpackId}
        </code>
      </div>
      {summary.isSigned && (
        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
          ✓ Signed
        </span>
      )}
    </div>

    <div className="grid grid-cols-2 gap-2 text-sm mb-4">
      <div>
        <span className="text-gray-500">Events:</span>
        <span className="ml-2 text-gray-300">{summary.eventCount}</span>
      </div>
      <div>
        <span className="text-gray-500">Generated:</span>
        <span className="ml-2 text-gray-300">
          {new Date(summary.generatedAt).toLocaleDateString()}
        </span>
      </div>
      {summary.signatureAlgorithm && (
        <div className="col-span-2">
          <span className="text-gray-500">Signature:</span>
          <span className="ml-2 text-gray-300">{summary.signatureAlgorithm}</span>
        </div>
      )}
    </div>

    <div className="flex gap-2">
      <button
        onClick={onVerify}
        disabled={isVerifying}
        className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 text-white text-sm rounded"
      >
        {isVerifying ? '⟳ Verifying...' : '🔍 Verify'}
      </button>
      <button
        onClick={onDownload}
        className="flex-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded"
      >
        ⬇ Download
      </button>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface ProofPackVerifierProps {
  /** ProofPack ID to verify (optional, for lookup mode) */
  proofpackId?: string;
  /** ProofPack summary if already loaded */
  summary?: PublicProofPackSummary;
  /** Callback to fetch ProofPack by ID */
  onFetchProofPack: (id: string) => Promise<PublicProofPackSummary>;
  /** Callback to verify ProofPack */
  onVerify: (id: string) => Promise<PublicVerificationResult>;
  /** Callback to download ProofPack */
  onDownload: (id: string) => void;
}

export const ProofPackVerifier: React.FC<ProofPackVerifierProps> = ({
  proofpackId: initialId,
  summary: initialSummary,
  onFetchProofPack,
  onVerify,
  onDownload,
}) => {
  const [inputId, setInputId] = useState(initialId || '');
  const [summary, setSummary] = useState<PublicProofPackSummary | null>(initialSummary || null);
  const [result, setResult] = useState<PublicVerificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ═══════════════════════════════════════════════════════════════════════════
  // HANDLERS
  // ═══════════════════════════════════════════════════════════════════════════

  const handleLookup = useCallback(async () => {
    if (!inputId.trim()) {
      setError('Please enter a ProofPack ID');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const fetchedSummary = await onFetchProofPack(inputId.trim());
      setSummary(fetchedSummary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch ProofPack');
      setSummary(null);
    } finally {
      setIsLoading(false);
    }
  }, [inputId, onFetchProofPack]);

  const handleVerify = useCallback(async () => {
    if (!summary) return;

    setIsVerifying(true);
    setError(null);

    try {
      const verificationResult = await onVerify(summary.proofpackId);
      setResult(verificationResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setIsVerifying(false);
    }
  }, [summary, onVerify]);

  const handleDownload = useCallback(() => {
    if (summary) {
      onDownload(summary.proofpackId);
    }
  }, [summary, onDownload]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleLookup();
    }
  }, [handleLookup]);

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden"
      aria-labelledby="verifier-title"
    >
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <h2 id="verifier-title" className="text-lg font-semibold text-gray-100">
          🔍 ProofPack Verifier
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          Verify the integrity and authenticity of ChainBridge ProofPacks
        </p>
      </header>

      {/* Lookup Input */}
      <div className="p-4 border-b border-gray-700">
        <label htmlFor="proofpack-id" className="block text-sm text-gray-400 mb-2">
          Enter ProofPack ID or Artifact ID
        </label>
        <div className="flex gap-2">
          <input
            id="proofpack-id"
            type="text"
            value={inputId}
            onChange={(e) => setInputId(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
            aria-describedby="lookup-hint"
          />
          <button
            onClick={handleLookup}
            disabled={isLoading || !inputId.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 text-white text-sm rounded"
          >
            {isLoading ? '⟳' : 'Lookup'}
          </button>
        </div>
        <p id="lookup-hint" className="text-xs text-gray-500 mt-1">
          ProofPacks are publicly verifiable evidence bundles
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-4 py-3 bg-red-900/20 border-b border-red-700">
          <p className="text-sm text-red-400">⚠ {error}</p>
        </div>
      )}

      {/* ProofPack Summary */}
      {summary && (
        <div className="p-4 border-b border-gray-700">
          <ProofPackCard
            summary={summary}
            onVerify={handleVerify}
            onDownload={handleDownload}
            isVerifying={isVerifying}
          />
        </div>
      )}

      {/* Verification Result */}
      {result && (
        <div className="p-4">
          <VerificationResult result={result} />
        </div>
      )}

      {/* Empty State */}
      {!summary && !error && !isLoading && (
        <div className="p-8 text-center text-gray-500">
          <div className="text-4xl mb-2">🔐</div>
          <p>Enter a ProofPack ID to verify its integrity</p>
          <p className="text-xs mt-2">
            All verifications are performed locally and do not require authentication
          </p>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-gray-850 px-4 py-2 border-t border-gray-700">
        <p className="text-xs text-gray-500 text-center">
          ProofPack verification is read-only and publicly accessible
        </p>
      </footer>
    </section>
  );
};

export default ProofPackVerifier;
