/**
 * CommandPalette Component
 *
 * Keyboard-driven command launcher for quick navigation (Cmd/Ctrl+K).
 */

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { CommandId, CommandItem } from "../core/command/types";
import { useDemo } from "../core/demo/DemoContext";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  items: CommandItem[];
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ open, onClose, items }) => {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { startScenario } = useDemo();

  // Reset query when opened
  useEffect(() => {
    if (open) {
      setQuery("");
    }
  }, [open]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;

    function onKeydown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    }

    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, [open, onClose]);

  if (!open) return null;

  // Filter items by query
  const filtered = items.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()));

  // Execute command
  const handleCommand = (id: CommandId) => {
    switch (id) {
      case "nav:overview":
        navigate("/");
        break;
      case "nav:shipments":
        navigate("/shipments");
        break;
      case "nav:triage":
        navigate("/triage");
        break;
      case "triage:my_alerts":
        navigate("/triage?view=my_alerts");
        break;
      case "nav:sandbox":
        navigate("/sandbox");
        break;
      case "demo:start_investor":
        startScenario("investor_hot_shipment");
        navigate("/");
        break;
      default:
        break;
    }
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 pt-24"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="border-b border-slate-200 px-3 py-2">
          <input
            autoFocus
            placeholder="Type a command or destination..."
            className="w-full border-none bg-transparent text-sm outline-none"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        {/* Command list */}
        <ul className="max-h-72 overflow-auto px-1 py-2">
          {filtered.length === 0 && (
            <li className="px-3 py-2 text-xs text-slate-500">
              No commands match &quot;{query}&quot;.
            </li>
          )}
          {filtered.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm text-slate-800 hover:bg-slate-50"
                onClick={() => handleCommand(item.id)}
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="text-[10px] uppercase text-slate-400">{item.shortcut}</span>
                )}
              </button>
            </li>
          ))}
        </ul>

        {/* Footer */}
        <div className="border-t border-slate-200 px-3 py-1 text-[10px] text-slate-400">
          Press Esc to close • Cmd/Ctrl+K to toggle
        </div>
      </div>
    </div>
  );
};
