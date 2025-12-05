import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Wifi, WifiOff } from "lucide-react";
import { useMemo } from "react";

import type { HealthResponse } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";

export function APIHealthIndicator() {
  const { data, isLoading, error, isError } = useQuery({
    queryKey: ["apiHealth"],
    queryFn: async () => {
      const response = await fetch("http://127.0.0.1:8001/health");
      if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
      return (await response.json()) as HealthResponse;
    },
    refetchInterval: 45_000, // Poll every 45 seconds
    retry: 2,
  });

  const statusInfo = useMemo(() => {
    if (isLoading) return { status: "checking", color: "bg-slate-600", icon: Wifi, label: "Checking..." };
    if (isError || !data) return { status: "down", color: "bg-red-600", icon: WifiOff, label: "API Down" };
    return { status: "healthy", color: "bg-green-600", icon: CheckCircle2, label: "API Healthy" };
  }, [isLoading, isError, data]);

  const StatusIcon = statusInfo.icon;

  return (
    <div className="group relative">
      <button
        className={classNames(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
          statusInfo.color,
          "text-white hover:opacity-90"
        )}
        title={`API Status: ${statusInfo.label}`}
      >
        <StatusIcon className="h-3.5 w-3.5" />
        <span>{statusInfo.label}</span>
      </button>

      {/* Tooltip */}
      <div className="absolute right-0 top-full mt-2 hidden group-hover:block z-50">
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 shadow-lg whitespace-nowrap">
          <p className="font-semibold mb-1 text-slate-200">{statusInfo.label}</p>
          {data && (
            <>
              <p>Version: {data.version}</p>
              <p>Modules: {data.modules_loaded}</p>
              <p>Pipelines: {data.active_pipelines}</p>
              <p className="text-slate-500 mt-1">{new Date(data.timestamp).toLocaleTimeString()}</p>
            </>
          )}
          {error && (
            <div className="text-red-300 mt-1">
              <p className="font-semibold">Error:</p>
              <p>{error instanceof Error ? error.message : "Unknown error"}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
