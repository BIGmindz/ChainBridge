/**
 * ShipmentTimeline Component
 *
 * Visual timeline showing shipment lifecycle events with type badges,
 * timestamps, and descriptions. Uses date-fns for formatting.
 */

import { formatDistanceToNow } from "date-fns";

import { TimelineEvent } from "../core/types/events";

interface ShipmentTimelineProps {
  events: TimelineEvent[];
  loading?: boolean;
  error?: Error | null;
}

/**
 * Get badge color based on event type severity/category.
 */
function getEventBadgeColor(eventType: string): string {
  switch (eventType) {
    case "iot_alert":
      return "bg-purple-100 text-purple-800 border-purple-400";
    case "customs_hold":
      return "bg-red-100 text-red-800 border-red-300";
    case "customs_released":
    case "delivered":
    case "payment_release":
      return "bg-green-100 text-green-800 border-green-300";
    case "departed_port":
    case "arrived_port":
    case "picked_up":
      return "bg-blue-100 text-blue-800 border-blue-300";
    default:
      return "bg-gray-100 text-gray-800 border-gray-300";
  }
}

/**
 * Get icon for IoT events to visually distinguish them.
 */
function getEventIcon(eventType: string): JSX.Element | null {
  if (eventType === "iot_alert") {
    return (
      <svg
        className="w-3.5 h-3.5 inline-block mr-1"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
        <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
      </svg>
    );
  }
  return null;
}

/**
 * Format event type as human-readable label.
 */
function formatEventType(eventType: string): string {
  return eventType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function ShipmentTimeline({ events, loading, error }: ShipmentTimelineProps) {
  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-sm text-gray-500">Loading timeline...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 p-4">
        <p className="text-sm text-red-800">
          <strong>Error loading timeline:</strong> {error.message}
        </p>
      </div>
    );
  }

  // Empty state
  if (events.length === 0) {
    return (
      <div className="rounded-lg bg-gray-50 border border-gray-200 p-6 text-center">
        <p className="text-sm text-gray-500">No events recorded yet.</p>
      </div>
    );
  }

  // Timeline rendering
  return (
    <div className="space-y-4">
      {events.map((event, index) => {
        const isLast = index === events.length - 1;
        const badgeColor = getEventBadgeColor(event.eventType);
        // Use index as key since TimelineEvent doesn't have unique eventId
        const eventKey = `${event.reference}-${event.occurredAt}-${index}`;

        return (
          <div key={eventKey} className="relative flex gap-4">
            {/* Timeline dot and line */}
            <div className="flex flex-col items-center">
              <div
                className={`w-3 h-3 rounded-full ring-4 ${
                  event.eventType === 'iot_alert'
                    ? 'bg-purple-600 ring-purple-100'
                    : 'bg-blue-600 ring-blue-100'
                }`}
              ></div>
              {!isLast && <div className="w-0.5 h-full bg-gray-300 mt-1"></div>}
            </div>

            {/* Event content */}
            <div className="flex-1 pb-6">
              {/* Event type badge */}
              <span
                className={`inline-block px-2 py-1 text-xs font-medium rounded border ${badgeColor}`}
              >
                {getEventIcon(event.eventType)}
                {formatEventType(event.eventType)}
              </span>

              {/* Timestamp */}
              <p className="text-xs text-gray-500 mt-1">
                {formatDistanceToNow(new Date(event.occurredAt), { addSuffix: true })}
              </p>

              {/* Description */}
              {event.description && (
                <p className="text-sm text-gray-700 mt-2">{event.description}</p>
              )}

              {/* Metadata (source, severity, corridor) */}
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-600">
                <span>
                  <strong>Source:</strong> {event.source}
                </span>
                {event.severity && (
                  <span>
                    <strong>Severity:</strong> {event.severity}
                  </span>
                )}
                <span>
                  <strong>Corridor:</strong> {event.corridor}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
