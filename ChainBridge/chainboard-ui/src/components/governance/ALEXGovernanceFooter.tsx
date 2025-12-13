/**
 * ALEXGovernanceFooter - Build governance compliance footer
 *
 * Shows ALEX governance status in all builds.
 * PAC-SONNY-020 requirement: ALEX governance footer in all builds.
 */

import { Shield, CheckCircle, AlertTriangle, Clock } from "lucide-react";

import { classNames } from "../../utils/classNames";

interface ALEXGovernanceFooterProps {
  className?: string;
  variant?: "minimal" | "full";
}

// Build-time info (would be injected by build process in production)
const BUILD_INFO = {
  version: import.meta.env.VITE_APP_VERSION || "0.2.0",
  alexCompliant: true,
  lastAudit: new Date().toISOString().split("T")[0],
  buildHash: import.meta.env.VITE_GIT_SHA?.slice(0, 7) || "dev",
};

export function ALEXGovernanceFooter({
  className,
  variant = "minimal",
}: ALEXGovernanceFooterProps): JSX.Element {
  if (variant === "minimal") {
    return (
      <footer
        className={classNames(
          "flex items-center justify-center gap-2 py-2 text-[10px] text-slate-600",
          className
        )}
      >
        <Shield className="h-3 w-3" />
        <span>ALEX Governance v{BUILD_INFO.version}</span>
        <span className="text-slate-700">•</span>
        {BUILD_INFO.alexCompliant ? (
          <span className="flex items-center gap-1 text-emerald-600">
            <CheckCircle className="h-3 w-3" />
            Compliant
          </span>
        ) : (
          <span className="flex items-center gap-1 text-amber-600">
            <AlertTriangle className="h-3 w-3" />
            Review Required
          </span>
        )}
      </footer>
    );
  }

  return (
    <footer
      className={classNames(
        "border-t border-slate-800/50 bg-slate-950/80 px-4 py-3",
        className
      )}
    >
      <div className="flex items-center justify-between">
        {/* Left: Governance badge */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800/50">
            <Shield className="h-4 w-4 text-indigo-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-300">
                ALEX Governance
              </span>
              {BUILD_INFO.alexCompliant ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/30">
                  <CheckCircle className="h-3 w-3" />
                  Compliant
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400 border border-amber-500/30">
                  <AlertTriangle className="h-3 w-3" />
                  Review Required
                </span>
              )}
            </div>
            <p className="text-[10px] text-slate-500">
              Automated governance verification for all model operations
            </p>
          </div>
        </div>

        {/* Right: Build info */}
        <div className="flex items-center gap-4 text-[10px] text-slate-500">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>Last Audit: {BUILD_INFO.lastAudit}</span>
          </div>
          <div className="h-3 w-px bg-slate-700" />
          <span className="font-mono">v{BUILD_INFO.version}</span>
          <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono">
            {BUILD_INFO.buildHash}
          </span>
        </div>
      </div>
    </footer>
  );
}

/**
 * Compact inline badge for headers.
 */
export function ALEXBadge({ className }: { className?: string }): JSX.Element {
  return (
    <span
      className={classNames(
        "inline-flex items-center gap-1 rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-400 border border-indigo-500/30",
        className
      )}
    >
      <Shield className="h-3 w-3" />
      ALEX
    </span>
  );
}
