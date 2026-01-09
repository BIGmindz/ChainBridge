/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * ProofPack Viewer (MANDATORY)
 * PAC-BENSON-P32: UI Implementation (Operator Experience Doctrine Apply)
 * 
 * DOCTRINE LAW 4, §4.2 — ProofPack Viewer (MANDATORY)
 * DOCTRINE LAW 10: Cryptographic Trust Indicators
 * 
 * Displays ProofPack contents with:
 * - Full ProofPack content display
 * - Signature verification status
 * - Download capability
 * - Hash verification UI
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display
 * - INV-DOC-003: Signature verification visible
 * - INV-DOC-004: Quantum-safe indicator displayed
 * 
 * Author: SONNY (GID-02) — UI Implementation Lead
 * Security: SAM (GID-06)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import type { 
  ProofPackData, 
  SignatureStatus, 
  HashChainStatus 
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// TRUST INDICATOR CONFIGS (LAW 10, §10.1)
// ═══════════════════════════════════════════════════════════════════════════════

const SIGNATURE_STATUS_CONFIG: Record<SignatureStatus, { icon: string; color: string; label: string }> = {
  VERIFIED: { icon: '✓', color: 'text-green-400', label: 'Verified' },
  PENDING: { icon: '⏳', color: 'text-yellow-400', label: 'Pending' },
  FAILED: { icon: '✗', color: 'text-red-400', label: 'Failed' },
  NOT_CHECKED: { icon: '○', color: 'text-gray-400', label: 'Not Checked' },
};

const HASH_CHAIN_STATUS_CONFIG: Record<HashChainStatus, { icon: string; color: string; label: string }> = {
  INTACT: { icon: '✓', color: 'text-green-400', label: 'Intact' },
  BROKEN: { icon: '✗', color: 'text-red-400', label: 'Broken' },
  PENDING: { icon: '⏳', color: 'text-yellow-400', label: 'Pending' },
};

// Quantum-safe algorithms (ALEX Rule 3)
const QUANTUM_SAFE_ALGORITHMS = ['SPHINCS+', 'Dilithium-3', 'XMSS', 'LMS', 'Kyber-768', 'Kyber-1024'];

// ═══════════════════════════════════════════════════════════════════════════════
// TRUST BADGE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TrustBadgeProps {
  label: string;
  status: 'verified' | 'pending' | 'failed' | 'unknown';
  detail?: string;
}

const TrustBadge: React.FC<TrustBadgeProps> = ({ label, status, detail }) => {
  const configs = {
    verified: { icon: '✓', bg: 'bg-green-900/30', border: 'border-green-700', text: 'text-green-400' },
    pending: { icon: '⏳', bg: 'bg-yellow-900/30', border: 'border-yellow-700', text: 'text-yellow-400' },
    failed: { icon: '✗', bg: 'bg-red-900/30', border: 'border-red-700', text: 'text-red-400' },
    unknown: { icon: '?', bg: 'bg-gray-800', border: 'border-gray-600', text: 'text-gray-400' },
  };

  const config = configs[status];

  return (
    <div 
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${config.bg} ${config.border}`}
      role="status"
      aria-label={`${label}: ${status}${detail ? ` - ${detail}` : ''}`}
    >
      <span className={`text-lg ${config.text}`} aria-hidden="true">{config.icon}</span>
      <div className="flex flex-col">
        <span className={`text-sm font-medium ${config.text}`}>{label}</span>
        {detail && <span className="text-xs text-gray-500">{detail}</span>}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// QUANTUM SAFE BADGE (ALEX Rule 3)
// ═══════════════════════════════════════════════════════════════════════════════

interface QuantumSafeBadgeProps {
  isQuantumSafe: boolean;
  algorithm?: string;
}

const QuantumSafeBadge: React.FC<QuantumSafeBadgeProps> = ({ isQuantumSafe, algorithm }) => {
  if (isQuantumSafe) {
    return (
      <div 
        className="flex items-center gap-2 px-3 py-2 rounded-lg border bg-purple-900/30 border-purple-700"
        role="status"
        aria-label="Quantum-safe cryptography enabled"
      >
        <span className="text-lg" aria-hidden="true">🛡</span>
        <div className="flex flex-col">
          <span className="text-sm font-medium text-purple-400">PQ-SAFE</span>
          {algorithm && <span className="text-xs text-gray-500">{algorithm}</span>}
        </div>
      </div>
    );
  }

  return (
    <div 
      className="flex items-center gap-2 px-3 py-2 rounded-lg border bg-yellow-900/30 border-yellow-700"
      role="status"
      aria-label="Legacy cryptography - not quantum-safe"
    >
      <span className="text-lg" aria-hidden="true">⚠️</span>
      <div className="flex flex-col">
        <span className="text-sm font-medium text-yellow-400">Legacy Crypto</span>
        <span className="text-xs text-gray-500">Not quantum-safe</span>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// HASH DISPLAY COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface HashDisplayProps {
  label: string;
  hash: string;
  onCopy?: () => void;
}

const HashDisplay: React.FC<HashDisplayProps> = ({ label, hash, onCopy }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(hash);
    setCopied(true);
    onCopy?.();
    setTimeout(() => setCopied(false), 2000);
  }, [hash, onCopy]);

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-gray-500">{label}</span>
      <div className="flex items-center gap-2">
        <code className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-300 font-mono truncate max-w-[300px]">
          {hash}
        </code>
        <button
          onClick={handleCopy}
          className="px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors"
          aria-label={`Copy ${label}`}
        >
          {copied ? '✓ Copied' : '📋 Copy'}
        </button>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface ProofPackViewerProps {
  /** ProofPack data from backend */
  proofPack: ProofPackData | null;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Callback to download ProofPack */
  onDownload: () => void;
  /** Callback to verify externally */
  onVerifyExternal: () => void;
  /** Callback when user copies hash */
  onHashCopy?: () => void;
}

export const ProofPackViewer: React.FC<ProofPackViewerProps> = ({
  proofPack,
  isLoading,
  error,
  onDownload,
  onVerifyExternal,
  onHashCopy,
}) => {
  const [showContents, setShowContents] = useState(false);

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Loading State
  // ═══════════════════════════════════════════════════════════════════════════
  if (isLoading && !proofPack) {
    return (
      <div 
        className="bg-gray-900 border border-gray-700 rounded-lg p-6"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <span className="animate-spin">⟳</span>
          <span>Loading ProofPack...</span>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Error State
  // ═══════════════════════════════════════════════════════════════════════════
  if (error) {
    return (
      <div 
        className="bg-red-900/20 border border-red-700 rounded-lg p-6"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center gap-2 text-red-400">
          <span>✗</span>
          <span>ProofPack Error: {error}</span>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: No ProofPack Selected
  // ═══════════════════════════════════════════════════════════════════════════
  if (!proofPack) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 text-center text-gray-500">
        No ProofPack selected. Select a settlement or decision to view its proof.
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // DETERMINE TRUST STATUS
  // ═══════════════════════════════════════════════════════════════════════════
  const sigStatus = SIGNATURE_STATUS_CONFIG[proofPack.signature.status];
  const hashStatus = HASH_CHAIN_STATUS_CONFIG[proofPack.hashChain.status];
  const isQuantumSafe = proofPack.quantumSafe || 
    QUANTUM_SAFE_ALGORITHMS.includes(proofPack.signature.algorithm);

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden"
      aria-labelledby="proofpack-title"
    >
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 id="proofpack-title" className="text-lg font-semibold text-gray-100">
              ProofPack
            </h2>
            <code className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded font-mono">
              {proofPack.proofPackId}
            </code>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowContents(!showContents)}
              className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
            >
              {showContents ? 'Hide Contents' : 'View Contents'}
            </button>
            <button
              onClick={onDownload}
              className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
            >
              📥 Download
            </button>
            <button
              onClick={onVerifyExternal}
              className="px-3 py-1.5 text-sm bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors"
            >
              🔍 Verify Externally
            </button>
          </div>
        </div>
      </header>

      {/* Trust Surface (LAW 10, §10.2) */}
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Trust Verification</h3>
        <div className="flex flex-wrap gap-3">
          <TrustBadge
            label="Signature"
            status={
              proofPack.signature.status === 'VERIFIED' ? 'verified' :
              proofPack.signature.status === 'PENDING' ? 'pending' :
              proofPack.signature.status === 'FAILED' ? 'failed' : 'unknown'
            }
            detail={proofPack.signature.algorithm}
          />

          <TrustBadge
            label="Hash Chain"
            status={
              proofPack.hashChain.status === 'INTACT' ? 'verified' :
              proofPack.hashChain.status === 'BROKEN' ? 'failed' : 'pending'
            }
            detail={`${proofPack.hashChain.blockCount} blocks`}
          />

          <TrustBadge
            label="Timestamp"
            status={proofPack.timestamp.attested ? 'verified' : 'pending'}
            detail={proofPack.timestamp.source}
          />

          <QuantumSafeBadge 
            isQuantumSafe={isQuantumSafe}
            algorithm={proofPack.signature.algorithm}
          />
        </div>
      </div>

      {/* Metadata */}
      <div className="p-4 border-b border-gray-700 space-y-3">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Metadata</h3>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">PAC ID:</span>
            <span className="ml-2 text-gray-300 font-mono">{proofPack.pacId}</span>
          </div>
          <div>
            <span className="text-gray-500">Created:</span>
            <span className="ml-2 text-gray-300">
              {new Date(proofPack.createdAt).toLocaleString()}
            </span>
          </div>
          {proofPack.signature.signerGid && (
            <div>
              <span className="text-gray-500">Signed By:</span>
              <span className="ml-2 text-gray-300 font-mono">{proofPack.signature.signerGid}</span>
            </div>
          )}
          {proofPack.timestamp.attested && (
            <div>
              <span className="text-gray-500">Attested:</span>
              <span className="ml-2 text-gray-300">
                {new Date(proofPack.timestamp.timestamp).toLocaleString()}
              </span>
            </div>
          )}
        </div>

        <HashDisplay 
          label="Root Hash" 
          hash={proofPack.hashChain.rootHash}
          onCopy={onHashCopy}
        />
      </div>

      {/* Contents (collapsible) */}
      {showContents && (
        <div className="p-4 bg-gray-950">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Contents</h3>
          <pre className="p-3 bg-gray-900 rounded-lg overflow-auto max-h-[400px] text-xs text-gray-300 font-mono">
            {JSON.stringify(proofPack.contents, null, 2)}
          </pre>
        </div>
      )}
    </section>
  );
};

export default ProofPackViewer;
