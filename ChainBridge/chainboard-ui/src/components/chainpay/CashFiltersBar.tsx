/**
 * CashFiltersBar
 *
 * Filter controls for ChainPay Cash View.
 * Allows filtering payment intents by status, corridor, and mode.
 */

interface CashFiltersBarProps {
  filters: {
    status?: string;
    corridor?: string;
    mode?: string;
  };
  onFiltersChange: (filters: {
    status?: string;
    corridor?: string;
    mode?: string;
  }) => void;
}

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All Statuses" },
  { value: "READY_FOR_PAYMENT", label: "Ready for Payment" },
  { value: "AWAITING_PROOF", label: "Awaiting Proof" },
  { value: "BLOCKED_BY_RISK", label: "Blocked by Risk" },
  { value: "PENDING", label: "Pending" },
  { value: "CANCELLED", label: "Cancelled" },
];

const MODE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All Modes" },
  { value: "OCEAN", label: "Ocean" },
  { value: "TRUCK_FTL", label: "Truck (FTL)" },
  { value: "TRUCK_LTL", label: "Truck (LTL)" },
  { value: "AIR", label: "Air" },
  { value: "RAIL", label: "Rail" },
  { value: "INTERMODAL", label: "Intermodal" },
];

export function CashFiltersBar({ filters, onFiltersChange }: CashFiltersBarProps) {
  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFiltersChange({ ...filters, status: e.target.value || undefined });
  };

  const handleModeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFiltersChange({ ...filters, mode: e.target.value || undefined });
  };

  const handleCorridorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({ ...filters, corridor: e.target.value || undefined });
  };

  const handleClearFilters = () => {
    onFiltersChange({ status: undefined, corridor: undefined, mode: undefined });
  };

  const hasActiveFilters = filters.status || filters.corridor || filters.mode;

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Status Filter */}
      <div className="flex items-center gap-2">
        <label htmlFor="status-filter" className="text-xs text-slate-400 font-medium">
          Status:
        </label>
        <select
          id="status-filter"
          value={filters.status || ""}
          onChange={handleStatusChange}
          className="bg-slate-800/50 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Mode Filter */}
      <div className="flex items-center gap-2">
        <label htmlFor="mode-filter" className="text-xs text-slate-400 font-medium">
          Mode:
        </label>
        <select
          id="mode-filter"
          value={filters.mode || ""}
          onChange={handleModeChange}
          className="bg-slate-800/50 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
        >
          {MODE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Corridor Filter */}
      <div className="flex items-center gap-2">
        <label htmlFor="corridor-filter" className="text-xs text-slate-400 font-medium">
          Corridor:
        </label>
        <input
          id="corridor-filter"
          type="text"
          value={filters.corridor || ""}
          onChange={handleCorridorChange}
          placeholder="e.g., IN_US, CN_EU"
          className="bg-slate-800/50 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 w-40"
        />
      </div>

      {/* Clear Filters */}
      {hasActiveFilters && (
        <button
          onClick={handleClearFilters}
          className="text-xs text-slate-400 hover:text-emerald-400 transition-colors underline"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
