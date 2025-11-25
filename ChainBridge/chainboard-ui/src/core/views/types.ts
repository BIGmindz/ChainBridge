/**
 * Shipments View & Filter Types
 *
 * Control Tower operator console view engine with saved filters.
 */

export type TimeRange = "24h" | "7d" | "30d";

/**
 * Shipments view filter criteria
 */
export interface ShipmentsViewFilters {
  corridor?: string | null;
  riskCategory?: "low" | "medium" | "high" | null;
  paymentState?: string | null;
  search?: string | null;
  timeRange?: TimeRange;
  hasIoTAlerts?: boolean | null;
  hasPaymentHold?: boolean | null;
}

/**
 * Saved shipments view (system or user-defined)
 */
export interface ShipmentsSavedView {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  filters: ShipmentsViewFilters;
  isSystem?: boolean; // true for built-in views
}
