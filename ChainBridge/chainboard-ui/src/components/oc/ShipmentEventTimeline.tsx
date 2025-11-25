/**
 * ShipmentEventTimeline - Simple vertical timeline for shipment events
 * Displays events from /debug/shipments/{id}/events in chronological order
 */

import { AlertCircle, Loader2, RefreshCw } from "lucide-react";

import { useShipmentEvents } from "../../hooks/useShipmentEvents";
import { ShipmentEvent, ShipmentEventType } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";

export interface ShipmentEventTimelineProps {
  shipmentId: string;
  className?: string;
}

const eventTypeConfig = {
  RISK_DECIDED: {
    label: "Risk Decided",
    color: "text-amber-400",
    bgColor: "bg-amber-500/20",
  },
  SNAPSHOT_REQUESTED: {
    label: "Snapshot Requested",
    color: "text-blue-400",
    bgColor: "bg-blue-500/20",
  },
  SNAPSHOT_CLAIMED: {
    label: "Snapshot Claimed",
    color: "text-purple-400",
    bgColor: "bg-purple-500/20",
  },
  SNAPSHOT_COMPLETED: {
    label: "Snapshot Completed",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/20",
  },
  SNAPSHOT_FAILED: {
    label: "Snapshot Failed",
    color: "text-red-400",
    bgColor: "bg-red-500/20",
  },
} as const;

function formatTimestamp(isoString: string): string {
  try {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(date);
  } catch {
    return "Invalid date";
  }
}

function EventItem({ event }: { event: ShipmentEvent }): JSX.Element {
  const config = eventTypeConfig[event.eventType as ShipmentEventType] || {
    label: event.eventType,
    color: "text-slate-400",
    bgColor: "bg-slate-500/20",
  };

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div
          className={classNames(
            "flex h-8 w-8 items-center justify-center rounded-full border-2 border-slate-700",
            config.bgColor
          )}
        >
          <div className={classNames("h-2 w-2 rounded-full", config.color.replace("text-", "bg-"))} />
        </div>
        <div className="h-6 w-px bg-slate-700" />
      </div>
      <div className="flex-1 pb-6">
        <div className="flex items-center justify-between">
          <div className={classNames("text-sm font-medium", config.color)}>
            {config.label}
          </div>
          <div className="text-xs text-slate-500">
            {formatTimestamp(event.occurredAt)}
          </div>
        </div>
        {event.payload && Object.keys(event.payload).length > 0 && (
          <div className="mt-2 text-xs text-slate-400">
            {Object.entries(event.payload).map(([key, value]) => (
              <div key={key} className="truncate">
                <span className="text-slate-500">{key}:</span>{" "}
                <span>{String(value)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function ShipmentEventTimeline({
  shipmentId,
  className
}: ShipmentEventTimelineProps): JSX.Element {
  const { data: events, isLoading, error, refetch } = useShipmentEvents(shipmentId);

  if (isLoading) {
    return (
      <div className={classNames("flex items-center justify-center py-8", className)}>
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        <span className="ml-2 text-sm text-slate-400">Loading events...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={classNames("flex flex-col items-center justify-center py-8", className)}>
        <AlertCircle className="h-8 w-8 text-red-400" />
        <div className="mt-2 text-sm text-red-300">Failed to load events</div>
        <div className="mt-1 text-xs text-slate-500">{error.message}</div>
        <button
          onClick={() => refetch()}
          className="mt-3 flex items-center gap-1 rounded bg-slate-800 px-3 py-1 text-xs text-slate-300 hover:bg-slate-700"
        >
          <RefreshCw className="h-3 w-3" />
          Retry
        </button>
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className={classNames("flex flex-col items-center justify-center py-8", className)}>
        <div className="text-sm text-slate-400">No events recorded</div>
        <div className="text-xs text-slate-500">Events will appear here as they occur</div>
      </div>
    );
  }

  return (
    <div className={classNames("space-y-0", className)}>
      <div className="mb-4 flex items-center justify-between">
        <div className="text-sm font-medium text-slate-300">
          Event Timeline ({events.length})
        </div>
        <button
          onClick={() => refetch()}
          title="Refresh events"
          className="flex items-center gap-1 rounded bg-slate-800 px-2 py-1 text-xs text-slate-400 hover:bg-slate-700"
        >
          <RefreshCw className="h-3 w-3" />
        </button>
      </div>
      <div className="space-y-0">
        {events.map((event) => (
          <EventItem key={event.eventId} event={event} />
        ))}
      </div>
    </div>
  );
}
