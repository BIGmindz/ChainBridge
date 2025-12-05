/**
 * OperatorCommandPalette
 *
 * Keyboard-first command palette for quick actions in the Operator Console.
 * Opens with Ctrl+K / Cmd+K.
 *
 * Features:
 * - Quick navigation to ChainPay, filters, layout toggles
 * - Keyboard navigation (↑/↓/Enter/Esc)
 * - Fuzzy search (simple substring matching)
 * - No external dependencies (keeps bundle size down)
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { classNames } from "../../utils/classNames";

interface Command {
  id: string;
  label: string;
  description: string;
  icon: string;
  action: () => void;
  keywords: string[];
}

interface OperatorCommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onToggleLayoutMode?: () => void;
  onFilterCritical?: () => void;
  onFocusMoneyView?: () => void;
  onReconcile?: () => void;
}

export function OperatorCommandPalette({
  isOpen,
  onClose,
  onToggleLayoutMode,
  onFilterCritical,
  onFocusMoneyView,
  onReconcile,
}: OperatorCommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Define available commands
  const commands: Command[] = [
    {
      id: "goto-chainpay",
      label: "Go to ChainPay Cash View",
      description: "Navigate to payment intents management",
      icon: "💰",
      action: () => {
        navigate("/chainpay");
        onClose();
      },
      keywords: ["chainpay", "cash", "payment", "money"],
    },
    {
      id: "filter-critical",
      label: "Filter: Critical Risk",
      description: "Show only CRITICAL risk shipments",
      icon: "🚨",
      action: () => {
        if (onFilterCritical) {
          onFilterCritical();
        }
        onClose();
      },
      keywords: ["filter", "critical", "risk", "high"],
    },
    {
      id: "toggle-layout",
      label: "Toggle Layout Mode",
      description: "Switch between layout modes",
      icon: "⚡",
      action: () => {
        if (onToggleLayoutMode) {
          onToggleLayoutMode();
        }
        onClose();
      },
      keywords: ["layout", "mode", "toggle", "switch"],
    },
    {
      id: "focus-money",
      label: "Focus Money View Panel",
      description: "Scroll to payment intents section",
      icon: "💵",
      action: () => {
        if (onFocusMoneyView) {
          onFocusMoneyView();
        }
        onClose();
      },
      keywords: ["money", "payment", "focus", "scroll"],
    },
    {
      id: "reconcile-payment",
      label: "Reconcile Selected Payment Intent",
      description: "Trigger reconciliation for active payment",
      icon: "⚖️",
      action: () => {
        if (onReconcile) {
          onReconcile();
        }
        onClose();
      },
      keywords: ["reconcile", "payment", "audit", "payout"],
    },
    {
      id: "goto-chainstake",
      label: "Go to ChainStake Liquidity Dashboard",
      description: "Navigate to corporate treasury staking interface",
      icon: "📊",
      action: () => {
        navigate("/chainstake");
        onClose();
      },
      keywords: ["chainstake", "liquidity", "treasury", "staking", "dashboard", "yield"],
    },
    {
      id: "goto-marketplace",
      label: "Go to ChainSalvage Marketplace",
      description: "Browse and bid on distressed asset inventory",
      icon: "🏪",
      action: () => {
        navigate("/marketplace");
        onClose();
      },
      keywords: ["marketplace", "salvage", "assets", "bid", "auction", "trading", "distressed"],
    },
  ];

  // Filter commands based on query
  const filteredCommands = query.trim()
    ? commands.filter((cmd) => {
        const searchText = query.toLowerCase();
        return (
          cmd.label.toLowerCase().includes(searchText) ||
          cmd.description.toLowerCase().includes(searchText) ||
          cmd.keywords.some((kw) => kw.includes(searchText))
        );
      })
    : commands;

  // Reset selection when filtered commands change
  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredCommands.length]);

  // Focus input when opening
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < filteredCommands.length - 1 ? prev + 1 : 0
          );
          break;

        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev > 0 ? prev - 1 : filteredCommands.length - 1
          );
          break;

        case "Enter":
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
          }
          break;

        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    },
    [filteredCommands, selectedIndex, onClose]
  );

  // Execute command on click
  const executeCommand = useCallback(
    (cmd: Command) => {
      cmd.action();
    },
    []
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Palette */}
      <div className="fixed top-24 left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 animate-in slide-in-from-top-4 duration-200">
        <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl overflow-hidden">
          {/* Search Input */}
          <div className="p-4 border-b border-slate-800">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a command or search..."
              className="w-full bg-slate-800 text-slate-200 placeholder-slate-500 px-4 py-3 rounded-lg border border-slate-700 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 outline-none transition-all"
            />
          </div>

          {/* Commands List */}
          <div className="max-h-96 overflow-y-auto">
            {filteredCommands.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                <div className="text-3xl mb-2">🔍</div>
                <div className="text-sm">No commands found</div>
              </div>
            ) : (
              <div className="py-2">
                {filteredCommands.map((cmd, index) => (
                  <button
                    key={cmd.id}
                    onClick={() => executeCommand(cmd)}
                    className={classNames(
                      "w-full px-4 py-3 flex items-center gap-3 transition-colors text-left",
                      index === selectedIndex
                        ? "bg-emerald-500/10 border-l-2 border-emerald-500"
                        : "hover:bg-slate-800/50 border-l-2 border-transparent"
                    )}
                  >
                    {/* Icon */}
                    <div className="text-2xl flex-shrink-0">{cmd.icon}</div>

                    {/* Label & Description */}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-200">
                        {cmd.label}
                      </div>
                      <div className="text-xs text-slate-500 truncate">
                        {cmd.description}
                      </div>
                    </div>

                    {/* Keyboard hint */}
                    {index === selectedIndex && (
                      <div className="text-xs text-emerald-400 font-mono">
                        ↵
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-slate-800 bg-slate-800/50">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <div>
                <span className="font-mono">↑↓</span> Navigate
                <span className="mx-2">·</span>
                <span className="font-mono">↵</span> Select
                <span className="mx-2">·</span>
                <span className="font-mono">Esc</span> Close
              </div>
              <div>{filteredCommands.length} commands</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
