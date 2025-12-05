/**
 * useShipmentsViews Hook
 *
 * View engine for Shipments page: manages saved views, current filters,
 * and syncs with localStorage.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  loadShipmentsViewState,
  saveShipmentsViewState,
  type ShipmentsViewState,
} from "../core/views/storage";
import type {
  ShipmentsSavedView,
  ShipmentsViewFilters,
} from "../core/views/types";

const DEFAULT_VIEW_ID = "default";

/**
 * Build system views (non-deletable, always present)
 */
function buildDefaultViews(): ShipmentsSavedView[] {
  const now = new Date().toISOString();

  return [
    {
      id: DEFAULT_VIEW_ID,
      name: "All Shipments",
      description: "Default Control Tower view",
      createdAt: now,
      updatedAt: now,
      isSystem: true,
      filters: {},
    },
    {
      id: "high-risk",
      name: "High Risk",
      description: "Shipments with high ChainIQ risk score",
      createdAt: now,
      updatedAt: now,
      isSystem: true,
      filters: { riskCategory: "high" },
    },
    {
      id: "payment-holds",
      name: "Payment Holds",
      description: "Shipments with ChainPay payment holds",
      createdAt: now,
      updatedAt: now,
      isSystem: true,
      filters: { hasPaymentHold: true },
    },
    {
      id: "iot-alerts",
      name: "IoT Alerts",
      description: "Shipments with recent ChainSense IoT anomalies",
      createdAt: now,
      updatedAt: now,
      isSystem: true,
      filters: { hasIoTAlerts: true },
    },
    {
      id: "customs-holds",
      name: "Customs Holds",
      description: "Shipments delayed at customs",
      createdAt: now,
      updatedAt: now,
      isSystem: true,
      filters: { paymentState: "blocked" },
    },
  ];
}

export interface UseShipmentsViewsResult {
  views: ShipmentsSavedView[];
  currentView: ShipmentsSavedView;
  currentFilters: ShipmentsViewFilters;
  setFilters: (filters: ShipmentsViewFilters) => void;
  selectView: (id: string) => void;
  saveCurrentAsView: (name: string, description?: string) => void;
  deleteView: (id: string) => void;
}

/**
 * Hook to manage shipments views and filters
 */
export function useShipmentsViews(): UseShipmentsViewsResult {
  const [state, setState] = useState<ShipmentsViewState>(() => {
    const saved = loadShipmentsViewState();
    const defaults = buildDefaultViews();

    // Merge system views with user-saved views
    const mergedViews = [
      ...defaults,
      ...(saved.views ?? []).filter((v) => !v.isSystem),
    ];

    return {
      views: mergedViews,
      lastSelectedId: saved.lastSelectedId ?? DEFAULT_VIEW_ID,
    };
  });

  const [filters, setFiltersState] = useState<ShipmentsViewFilters>({});

  // Current view based on lastSelectedId
  const currentView = useMemo(() => {
    const id = state.lastSelectedId ?? DEFAULT_VIEW_ID;
    return (
      state.views.find((v) => v.id === id) ??
      state.views.find((v) => v.id === DEFAULT_VIEW_ID)!
    );
  }, [state]);

  // Update filters
  const setFilters = useCallback((next: ShipmentsViewFilters) => {
    setFiltersState(next);
  }, []);

  // Select a view and apply its filters
  const selectView = useCallback(
    (id: string) => {
      setState((prev) => ({ ...prev, lastSelectedId: id }));
      const found = state.views.find((v) => v.id === id);
      if (found) {
        setFiltersState(found.filters ?? {});
      }
    },
    [state.views]
  );

  // Save current filters as a new user view
  const saveCurrentAsView = useCallback(
    (name: string, description?: string) => {
      const now = new Date().toISOString();
      const id = `user-${Date.now()}`;

      const newView: ShipmentsSavedView = {
        id,
        name,
        description,
        createdAt: now,
        updatedAt: now,
        isSystem: false,
        filters,
      };

      setState((prev) => ({
        views: [...prev.views, newView],
        lastSelectedId: id,
      }));
    },
    [filters]
  );

  // Delete a user view (system views cannot be deleted)
  const deleteView = useCallback((id: string) => {
    setState((prev) => {
      const remaining = prev.views.filter((v) => v.id !== id || v.isSystem);
      const lastSelectedId =
        prev.lastSelectedId === id ? DEFAULT_VIEW_ID : prev.lastSelectedId;
      return { views: remaining, lastSelectedId };
    });
  }, []);

  // Persist to localStorage when state changes
  useEffect(() => {
    saveShipmentsViewState(state);
  }, [state]);

  // Sync filters when currentView changes initially
  useEffect(() => {
    setFiltersState(currentView.filters ?? {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentView.id]);

  return {
    views: state.views,
    currentView,
    currentFilters: filters,
    setFilters,
    selectView,
    saveCurrentAsView,
    deleteView,
  };
}
