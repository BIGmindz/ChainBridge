import React, { useEffect } from 'react';
import { useEventBusStore } from '../state/eventBusStore';
import { useEventStream } from '../events/useEventStream';
import { ChainBridgeEvent } from '../events/eventTypes';

export default function ChainSensePanel() {
  const events = useEventBusStore((s) => s.events);
  const addEvent = useEventBusStore((s) => s.addEvent);

  // Example: subscribe to event stream and add events to store
  useEventStream((event: ChainBridgeEvent) => {
    if (event.event_type === 'IOT_ANOMALY') {
      addEvent(event);
    }
  }, null); // TODO: Replace null with real auth token

  return (
    <div className="p-4 bg-gray-900 rounded-lg shadow-lg h-full">
      <h2 className="text-lg font-bold mb-2 text-white">ChainSense Panel</h2>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {events.filter(e => e.event_type === 'IOT_ANOMALY').length === 0 && (
          <div className="text-gray-400">No IoT anomalies detected.</div>
        )}
        {events.filter(e => e.event_type === 'IOT_ANOMALY').map((event) => (
          <div key={event.event_id} className="rounded px-3 py-2 bg-orange-100 text-orange-900 flex flex-col">
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
