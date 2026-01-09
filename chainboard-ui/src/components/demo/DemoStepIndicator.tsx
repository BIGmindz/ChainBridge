/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Demo Step Indicator
 * PAC-BENSON-P35R: Operator + Auditor Demo Experience
 * 
 * Shows progress through demo flow steps.
 * 
 * DOCTRINE REFERENCES:
 * - Law 4: PDO Lifecycle (Proof → Decision → Outcome)
 * - Law 6: Visual Invariants
 * 
 * Author: SONNY (GID-02) — OCC Demo Flow
 * UX: LIRA (GID-09) — Accessibility & Cognitive Load
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React from 'react';
import type { DemoStep, DemoStepStatus } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS ICONS
// ═══════════════════════════════════════════════════════════════════════════════

const STEP_STATUS_CONFIG: Record<DemoStepStatus, {
  icon: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
}> = {
  pending: {
    icon: '○',
    bgColor: 'bg-gray-700',
    textColor: 'text-gray-400',
    borderColor: 'border-gray-600',
  },
  active: {
    icon: '◉',
    bgColor: 'bg-blue-600',
    textColor: 'text-blue-300',
    borderColor: 'border-blue-500',
  },
  completed: {
    icon: '✓',
    bgColor: 'bg-green-600',
    textColor: 'text-green-300',
    borderColor: 'border-green-500',
  },
  failed: {
    icon: '✗',
    bgColor: 'bg-red-600',
    textColor: 'text-red-300',
    borderColor: 'border-red-500',
  },
  skipped: {
    icon: '—',
    bgColor: 'bg-gray-600',
    textColor: 'text-gray-500',
    borderColor: 'border-gray-500',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// SINGLE STEP INDICATOR
// ═══════════════════════════════════════════════════════════════════════════════

interface StepIndicatorProps {
  step: DemoStep;
  stepNumber: number;
  isLast: boolean;
  onClick?: () => void;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({
  step,
  stepNumber,
  isLast,
  onClick,
}) => {
  const config = STEP_STATUS_CONFIG[step.status];

  return (
    <div className="flex items-start">
      {/* Step Circle & Line */}
      <div className="flex flex-col items-center">
        <button
          onClick={onClick}
          disabled={step.status === 'pending'}
          className={`
            w-8 h-8 rounded-full flex items-center justify-center
            ${config.bgColor} ${config.textColor}
            border-2 ${config.borderColor}
            transition-all duration-200
            ${onClick && step.status !== 'pending' ? 'cursor-pointer hover:ring-2 hover:ring-offset-2 hover:ring-offset-gray-900' : ''}
          `}
          aria-label={`Step ${stepNumber}: ${step.label} - ${step.status}`}
        >
          <span className="text-sm font-bold">{config.icon}</span>
        </button>
        
        {/* Connecting Line */}
        {!isLast && (
          <div 
            className={`w-0.5 h-8 ${step.status === 'completed' ? 'bg-green-500' : 'bg-gray-600'}`}
            aria-hidden="true"
          />
        )}
      </div>

      {/* Step Content */}
      <div className="ml-3 pb-8">
        <h4 className={`text-sm font-medium ${config.textColor}`}>
          {step.label}
        </h4>
        <p className="text-xs text-gray-500 mt-0.5">
          {step.description}
        </p>
        {step.doctrineRef && (
          <span className="text-xs text-purple-400 mt-1 inline-block">
            📜 {step.doctrineRef}
          </span>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// STEP PROGRESS BAR (Horizontal)
// ═══════════════════════════════════════════════════════════════════════════════

interface DemoStepProgressProps {
  steps: DemoStep[];
  currentIndex: number;
  onStepClick?: (index: number) => void;
}

export const DemoStepProgress: React.FC<DemoStepProgressProps> = ({
  steps,
  currentIndex,
  onStepClick,
}) => {
  return (
    <nav aria-label="Demo progress">
      <ol className="flex items-center w-full">
        {steps.map((step, index) => {
          const config = STEP_STATUS_CONFIG[step.status];
          const isLast = index === steps.length - 1;

          return (
            <li 
              key={step.stepId} 
              className={`flex items-center ${isLast ? '' : 'flex-1'}`}
            >
              {/* Step Circle */}
              <button
                onClick={() => onStepClick?.(index)}
                disabled={step.status === 'pending'}
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center
                  ${config.bgColor} ${config.textColor}
                  text-sm font-bold
                  ${step.status !== 'pending' ? 'cursor-pointer' : 'cursor-default'}
                `}
                aria-label={`${step.label}: ${step.status}`}
                aria-current={index === currentIndex ? 'step' : undefined}
              >
                {step.status === 'completed' ? '✓' : index + 1}
              </button>

              {/* Connector Line */}
              {!isLast && (
                <div 
                  className={`
                    flex-1 h-0.5 mx-2
                    ${index < currentIndex ? 'bg-green-500' : 'bg-gray-600'}
                  `}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>

      {/* Current Step Label */}
      <div className="mt-2 text-center">
        <span className="text-sm text-gray-300">
          {steps[currentIndex]?.label}
        </span>
      </div>
    </nav>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// VERTICAL STEP LIST
// ═══════════════════════════════════════════════════════════════════════════════

interface DemoStepListProps {
  steps: DemoStep[];
  onStepClick?: (index: number) => void;
}

export const DemoStepList: React.FC<DemoStepListProps> = ({
  steps,
  onStepClick,
}) => {
  return (
    <nav aria-label="Demo steps" className="p-4">
      {steps.map((step, index) => (
        <StepIndicator
          key={step.stepId}
          step={step}
          stepNumber={index + 1}
          isLast={index === steps.length - 1}
          onClick={onStepClick ? () => onStepClick(index) : undefined}
        />
      ))}
    </nav>
  );
};

export default DemoStepProgress;
