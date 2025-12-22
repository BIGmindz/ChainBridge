/**
 * Layout mode type and configuration for Operator Console.
 *
 * Modes:
 * - FULL_INTEL: Maximum settlement intelligence (balanced 3-panel view)
 * - HYBRID: Operator triage mode (emphasis on queue + detail)
 * - CASH_OPS: Payment operations focus (emphasis on money view)
 */

export type OperatorLayoutMode = "FULL_INTEL" | "HYBRID" | "CASH_OPS";

export const LAYOUT_STORAGE_KEY = "chainbridge.operator.layoutMode";

interface LayoutConfig {
  queue: {
    containerClass: string;
    rowClass: string;
    fontSize: string;
    visible: boolean;
  };
  detail: {
    containerClass: string;
    timelineMode: "expanded" | "accordion";
    metadataMode: "full" | "minimal";
    visible: boolean;
  };
  activity: {
    containerClass: string;
    visible: boolean;
  };
  money: {
    containerClass: string;
    visible: boolean;
    expanded: boolean;
  };
}

export const LAYOUT_CONFIG: Record<OperatorLayoutMode, LayoutConfig> = {
  FULL_INTEL: {
    queue: {
      containerClass: "w-96", // Fixed width for queue
      rowClass: "p-3",
      fontSize: "text-sm",
      visible: true,
    },
    detail: {
      containerClass: "flex-1", // Detail takes remaining space
      timelineMode: "expanded" as const,
      metadataMode: "full" as const,
      visible: true,
    },
    activity: {
      containerClass: "w-80",
      visible: true,
    },
    money: {
      containerClass: "h-1/3", // Balanced money view
      visible: true,
      expanded: true,
    },
  },
  HYBRID: {
    queue: {
      containerClass: "w-1/2", // Wider queue for scanning
      rowClass: "p-2",
      fontSize: "text-xs",
      visible: true,
    },
    detail: {
      containerClass: "flex-1", // Narrower detail panel
      timelineMode: "accordion" as const,
      metadataMode: "minimal" as const,
      visible: true,
    },
    activity: {
      containerClass: "w-80",
      visible: false,
    },
    money: {
      containerClass: "h-1/4", // Compact money view
      visible: true,
      expanded: false,
    },
  },
  CASH_OPS: {
    queue: {
      containerClass: "w-80", // Minimal queue width
      rowClass: "p-2",
      fontSize: "text-xs",
      visible: true,
    },
    detail: {
      containerClass: "w-96", // Fixed detail width
      timelineMode: "accordion" as const,
      metadataMode: "minimal" as const,
      visible: true,
    },
    activity: {
      containerClass: "w-80",
      visible: false,
    },
    money: {
      containerClass: "flex-1", // Money view takes most space
      visible: true,
      expanded: true,
    },
  },
} as const;

/**
 * Read layout mode from localStorage with fallback.
 */
export function readLayoutMode(): OperatorLayoutMode {
  try {
    const stored = localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (stored === "FULL_INTEL" || stored === "HYBRID" || stored === "CASH_OPS") {
      return stored;
    }
    // Migrate old modes
    if (stored === "WIDE_OPS") return "FULL_INTEL";
    if (stored === "COMPACT_LIST") return "HYBRID";
  } catch (error) {
    console.warn("Failed to read layout mode from localStorage:", error);
  }
  return "FULL_INTEL"; // Default
}

/**
 * Write layout mode to localStorage.
 */
export function writeLayoutMode(mode: OperatorLayoutMode): void {
  try {
    localStorage.setItem(LAYOUT_STORAGE_KEY, mode);
  } catch (error) {
    console.error("Failed to write layout mode to localStorage:", error);
  }
}
