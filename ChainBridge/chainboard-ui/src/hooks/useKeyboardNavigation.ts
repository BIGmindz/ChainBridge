/**
 * useKeyboardNavigation (Enhanced v2)
 *
 * Custom hook for keyboard-native navigation in the Operator Console.
 *
 * Features:
 * - Arrow Up/Down, J/K: Navigate queue selection
 * - Enter: Focus/open detail panel
 * - E: Export snapshot for selected shipment
 * - Shift+E: Trigger bulk export mode
 * - Shift+R: Reconcile payment intent for selected shipment
 * - S: Open "Stake Inventory" modal (ChainStake)
 * - V: Verify Ricardian Hash for selected shipment
 * - /: Focus global search/filter
 * - Ctrl/Cmd+K: Open command palette
 * - Space: Toggle multi-select on focused row
 * - Guard: Ignore keyboard events in input/textarea/select/contenteditable elements
 *
 * Usage:
 * ```tsx
 * const { selectedIndex, handleKeyDown, selectedIds, toggleSelection } = useKeyboardNavigation({
 *   items: queue,
 *   onSelect: setSelectedShipmentId,
 *   onExport: handleExport,
 *   onBulkExport: handleBulkExport,
 *   onReconcile: handleReconcile,
 *   onStakeInventory: openStakeModal,
 *   onVerifyRicardian: verifyHash,
 *   onCommandPalette: openPalette,
 *   onFocusSearch: focusSearchInput,
 *   multiSelectEnabled: true,
 * });
 *
 * useEffect(() => {
 *   window.addEventListener("keydown", handleKeyDown);
 *   return () => window.removeEventListener("keydown", handleKeyDown);
 * }, [handleKeyDown]);
 * ```
 */

import { useCallback, useRef, useState } from "react";

interface UseKeyboardNavigationOptions<T extends { shipmentId: string }> {
  items: T[];
  onSelect: (shipmentId: string | null) => void;
  onExport?: (shipmentId: string) => void;
  onBulkExport?: (shipmentIds: string[]) => void;
  onReconcile?: (shipmentId: string) => void;
  onStakeInventory?: (shipmentId: string) => void; // S key: Open stake modal
  onVerifyRicardian?: (shipmentId: string) => void; // V key: Verify Ricardian hash
  onCommandPalette?: () => void;
  onFocusSearch?: () => void;
  multiSelectEnabled?: boolean;
  enabled?: boolean;
}

export function useKeyboardNavigation<T extends { shipmentId: string }>({
  items,
  onSelect,
  onExport,
  onBulkExport,
  onReconcile,
  onStakeInventory,
  onVerifyRicardian,
  onCommandPalette,
  onFocusSearch,
  multiSelectEnabled = false,
  enabled = true,
}: UseKeyboardNavigationOptions<T>) {
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const itemsRef = useRef(items);

  // Keep items ref up to date for stable callback
  itemsRef.current = items;

  // Toggle selection for multi-select mode
  const toggleSelection = useCallback((shipmentId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(shipmentId)) {
        next.delete(shipmentId);
      } else {
        next.add(shipmentId);
      }
      return next;
    });
  }, []);

  // Clear all selections
  const clearSelections = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // Guard: Don't fire in input fields, textareas, selects, or contenteditable
      const target = e.target as HTMLElement;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target.isContentEditable
      ) {
        return;
      }

      const currentItems = itemsRef.current;
      if (currentItems.length === 0) return;

      // Command palette (Ctrl+K or Cmd+K)
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        if (onCommandPalette) {
          onCommandPalette();
        }
        return;
      }

      // Focus search (/)
      if (e.key === "/" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        if (onFocusSearch) {
          onFocusSearch();
        }
        return;
      }

      switch (e.key) {
        case "ArrowUp":
        case "k":
        case "K":
          e.preventDefault();
          setSelectedIndex((prev) => {
            const newIndex = prev > 0 ? prev - 1 : currentItems.length - 1; // Wrap to end
            onSelect(currentItems[newIndex]?.shipmentId ?? null);
            return newIndex;
          });
          break;

        case "ArrowDown":
        case "j":
        case "J":
          e.preventDefault();
          setSelectedIndex((prev) => {
            const newIndex = prev < currentItems.length - 1 ? prev + 1 : 0; // Wrap to start
            onSelect(currentItems[newIndex]?.shipmentId ?? null);
            return newIndex;
          });
          break;

        case "Enter":
          e.preventDefault();
          // Focus detail panel (visual cue only - panel auto-updates via selection)
          // Could add scroll-to-detail behavior here if needed
          break;

        case " ": // Space for multi-select toggle
          if (multiSelectEnabled && currentItems[selectedIndex]) {
            e.preventDefault();
            toggleSelection(currentItems[selectedIndex].shipmentId);
          }
          break;

        case "r":
        case "R":
          e.preventDefault();
          // Shift+R: Trigger reconciliation for selected shipment
          if (e.shiftKey && onReconcile && currentItems[selectedIndex]) {
            onReconcile(currentItems[selectedIndex].shipmentId);
          }
          break;

        case "e":
        case "E":
          e.preventDefault();
          // Shift+E: Bulk export
          if (e.shiftKey && onBulkExport && selectedIds.size > 0) {
            onBulkExport(Array.from(selectedIds));
          }
          // E: Single export
          else if (onExport && currentItems[selectedIndex]) {
            onExport(currentItems[selectedIndex].shipmentId);
          }
          break;

        case "s":
        case "S":
          e.preventDefault();
          // S: Open stake inventory modal
          if (!e.shiftKey && onStakeInventory && currentItems[selectedIndex]) {
            onStakeInventory(currentItems[selectedIndex].shipmentId);
          }
          break;

        case "v":
        case "V":
          e.preventDefault();
          // V: Verify Ricardian hash
          if (!e.shiftKey && onVerifyRicardian && currentItems[selectedIndex]) {
            onVerifyRicardian(currentItems[selectedIndex].shipmentId);
          }
          break;

        // Future: Add more shortcuts as needed
      }
    },
    [enabled, onSelect, onExport, onBulkExport, onReconcile, onStakeInventory, onVerifyRicardian, onCommandPalette, onFocusSearch, selectedIndex, multiSelectEnabled, toggleSelection, selectedIds]
  );

  // Auto-select first item when queue loads/changes
  const autoSelectFirst = useCallback(() => {
    if (items.length > 0 && selectedIndex >= items.length) {
      setSelectedIndex(0);
      onSelect(items[0]?.shipmentId ?? null);
    } else if (items.length > 0 && selectedIndex < items.length) {
      onSelect(items[selectedIndex]?.shipmentId ?? null);
    }
  }, [items, selectedIndex, onSelect]);

  return {
    selectedIndex,
    handleKeyDown,
    autoSelectFirst,
    selectedIds: Array.from(selectedIds),
    toggleSelection,
    clearSelections,
  };
}
