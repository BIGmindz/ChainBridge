// ═══════════════════════════════════════════════════════════════════════════════
// ChainBridge Non-Capabilities Banner
// PAC-012: Governance Hardening — ORDER 3 (Sonny GID-05)
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import type { NonCapabilityDTO, NonCapabilitiesListDTO, CapabilityCategory } from '../../types/governance';

interface NonCapabilitiesBannerProps {
  data: NonCapabilitiesListDTO;
  expanded?: boolean;
  onToggleExpand?: () => void;
}

/**
 * Get category icon.
 */
function getCategoryIcon(category: CapabilityCategory): string {
  switch (category) {
    case 'FINANCIAL_ACTION':
      return '💰';
    case 'USER_IMPERSONATION':
      return '👤';
    case 'DATA_MUTATION':
      return '📝';
    case 'SYSTEM_CONTROL':
      return '⚙️';
    case 'TRAINING_FEEDBACK':
      return '🧠';
    case 'EXTERNAL_API':
      return '🌐';
    case 'DATA_ACCESS':
      return '🔒';
    default:
      return '🚫';
  }
}

/**
 * Get category display name.
 */
function getCategoryName(category: CapabilityCategory): string {
  switch (category) {
    case 'FINANCIAL_ACTION':
      return 'Financial Actions';
    case 'USER_IMPERSONATION':
      return 'User Impersonation';
    case 'DATA_MUTATION':
      return 'Data Mutation';
    case 'SYSTEM_CONTROL':
      return 'System Control';
    case 'TRAINING_FEEDBACK':
      return 'Training Feedback';
    case 'EXTERNAL_API':
      return 'External API';
    case 'DATA_ACCESS':
      return 'Data Access';
    default:
      return category;
  }
}

/**
 * Single non-capability item.
 */
const NonCapabilityItem: React.FC<{ item: NonCapabilityDTO }> = ({ item }) => {
  return (
    <div className="border border-red-200 bg-red-50 rounded-md p-3">
      <div className="flex items-start gap-2">
        <span className="text-lg">{getCategoryIcon(item.category)}</span>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <span className="font-medium text-red-800 text-sm">
              {item.capability_id}
            </span>
            {item.enforced && (
              <span className="px-2 py-0.5 rounded bg-red-600 text-white text-xs">
                ENFORCED
              </span>
            )}
          </div>
          <p className="text-sm text-red-700 mt-1">{item.description}</p>
          <p className="text-xs text-red-600 mt-1 opacity-75">
            Reason: {item.reason}
          </p>
        </div>
      </div>
    </div>
  );
};

/**
 * Non-capabilities banner component.
 * 
 * INV-GOV-004: No undeclared capabilities.
 */
export const NonCapabilitiesBanner: React.FC<NonCapabilitiesBannerProps> = ({
  data,
  expanded = false,
  onToggleExpand,
}) => {
  // Group by category
  const byCategory = data.non_capabilities.reduce<Record<string, NonCapabilityDTO[]>>(
    (acc, nc) => {
      const cat = nc.category;
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(nc);
      return acc;
    },
    {}
  );

  return (
    <div className="bg-red-100 border-2 border-red-400 rounded-lg overflow-hidden">
      {/* Header banner */}
      <div
        className="bg-red-600 text-white p-3 flex items-center justify-between cursor-pointer"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-2">
          <span className="text-xl">🚫</span>
          <div>
            <h3 className="font-bold text-lg">System Non-Capabilities</h3>
            <p className="text-sm opacity-90">
              INV-GOV-004: The following actions are explicitly NOT supported
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="bg-red-500 px-3 py-1 rounded-full text-sm font-medium">
            {data.total} declared
          </span>
          {onToggleExpand && (
            <span className="text-xl">{expanded ? '▼' : '▶'}</span>
          )}
        </div>
      </div>

      {/* Collapsed summary */}
      {!expanded && (
        <div className="p-3 flex flex-wrap gap-2">
          {data.non_capabilities.map((nc) => (
            <span
              key={nc.capability_id}
              className="px-2 py-1 bg-white border border-red-300 rounded text-xs text-red-700"
              title={nc.description}
            >
              {getCategoryIcon(nc.category)} {nc.capability_id}
            </span>
          ))}
        </div>
      )}

      {/* Expanded view */}
      {expanded && (
        <div className="p-4 space-y-4">
          {Object.entries(byCategory).map(([category, items]) => (
            <div key={category}>
              <h4 className="text-sm font-medium text-red-800 mb-2 flex items-center gap-2">
                <span>{getCategoryIcon(category as CapabilityCategory)}</span>
                {getCategoryName(category as CapabilityCategory)}
                <span className="text-xs opacity-60">({items.length})</span>
              </h4>
              <div className="space-y-2">
                {items.map((item) => (
                  <NonCapabilityItem key={item.capability_id} item={item} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer notice */}
      <div className="bg-red-200 p-2 text-center text-xs text-red-800">
        <strong>FAIL-CLOSED:</strong> Attempting any non-capability triggers INV-GOV-008
      </div>
    </div>
  );
};

export default NonCapabilitiesBanner;
