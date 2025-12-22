import React from 'react';
import { useEventBusStore } from '../state/eventBusStore';

export default function SettlementsConsole() {
  const settlementProgress = useEventBusStore((s) => s.settlementProgress);
  return (
    <div className="p-4 bg-green-900 rounded-lg shadow h-full">
      <h2 className="text-lg font-bold mb-2 text-white">Settlements Console</h2>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {Object.keys(settlementProgress).length === 0 && (
          <div className="text-gray-400">No settlement events yet.</div>
        )}
        {Object.entries(settlementProgress).map(([shipmentId, progress]) => (
          <div key={shipmentId} className="rounded px-3 py-2 bg-green-100 text-green-900 flex flex-col">
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs">Shipment {shipmentId}</span>
              <span className="text-xs font-bold">{JSON.stringify(progress)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
