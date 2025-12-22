import React from 'react';
import { useEventBusStore } from '../state/eventBusStore';

export default function ShipmentFeed() {
  const events = useEventBusStore((s) => s.events);
  return (
    <div className="p-4 bg-white rounded-lg shadow h-full">
      <h2 className="text-lg font-bold mb-2">Shipment Feed</h2>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {events.length === 0 && (
          <div className="text-gray-400">No shipment events yet.</div>
        )}
        {events.map((event) => (
          <div key={event.event_id} className="rounded px-3 py-2 bg-blue-50 flex flex-col">
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
