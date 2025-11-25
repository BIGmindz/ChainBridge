/**
 * OCQueueTable - Operator Console Queue Table
 *
 * Displays prioritized shipment queue with row selection.
 * Pure visualization component - displays backend data as-is with NO frontend sorting/filtering.
 *
 * Performance: Implements windowing for queues > 100 items (renders ±30 rows around selection).
 */

import { AlertTriangle, CheckCircle, Shield, Zap } from "lucide-react";
import { useMemo } from "react";

import type { OperatorQueueItem, TransportMode } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

import { ModeBadge } from "./hud/ModeBadge";
import { RiskBadge } from "./hud/RiskBadge";

const VIRTUALIZATION_THRESHOLD = 100;
const WINDOW_SIZE = 30; // Show ±30 rows around selected index

interface OCQueueTableProps {
  items: OperatorQueueItem[];
  selectedId: string | null;
  selectedIndex?: number; // For keyboard focus visual feedback
  selectedIds?: string[]; // For multi-select
  onToggleSelection?: (shipmentId: string) => void; // Toggle multi-select
  isLoading: boolean;
  error: Error | null;
  onSelect: (shipmentId: string) => void;
}

export function OCQueueTable({
  items,
  selectedId,
  selectedIndex,
  selectedIds = [],
  onToggleSelection,
  isLoading,
  error,
  onSelect,
}: OCQueueTableProps) {
  // Virtualization: Only render window around selected index for large queues
  // MUST be before early returns to satisfy React Hook rules
  const { displayItems, startIndex, totalCount, isVirtualized } = useMemo(() => {
    if (items.length <= VIRTUALIZATION_THRESHOLD) {
      return {
        displayItems: items,
        startIndex: 0,
        totalCount: items.length,
        isVirtualized: false,
      };
    }

    // Calculate window range around selected index
    const focusIndex = selectedIndex ?? 0;
    const start = Math.max(0, focusIndex - WINDOW_SIZE);
    const end = Math.min(items.length, focusIndex + WINDOW_SIZE + 1);

    return {
      displayItems: items.slice(start, end),
      startIndex: start,
      totalCount: items.length,
      isVirtualized: true,
    };
  }, [items, selectedIndex]);

  if (error) {
    return (
      <div className="p-4 text-center text-rose-400">
        <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
        <p>Failed to load queue</p>
        <p className="text-xs text-slate-400 mt-1">{error.message}</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400">
        <CheckCircle className="h-12 w-12 mx-auto mb-3 text-emerald-500" />
        <p className="font-medium">No Critical/High at-risk shipments</p>
        <p className="text-xs mt-1">All systems nominal ✨</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Virtualization indicator */}
      {isVirtualized && (
        <div className="px-4 py-2 bg-slate-800/30 border-b border-slate-700 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Showing {displayItems.length} of {totalCount} items (window mode)
          </span>
          <span className="text-xs text-slate-500 font-mono">
            #{startIndex + 1} - #{startIndex + displayItems.length}
          </span>
        </div>
      )}

      <div className="overflow-y-auto divide-y divide-slate-700 flex-1" role="list">
      {displayItems.map((item, displayIndex) => {
        const actualIndex = startIndex + displayIndex;
        const isSelected = selectedId === item.shipmentId;
        const isKeyboardFocused = selectedIndex === actualIndex;
        const isMultiSelected = selectedIds.includes(item.shipmentId);

        return (
          <div
            key={item.shipmentId}
            onClick={() => onSelect(item.shipmentId)}
            className={classNames(
              "p-3 cursor-pointer transition-all border-l-4 relative",
              isSelected && isKeyboardFocused
                ? "bg-slate-700 border-emerald-400 ring-2 ring-emerald-500/50"
                : isSelected
                ? "bg-slate-700 border-blue-500"
                : isMultiSelected
                ? "bg-emerald-500/5 border-emerald-500/50"
                : "bg-slate-800/50 border-slate-700 hover:bg-slate-700/50"
            )}
            role="listitem"
            aria-current={isSelected ? "true" : undefined}
          >
            {/* Multi-select checkbox (subtle) */}
            {onToggleSelection && (
              <div
                className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleSelection(item.shipmentId);
                }}
              >
                <input
                  type="checkbox"
                  checked={isMultiSelected}
                  onChange={() => onToggleSelection(item.shipmentId)}
                  className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500 cursor-pointer"
                  onClick={(e) => e.stopPropagation()}
                  aria-label={`Select ${item.shipmentId}`}
                />
              </div>
            )}

            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="font-mono text-xs font-bold text-slate-200 truncate">
                  {item.shipmentId}
                </div>
                <div className="flex gap-2 mt-1 flex-wrap">
                  {item.corridorCode && (
                    <span className="text-xs text-slate-400 bg-slate-900/50 px-2 py-0.5 rounded">
                      {item.corridorCode}
                    </span>
                  )}
                  {item.mode && (
                    <ModeBadge
                      mode={item.mode as TransportMode}
                      size="sm"
                      showLabel
                    />
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <RiskBadge
                  riskLevel={item.riskLevel}
                  size="sm"
                />
                {item.needsSnapshot && (
                  <span className="text-xs bg-red-950 text-red-300 px-2 py-0.5 rounded font-medium border border-red-700/50">
                    NEEDS SNAPSHOT
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-slate-400">
              <div className="flex items-center gap-3">
                <span>Risk Score: {item.riskScore}</span>

                {/* Reconciliation Status Badge */}
                {item.reconState && (
                  <div className="flex items-center gap-1.5 group relative">
                    <span
                      className={classNames(
                        "px-2 py-0.5 rounded text-xs font-medium",
                        item.reconState === "CLEAN"
                          ? "bg-emerald-900/50 text-emerald-300 border border-emerald-700/50"
                          : item.reconState === "PARTIAL_ESCROW"
                          ? "bg-amber-900/50 text-amber-300 border border-amber-700/50"
                          : "bg-rose-900/50 text-rose-300 border border-rose-700/50"
                      )}
                    >
                      {item.reconState === "CLEAN"
                        ? "Clean"
                        : item.reconState === "PARTIAL_ESCROW"
                        ? "Partial"
                        : "Blocked"}
                    </span>

                    {/* Tooltip with reconciliation details */}
                    <div className="invisible group-hover:visible absolute bottom-full left-0 mb-2 w-48 p-2 bg-slate-900 border border-slate-700 rounded text-xs shadow-xl z-10">
                      <div className="space-y-1">
                        {item.approvedAmount !== undefined && item.approvedAmount !== null && (
                          <div className="flex justify-between">
                            <span className="text-slate-400">Approved:</span>
                            <span className="text-emerald-400 font-mono">${item.approvedAmount.toFixed(2)}</span>
                          </div>
                        )}
                        {item.heldAmount !== undefined && item.heldAmount !== null && (
                          <div className="flex justify-between">
                            <span className="text-slate-400">Held:</span>
                            <span className="text-amber-400 font-mono">${item.heldAmount.toFixed(2)}</span>
                          </div>
                        )}
                        {item.reconScore !== undefined && item.reconScore !== null && (
                          <div className="flex justify-between">
                            <span className="text-slate-400">Recon Score:</span>
                            <span className="text-slate-200 font-mono">{item.reconScore}/100</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Legal Wrapper Status Badge */}
                {item.hasRicardianWrapper && item.ricardianStatus && (
                  <div className="flex items-center gap-1 group relative" title="Ricardian legal wrapper status">
                    <Shield
                      className={classNames(
                        "h-3.5 w-3.5",
                        item.ricardianStatus === "ACTIVE"
                          ? "text-emerald-400"
                          : item.ricardianStatus === "FROZEN"
                          ? "text-rose-400"
                          : "text-slate-500"
                      )}
                    />
                    <span
                      className={classNames(
                        "text-xs font-medium",
                        item.ricardianStatus === "ACTIVE"
                          ? "text-emerald-400"
                          : item.ricardianStatus === "FROZEN"
                          ? "text-rose-400"
                          : "text-slate-500"
                      )}
                    >
                      {item.ricardianStatus === "ACTIVE"
                        ? "Wrapped"
                        : item.ricardianStatus === "FROZEN"
                        ? "Frozen"
                        : "Term"}
                    </span>

                    {/* Tooltip */}
                    <div className="invisible group-hover:visible absolute bottom-full left-0 mb-2 w-36 p-2 bg-slate-900 border border-slate-700 rounded text-xs shadow-xl z-10">
                      <div className="font-medium">
                        {item.ricardianStatus === "ACTIVE"
                          ? "Ricardian Wrapped (Active)"
                          : item.ricardianStatus === "FROZEN"
                          ? "FROZEN – Legal Hold"
                          : "Terminated"}
                      </div>
                      <div className="text-slate-500 mt-1">
                        {item.ricardianStatus === "ACTIVE"
                          ? "Bankable asset"
                          : item.ricardianStatus === "FROZEN"
                          ? "Under legal review"
                          : "Wrapper terminated"}
                      </div>
                    </div>
                  </div>
                )}

                {/* Digital Supremacy Badge - SONNY PACK */}
                {item.hasRicardianWrapper && item.supremacyEnabled !== null && item.supremacyEnabled !== undefined && (
                  <div className="flex items-center gap-1 group relative" title="Digital Supremacy status">
                    <Zap
                      className={classNames(
                        "h-3.5 w-3.5",
                        item.materialAdverseOverride
                          ? "text-rose-400"
                          : item.supremacyEnabled
                          ? "text-purple-400"
                          : "text-slate-500"
                      )}
                    />

                    {/* Tooltip */}
                    <div className="invisible group-hover:visible absolute bottom-full left-0 mb-2 w-48 p-2 bg-slate-900 border border-slate-700 rounded text-xs shadow-xl z-10">
                      <div className="font-medium">
                        {item.materialAdverseOverride
                          ? "🚨 Kill Switch Active"
                          : item.supremacyEnabled
                          ? "⚡ Digital Supremacy Active"
                          : "Digital Supremacy Off"}
                      </div>
                      <div className="text-slate-500 mt-1">
                        {item.materialAdverseOverride
                          ? "Code precedence suspended"
                          : item.supremacyEnabled
                          ? "Smart Contract overrides PDF"
                          : "Code-prose parity only"}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {item.latestSnapshotStatus && (
                <div className="flex items-center gap-1">
                  <div className={classNames(
                    "w-2 h-2 rounded-full",
                    item.latestSnapshotStatus === "SUCCESS" ? "bg-emerald-400" :
                    item.latestSnapshotStatus === "IN_PROGRESS" ? "bg-amber-400 animate-pulse" :
                    item.latestSnapshotStatus === "PENDING" ? "bg-blue-400" : "bg-rose-400"
                  )} />
                  <span
                    className={classNames(
                      "font-medium",
                      item.latestSnapshotStatus === "SUCCESS" ? "text-emerald-400" :
                      item.latestSnapshotStatus === "IN_PROGRESS" ? "text-amber-400" :
                      item.latestSnapshotStatus === "PENDING" ? "text-blue-400" : "text-rose-400"
                    )}
                  >
                    {item.latestSnapshotStatus}
                  </span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
    </div>
  );
}
