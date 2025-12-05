import React from 'react';
import { useEventBusStore } from '../state/eventBusStore';
import { TokenEvent, EventSeverity } from '../events/eventTypes';

function severityColor(severity: EventSeverity = 'INFO') {
  switch (severity) {
    case 'CRITICAL': return 'border-red-500 bg-red-900 text-white animate-pulse';
    case 'HIGH': return 'border-yellow-500 bg-yellow-900 text-black animate-pulse';
    case 'MEDIUM': return 'border-yellow-400 bg-yellow-800 text-black';
    case 'LOW': return 'border-green-500 bg-green-900 text-white';
    case 'INFO':
    default: return 'border-blue-500 bg-blue-900 text-white';
  }
}

function rewardColor() {
  return 'shadow-lg animate-glow';
}
function burnColor() {
  return 'animate-slide-left border-l-8 border-red-600';
}

export default function TokenFlowPanel() {
  const tokenEvents = useEventBusStore((s) => s.tokenEvents);

  return (
    <div className="flex flex-col gap-3 p-4 bg-neutral-900/40 rounded-xl shadow-lg">
      <h2 className="text-lg font-bold mb-2 text-white">Token Flow HUD</h2>
      {tokenEvents.length === 0 && (
        <div className="text-gray-400">No token events yet.</div>
      )}
      {tokenEvents.map((event: TokenEvent) => {
        const isBurn = event.event_type === 'TOKEN_BURN' || event.event_type === 'TOKEN_PENALTY';
        const cardClass = `${severityColor(event.severity)} rounded-xl p-4 shadow-lg border-l-4 mb-2 transition-all duration-150 animate-fade-in`;
        return (
          <div key={event.event_id} className={cardClass} style={{ animationDuration: '0.7s' }}>
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs">Shipment {event.canonical_shipment_id}</span>
              <span className="text-xs opacity-70">{new Date(event.timestamp || '').toLocaleTimeString()}</span>
            </div>
            <div className="flex flex-wrap gap-2 text-xs mt-1 items-center">
              <span className="font-bold">Type:</span> {event.event_type.replace('TOKEN_', '')}
              <span className="font-bold">Token:</span> {event.tokenAmount}
              {isBurn && <span className="font-bold text-red-300">Burn:</span>}
              {isBurn && <span className="text-red-300">{event.burnAmount}</span>}
              {event.finalAmount !== undefined && <span className="font-bold">Final:</span>}
              {event.finalAmount !== undefined && <span>{event.finalAmount}</span>}
              <span className="font-bold">ML Multiplier:</span> {event.mlAdjustment}
              <span className="font-bold">Risk Multiplier:</span> {event.riskMultiplier}
              {event.economicReliability !== undefined && <span className="font-bold">Reliability:</span>}
              {event.economicReliability !== undefined && <span>{event.economicReliability}</span>}
              <span className="font-bold">Net Token:</span> {event.netToken?.toFixed(2)}
            </div>
            <div className="text-xs mt-1">
              <span className="font-bold">Trace ID:</span> {event.traceId}
            </div>
            {event.rationale && (
              <div className="text-xs mt-1 text-yellow-300">
                <span className="font-bold">Rationale:</span> {event.rationale}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Tailwind custom animations (add to tailwind.config.js if needed):
// .animate-glow { animation: glow 0.7s; }
// .animate-slide-left { animation: slideLeft 0.7s; }
// .animate-pulse { animation: pulse 0.7s; }
