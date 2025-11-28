/**
 * useCashKeyboardNavigation
 *
 * Lightweight keyboard navigation for ChainPay Cash View.
 * Simpler than OC version - no export actions, just navigation.
 *
 * Features:
 * - Arrow Up/Down: Navigate payment intents list
 * - Enter: Focus detail panel (visual only)
 * - Guard: Ignore events in input/textarea
 *
 * Usage:
 * ```tsx
 * const { selectedIndex, handleKeyDown, autoSelectFirst } = useCashKeyboardNavigation({
 *   items: intents,
 *   onSelect: setSelectedIntentId,
 * });
 * ```
 */

import { useCallback, useRef, useState } from "react";

interface UseCashKeyboardNavigationOptions<T extends { id: string }> {
  items: T[];
  onSelect: (id: string | null) => void;
  enabled?: boolean;
}

export function useCashKeyboardNavigation<T extends { id: string }>({
  items,
  onSelect,
  enabled = true,
}: UseCashKeyboardNavigationOptions<T>) {
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const itemsRef = useRef(items);

  // Keep items ref up to date for stable callback
  itemsRef.current = items;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // Guard: Don't fire in input fields
      const target = e.target as HTMLElement;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target.isContentEditable
      ) {
        return;
      }

      const currentItems = itemsRef.current;
      if (currentItems.length === 0) return;

      switch (e.key) {
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) => {
            const newIndex = prev > 0 ? prev - 1 : currentItems.length - 1; // Wrap to end
            onSelect(currentItems[newIndex]?.id ?? null);
            return newIndex;
          });
          break;

        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) => {
            const newIndex = prev < currentItems.length - 1 ? prev + 1 : 0; // Wrap to start
            onSelect(currentItems[newIndex]?.id ?? null);
            return newIndex;
          });
          break;

        case "Enter":
          e.preventDefault();
          // Focus detail panel (visual cue only - panel auto-updates via selection)
          break;
      }
    },
    [enabled, onSelect]
  );

  // Auto-select first item when list loads/changes
  const autoSelectFirst = useCallback(() => {
    if (items.length > 0 && selectedIndex >= items.length) {
      setSelectedIndex(0);
      onSelect(items[0]?.id ?? null);
    } else if (items.length > 0 && selectedIndex < items.length) {
      onSelect(items[selectedIndex]?.id ?? null);
    }
  }, [items, selectedIndex, onSelect]);

  return {
    selectedIndex,
    handleKeyDown,
    autoSelectFirst,
  };
}
