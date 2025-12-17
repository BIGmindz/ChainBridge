/**
 * Diggi Denial Panel — CRC v1
 *
 * Main panel component for displaying a governance denial with correction plan.
 * Renders the denial reason, constraints, and allowed next steps.
 *
 * CONSTRAINTS:
 * - UI renders only backend-provided steps
 * - No additional buttons appear
 * - No free-text retry paths
 * - All buttons disabled if plan invalid
 * - Fail closed if correction payload missing or invalid
 *
 * @see PAC-DIGGI-03 — Correction Rendering Contract
 */

import { XCircle, Info, ChevronRight } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { DiggiErrorBoundary } from './DiggiErrorBoundary';
import { DiggiConstraintList } from './DiggiConstraintList';
import { DiggiNextStepButton } from './DiggiNextStepButton';
import type {
  DiggiDenialPanelProps,
  DiggiCorrectionStep,
} from '../../types/diggi';
import { validateCorrectionPlan } from '../../types/diggi';

/**
 * Status banner showing the denial state.
 */
function DenialStatusBanner({
  reason,
  reasonDetail,
}: {
  reason: string;
  reasonDetail?: string;
}): JSX.Element {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-rose-500/40 bg-rose-500/10 p-4">
      <XCircle className="h-6 w-6 text-rose-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-base font-semibold text-rose-300">
            Action Denied
          </span>
          <Badge variant="danger">{reason}</Badge>
        </div>
        {reasonDetail && (
          <p className="mt-1 text-sm text-rose-300/80 leading-relaxed">
            {reasonDetail}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Section showing allowed next steps as buttons.
 */
function NextStepsSection({
  steps,
  onStepSelect,
  disabled,
}: {
  steps: DiggiCorrectionStep[];
  onStepSelect?: (step: DiggiCorrectionStep) => void;
  disabled: boolean;
}): JSX.Element {
  if (!steps || steps.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
        <div className="flex items-center gap-2 text-slate-400">
          <Info className="h-4 w-4" />
          <span className="text-sm">
            No allowed next steps. Escalation to human operator may be required.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <ChevronRight className="h-4 w-4 text-emerald-400" />
        <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-300">
          Allowed Next Steps
        </h4>
      </div>
      <div className="space-y-2">
        {steps.map((step, index) => (
          <DiggiNextStepButton
            key={`${step.verb}-${index}`}
            step={step}
            onClick={() => onStepSelect?.(step)}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * Hard error display when correction plan is invalid.
 */
function InvalidPlanError({ error }: { error: string }): JSX.Element {
  return (
    <Card className="border-rose-500/40 bg-rose-500/5">
      <CardContent className="py-6">
        <div className="flex items-start gap-3">
          <XCircle className="h-6 w-6 text-rose-400 flex-shrink-0" />
          <div className="space-y-1">
            <p className="text-sm font-semibold text-rose-300">
              Governance Response Invalid
            </p>
            <p className="text-xs text-rose-400/80">{error}</p>
            <p className="text-xs text-slate-500 mt-2">
              Contact system administrator. No actions available.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Main denial panel component.
 * Renders the full denial response with correction plan.
 */
export function DiggiDenialPanel({
  denial,
  onStepSelect,
  className,
}: DiggiDenialPanelProps): JSX.Element {
  // Validate the correction plan
  const validation = validateCorrectionPlan(denial.correction_plan);

  // If invalid, render hard error (fail closed)
  if (!validation.isValid) {
    return (
      <DiggiErrorBoundary fallbackMessage={validation.error}>
        <InvalidPlanError error={validation.error || 'Unknown validation error'} />
      </DiggiErrorBoundary>
    );
  }

  // Extract the inner correction plan (validation ensures it exists)
  const plan = denial.correction_plan!.correction_plan;

  return (
    <DiggiErrorBoundary>
      <Card className={classNames('overflow-hidden', className)}>
        <CardContent className="space-y-6 py-6">
          {/* Section 1: Status Banner */}
          <DenialStatusBanner
            reason={denial.reason}
            reasonDetail={denial.reason_detail}
          />

          {/* Agent & Intent Info */}
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span>
              Agent: <code className="text-slate-400">{denial.agent_gid}</code>
            </span>
            <span>
              Intent:{' '}
              <code className="text-slate-400">
                {denial.intent_verb} → {denial.intent_target}
              </code>
            </span>
            {denial.next_hop && (
              <span>
                Routed to:{' '}
                <code className="text-emerald-400">{denial.next_hop}</code>
              </span>
            )}
          </div>

          {/* Section 2: Constraints */}
          <DiggiConstraintList constraints={plan.constraints} />

          {/* Section 3: Allowed Next Steps */}
          <NextStepsSection
            steps={plan.allowed_next_steps}
            onStepSelect={onStepSelect}
            disabled={false}
          />

          {/* Audit Trail Info */}
          {denial.correlation_id && (
            <div className="pt-4 border-t border-slate-800/50">
              <p className="text-xs text-slate-600">
                Correlation ID:{' '}
                <code className="text-slate-500">{denial.correlation_id}</code>
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </DiggiErrorBoundary>
  );
}
