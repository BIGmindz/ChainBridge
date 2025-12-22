/**
 * useCommandPalette Hook
 *
 * Manages command palette state and keyboard shortcuts (Cmd/Ctrl+K).
 */

import { useCallback, useEffect, useState } from "react";

import type { CommandItem } from "./types";

export interface UseCommandPaletteResult {
  open: boolean;
  toggle: (value?: boolean) => void;
  items: CommandItem[];
}

/**
 * Hook for command palette with keyboard shortcut handling
 */
export function useCommandPalette(): UseCommandPaletteResult {
  const [open, setOpen] = useState(false);

  const items: CommandItem[] = [
    { id: "nav:overview", label: "Go to Overview", shortcut: "G O" },
    { id: "nav:shipments", label: "Go to Shipments", shortcut: "G S" },
    { id: "nav:triage", label: "Open Triage Work Queue", shortcut: "G T" },
    { id: "triage:my_alerts", label: "Show My Alerts in Triage", shortcut: "T M" },
    { id: "nav:sandbox", label: "Open Sandbox", shortcut: "G B" },
    { id: "demo:start_investor", label: "Start Investor Demo", shortcut: "D I" },
  ];

  const toggle = useCallback((value?: boolean) => {
    setOpen((prev) => (typeof value === "boolean" ? value : !prev));
  }, []);

  // Cmd/Ctrl+K to toggle palette
  useEffect(() => {
    function onKeydown(e: KeyboardEvent) {
      const isMac = navigator.platform.toLowerCase().includes("mac");
      const metaKey = isMac ? e.metaKey : e.ctrlKey;

      if (metaKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }

    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, []);

  return { open, toggle, items };
}
