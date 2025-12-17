/**
 * Diggi Next Step Button — CRC v1
 *
 * Button component for a single allowed next step.
 * Renders exactly one action from the correction plan.
 *
 * CONSTRAINTS:
 * - Button label is the step description (verbatim)
 * - Button style varies by verb type
 * - No additional actions beyond onClick
 * - Unknown verbs do not render
 *
 * @see PAC-DIGGI-03 — Correction Rendering Contract
 */

import { ArrowRight, MessageSquare, AlertTriangle } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import type { DiggiNextStepButtonProps, DiggiCorrectionVerb } from '../../types/diggi';
import { isKnownVerb } from '../../types/diggi';

/**
 * Icon mapping for each verb type.
 */
const verbIcons: Record<DiggiCorrectionVerb, typeof ArrowRight> = {
  PROPOSE: MessageSquare,
  ESCALATE: AlertTriangle,
  READ: ArrowRight,
};

/**
 * Style classes for each verb type.
 */
const verbStyles: Record<DiggiCorrectionVerb, string> = {
  PROPOSE:
    'border-sky-500/40 bg-sky-500/10 text-sky-200 hover:bg-sky-500/20 hover:border-sky-500/60',
  ESCALATE:
    'border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20 hover:border-amber-500/60',
  READ:
    'border-slate-500/40 bg-slate-500/10 text-slate-200 hover:bg-slate-500/20 hover:border-slate-500/60',
};

/**
 * Disabled button styles.
 */
const disabledStyles =
  'border-slate-700/40 bg-slate-800/30 text-slate-500 cursor-not-allowed';

/**
 * Renders a single next step button.
 * Returns null for unknown verbs (fail closed).
 */
export function DiggiNextStepButton({
  step,
  onClick,
  disabled = false,
  className,
}: DiggiNextStepButtonProps): JSX.Element | null {
  // Unknown verb — do not render button (fail closed)
  if (!isKnownVerb(step.verb)) {
    console.warn('[Diggi] Unknown verb in correction step:', step.verb);
    return null;
  }

  const verb = step.verb.toUpperCase() as DiggiCorrectionVerb;
  const Icon = verbIcons[verb];
  const buttonStyles = disabled ? disabledStyles : verbStyles[verb];

  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={classNames(
        'flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left transition-colors',
        buttonStyles,
        className
      )}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="block text-xs font-semibold uppercase tracking-wider opacity-60 mb-0.5">
          {verb}
        </span>
        <span className="block text-sm leading-snug truncate">
          {step.description}
        </span>
        {step.target && (
          <span className="block text-xs opacity-50 mt-1 font-mono">
            → {step.target}
          </span>
        )}
        {step.target_scope && (
          <span className="block text-xs opacity-50 mt-1 font-mono">
            scope: {step.target_scope}
          </span>
        )}
      </div>
      {!disabled && (
        <ArrowRight className="h-4 w-4 flex-shrink-0 opacity-40" />
      )}
    </button>
  );
}
