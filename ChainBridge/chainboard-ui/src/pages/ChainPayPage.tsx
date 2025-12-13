/**
 * ChainPayPage
 *
 * Dedicated Cash View page for ChainPay payment intent management.
 * Clean, investor-friendly interface built on Money View foundation.
 *
 * Features:
 * - Payment intent summary KPIs
 * - Filterable payment intents table
 * - Detail panel for selected intent
 * - Keyboard navigation support
 * - Deep linking support (/chainpay?intent=abc123)
 */

import { useEffect, useState } from "react";

import { CashFiltersBar } from "../components/chainpay/CashFiltersBar";
import { CashLayout } from "../components/chainpay/CashLayout";
import { CashPaymentIntentDetail } from "../components/chainpay/CashPaymentIntentDetail";
import { CashPaymentIntentsTable } from "../components/chainpay/CashPaymentIntentsTable";
import { useCashKeyboardNavigation } from "../hooks/useCashKeyboardNavigation";
import { useAutoSelect, useChainPayDeepLink } from "../hooks/useDeepLink";
import { usePaymentIntents, usePaymentIntentSummary } from "../hooks/usePaymentIntents";

export default function ChainPayPage() {
  const [selectedIntentId, setSelectedIntentId] = useState<string | null>(null);
  const [filters, setFilters] = useState<{
    status?: string;
    corridor?: string;
    mode?: string;
  }>({});

  // Deep link handling
  const { intentId: deepLinkIntentId, highlight, clearDeepLink } = useChainPayDeepLink();

  // Fetch summary KPIs
  const { data: summary, isLoading: summaryLoading } = usePaymentIntentSummary();

  // Fetch payment intents with filters
  const { data: intents = [], isLoading: intentsLoading } = usePaymentIntents(filters);

  // Auto-select from deep link if present
  useAutoSelect(intents, deepLinkIntentId, setSelectedIntentId, "id");

  // Keyboard navigation hook
  const { selectedIndex, handleKeyDown, autoSelectFirst } = useCashKeyboardNavigation({
    items: intents,
    onSelect: setSelectedIntentId,
    enabled: true,
  });

  // Auto-select first item when intents load (only if no deep link)
  useEffect(() => {
    if (!deepLinkIntentId) {
      autoSelectFirst();
    }
  }, [autoSelectFirst, deepLinkIntentId]);

  // Apply highlight filter from deep link
  useEffect(() => {
    if (highlight === "ready") {
      setFilters({ status: "READY_FOR_PAYMENT" });
      clearDeepLink();
    }
  }, [highlight, clearDeepLink]);

  // Register keyboard event listener
  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Find selected intent
  const selectedIntent = intents.find((i) => i.id === selectedIntentId) ?? null;

  return (
    <CashLayout
      filterBar={
        <CashFiltersBar filters={filters} onFiltersChange={setFilters} />
      }
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
          <div className="text-sm text-slate-400">Ready for Payment</div>
          <div className="text-2xl font-bold text-emerald-400">
            {summaryLoading ? "—" : summary?.ready_for_payment ?? 0}
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
          <div className="text-sm text-slate-400">Awaiting Proof</div>
          <div className="text-2xl font-bold text-amber-400">
            {summaryLoading ? "—" : summary?.awaiting_proof ?? 0}
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
          <div className="text-sm text-slate-400">Blocked by Risk</div>
          <div className="text-2xl font-bold text-red-400">
            {summaryLoading ? "—" : summary?.blocked_by_risk ?? 0}
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
          <div className="text-sm text-slate-400">Total Intents</div>
          <div className="text-2xl font-bold text-slate-300">
            {summaryLoading ? "—" : summary?.total ?? 0}
          </div>
        </div>
      </div>

      {/* Main Content: Table + Detail */}
      <div className="flex gap-4 flex-1 overflow-hidden">
        {/* Left: Payment Intents Table */}
        <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <CashPaymentIntentsTable
            items={intents}
            selectedId={selectedIntentId ?? undefined}
            selectedIndex={selectedIndex}
            isLoading={intentsLoading}
            onSelect={setSelectedIntentId}
          />
        </div>

        {/* Right: Detail Panel */}
        <div className="w-96 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <CashPaymentIntentDetail intent={selectedIntent} />
        </div>
      </div>
    </CashLayout>
  );
}
