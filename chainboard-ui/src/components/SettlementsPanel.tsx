import React from 'react';
import clsx from 'clsx';
import { useEventBusStore } from '../state/eventBusStore';

import type { IntentId } from '../routes/OperatorConsole';

interface SettlementEvent {
  event_id: string;
  shipment_id: string;
  timestamp: string;
  milestone: string;
  amount: number;
  risk_decision: string;
  trace_id: string;
  payment_intent_id?: IntentId;
  intent_id?: IntentId;
  rationale?: string;
}

function getSeverity(event: SettlementEvent) {
  if (event.risk_decision === 'HOLD') return 'HOLD';
  if (event.milestone === 'FINALIZED') return 'FINALIZED';
  if (event.milestone === 'MILESTONE_PAID') return 'MILESTONE_PAID';
  if (event.milestone === 'STARTED') return 'STARTED';
  return 'STARTED';
}

const severityMap: Record<string, string> = {
  HOLD: 'bg-red-700 text-white animate-shake',
  FINALIZED: 'bg-green-700 text-white animate-bounce',
  MILESTONE_PAID: 'bg-blue-700 text-white animate-pulse',
  STARTED: 'bg-gray-700 text-white',
};

interface SettlementsPanelProps {
  selectedIntentId: IntentId | null;
  onSelectIntent: (intentId: IntentId) => void;
}

export default function SettlementsPanel({
  selectedIntentId,
  onSelectIntent,
}: SettlementsPanelProps) {
  const settlementEvents = useEventBusStore((s) => s.settlementEvents);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 h-full">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-slate-100 tracking-wide">
          Settlements
        </h2>
        <span className="text-[11px] text-slate-500">
          {settlementEvents.length} events
        </span>
      </div>
      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {settlementEvents.length === 0 && (
          <div className="text-xs text-slate-400">
            No settlement events yet. Once ChainPay starts emitting context
            ledger events, they will appear here.
          </div>
        )}
        {settlementEvents.map((event: SettlementEvent) => {
          const severity = getSeverity(event);
          const intentId = event.payment_intent_id ?? event.intent_id ?? null;
          const isSelected = Boolean(intentId && intentId === selectedIntentId);

          return (
            <button
              key={event.event_id}
              type="button"
              onClick={() => {
                if (!intentId) return;
                onSelectIntent(intentId);
              }}
              className={clsx(
                'w-full text-left rounded-xl px-3 py-2 flex flex-col transition-all duration-150 border',
                severityMap[severity],
                isSelected
                  ? 'ring-2 ring-amber-400/80 border-amber-400'
                  : 'border-transparent',
              )}
              style={{ animationDuration: '0.7s' }}
            >
              <div className="flex justify-between items-center">
                <span className="font-mono text-[11px]">
                  Shipment {event.shipment_id}
                </span>
                <span className="text-[10px] opacity-70">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="flex flex-wrap gap-2 text-[11px] mt-1">
                <span className="font-bold">Milestone:</span> {event.milestone}
                <span className="font-bold">Amount:</span> ${event.amount}
                <span className="font-bold">Risk:</span> {event.risk_decision}
              </div>
              <div className="text-[11px] mt-1 flex justify-between items-center">
                <span>
                  <span className="font-bold">Trace ID:</span> {event.trace_id}
                </span>
                {intentId && (
                  <span className="text-[10px] text-slate-200">
                    Intent {intentId}
                  </span>
                )}
              </div>
              {event.rationale && (
                <div className="text-[11px] mt-1 text-yellow-300">
                  <span className="font-bold">Rationale:</span> {event.rationale}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Tailwind custom animations (add to tailwind.config.js if needed):
// .animate-shake { animation: shake 0.7s; }
// .animate-bounce { animation: bounce 0.7s; }
// .animate-pulse { animation: pulse 0.7s; }
