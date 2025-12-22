/**
 * LocalStorage Persistence for Shipments Views
 *
 * Namespaced storage layer for saved views and last selected view.
 */

import type { ShipmentsSavedView } from "./types";

const STORAGE_KEY = "chainboard.shipments.views.v1";

export interface ShipmentsViewState {
  views: ShipmentsSavedView[];
  lastSelectedId?: string | null;
}

/**
 * Load shipments view state from localStorage
 */
export function loadShipmentsViewState(): ShipmentsViewState {
  if (typeof window === "undefined") {
    return { views: [], lastSelectedId: null };
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { views: [], lastSelectedId: null };

    const parsed = JSON.parse(raw) as ShipmentsViewState;
    if (!parsed.views) return { views: [], lastSelectedId: null };

    return parsed;
  } catch {
    return { views: [], lastSelectedId: null };
  }
}

/**
 * Save shipments view state to localStorage
 */
export function saveShipmentsViewState(state: ShipmentsViewState): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore storage errors (quota exceeded, private browsing, etc.)
  }
}
