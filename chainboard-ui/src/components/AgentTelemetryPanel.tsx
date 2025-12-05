import React from 'react';
import { useEventBusStore } from '../state/eventBusStore';
import { ChainBridgeEvent } from '../events/eventTypes';

const severityColor: Record<string, string> = {
  CRITICAL: 'bg-red-700 text-white',
  HIGH: 'bg-orange-500 text-white',
  MEDIUM: 'bg-yellow-400 text-black',
  LOW: 'bg-blue-400 text-white',
  INFO: 'bg-gray-300 text-black',
};

export default function AgentTelemetryPanel() {
  const systemEvents = useEventBusStore((s) => s.systemEvents);
  return (
    <div className="p-4 bg-black rounded-lg shadow-lg h-full">
      <h2 className="text-lg font-bold mb-2 text-white">Agent Telemetry Panel</h2>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {systemEvents.length === 0 && (
          <div className="text-gray-400">No agent telemetry events yet.</div>
        )}
        {systemEvents.map((event: ChainBridgeEvent) => (
          <div
            key={event.event_id}
            className={`rounded px-3 py-2 flex flex-col transition-all duration-100 ${
              severityColor[event.severity || 'INFO']
            }`}
          >
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs">{event.event_type}</span>
              <span className="text-xs opacity-70">{new Date(event.timestamp).toLocaleTimeString()}</span>
            </div>
            <div className="text-xs mt-1 break-all">
              {event.payload && JSON.stringify(event.payload)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
