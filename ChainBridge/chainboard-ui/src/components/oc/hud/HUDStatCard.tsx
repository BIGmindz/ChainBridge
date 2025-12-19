/**
 * HUDStatCard - Minimal statistical display card for The OC
 * Pure presentational component with no business logic
 * 
 * NEUTRALIZED: PAC-BENSON-SONNY-ACTIVATION-BLOCK-UI-ENFORCEMENT-02
 * - No semantic colors
 * - No icons
 * - Monospace data display
 */

import { classNames } from "../../../utils/classNames";

export interface HUDStatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  className?: string;
}

export function HUDStatCard({
  title,
  value,
  subtitle,
  className,
}: HUDStatCardProps): JSX.Element {
  return (
    <div
      className={classNames(
        "border border-slate-700/50 bg-slate-900/50 p-4",
        className
      )}
    >
      <p className="text-xs text-slate-600 uppercase tracking-wider font-mono">
        {title.toLowerCase().replace(/\s+/g, '_')}
      </p>
      <p className="mt-1 text-xl font-mono text-slate-400 tabular-nums">
        {value}
      </p>
      {subtitle && (
        <p className="mt-1 text-xs text-slate-600 font-mono">
          {subtitle}
        </p>
      )}
    </div>
  );
}
