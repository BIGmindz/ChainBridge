import React from 'react';
import { useEventBusStore } from '../state/eventBusStore';

export default function RiskConsole() {
  const latestRiskScore = useEventBusStore((s) => s.latestRiskScore);
  return (
    <div className="p-4 bg-gray-800 rounded-lg shadow h-full">
      <h2 className="text-lg font-bold mb-2 text-white">Risk Console</h2>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {Object.keys(latestRiskScore).length === 0 && (
          <div className="text-gray-400">No risk scores yet.</div>
        )}
        {Object.entries(latestRiskScore).map(([shipmentId, score]) => (
          <div key={shipmentId} className="rounded px-3 py-2 bg-yellow-100 text-yellow-900 flex flex-col">
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs">Shipment {shipmentId}</span>
              <span className="text-xs font-bold">Risk: {score}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
