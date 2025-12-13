/**
 * CorridorSelector - Trade corridor filter component
 *
 * ADHD-friendly: clear visual feedback, keyboard navigable.
 * WCAG AA compliant contrast and focus states.
 */

import { ChevronDown, MapPin } from "lucide-react";
import { useState, useRef, useEffect } from "react";

import { classNames } from "../../utils/classNames";

import { DriftDot } from "./DriftSignalBadge";

interface CorridorOption {
  corridor: string;
  eventCount: number;
  driftFlag: boolean;
  p95Delta: number;
}

interface CorridorSelectorProps {
  corridors: CorridorOption[];
  selectedCorridor: string | null;
  onSelect: (corridor: string | null) => void;
  isLoading?: boolean;
  className?: string;
}

export function CorridorSelector({
  corridors,
  selectedCorridor,
  onSelect,
  isLoading,
  className,
}: CorridorSelectorProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close on escape
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  const selectedOption = corridors.find((c) => c.corridor === selectedCorridor);
  const driftingCount = corridors.filter((c) => c.driftFlag).length;

  return (
    <div ref={containerRef} className={classNames("relative", className)}>
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={classNames(
          "flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-all",
          "bg-slate-900/50 hover:bg-slate-800/70 focus:outline-none focus:ring-2 focus:ring-indigo-500/50",
          isOpen ? "border-indigo-500/50" : "border-slate-700/50",
          isLoading && "opacity-50 cursor-not-allowed"
        )}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-slate-400" />
          <span className="text-sm text-slate-200">
            {selectedCorridor || "All Corridors"}
          </span>
          {selectedOption && (
            <DriftDot
              driftDetected={selectedOption.driftFlag}
              p95Delta={selectedOption.p95Delta}
            />
          )}
        </div>
        <div className="flex items-center gap-2">
          {driftingCount > 0 && !selectedCorridor && (
            <span className="rounded bg-red-500/20 px-1.5 py-0.5 text-[10px] font-bold text-red-400">
              {driftingCount} DRIFT
            </span>
          )}
          <ChevronDown
            className={classNames(
              "h-4 w-4 text-slate-400 transition-transform",
              isOpen && "rotate-180"
            )}
          />
        </div>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className={classNames(
            "absolute z-50 mt-1 w-full rounded-lg border border-slate-700/50 bg-slate-900/95 shadow-xl backdrop-blur-md",
            "max-h-64 overflow-y-auto"
          )}
          role="listbox"
        >
          {/* All Corridors option */}
          <button
            type="button"
            onClick={() => {
              onSelect(null);
              setIsOpen(false);
            }}
            className={classNames(
              "flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors",
              "hover:bg-slate-800/70",
              !selectedCorridor && "bg-indigo-500/10 text-indigo-400"
            )}
            role="option"
            aria-selected={!selectedCorridor}
          >
            <span>All Corridors</span>
            <span className="text-xs text-slate-500">{corridors.length} total</span>
          </button>

          {/* Divider */}
          <div className="border-t border-slate-700/50 my-1" />

          {/* Corridor options */}
          {corridors.map((corridor) => (
            <button
              key={corridor.corridor}
              type="button"
              onClick={() => {
                onSelect(corridor.corridor);
                setIsOpen(false);
              }}
              className={classNames(
                "flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors",
                "hover:bg-slate-800/70",
                selectedCorridor === corridor.corridor && "bg-indigo-500/10 text-indigo-400"
              )}
              role="option"
              aria-selected={selectedCorridor === corridor.corridor}
            >
              <div className="flex items-center gap-2">
                <DriftDot
                  driftDetected={corridor.driftFlag}
                  p95Delta={corridor.p95Delta}
                />
                <span className="text-slate-200">{corridor.corridor}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">
                  {corridor.eventCount} events
                </span>
                {corridor.driftFlag && (
                  <span className="rounded bg-red-500/20 px-1 py-0.5 text-[9px] font-bold text-red-400">
                    DRIFT
                  </span>
                )}
              </div>
            </button>
          ))}

          {corridors.length === 0 && (
            <div className="px-3 py-4 text-center text-sm text-slate-500">
              No corridors available
            </div>
          )}
        </div>
      )}
    </div>
  );
}
