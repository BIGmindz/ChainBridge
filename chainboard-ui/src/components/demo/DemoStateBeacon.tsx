/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Demo State Beacon
 * PAC-BENSON-P35R: Operator + Auditor Demo Experience
 * 
 * Visual state indicator following Law 6 color semantics.
 * Reduces cognitive load by providing clear status at a glance.
 * 
 * DOCTRINE REFERENCES:
 * - Law 6, §6.1: Visual Invariants (GREEN/YELLOW/RED)
 * 
 * Author: SONNY (GID-02) — OCC Demo Flow
 * UX: LIRA (GID-09) — Accessibility & Cognitive Load
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React from 'react';
import type { StateBeacon, BeaconStatus } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS CONFIGURATION (Law 6)
// ═══════════════════════════════════════════════════════════════════════════════

const STATUS_CONFIG: Record<BeaconStatus, {
  bgColor: string;
  ringColor: string;
  textColor: string;
  pulseClass: string;
  ariaLabel: string;
}> = {
  green: {
    bgColor: 'bg-green-500',
    ringColor: 'ring-green-400/50',
    textColor: 'text-green-400',
    pulseClass: '',
    ariaLabel: 'Status: Good',
  },
  yellow: {
    bgColor: 'bg-yellow-500',
    ringColor: 'ring-yellow-400/50',
    textColor: 'text-yellow-400',
    pulseClass: 'animate-pulse',
    ariaLabel: 'Status: Warning - Attention needed',
  },
  red: {
    bgColor: 'bg-red-500',
    ringColor: 'ring-red-400/50',
    textColor: 'text-red-400',
    pulseClass: 'animate-pulse',
    ariaLabel: 'Status: Critical - Action required',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface DemoStateBeaconProps {
  beacon: StateBeacon;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show label */
  showLabel?: boolean;
}

export const DemoStateBeacon: React.FC<DemoStateBeaconProps> = ({
  beacon,
  size = 'md',
  showLabel = true,
}) => {
  const config = STATUS_CONFIG[beacon.status];
  
  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4',
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  return (
    <div 
      className="flex items-center gap-2"
      role="status"
      aria-label={`${beacon.label}: ${config.ariaLabel}`}
      title={beacon.tooltip}
    >
      {/* Beacon Dot */}
      <span
        className={`
          ${sizeClasses[size]} 
          ${config.bgColor} 
          ${config.pulseClass}
          rounded-full 
          ring-2 
          ${config.ringColor}
        `}
        aria-hidden="true"
      />
      
      {/* Label */}
      {showLabel && (
        <span className={`${textSizeClasses[size]} ${config.textColor} font-medium`}>
          {beacon.label}
        </span>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// BEACON GROUP
// ═══════════════════════════════════════════════════════════════════════════════

interface DemoBeaconGroupProps {
  beacons: StateBeacon[];
  /** Layout direction */
  direction?: 'row' | 'column';
}

export const DemoBeaconGroup: React.FC<DemoBeaconGroupProps> = ({
  beacons,
  direction = 'row',
}) => {
  return (
    <div 
      className={`
        flex gap-4
        ${direction === 'column' ? 'flex-col' : 'flex-row flex-wrap'}
      `}
      role="group"
      aria-label="System status indicators"
    >
      {beacons.map((beacon) => (
        <DemoStateBeacon key={beacon.beaconId} beacon={beacon} />
      ))}
    </div>
  );
};

export default DemoStateBeacon;
