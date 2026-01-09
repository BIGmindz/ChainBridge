/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Verification Status Badge
 * PAC-BENSON-P34: Trust Center (Public Audit Interface)
 * 
 * Displays verification status with appropriate visual indicators.
 * 
 * DOCTRINE LAW 6 — Visual Invariants:
 * - §6.1: GREEN = Verified/Valid
 * - §6.1: YELLOW = Pending/In Progress
 * - §6.1: RED = Failed/Invalid
 * - §6.2: PULSING = Active verification
 * - §6.2: STATIC = Completed verification
 * 
 * ACCESSIBILITY (LIRA GID-09):
 * - Color is not sole indicator
 * - ARIA labels for screen readers
 * - High contrast support
 * 
 * Author: SONNY (GID-02) — Trust Center UI
 * UX: LIRA (GID-09) — Public UX & Accessibility
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React from 'react';
import type { VerificationStatus } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS CONFIGURATION (Law 6, §6.1)
// ═══════════════════════════════════════════════════════════════════════════════

const STATUS_CONFIG: Record<VerificationStatus, {
  icon: string;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  animate: boolean;
}> = {
  VERIFIED: {
    icon: '✓',
    label: 'Verified',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500',
    animate: false,
  },
  PENDING: {
    icon: '◐',
    label: 'Pending',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500',
    animate: true,
  },
  FAILED: {
    icon: '✗',
    label: 'Failed',
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500',
    animate: false,
  },
  EXPIRED: {
    icon: '⏱',
    label: 'Expired',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
    borderColor: 'border-orange-500',
    animate: false,
  },
  UNKNOWN: {
    icon: '?',
    label: 'Unknown',
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/20',
    borderColor: 'border-gray-500',
    animate: false,
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface VerificationStatusBadgeProps {
  /** Verification status */
  status: VerificationStatus;
  /** Optional size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show label text */
  showLabel?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export const VerificationStatusBadge: React.FC<VerificationStatusBadgeProps> = ({
  status,
  size = 'md',
  showLabel = true,
  className = '',
}) => {
  const config = STATUS_CONFIG[status];

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-3 py-1',
    lg: 'text-base px-4 py-1.5',
  };

  const iconSizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded-full border
        ${config.bgColor} ${config.borderColor} ${config.color}
        ${sizeClasses[size]}
        ${className}
      `}
      role="status"
      aria-label={`Verification status: ${config.label}`}
    >
      {/* Status Icon */}
      <span
        className={`
          ${iconSizes[size]}
          ${config.animate ? 'animate-pulse' : ''}
        `}
        aria-hidden="true"
      >
        {config.icon}
      </span>

      {/* Label Text */}
      {showLabel && (
        <span className="font-medium">{config.label}</span>
      )}
    </span>
  );
};

export default VerificationStatusBadge;
