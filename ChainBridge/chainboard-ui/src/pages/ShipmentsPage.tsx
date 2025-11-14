import { useEffect, useMemo, useState } from "react";
import type { PaymentState, RiskCategory, Shipment } from "../types";
import { apiClient } from "../services/api";
import ShipmentsTable from "../components/ShipmentsTable";
import type { CorridorId } from "../utils/corridors";
import {
  classifyCorridor,
  getCorridorLabel,
  isCorridorId,
  CORRIDOR_FILTER_OPTIONS,
} from "../utils/corridors";

type StatusFilter = CorridorId | "all";
type RiskFilter = RiskCategory | "all";
type PaymentFilter = PaymentState | "all";

interface FilterState {
  statusFilter: StatusFilter;
  riskFilter: RiskFilter;
  paymentFilter: PaymentFilter;
}

const DEFAULT_FILTERS: FilterState = {
  statusFilter: "all",
  riskFilter: "all",
  paymentFilter: "all",
};

const RISK_FILTER_OPTIONS: Array<{ value: RiskFilter; label: string }> = [
  { value: "all", label: "All Risk Levels" },
  { value: "high", label: "High Risk" },
  { value: "medium", label: "Medium Risk" },
  { value: "low", label: "Low Risk" },
];

const PAYMENT_FILTER_OPTIONS: Array<{ value: PaymentFilter; label: string }> = [
  { value: "all", label: "All Payment States" },
  { value: "blocked", label: "Blocked" },
  { value: "partially_paid", label: "Partially Paid" },
  { value: "in_progress", label: "In Progress" },
  { value: "not_started", label: "Not Started" },
  { value: "completed", label: "Completed" },
];

export default function ShipmentsPage(): JSX.Element {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);

  const initialFilters = useMemo<FilterState>(() => deriveFiltersFromUrl(), []);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(initialFilters.statusFilter);
  const [riskFilter, setRiskFilter] = useState<RiskFilter>(initialFilters.riskFilter);
  const [paymentFilter, setPaymentFilter] = useState<PaymentFilter>(initialFilters.paymentFilter);

  useEffect(() => {
    const fetchShipments = async (): Promise<void> => {
      try {
        const data = await apiClient.getShipments();
        setShipments(data);
      } catch (error) {
        console.error("Failed to load shipments:", error);
      } finally {
        setLoading(false);
      }
    };

    void fetchShipments();
  }, []);

  const filteredShipments = useMemo(() => {
    if (shipments.length === 0) return [];
    return shipments.filter((shipment) => {
      if (
        statusFilter !== "all" &&
        classifyCorridor({ origin: shipment.origin, destination: shipment.destination }).id !== statusFilter
      ) {
        return false;
      }

      if (riskFilter !== "all" && shipment.risk.risk_category !== riskFilter) {
        return false;
      }

      if (paymentFilter !== "all" && shipment.payment_state !== paymentFilter) {
        return false;
      }

      return true;
    });
  }, [shipments, statusFilter, riskFilter, paymentFilter]);

  const activeFilters = useMemo(() => {
    const chips: string[] = [];
    if (statusFilter !== "all" && isCorridorId(statusFilter)) {
      chips.push(`Corridor · ${getCorridorLabel(statusFilter)}`);
    }
    if (riskFilter !== "all") {
      chips.push(`Risk · ${riskFilter}`);
    }
    if (paymentFilter !== "all") {
      chips.push(`Payment · ${paymentFilter.replace(/_/g, " ")}`);
    }
    return chips;
  }, [statusFilter, riskFilter, paymentFilter]);

  return (
    <div className="space-y-6 text-slate-100">
      <header className="space-y-2 border-b border-slate-800/60 pb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">Shipments Intelligence</p>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-50">Manifest Drilldown</h1>
            <p className="text-sm text-slate-400">
              Filter shipments by corridor lens, ChainIQ risk posture, and ChainPay payment holds.
            </p>
          </div>
          {activeFilters.length > 0 && (
            <div className="flex flex-wrap gap-2 text-[11px]">
              {activeFilters.map((chip) => (
                <span
                  key={chip}
                  className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 font-mono text-slate-300"
                >
                  {chip}
                </span>
              ))}
            </div>
          )}
        </div>
      </header>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
        <div className="mb-3 flex items-center justify-between text-[11px] text-slate-400">
          <span className="uppercase tracking-[0.2em]">Filters</span>
          <span className="font-mono text-slate-500">{filteredShipments.length} / {shipments.length || "–"} displayed</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <FilterSelect
            label="Corridor Lens"
            value={statusFilter}
            onChange={setStatusFilter}
            options={CORRIDOR_FILTER_OPTIONS}
          />
          <FilterSelect
            label="Risk Posture"
            value={riskFilter}
            onChange={setRiskFilter}
            options={RISK_FILTER_OPTIONS}
          />
          <FilterSelect
            label="Payment State"
            value={paymentFilter}
            onChange={setPaymentFilter}
            options={PAYMENT_FILTER_OPTIONS}
          />
        </div>
      </section>

      {loading ? (
        <div className="flex h-72 items-center justify-center rounded-2xl border border-slate-800 bg-slate-950/60">
          <div className="text-center text-sm text-slate-400">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-slate-800 border-t-emerald-400" />
            Fetching manifest telemetry…
          </div>
        </div>
      ) : (
        <ShipmentsTable shipments={filteredShipments} />
      )}
    </div>
  );
}

interface FilterSelectProps<T extends string> {
  label: string;
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (value: T) => void;
}

function FilterSelect<T extends string>({ label, value, options, onChange }: FilterSelectProps<T>) {
  return (
    <label className="flex flex-col gap-2 text-sm text-slate-300">
      <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</span>
      <select
        className="rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-slate-100 focus:outline-none focus-visible:border-emerald-400"
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function deriveFiltersFromUrl(): FilterState {
  if (typeof window === "undefined") {
    return DEFAULT_FILTERS;
  }

  const params = new URLSearchParams(window.location.search);
  const corridorParam = params.get("corridor");
  const riskParam = params.get("risk_category");
  const paymentParam = params.get("payment_state");

  return {
    statusFilter: isCorridorId(corridorParam) ? corridorParam : DEFAULT_FILTERS.statusFilter,
    riskFilter: isRiskCategory(riskParam) ? (riskParam as RiskCategory) : DEFAULT_FILTERS.riskFilter,
    paymentFilter: isPaymentState(paymentParam) ? (paymentParam as PaymentState) : DEFAULT_FILTERS.paymentFilter,
  };
}

function isRiskCategory(value: string | null): value is RiskCategory {
  return value === "low" || value === "medium" || value === "high";
}

function isPaymentState(value: string | null): value is PaymentState {
  return (
    value === "not_started" ||
    value === "in_progress" ||
    value === "partially_paid" ||
    value === "blocked" ||
    value === "completed"
  );
}
