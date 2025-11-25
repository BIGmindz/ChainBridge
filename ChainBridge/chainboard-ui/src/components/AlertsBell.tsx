import React from "react";

import { useAlertsFeed } from "../hooks/useAlertsFeed";

interface AlertsBellProps {
  onClick: () => void;
  highlighted?: boolean; // for demo mode, optional
}

export const AlertsBell: React.FC<AlertsBellProps> = ({ onClick, highlighted }) => {
  const { alerts, loading } = useAlertsFeed({ status: "open", limit: 50 });

  const count = alerts?.length ?? 0;

  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white hover:bg-slate-50 transition",
        highlighted ? "ring-2 ring-emerald-400 ring-offset-2" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      aria-label="Open alerts"
    >
      {/* Use your actual icon system if you have one */}
      <span className="text-sm font-semibold text-slate-700">🔔</span>

      {!loading && count > 0 && (
        <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white">
          {count > 9 ? "9+" : count}
        </span>
      )}
    </button>
  );
};
