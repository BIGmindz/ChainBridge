// ═══════════════════════════════════════════════════════════════════════════════
// ChainTrust Invariant Coverage Panel
// PAC-JEFFREY-P19R: ChainTrust UI Implementation (Sonny GID-02)
//
// READ-ONLY invariant coverage visualization.
// Displays: S/A/X/T/F/UNIFORM categories, enforcement mode, validation timestamps.
//
// DATA SOURCE: INVARIANT_REGISTRY from lint_v2
// INVARIANT: INV-LINT-PLAT-003 — UI renders only lint-validated state
// ═══════════════════════════════════════════════════════════════════════════════

import React, { useState } from 'react';
import type {
  InvariantCoveragePanelDTO,
  InvariantCategoryStats,
  InvariantDisplay,
  InvariantClassCategory,
} from '../../types/chaintrust';
import {
  INVARIANT_CLASS_COLORS,
  INVARIANT_CLASS_LABELS,
} from '../../types/chaintrust';

interface InvariantCoveragePanelProps {
  data: InvariantCoveragePanelDTO | null;
  loading: boolean;
  error: string | null;
}

/**
 * Category progress bar.
 */
const CategoryBar: React.FC<{ category: InvariantCategoryStats }> = ({ category }) => {
  const colorClass = INVARIANT_CLASS_COLORS[category.category];
  const label = INVARIANT_CLASS_LABELS[category.category];
  
  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded ${colorClass}`}></div>
          <span className="text-sm text-gray-300">{label}</span>
          <span className="text-xs text-gray-500 font-mono">({category.category})</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-green-400">{category.pass_count} pass</span>
          {category.fail_count > 0 && (
            <span className="text-xs text-red-400">{category.fail_count} fail</span>
          )}
          <span className="text-xs text-gray-500">{category.invariant_count} total</span>
        </div>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div
          className={`${colorClass} h-2 rounded-full transition-all duration-300`}
          style={{ width: `${category.coverage_percent}%` }}
        ></div>
      </div>
      <div className="text-xs text-gray-500 text-right mt-1">
        {category.coverage_percent.toFixed(1)}% coverage
      </div>
    </div>
  );
};

/**
 * Single invariant row in the detailed list.
 */
const InvariantRow: React.FC<{ invariant: InvariantDisplay }> = ({ invariant }) => {
  const categoryColor = INVARIANT_CLASS_COLORS[invariant.invariant_class];
  
  return (
    <div className="bg-gray-800 rounded-lg p-3 mb-2">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded ${categoryColor}`}></div>
          <span className="text-sm font-mono text-blue-400">{invariant.invariant_id}</span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            invariant.enforcement_mode === 'HARD_FAIL' 
              ? 'bg-red-900/30 text-red-400' 
              : 'bg-yellow-900/30 text-yellow-400'
          }`}>
            {invariant.enforcement_mode}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-green-400">{invariant.validation_count} ✓</span>
          {invariant.violation_count > 0 && (
            <span className="text-xs text-red-400">{invariant.violation_count} ✗</span>
          )}
        </div>
      </div>
      <div className="text-sm text-white mb-1">{invariant.name}</div>
      <div className="text-xs text-gray-500">{invariant.description}</div>
      {invariant.last_validated_at && (
        <div className="text-xs text-gray-600 mt-2">
          Last validated: {new Date(invariant.last_validated_at).toLocaleString()}
        </div>
      )}
    </div>
  );
};

/**
 * Filter tabs for invariant categories.
 */
const CategoryTabs: React.FC<{
  categories: InvariantCategoryStats[];
  selected: InvariantClassCategory | 'ALL';
  onSelect: (category: InvariantClassCategory | 'ALL') => void;
}> = ({ categories, selected, onSelect }) => {
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      <button
        onClick={() => onSelect('ALL')}
        className={`text-xs px-3 py-1 rounded ${
          selected === 'ALL'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        All
      </button>
      {categories.map((cat) => (
        <button
          key={cat.category}
          onClick={() => onSelect(cat.category)}
          className={`text-xs px-3 py-1 rounded ${
            selected === cat.category
              ? `${INVARIANT_CLASS_COLORS[cat.category]} text-white`
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          {cat.category} ({cat.invariant_count})
        </button>
      ))}
    </div>
  );
};

/**
 * Loading skeleton.
 */
const LoadingSkeleton: React.FC = () => (
  <div className="animate-pulse space-y-4">
    {[1, 2, 3, 4, 5, 6].map((i) => (
      <div key={i}>
        <div className="h-4 bg-gray-700 rounded w-32 mb-2"></div>
        <div className="h-2 bg-gray-700 rounded w-full"></div>
      </div>
    ))}
  </div>
);

/**
 * Invariant Coverage Panel for ChainTrust.
 * Shows invariant categories with coverage stats and detailed list.
 */
export const InvariantCoveragePanel: React.FC<InvariantCoveragePanelProps> = ({
  data,
  loading,
  error,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<InvariantClassCategory | 'ALL'>('ALL');
  const [showDetails, setShowDetails] = useState(false);

  if (error) {
    return (
      <div className="bg-gray-900 border border-red-500 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-400 mb-2">Invariant Coverage Error</h3>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  // Filter invariants by selected category
  const filteredInvariants = data?.invariants.filter(
    (inv) => selectedCategory === 'ALL' || inv.invariant_class === selectedCategory
  ) || [];

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Invariant Coverage</h3>
        {!loading && data && (
          <div className="flex items-center gap-4">
            <span className="text-sm text-blue-400">
              {data.total_invariants} Invariants
            </span>
            <span className={`text-xs px-2 py-1 rounded ${
              data.enforcement_mode === 'HARD_FAIL'
                ? 'bg-red-900/30 text-red-400'
                : 'bg-yellow-900/30 text-yellow-400'
            }`}>
              {data.enforcement_mode}
            </span>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingSkeleton />
      ) : data ? (
        <>
          {/* Category Coverage Bars */}
          <div className="mb-6">
            {data.categories.map((cat) => (
              <CategoryBar key={cat.category} category={cat} />
            ))}
          </div>

          {/* Toggle Details */}
          <div className="border-t border-gray-700 pt-4">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-sm text-blue-400 hover:text-blue-300 mb-4"
            >
              {showDetails ? '▼ Hide Details' : '▶ Show Invariant Details'}
            </button>

            {showDetails && (
              <>
                {/* Category Filter */}
                <CategoryTabs
                  categories={data.categories}
                  selected={selectedCategory}
                  onSelect={setSelectedCategory}
                />

                {/* Invariant List */}
                <div className="max-h-[400px] overflow-y-auto">
                  {filteredInvariants.length === 0 ? (
                    <div className="text-center text-gray-500 py-4">
                      No invariants in selected category
                    </div>
                  ) : (
                    filteredInvariants.map((inv) => (
                      <InvariantRow key={inv.invariant_id} invariant={inv} />
                    ))
                  )}
                </div>
              </>
            )}
          </div>

          {/* Last Full Validation */}
          <div className="border-t border-gray-700 pt-4 mt-4">
            <span className="text-xs text-gray-500">
              Last Full Validation: {new Date(data.last_full_validation_at).toLocaleString()}
            </span>
          </div>
        </>
      ) : null}
    </div>
  );
};

export default InvariantCoveragePanel;
