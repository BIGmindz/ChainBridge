/**
 * Utility functions for data transformation and formatting
 */

import { Shipment, ExceptionRow, ShipmentStatus, PaymentState } from "../types";

/**
 * Format a risk score as a human-readable string with color guidance
 */
export function formatRiskScore(score: number): {
  text: string;
  color: string;
  bgColor: string;
} {
  if (score < 35) {
    return { text: "Low", color: "text-success-700", bgColor: "bg-success-100" };
  }
  if (score < 70) {
    return { text: "Medium", color: "text-warning-700", bgColor: "bg-warning-100" };
  }
  return { text: "High", color: "text-danger-700", bgColor: "bg-danger-100" };
}

/**
 * Format status as human-readable with Tailwind colors
 */
export function formatStatus(status: ShipmentStatus): {
  text: string;
  color: string;
  icon: string;
} {
  const map: Record<ShipmentStatus, { text: string; color: string; icon: string }> = {
    pickup: { text: "Pickup", color: "text-blue-600", icon: "📦" },
    in_transit: { text: "In Transit", color: "text-primary-600", icon: "🚚" },
    delivery: { text: "Delivery", color: "text-success-600", icon: "📍" },
    delayed: { text: "Delayed", color: "text-warning-600", icon: "⏱️" },
    blocked: { text: "Blocked", color: "text-danger-600", icon: "🚫" },
    completed: { text: "Completed", color: "text-success-600", icon: "✓" },
  };
  return map[status];
}

/**
 * Format payment state for display
 */
export function formatPaymentState(state: PaymentState): {
  text: string;
  color: string;
} {
  const map: Record<PaymentState, { text: string; color: string }> = {
    not_started: { text: "Not started", color: "text-gray-500" },
    in_progress: { text: "In progress", color: "text-primary-600" },
    partially_paid: { text: "Partially paid", color: "text-warning-600" },
    blocked: { text: "Blocked", color: "text-danger-600" },
    completed: { text: "Complete", color: "text-success-600" },
  };
  return map[state];
}

/**
 * Format date for display (relative time)
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

/**
 * Format USD currency
 */
export function formatUSD(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
  }).format(value);
}

/**
 * Calculate percentage of payment completed
 */
export function calculatePaymentProgress(shipment: Shipment): number {
  if (!shipment.payment_schedule.length) return 0;
  const releasedPercentage = shipment.payment_schedule
    .filter((m) => m.status === "released")
    .reduce((sum, m) => sum + m.percentage, 0);
  return Math.min(releasedPercentage, 100);
}

/**
 * Build shipment lane string
 */
export function buildLane(origin: string, destination: string): string {
  return `${origin} → ${destination}`;
}

/**
 * Filter exceptions by criteria
 */
export function filterExceptions(
  exceptions: ExceptionRow[],
  filters: {
    risk_min?: number;
    risk_max?: number;
    issue_types?: string[];
    time_window?: "2h" | "24h" | "7d";
  }
): ExceptionRow[] {
  return exceptions.filter((e) => {
    if (filters.risk_min !== undefined && e.risk_score < filters.risk_min) return false;
    if (filters.risk_max !== undefined && e.risk_score > filters.risk_max) return false;

    if (filters.issue_types && filters.issue_types.length > 0) {
      const hasMatchingIssue = e.issue_types.some((it) =>
        filters.issue_types!.includes(it)
      );
      if (!hasMatchingIssue) return false;
    }

    return true;
  });
}

/**
 * Export data to CSV
 */
export function exportToCSV(data: ExceptionRow[], filename: string = "exceptions.csv"): void {
  const headers = ["Shipment ID", "Lane", "Status", "Risk Score", "Payment State", "Age"];
  const rows = data.map((row) => [
    row.shipment_id,
    row.lane,
    row.current_status,
    row.risk_score,
    row.payment_state,
    row.age_of_issue,
  ]);

  const csv = [headers, ...rows].map((row) => row.map((cell) => `"${cell}"`).join(",")).join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
}
