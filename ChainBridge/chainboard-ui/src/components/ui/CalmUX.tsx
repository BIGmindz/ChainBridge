/**
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 * LIRA — GID-09 — EXPERIENCE ENGINEER
 * PAC-06-F — UX Calm & Cognitive Load
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 *
 * Components designed to reduce operator anxiety and increase confidence.
 *
 * DESIGN PHILOSOPHY:
 * - "Calm under pressure" - reduce visual noise during stress
 * - Clear positive signals for healthy states
 * - Gradual, non-jarring transitions
 * - Human-readable status messages
 * - Trust-building through transparency
 *
 * ACCESSIBILITY:
 * - WCAG 2.1 AA compliant
 * - Reduced motion support
 * - Screen reader friendly
 * - High contrast mode support
 */

import {
  CheckCircle2,
  Shield,
  ShieldCheck,
  Activity,
  Clock,
  Eye,
  Info,
  TrendingUp,
  Heart,
} from 'lucide-react';
import { ReactNode, useEffect, useState } from 'react';
import { classNames } from '../../utils/classNames';
import { STATUS_COLORS } from './design-tokens';

// =============================================================================
// ALL CLEAR STATES — Positive Reinforcement
// =============================================================================

export interface AllClearProps {
  /** Headline message - keep short and positive */
  title?: string;
  /** Optional supporting message */
  subtitle?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Optional timestamp */
  lastChecked?: string;
  /** Custom icon */
  icon?: ReactNode;
  /** Additional class names */
  className?: string;
}

/**
 * AllClearBadge - Compact positive status indicator
 *
 * Use when: Space is tight but you want to show healthy status
 * Psychology: Green checkmark with calm pulsing reinforces "all is well"
 */
export function AllClearBadge({ className }: { className?: string }) {
  return (
    <div
      className={classNames(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full',
        'bg-emerald-500/10 border border-emerald-500/20',
        'text-emerald-400 text-xs font-medium',
        'animate-calm-breathe',
        className
      )}
      role="status"
      aria-label="All systems operational"
    >
      <CheckCircle2 className="w-3.5 h-3.5" />
      <span>All Clear</span>
    </div>
  );
}

/**
 * AllClearCard - Full positive status display
 *
 * Use when: Dashboard has no alerts/issues to show
 * Psychology: Celebrates the absence of problems, builds operator confidence
 */
export function AllClearCard({
  title = 'All Systems Operational',
  subtitle = 'No issues detected. System performing within normal parameters.',
  size = 'md',
  lastChecked,
  icon,
  className,
}: AllClearProps) {
  const sizeStyles = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const iconSizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };

  return (
    <div
      className={classNames(
        'rounded-xl border',
        'bg-gradient-to-br from-emerald-500/5 via-slate-900/50 to-emerald-500/5',
        'border-emerald-500/20',
        sizeStyles[size],
        'text-center',
        'animate-calm-fade-in',
        className
      )}
      role="status"
      aria-live="polite"
    >
      {/* Icon with gentle glow */}
      <div className="flex justify-center mb-4">
        <div
          className={classNames(
            'rounded-full p-3',
            'bg-emerald-500/10',
            'ring-4 ring-emerald-500/5',
            'animate-calm-breathe'
          )}
        >
          {icon || (
            <ShieldCheck
              className={classNames(iconSizes[size], 'text-emerald-400')}
            />
          )}
        </div>
      </div>

      {/* Title */}
      <h3
        className={classNames(
          'font-semibold text-emerald-300 mb-2',
          size === 'sm' && 'text-sm',
          size === 'md' && 'text-base',
          size === 'lg' && 'text-lg'
        )}
      >
        {title}
      </h3>

      {/* Subtitle */}
      <p
        className={classNames(
          'text-slate-400',
          size === 'sm' && 'text-xs',
          size === 'md' && 'text-sm',
          size === 'lg' && 'text-sm'
        )}
      >
        {subtitle}
      </p>

      {/* Last checked timestamp */}
      {lastChecked && (
        <div className="mt-4 flex items-center justify-center gap-1.5 text-xs text-slate-500">
          <Clock className="w-3 h-3" />
          <span>Last verified {lastChecked}</span>
        </div>
      )}
    </div>
  );
}

/**
 * AllClearStrip - Horizontal banner version
 *
 * Use when: Top of page/section confirmation that everything is healthy
 */
export function AllClearStrip({
  message = 'All systems operational',
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      className={classNames(
        'flex items-center justify-center gap-2 py-2 px-4',
        'bg-emerald-500/5 border-y border-emerald-500/10',
        'text-emerald-400 text-xs',
        className
      )}
      role="status"
    >
      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-calm-pulse" />
      <span>{message}</span>
    </div>
  );
}

// =============================================================================
// OPERATOR REASSURANCE PATTERNS
// =============================================================================

export interface ReassuranceMessageProps {
  /** Message type determines icon and color */
  type: 'watching' | 'protected' | 'verified' | 'improving' | 'healthy';
  /** Main message */
  message: string;
  /** Optional detail line */
  detail?: string;
  /** Additional class names */
  className?: string;
}

const REASSURANCE_CONFIG = {
  watching: {
    icon: Eye,
    color: 'text-sky-400',
    bgColor: 'bg-sky-500/10',
    borderColor: 'border-sky-500/20',
    label: 'Actively monitored',
  },
  protected: {
    icon: Shield,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/20',
    label: 'Protected',
  },
  verified: {
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/20',
    label: 'Verified',
  },
  improving: {
    icon: TrendingUp,
    color: 'text-sky-400',
    bgColor: 'bg-sky-500/10',
    borderColor: 'border-sky-500/20',
    label: 'Improving',
  },
  healthy: {
    icon: Heart,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/20',
    label: 'Healthy',
  },
} as const;

/**
 * ReassuranceMessage - Contextual confidence-building message
 *
 * Use when: Displaying status that might cause anxiety (risk scores, alerts)
 * Psychology: Pairs potentially concerning data with reassuring context
 */
export function ReassuranceMessage({
  type,
  message,
  detail,
  className,
}: ReassuranceMessageProps) {
  const config = REASSURANCE_CONFIG[type];
  const Icon = config.icon;

  return (
    <div
      className={classNames(
        'flex items-start gap-3 p-3 rounded-lg',
        config.bgColor,
        'border',
        config.borderColor,
        'animate-calm-fade-in',
        className
      )}
      role="status"
    >
      <div className={classNames('mt-0.5', config.color)}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className={classNames('text-sm font-medium', config.color)}>
          {message}
        </p>
        {detail && (
          <p className="text-xs text-slate-400 mt-0.5">{detail}</p>
        )}
      </div>
    </div>
  );
}

/**
 * ConfidenceIndicator - Trust-building progress indicator
 *
 * Use when: Showing system confidence/trust scores
 * Psychology: Makes abstract numbers feel trustworthy
 */
export function ConfidenceIndicator({
  score,
  label = 'System Confidence',
  className,
}: {
  score: number; // 0-100
  label?: string;
  className?: string;
}) {
  // Determine color based on score
  const getColor = () => {
    if (score >= 80) return STATUS_COLORS.green;
    if (score >= 60) return STATUS_COLORS.blue;
    if (score >= 40) return STATUS_COLORS.amber;
    return STATUS_COLORS.red;
  };

  const color = getColor();

  return (
    <div className={classNames('space-y-2', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className={classNames('font-semibold tabular-nums', color.text)}>
          {score}%
        </span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={classNames(
            'h-full rounded-full transition-all duration-1000 ease-out',
            color.bgSolid
          )}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${label}: ${score}%`}
        />
      </div>
    </div>
  );
}

// =============================================================================
// CALM TRANSITION WRAPPERS
// =============================================================================

/**
 * CalmTransition - Wrapper that applies smooth entry animations
 *
 * Use when: Content appears/disappears and you want to avoid jarring changes
 */
export function CalmTransition({
  children,
  show = true,
  delay = 0,
  className,
}: {
  children: ReactNode;
  show?: boolean;
  delay?: number;
  className?: string;
}) {
  const [shouldRender, setShouldRender] = useState(show);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (show) {
      setShouldRender(true);
      const timer = setTimeout(() => setIsVisible(true), delay);
      return () => clearTimeout(timer);
    } else {
      setIsVisible(false);
      const timer = setTimeout(() => setShouldRender(false), 300);
      return () => clearTimeout(timer);
    }
  }, [show, delay]);

  if (!shouldRender) return null;

  return (
    <div
      className={classNames(
        'transition-all duration-300 ease-out',
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2',
        className
      )}
    >
      {children}
    </div>
  );
}

/**
 * CalmPulse - Subtle pulsing wrapper for status indicators
 *
 * Use when: Need to draw attention without causing alarm
 */
export function CalmPulse({
  children,
  active = true,
  intensity = 'normal',
  className,
}: {
  children: ReactNode;
  active?: boolean;
  intensity?: 'subtle' | 'normal' | 'strong';
  className?: string;
}) {
  const pulseClass = {
    subtle: 'animate-calm-pulse-subtle',
    normal: 'animate-calm-pulse',
    strong: 'animate-calm-pulse-strong',
  };

  return (
    <div className={classNames(active && pulseClass[intensity], className)}>
      {children}
    </div>
  );
}

// =============================================================================
// COGNITIVE LOAD REDUCERS
// =============================================================================

/**
 * ProgressiveDisclosure - Shows summary with expand option
 *
 * Use when: Complex data that might overwhelm operators
 * Psychology: Gives control back to operator, reduces cognitive overload
 */
export function ProgressiveDisclosure({
  summary,
  children,
  defaultOpen = false,
  className,
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={classNames('rounded-lg border border-slate-700/50', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={classNames(
          'w-full flex items-center justify-between p-3',
          'text-left text-sm text-slate-300',
          'hover:bg-slate-800/30 transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-primary-500/50'
        )}
        aria-expanded={isOpen}
      >
        <span>{summary}</span>
        <Info
          className={classNames(
            'w-4 h-4 text-slate-500 transition-transform duration-200',
            isOpen && 'rotate-180'
          )}
        />
      </button>
      <CalmTransition show={isOpen}>
        <div className="p-3 pt-0 border-t border-slate-700/30">
          {children}
        </div>
      </CalmTransition>
    </div>
  );
}

/**
 * QuietLoading - Non-intrusive loading state
 *
 * Use when: Background refresh that shouldn't alarm the operator
 */
export function QuietLoading({
  text = 'Updating...',
  className,
}: {
  text?: string;
  className?: string;
}) {
  return (
    <div
      className={classNames(
        'inline-flex items-center gap-2 text-xs text-slate-500',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <Activity className="w-3 h-3 animate-calm-spin" />
      <span>{text}</span>
    </div>
  );
}

/**
 * StatusHeartbeat - Visual "system alive" indicator
 *
 * Use when: Operator needs confidence system is responsive
 */
export function StatusHeartbeat({
  label = 'System Active',
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={classNames(
        'inline-flex items-center gap-2 text-xs text-slate-400',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-50" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </span>
      <span>{label}</span>
    </div>
  );
}

// =============================================================================
// VISUAL HIERARCHY HELPERS
// =============================================================================

/**
 * SectionDivider - Clean visual separator with optional label
 */
export function SectionDivider({
  label,
  className,
}: {
  label?: string;
  className?: string;
}) {
  if (!label) {
    return <hr className={classNames('border-slate-700/30 my-4', className)} />;
  }

  return (
    <div className={classNames('flex items-center gap-4 my-4', className)}>
      <hr className="flex-1 border-slate-700/30" />
      <span className="text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </span>
      <hr className="flex-1 border-slate-700/30" />
    </div>
  );
}

/**
 * ImportanceHint - Visual weight indicator for content priority
 */
export function ImportanceHint({
  level,
  children,
  className,
}: {
  level: 'high' | 'medium' | 'low';
  children: ReactNode;
  className?: string;
}) {
  const styles = {
    high: 'border-l-2 border-amber-500/50 pl-3 bg-amber-500/5',
    medium: 'border-l-2 border-slate-500/50 pl-3',
    low: 'opacity-70 text-sm',
  };

  return (
    <div className={classNames(styles[level], className)}>
      {children}
    </div>
  );
}

/**
 * 🩵 LIRA — GID-09 — EXPERIENCE ENGINEER
 * 🩵🩵🩵 END OF PAC-06-F 🩵🩵🩵
 */
