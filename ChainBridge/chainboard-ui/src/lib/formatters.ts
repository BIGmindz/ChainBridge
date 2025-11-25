/**
 * Shared formatting helpers for ChainBoard UI.
 * Keep these pure so they can be reused across hooks, services, and components.
 */

import type {
  Shipment,
  ExceptionRow,
  ShipmentStatus,
  PaymentState,
} from "./types";

/**
 * Format a risk score as a human-readable string with Tailwind-friendly colors.
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
 * Format shipment status into a friendly label/color/icon set.
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
 * Format payment state for display.
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
 * Format timestamp relative to now (e.g. "2h ago").
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
 * Format timestamp into a short HH:MM string.
 */
export function formatTimeOfDay(dateString: string): string {
  return new Date(dateString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * Format USD currency.
 */
export function formatUSD(value: number | string): string {
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
  }).format(numValue);
}

/**
 * Calculate percentage of payment completed based on released milestones.
 */
export function calculatePaymentProgress(shipment: Shipment): number {
  const releasedFromMilestones = shipment.payment.milestones
    .filter((milestone) => milestone.state === "released")
    .reduce((sum, milestone) => sum + milestone.percentage, 0);

  const releasedPercentage = Math.max(
    shipment.payment.released_percentage ?? 0,
    releasedFromMilestones
  );

  return Math.min(releasedPercentage, 100);
}

/**
 * Build shipment lane label.
 */
export function formatLane(origin: string, destination: string): string {
  return `${origin} → ${destination}`;
}

/**
 * Filter exceptions locally for simple dashboards.
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
  return exceptions.filter((exception) => {
    if (filters.risk_min !== undefined && exception.riskScore < filters.risk_min) {
      return false;
    }
    if (filters.risk_max !== undefined && exception.riskScore > filters.risk_max) {
      return false;
    }

    if (filters.issue_types && filters.issue_types.length > 0) {
      const hasMatchingIssue = exception.issue_types.some((issue) =>
        filters.issue_types!.includes(issue)
      );
      if (!hasMatchingIssue) {
        return false;
      }
    }

    if (filters.time_window) {
      const limitMs =
        filters.time_window === "2h"
          ? 2 * 3600000
          : filters.time_window === "24h"
            ? 24 * 3600000
            : 7 * 24 * 3600000;
      const lastUpdate = new Date(exception.last_update).getTime();
      if (Date.now() - lastUpdate > limitMs) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Export exception data to CSV (browser-only helper).
 */
export function exportToCSV(
  data: ExceptionRow[],
  filename: string = "exceptions.csv"
): void {
  const headers = ["Shipment ID", "Lane", "Status", "Risk Score", "Payment State", "Age"];
  const rows = data.map((row) => [
    row.shipmentId,
    row.lane,
    row.current_status,
    row.riskScore,
    row.payment_state,
    row.age_of_issue,
  ]);

  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${cell}"`).join(","))
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
}

/**
 * Format a latency budget for display.
 */
export function formatLatency(latencyMs: number): string {
  if (latencyMs >= 1000) {
    return `${(latencyMs / 1000).toFixed(1)}s`;
  }
  return `${latencyMs}ms`;
}

/**
 * Convert a duration in hours to a compact badge format ("15m", "3h", "2d").
 */
export function formatHoursAsAge(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

/**
 * Helper to describe "last updated" timestamps consistently.
 */
export function formatUpdatedTimestamp(timestamp: string): string {
  return formatRelativeTime(timestamp);
}
