/**
 * CorrectionCycleStepper — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * Visual stepper showing correction cycle progression.
 * Displays correction history with violations addressed at each step.
 *
 * UX RULES (FAIL-CLOSED):
 * - corrections_must_show_lineage: Every correction shows what it fixed
 * - hover_explains_violation_codes: Hover reveals violation details
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import React, { useState } from 'react';
import type { CorrectionRecord, ViolationRecord } from '../../types/governanceLedger';

export interface CorrectionCycleStepperProps {
  /** Correction records */
  corrections: CorrectionRecord[];
  /** Currently active violations (not yet resolved) */
  activeViolations?: ViolationRecord[];
  /** Orientation */
  orientation?: 'horizontal' | 'vertical';
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Violation badge with tooltip.
 */
function ViolationBadge({
  violation,
  resolved,
}: {
  violation: ViolationRecord;
  resolved: boolean;
}) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span
        className={`
          inline-flex items-center px-2 py-0.5 text-xs font-mono rounded
          ${resolved
            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200'
            : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200'
          }
        `}
      >
        {violation.violation_id}
      </span>

      {/* Tooltip */}
      {showTooltip && (
        <div
          className="
            absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2
            px-3 py-2 text-xs rounded-lg shadow-lg
            bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900
            whitespace-nowrap
          "
          role="tooltip"
        >
          <div className="font-semibold">{violation.violation_id}</div>
          <div className="text-gray-300 dark:text-gray-600">{violation.description}</div>
          {resolved && violation.resolution && (
            <div className="text-green-400 dark:text-green-600 mt-1">
              ✓ {violation.resolution}
            </div>
          )}
          <div
            className="
              absolute top-full left-1/2 -translate-x-1/2 -mt-1
              border-4 border-transparent border-t-gray-900 dark:border-t-gray-100
            "
          />
        </div>
      )}
    </span>
  );
}

/**
 * Step indicator icon.
 */
function StepIcon({
  status,
  number,
}: {
  status: 'complete' | 'current' | 'pending';
  number: number;
}) {
  if (status === 'complete') {
    return (
      <div className="
        w-8 h-8 rounded-full flex items-center justify-center
        bg-green-600 text-white
      ">
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
          <polyline points="20,6 9,17 4,12" />
        </svg>
      </div>
    );
  }

  if (status === 'current') {
    return (
      <div className="
        w-8 h-8 rounded-full flex items-center justify-center
        bg-amber-500 text-white animate-pulse
      ">
        <span className="text-sm font-bold">{number}</span>
      </div>
    );
  }

  return (
    <div className="
      w-8 h-8 rounded-full flex items-center justify-center
      bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400
    ">
      <span className="text-sm font-bold">{number}</span>
    </div>
  );
}

/**
 * Single correction step.
 */
function CorrectionStep({
  correction,
  stepNumber,
  isLast,
  orientation,
  compact,
}: {
  correction: CorrectionRecord;
  stepNumber: number;
  isLast: boolean;
  orientation: 'horizontal' | 'vertical';
  compact: boolean;
}) {
  const status = correction.status === 'APPLIED' ? 'complete' : 'current';
  const isVertical = orientation === 'vertical';

  return (
    <div className={`flex ${isVertical ? 'flex-row' : 'flex-col items-center'}`}>
      {/* Step indicator */}
      <div className={`flex ${isVertical ? 'flex-col items-center' : 'flex-row items-center'}`}>
        <StepIcon status={status} number={stepNumber} />

        {/* Connector line */}
        {!isLast && (
          <div className={`
            ${isVertical
              ? 'w-0.5 h-8 mx-auto bg-gray-300 dark:bg-gray-600'
              : 'h-0.5 w-8 bg-gray-300 dark:bg-gray-600'
            }
          `} />
        )}
      </div>

      {/* Step content */}
      <div className={`
        ${isVertical ? 'ml-4 pb-6' : 'mt-2 text-center'}
        ${compact ? 'max-w-[120px]' : ''}
      `}>
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
          Correction {correction.correction_version}
        </div>

        {!compact && (
          <>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {formatDate(correction.applied_at)}
            </div>

            {/* Violations */}
            <div className="flex flex-wrap gap-1 mt-2">
              {correction.violations_addressed.map((v) => (
                <ViolationBadge key={v.violation_id} violation={v} resolved={v.resolved} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Active violations step (not yet resolved).
 */
function ActiveViolationsStep({
  violations,
  orientation,
}: {
  violations: ViolationRecord[];
  orientation: 'horizontal' | 'vertical';
}) {
  const isVertical = orientation === 'vertical';

  return (
    <div className={`flex ${isVertical ? 'flex-row' : 'flex-col items-center'}`}>
      <div className={`flex ${isVertical ? 'flex-col items-center' : 'flex-row items-center'}`}>
        <div className="
          w-8 h-8 rounded-full flex items-center justify-center
          bg-red-500 text-white animate-pulse
        ">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
      </div>

      <div className={`${isVertical ? 'ml-4' : 'mt-2 text-center'}`}>
        <div className="text-sm font-medium text-red-600 dark:text-red-400">
          Active Violations
        </div>
        <div className="flex flex-wrap gap-1 mt-2">
          {violations.map((v) => (
            <ViolationBadge key={v.violation_id} violation={v} resolved={false} />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Format date for display.
 */
function formatDate(dateStr?: string): string {
  if (!dateStr) return 'Pending';
  try {
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return dateStr;
  }
}

/**
 * CorrectionCycleStepper component.
 *
 * Displays correction history as a visual stepper.
 * Shows lineage of corrections with violations addressed.
 */
export function CorrectionCycleStepper({
  corrections,
  activeViolations = [],
  orientation = 'vertical',
  compact = false,
  className = '',
}: CorrectionCycleStepperProps) {
  // Sort corrections by version
  const sortedCorrections = [...corrections].sort(
    (a, b) => a.correction_version - b.correction_version
  );

  const hasActiveViolations = activeViolations.length > 0;
  const isVertical = orientation === 'vertical';

  // Empty state
  if (sortedCorrections.length === 0 && !hasActiveViolations) {
    return (
      <div className={`text-sm text-gray-500 dark:text-gray-400 ${className}`}>
        No correction cycles
      </div>
    );
  }

  return (
    <div
      className={`
        ${isVertical ? '' : 'flex items-start gap-4 overflow-x-auto pb-2'}
        ${className}
      `}
      role="list"
      aria-label="Correction cycle history"
    >
      {sortedCorrections.map((correction, index) => (
        <CorrectionStep
          key={correction.correction_pac_id}
          correction={correction}
          stepNumber={index + 1}
          isLast={index === sortedCorrections.length - 1 && !hasActiveViolations}
          orientation={orientation}
          compact={compact}
        />
      ))}

      {hasActiveViolations && (
        <ActiveViolationsStep
          violations={activeViolations}
          orientation={orientation}
        />
      )}
    </div>
  );
}

export default CorrectionCycleStepper;
