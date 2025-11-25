/**
 * Shadow KPI Component
 *
 * Reusable KPI card component for displaying Shadow Pilot metrics.
 * Consistent with ChainBridge's OC mission-control aesthetics.
 */

import type { ReactNode } from 'react';

interface ShadowKPIProps {
  label: string;
  value: number;
  format?: 'currency' | 'number' | 'days' | 'percentage';
  tooltip?: string;
  subtitle?: string;
  icon?: ReactNode;
  className?: string;
}

function formatValue(value: number, format: ShadowKPIProps['format']): string {
  switch (format) {
    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);

    case 'percentage':
      return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }).format(value / 100);

    case 'days':
      return `${value.toFixed(1)} days`;

    case 'number':
    default:
      return new Intl.NumberFormat('en-US').format(value);
  }
}

export function ShadowKPI({
  label,
  value,
  format = 'number',
  tooltip,
  subtitle,
  icon,
  className = '',
}: ShadowKPIProps): JSX.Element {
  const formattedValue = formatValue(value, format);

  return (
    <div
      className={`
        bg-slate-900/80 border border-slate-700/50 rounded-lg p-6
        hover:bg-slate-900/90 transition-colors duration-200
        ${className}
      `}
      title={tooltip}
    >
      {/* Header with icon and label */}
      <div className="flex items-center gap-3 mb-2">
        {icon && (
          <div className="flex-shrink-0 text-violet-400">
            {icon}
          </div>
        )}
        <h3 className="text-sm font-medium text-slate-400 tracking-wide uppercase">
          {label}
        </h3>
      </div>

      {/* Main value */}
      <div className="mb-1">
        <span className="text-2xl font-bold text-slate-100">
          {formattedValue}
        </span>
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-slate-500">
          {subtitle}
        </p>
      )}
    </div>
  );
}
