import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle, Clock, Loader2, X } from "lucide-react";
import { useEffect } from "react";

import { fetchSnapshotExports } from "../../services/apiClient";
import type { SnapshotExportEvent } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";
import { Badge } from "../ui/Badge";
import { Skeleton } from "../ui/Skeleton";

interface SnapshotTimelineDrawerProps {
  shipmentId: string | null;
  onClose: () => void;
}

export function SnapshotTimelineDrawer({ shipmentId, onClose }: SnapshotTimelineDrawerProps) {
  const isOpen = !!shipmentId;

  // Close on escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  const { data: events, isLoading, isError, error } = useQuery({
    queryKey: ["snapshotExports", shipmentId],
    queryFn: () => (shipmentId ? fetchSnapshotExports(shipmentId) : Promise.resolve([])),
    enabled: !!shipmentId,
    refetchInterval: 5000, // Auto-refresh timeline every 5s while open
  });

  return (
    <>
      {/* Backdrop */}
      <div
        className={classNames(
          "fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40 transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={classNames(
          "fixed inset-y-0 right-0 w-full sm:w-96 bg-slate-900 border-l border-slate-800 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Snapshot Timeline</h2>
              <p className="text-xs text-slate-400 font-mono mt-0.5">{shipmentId}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-full transition-colors"
              title="Close timeline"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {isLoading ? (
              <div className="space-y-6">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex gap-4">
                    <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
                    <div className="space-y-2 flex-1">
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-16 w-full" />
                    </div>
                  </div>
                ))}
              </div>
            ) : isError ? (
              <div className="p-4 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-200 text-sm">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="h-4 w-4" />
                  <span className="font-semibold">Failed to load timeline</span>
                </div>
                {error instanceof Error ? error.message : "Unknown error"}
              </div>
            ) : !events || events.length === 0 ? (
              <div className="text-center py-12 text-slate-500">
                <Clock className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <p>No snapshot history found.</p>
              </div>
            ) : (
              <div className="relative space-y-8 before:absolute before:inset-0 before:ml-3.5 before:-translate-x-px before:h-full before:w-0.5 before:bg-slate-800 before:content-['']">
                {events.map((event) => (
                  <TimelineItem key={event.eventId} event={event} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function TimelineItem({ event }: { event: SnapshotExportEvent }) {
  const getRelativeTime = (isoString: string) => {
    const now = new Date();
    const then = new Date(isoString);
    const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);

    if (seconds < 60) return "Just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "SUCCESS":
        return <CheckCircle className="h-5 w-5 text-emerald-500" />;
      case "FAILED":
        return <AlertCircle className="h-5 w-5 text-rose-500" />;
      case "PENDING":
      case "IN_PROGRESS":
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-slate-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "SUCCESS":
        return "success";
      case "FAILED":
        return "danger";
      case "PENDING":
      case "IN_PROGRESS":
        return "warning";
      default:
        return "info";
    }
  };

  return (
    <div className="relative pl-10 group">
      {/* Icon */}
      <div className="absolute left-0 top-1 flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 ring-2 ring-slate-800 group-hover:ring-slate-700 transition-all">
        {getStatusIcon(event.status)}
      </div>

      {/* Content */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-3">
          <Badge variant={getStatusColor(event.status)} className="text-[10px] px-2 py-0.5 font-semibold">
            {event.status}
          </Badge>
          <div className="flex items-center gap-1">
            <span className="text-xs text-slate-400">{new Date(event.createdAt).toLocaleString()}</span>
            <span className="text-xs text-slate-500 bg-slate-800/50 px-2 py-0.5 rounded">
              {getRelativeTime(event.createdAt)}
            </span>
          </div>
        </div>

        <div className="mt-2 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
            <div>
              <span className="text-slate-500 block">Event ID</span>
              <span className="text-slate-300 font-mono text-[11px]">{event.eventId.slice(0, 8)}...</span>
            </div>
            {event.claimedBy && (
              <div>
                <span className="text-slate-500 block">Worker</span>
                <span className="text-slate-300 font-mono text-[11px]">{event.claimedBy}</span>
              </div>
            )}
            {event.retryCount > 0 && (
              <div>
                <span className="text-slate-500 block">Retries</span>
                <span className="text-yellow-300 font-semibold">{event.retryCount}</span>
              </div>
            )}
          </div>

          {event.failureReason && (
            <div className="mt-3 pt-2 border-t border-slate-700/50">
              <span className="text-rose-400 text-xs font-medium block mb-1">⚠️ Failure Reason</span>
              <p className="text-rose-200/80 text-xs font-mono bg-rose-950/30 p-2 rounded overflow-auto max-h-20">
                {event.failureReason}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
