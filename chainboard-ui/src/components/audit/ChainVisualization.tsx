/**
 * ChainVisualization — Visual representation of Proof→Decision→Outcome chain
 * ════════════════════════════════════════════════════════════════════════════════
 *
 * PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
 * Agent: Sonny (GID-02) — Audit UI
 * Order: ORDER 3
 * Effective Date: 2025-12-30
 *
 * PURPOSE:
 *   Visual representation of audit chains for external auditors.
 *   Shows complete chain with hash verification status at each link.
 *
 * ════════════════════════════════════════════════════════════════════════════════
 */

import React from "react";
import {
  ChainReconstruction,
  ChainLink,
  ChainLinkType,
  VerificationStatus,
} from "../../types/audit";

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function getLinkTypeColor(linkType: ChainLinkType): string {
  switch (linkType) {
    case ChainLinkType.PROOF:
      return "bg-blue-100 border-blue-500 text-blue-800";
    case ChainLinkType.DECISION:
      return "bg-yellow-100 border-yellow-500 text-yellow-800";
    case ChainLinkType.OUTCOME:
      return "bg-green-100 border-green-500 text-green-800";
    case ChainLinkType.SETTLEMENT:
      return "bg-purple-100 border-purple-500 text-purple-800";
    case ChainLinkType.PDO:
      return "bg-gray-100 border-gray-500 text-gray-800";
    default:
      return "bg-gray-100 border-gray-300 text-gray-700";
  }
}

function getVerificationBadge(status: VerificationStatus): JSX.Element {
  switch (status) {
    case VerificationStatus.VERIFIED:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
          ✓ Verified
        </span>
      );
    case VerificationStatus.FAILED:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
          ✗ Failed
        </span>
      );
    case VerificationStatus.PENDING:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
          ⏳ Pending
        </span>
      );
    case VerificationStatus.UNAVAILABLE:
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
          — Unavailable
        </span>
      );
  }
}

function truncateHash(hash: string, length: number = 8): string {
  if (hash.length <= length * 2 + 3) return hash;
  return `${hash.slice(0, length)}...${hash.slice(-length)}`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CHAIN LINK NODE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface ChainLinkNodeProps {
  link: ChainLink;
  isFirst: boolean;
  isLast: boolean;
}

function ChainLinkNode({ link, isFirst, isLast }: ChainLinkNodeProps): JSX.Element {
  const colorClass = getLinkTypeColor(link.link_type);

  return (
    <div className="flex items-center">
      {/* Connector line (before) */}
      {!isFirst && (
        <div className="w-8 h-0.5 bg-gray-300" />
      )}

      {/* Node */}
      <div className={`border-2 rounded-lg p-3 min-w-[180px] ${colorClass}`}>
        {/* Header */}
        <div className="flex justify-between items-start mb-2">
          <span className="font-semibold text-sm">{link.link_type}</span>
          {getVerificationBadge(link.verification_status)}
        </div>

        {/* Details */}
        <div className="space-y-1 text-xs">
          <div>
            <span className="text-gray-500">ID: </span>
            <span className="font-mono">{truncateHash(link.link_id, 6)}</span>
          </div>
          <div>
            <span className="text-gray-500">Hash: </span>
            <span className="font-mono">{truncateHash(link.content_hash)}</span>
          </div>
          <div>
            <span className="text-gray-500">Seq: </span>
            <span>{link.sequence_number}</span>
          </div>
          <div>
            <span className="text-gray-500">Time: </span>
            <span>{new Date(link.timestamp).toLocaleTimeString()}</span>
          </div>
        </div>

        {/* Content summary (if present) */}
        {Object.keys(link.content_summary).length > 0 && (
          <div className="mt-2 pt-2 border-t border-current border-opacity-20">
            <details className="text-xs">
              <summary className="cursor-pointer text-gray-500">Summary</summary>
              <pre className="mt-1 text-xs overflow-x-auto">
                {JSON.stringify(link.content_summary, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>

      {/* Connector line (after) */}
      {!isLast && (
        <div className="w-8 h-0.5 bg-gray-300" />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface ChainVisualizationProps {
  chain: ChainReconstruction;
  onVerify?: (chainId: string) => void;
}

export default function ChainVisualization({
  chain,
  onVerify,
}: ChainVisualizationProps): JSX.Element {
  const integrityColor =
    chain.chain_integrity === VerificationStatus.VERIFIED
      ? "text-green-600"
      : chain.chain_integrity === VerificationStatus.FAILED
      ? "text-red-600"
      : "text-yellow-600";

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Chain: {truncateHash(chain.chain_id, 12)}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {chain.total_links} links · Reconstructed{" "}
            {new Date(chain.reconstruction_timestamp).toLocaleString()}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className={`font-medium ${integrityColor}`}>
            Integrity: {chain.chain_integrity}
          </div>
          {onVerify && (
            <button
              onClick={() => onVerify(chain.chain_id)}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
            >
              Verify Chain
            </button>
          )}
        </div>
      </div>

      {/* Temporal bounds */}
      <div className="flex gap-6 mb-6 text-sm text-gray-600">
        <div>
          <span className="font-medium">Earliest:</span>{" "}
          {new Date(chain.earliest_timestamp).toLocaleString()}
        </div>
        <div>
          <span className="font-medium">Latest:</span>{" "}
          {new Date(chain.latest_timestamp).toLocaleString()}
        </div>
      </div>

      {/* Chain visualization */}
      <div className="overflow-x-auto">
        <div className="flex items-center py-4 min-w-max">
          {chain.links.map((link, index) => (
            <ChainLinkNode
              key={link.link_id}
              link={link}
              isFirst={index === 0}
              isLast={index === chain.links.length - 1}
            />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 mb-2">Link Types:</div>
        <div className="flex flex-wrap gap-3">
          {Object.values(ChainLinkType).map((type) => (
            <div
              key={type}
              className={`px-2 py-1 rounded text-xs border ${getLinkTypeColor(
                type
              )}`}
            >
              {type}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
