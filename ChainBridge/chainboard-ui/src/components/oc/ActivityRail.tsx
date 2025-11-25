import { formatDistanceToNow } from "date-fns";
import {
    Activity,
    AlertTriangle,
    Camera,
    CheckCircle2,
    DollarSign,
    FileCheck2,
    Layers,
    Loader2,
    Radio,
    RefreshCw,
    Shield,
    X,
} from "lucide-react";
import { useMemo } from "react";

import { useEventsFeed, useEventsHeartbeat } from "../../hooks/useEventsFeed";
import type { OperatorEventListItem, OperatorEventType } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";

interface ActivityRailPanelProps {
  limit?: number;
  variant?: "inline" | "drawer";
  onClose?: () => void;
}

type EventMeta = {
  label: string;
  icon: JSX.Element;
  color: string;
  pillClass: string;
};

const EVENT_META: Record<OperatorEventType, EventMeta> = {
  PAYMENT_INTENT_CREATED: {
    label: "Payment Intent Created",
    icon: <DollarSign className="h-3.5 w-3.5" />,
    color: "text-emerald-300",
    pillClass: "bg-emerald-900/40 border border-emerald-700/50",
  },
  PAYMENT_STATUS_UPDATED: {
    label: "Payment Status Updated",
    icon: <RefreshCw className="h-3.5 w-3.5" />,
    color: "text-blue-300",
    pillClass: "bg-blue-900/40 border border-blue-700/50",
  },
  SETTLEMENT_EVENT_CREATED: {
    label: "Settlement Event",
    icon: <Layers className="h-3.5 w-3.5" />,
    color: "text-cyan-300",
    pillClass: "bg-cyan-900/40 border border-cyan-700/50",
  },
  PROOF_ATTACHED: {
    label: "Proof Attached",
    icon: <FileCheck2 className="h-3.5 w-3.5" />,
    color: "text-indigo-300",
    pillClass: "bg-indigo-900/40 border border-indigo-700/50",
  },
  SNAPSHOT_REQUESTED: {
    label: "Snapshot Requested",
    icon: <Camera className="h-3.5 w-3.5" />,
    color: "text-amber-300",
    pillClass: "bg-amber-900/40 border border-amber-700/50",
  },
  SNAPSHOT_COMPLETED: {
    label: "Snapshot Completed",
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    color: "text-emerald-300",
    pillClass: "bg-emerald-900/40 border border-emerald-700/50",
  },
  SNAPSHOT_FAILED: {
    label: "Snapshot Failed",
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
    color: "text-rose-300",
    pillClass: "bg-rose-900/40 border border-rose-700/50",
  },
};

function getEventMeta(type: OperatorEventType): EventMeta {
  return (
    EVENT_META[type] || {
      label: type,
      icon: <Activity className="h-3.5 w-3.5" />,
      color: "text-slate-200",
      pillClass: "bg-slate-800 border border-slate-700",
    }
  );
}

function formatEventTime(timestamp: string): string {
  try {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
  } catch (error) {
    console.warn("Failed to format event timestamp", error);
    return "just now";
  }
}

function getHeartbeatStatus(lastHeartbeatAt: string | null) {
  if (!lastHeartbeatAt) {
    return {
      label: "Unknown",
      className: "bg-slate-500",
      subtitle: "No heartbeat detected",
    };
  }

  const lagMs = Date.now() - Date.parse(lastHeartbeatAt);
  if (lagMs < 60_000) {
    return {
      label: "Live",
      className: "bg-emerald-400",
      subtitle: "Event worker healthy",
    };
  }
  if (lagMs < 180_000) {
    return {
      label: "Lagging",
      className: "bg-amber-400 animate-pulse",
      subtitle: "Worker heartbeat delayed",
    };
  }
  return {
    label: "Stale",
    className: "bg-rose-400 animate-pulse",
    subtitle: "Heartbeat missing",
  };
}

export function ActivityRailPanel({ limit = 30, variant = "inline", onClose }: ActivityRailPanelProps) {
  const {
    data,
    error,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
  } = useEventsFeed({ limit });
  const {
    data: heartbeat,
    error: heartbeatError,
    isFetching: heartbeatFetching,
    refetch: refetchHeartbeat,
  } = useEventsHeartbeat();

  const events = useMemo<OperatorEventListItem[]>(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data]
  );

  const heartbeatStatus = getHeartbeatStatus(heartbeat?.last_worker_heartbeat_at ?? null);
  const lastEventLabel = heartbeat?.last_event_at
    ? formatEventTime(heartbeat.last_event_at)
    : "No events yet";

  const showEmptyState = !isLoading && events.length === 0;

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-800 px-4 py-3 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-white">Activity Rail</h3>
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <span className={classNames("w-2 h-2 rounded-full", heartbeatStatus.className)} />
              <span>{heartbeatStatus.label}</span>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {heartbeatStatus.subtitle}. Last event {lastEventLabel}.
          </p>
          {heartbeatError && (
            <p className="text-xs text-rose-300 mt-1">Failed to read heartbeat: {heartbeatError.message}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="flex items-center gap-1 rounded-md border border-slate-700 px-3 py-1 text-xs font-medium text-slate-200 hover:bg-slate-800"
            onClick={() => {
              refetch();
              refetchHeartbeat();
            }}
            disabled={isFetching || heartbeatFetching}
          >
            {isFetching || heartbeatFetching ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Refresh
          </button>
          {variant === "drawer" && (
            <button
              type="button"
              className="rounded-md border border-slate-700 p-1.5 text-slate-300 hover:bg-slate-800"
              onClick={onClose}
              aria-label="Close Activity Rail"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {isLoading && events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <Loader2 className="h-5 w-5 animate-spin mb-3" />
            <p className="text-sm">Syncing live event feed…</p>
          </div>
        ) : error ? (
          <div className="rounded-md border border-rose-700/50 bg-rose-950/40 p-4 text-sm text-rose-200">
            Failed to load event feed: {error.message}
          </div>
        ) : showEmptyState ? (
          <div className="rounded-md border border-slate-800 bg-slate-900/80 p-6 text-center text-slate-400">
            <Radio className="mx-auto mb-3 h-6 w-6 text-slate-500" />
            <p className="font-medium">No operator events yet</p>
            <p className="text-xs mt-1">ChainPay + ChainIQ quiet at the moment.</p>
          </div>
        ) : (
          events.map((event) => <EventRow key={event.id} event={event} />)
        )}
      </div>

      <div className="border-t border-slate-800 px-4 py-3 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <span>Auto-refreshes every 30s</span>
          {hasNextPage && (
            <button
              type="button"
              className="rounded-md border border-slate-700 px-3 py-1 text-xs font-medium text-slate-200 hover:bg-slate-800"
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
            >
              {isFetchingNextPage ? "Loading…" : "Load older"}
            </button>
          )}
        </div>
        <span>{events.length} events</span>
      </div>
    </div>
  );
}

interface EventRowProps {
  event: OperatorEventListItem;
}

function EventRow({ event }: EventRowProps) {
  const meta = getEventMeta(event.eventType);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className={classNames("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold", meta.pillClass, meta.color)}>
              {meta.icon}
              {meta.label}
            </span>
            <span className="text-[11px]">{formatEventTime(event.occurredAt)}</span>
          </div>
          <p className="mt-2 text-sm text-slate-100">{event.summary}</p>
        </div>
        <Shield className="h-4 w-4 text-slate-600" />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
        {event.shipmentId && (
          <span className="font-mono rounded-full border border-slate-700 bg-slate-950/70 px-2 py-0.5">
            {event.shipmentId}
          </span>
        )}
        {event.payment_intent_id && (
          <span className="font-mono rounded-full border border-slate-700 bg-slate-950/70 px-2 py-0.5">
            PI {event.payment_intent_id}
          </span>
        )}
        <span className="rounded-full border border-slate-800 px-2 py-0.5 capitalize">{event.source}</span>
        {event.actor && <span className="px-2 py-0.5 text-slate-300">{event.actor}</span>}
      </div>
    </div>
  );
}
