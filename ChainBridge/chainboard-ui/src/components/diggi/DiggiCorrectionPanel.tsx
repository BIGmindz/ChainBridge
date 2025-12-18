/**
 * Diggi Correction Panel — PAC-DIGGI-05-FE
 *
 * Read-only correction plan display with human acknowledgement.
 * Renders Diggi-proposed correction steps as a checklist.
 *
 * CONSTRAINTS (NON-NEGOTIABLE):
 * - Steps are READ-ONLY — no user edits
 * - Steps are labeled "Proposed by Diggi"
 * - Steps disabled until human ACK (if required)
 * - No free-text inputs
 * - No retry buttons
 * - Button labels match backend schema exactly
 *
 * @see PAC-DIGGI-05-FE — Diggi Operator UX
 */

import { useState } from 'react';
import { CheckSquare, Square, Lock, Info, AlertTriangle } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type {
  DiggiCorrectionPlan,
  DiggiCorrectionStep,
} from '../../types/diggi';

/**
 * Props for DiggiCorrectionPanel.
 */
export interface DiggiCorrectionPanelProps {
  /** The correction plan from backend */
  correctionPlan: DiggiCorrectionPlan;
  /** Whether human acknowledgement is required before proceeding */
  requiresHumanAck: boolean;
  /** Callback when human acknowledges the correction plan */
  onAcknowledge?: () => void;
  /** Callback when a step is selected (only if acknowledged or not required) */
  onStepSelect?: (step: DiggiCorrectionStep) => void;
  /** Optional correlation ID for audit display */
  correlationId?: string;
  /** Optional additional className */
  className?: string;
}

/**
 * Single correction step item — READ-ONLY.
 * No editing, no free-text, no user modification.
 */
function CorrectionStepItem({
  step,
  index,
  disabled,
  onSelect,
}: {
  step: DiggiCorrectionStep;
  index: number;
  disabled: boolean;
  onSelect?: () => void;
}): JSX.Element {
  return (
    <li
      className={classNames(
        'flex items-start gap-3 rounded-lg border px-4 py-3 transition-colors',
        disabled
          ? 'border-slate-700/30 bg-slate-800/20 opacity-60 cursor-not-allowed'
          : 'border-slate-700/50 bg-slate-800/30 hover:bg-slate-800/50 cursor-pointer'
      )}
      onClick={disabled ? undefined : onSelect}
      role={disabled ? undefined : 'button'}
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => {
        if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onSelect?.();
        }
      }}
    >
      {/* Step number — read-only indicator */}
      <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-slate-700/50 text-xs font-semibold text-slate-400">
        {index + 1}
      </div>

      <div className="flex-1 min-w-0">
        {/* Verb badge */}
        <div className="flex items-center gap-2 mb-1">
          <Badge
            variant={
              step.verb === 'ESCALATE'
                ? 'warning'
                : step.verb === 'PROPOSE'
                ? 'info'
                : 'default'
            }
            className="text-xs"
          >
            {step.verb}
          </Badge>
          <span className="text-xs text-slate-500 italic">Proposed by Diggi</span>
        </div>

        {/* Step description — verbatim from backend */}
        <p className="text-sm text-slate-300 leading-relaxed">
          {step.description}
        </p>

        {/* Target info if present */}
        {step.target && (
          <p className="mt-1 text-xs text-slate-500 font-mono">
            → Target: {step.target}
          </p>
        )}
        {step.target_scope && (
          <p className="mt-1 text-xs text-slate-500 font-mono">
            Scope: {step.target_scope}
          </p>
        )}
      </div>

      {/* Lock indicator when disabled */}
      {disabled && (
        <Lock className="h-4 w-4 flex-shrink-0 text-slate-600" />
      )}
    </li>
  );
}

/**
 * Human acknowledgement section.
 * Button text matches backend schema exactly.
 */
function HumanAckSection({
  acknowledged,
  onAcknowledge,
}: {
  acknowledged: boolean;
  onAcknowledge?: () => void;
}): JSX.Element {
  if (acknowledged) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
        <CheckSquare className="h-5 w-5 text-emerald-400" />
        <span className="text-sm text-emerald-300">
          Governance decision acknowledged
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
        <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-amber-300">
          Human acknowledgement required before correction steps can proceed.
        </p>
      </div>

      <button
        type="button"
        onClick={onAcknowledge}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-amber-500/40 bg-amber-500/20 px-4 py-3 text-amber-200 transition-colors hover:bg-amber-500/30 hover:border-amber-500/60"
      >
        <Square className="h-4 w-4" />
        {/* Button text matches backend schema exactly — no alternative wording */}
        <span className="font-semibold">ACKNOWLEDGE GOVERNANCE DECISION</span>
      </button>
    </div>
  );
}

/**
 * Main correction panel component.
 * Renders Diggi-proposed correction steps as read-only checklist.
 */
export function DiggiCorrectionPanel({
  correctionPlan,
  requiresHumanAck,
  onAcknowledge,
  onStepSelect,
  correlationId,
  className,
}: DiggiCorrectionPanelProps): JSX.Element {
  const [acknowledged, setAcknowledged] = useState(!requiresHumanAck);

  // Handle acknowledgement
  const handleAcknowledge = () => {
    setAcknowledged(true);
    onAcknowledge?.();
  };

  // Steps disabled until acknowledged (if ACK required)
  const stepsDisabled = requiresHumanAck && !acknowledged;

  // Fail closed: If no correction plan data, render error state
  if (!correctionPlan) {
    return (
      <Card className={classNames('border-rose-500/40 bg-rose-500/5', className)}>
        <CardContent className="py-6">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-6 w-6 text-rose-400" />
            <p className="text-sm text-rose-300">
              Correction plan data missing. Cannot render steps.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info className="h-5 w-5 text-sky-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Correction Plan
            </h3>
            <Badge variant="info" className="text-xs">
              READ-ONLY
            </Badge>
          </div>
          <span className="text-xs text-slate-500 italic">
            Proposed by Diggi
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 py-6">
        {/* Cause banner */}
        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 px-4 py-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Denial Cause
          </p>
          <p className="text-sm text-slate-300 font-mono">{correctionPlan.cause}</p>
        </div>

        {/* Human ACK section (if required) */}
        {requiresHumanAck && (
          <HumanAckSection
            acknowledged={acknowledged}
            onAcknowledge={handleAcknowledge}
          />
        )}

        {/* Correction steps — read-only checklist */}
        {correctionPlan.allowed_next_steps.length > 0 ? (
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Correction Steps ({correctionPlan.allowed_next_steps.length})
            </h4>
            <ul className="space-y-2">
              {correctionPlan.allowed_next_steps.map((step, index) => (
                <CorrectionStepItem
                  key={`${step.verb}-${index}`}
                  step={step}
                  index={index}
                  disabled={stepsDisabled}
                  onSelect={() => onStepSelect?.(step)}
                />
              ))}
            </ul>
          </div>
        ) : (
          <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 px-4 py-3">
            <p className="text-sm text-slate-500 italic">
              No correction steps available. Manual escalation may be required.
            </p>
          </div>
        )}

        {/* Correlation ID for audit */}
        {correlationId && (
          <div className="pt-4 border-t border-slate-800/50">
            <p className="text-xs text-slate-600">
              Correlation ID:{' '}
              <code className="text-slate-500">{correlationId}</code>
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
