/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Kill Switch UI Component — Emergency Execution Halt Control
 * PAC-BENSON-P21-C: OCC Intensive Multi-Agent Execution
 * 
 * Displays kill switch status and controls:
 * - Current state (DISARMED/ARMED/ENGAGED/COOLDOWN)
 * - Authorization level
 * - Engagement details (who, when, why)
 * - Affected PACs
 * 
 * INVARIANTS:
 * - INV-KILL-001: Kill switch is DISABLED unless explicitly authorized
 * - INV-KILL-002: No optimistic state - always reflects backend
 * - INV-KILL-003: All actions require confirmation
 * - INV-SAM-001: No hidden execution paths
 * 
 * Author: SONNY (GID-02) — Frontend
 * Security: SAM (GID-06)
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import type { KillSwitchStatus, KillSwitchState, KillSwitchAuthLevel } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const KILL_SWITCH_STATE_CONFIG: Record<KillSwitchState, {
  color: string;
  bgColor: string;
  borderColor: string;
  label: string;
  icon: string;
  description: string;
}> = {
  DISARMED: {
    color: 'text-green-400',
    bgColor: 'bg-green-900/20',
    borderColor: 'border-green-700',
    label: 'DISARMED',
    icon: '🟢',
    description: 'Normal operation — all systems active',
  },
  ARMED: {
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/20',
    borderColor: 'border-yellow-700',
    label: 'ARMED',
    icon: '🟡',
    description: 'Ready to engage — awaiting confirmation',
  },
  ENGAGED: {
    color: 'text-red-400',
    bgColor: 'bg-red-900/20',
    borderColor: 'border-red-700',
    label: 'ENGAGED',
    icon: '🔴',
    description: 'ALL EXECUTION HALTED',
  },
  COOLDOWN: {
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/20',
    borderColor: 'border-blue-700',
    label: 'COOLDOWN',
    icon: '🔵',
    description: 'Recently disengaged — cooldown period active',
  },
};

const AUTH_LEVEL_CONFIG: Record<KillSwitchAuthLevel, {
  color: string;
  label: string;
  canArm: boolean;
  canEngage: boolean;
}> = {
  UNAUTHORIZED: {
    color: 'text-gray-500',
    label: 'Unauthorized',
    canArm: false,
    canEngage: false,
  },
  ARM_ONLY: {
    color: 'text-yellow-400',
    label: 'Arm Only',
    canArm: true,
    canEngage: false,
  },
  FULL_ACCESS: {
    color: 'text-green-400',
    label: 'Full Access',
    canArm: true,
    canEngage: true,
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIRMATION DIALOG
// ═══════════════════════════════════════════════════════════════════════════════

interface ConfirmationDialogProps {
  isOpen: boolean;
  action: 'ARM' | 'ENGAGE' | 'DISARM';
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({
  isOpen,
  action,
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState('');

  if (!isOpen) return null;

  const actionConfig = {
    ARM: {
      title: 'Arm Kill Switch',
      message: 'This will prepare the kill switch for engagement. Are you sure?',
      confirmLabel: 'Arm',
      confirmColor: 'bg-yellow-600 hover:bg-yellow-700',
    },
    ENGAGE: {
      title: '⚠️ ENGAGE KILL SWITCH',
      message: 'THIS WILL HALT ALL AGENT EXECUTION IMMEDIATELY. This action is logged and audited.',
      confirmLabel: 'ENGAGE',
      confirmColor: 'bg-red-600 hover:bg-red-700',
    },
    DISARM: {
      title: 'Disarm Kill Switch',
      message: 'This will return the system to normal operation. Are you sure?',
      confirmLabel: 'Disarm',
      confirmColor: 'bg-green-600 hover:bg-green-700',
    },
  };

  const config = actionConfig[action];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-md w-full mx-4">
        <h3
          id="confirm-dialog-title"
          className={`text-lg font-bold mb-4 ${action === 'ENGAGE' ? 'text-red-400' : 'text-gray-100'}`}
        >
          {config.title}
        </h3>

        <p className="text-sm text-gray-300 mb-4">{config.message}</p>

        {action === 'ENGAGE' && (
          <div className="mb-4">
            <label htmlFor="engage-reason" className="block text-sm text-gray-400 mb-2">
              Reason (required):
            </label>
            <textarea
              id="engage-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
              rows={3}
              placeholder="Enter reason for engagement..."
              required
            />
          </div>
        )}

        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 rounded hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={action === 'ENGAGE' && !reason.trim()}
            className={`px-4 py-2 text-sm font-medium text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 ${config.confirmColor} ${
              action === 'ENGAGE' && !reason.trim() ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {config.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// KILL SWITCH UI COMPONENT (MAIN EXPORT)
// ═══════════════════════════════════════════════════════════════════════════════

interface KillSwitchUIProps {
  /** Kill switch status from backend */
  status: KillSwitchStatus | null;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
  /** Callback to arm the kill switch */
  onArm?: () => Promise<void>;
  /** Callback to engage the kill switch */
  onEngage?: (reason: string) => Promise<void>;
  /** Callback to disarm the kill switch */
  onDisarm?: () => Promise<void>;
}

export const KillSwitchUI: React.FC<KillSwitchUIProps> = ({
  status,
  loading = false,
  error = null,
  onArm,
  onEngage,
  onDisarm,
}) => {
  const [confirmAction, setConfirmAction] = useState<'ARM' | 'ENGAGE' | 'DISARM' | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const handleConfirm = useCallback(async () => {
    if (!confirmAction) return;

    setActionLoading(true);
    try {
      switch (confirmAction) {
        case 'ARM':
          await onArm?.();
          break;
        case 'ENGAGE':
          await onEngage?.('Manual engagement via OCC');
          break;
        case 'DISARM':
          await onDisarm?.();
          break;
      }
    } finally {
      setActionLoading(false);
      setConfirmAction(null);
    }
  }, [confirmAction, onArm, onEngage, onDisarm]);

  if (error) {
    return (
      <div
        className="bg-gray-800 border border-red-700 rounded-lg p-4"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <span aria-hidden="true">🛑</span>
          <span className="font-medium">Kill Switch Error</span>
        </div>
        <p className="text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-center py-4 text-gray-500">
          <span>Kill switch status unavailable</span>
        </div>
      </div>
    );
  }

  const stateConfig = KILL_SWITCH_STATE_CONFIG[status.state];
  const authConfig = AUTH_LEVEL_CONFIG[status.authLevel];

  return (
    <section
      className={`bg-gray-900 border rounded-lg ${stateConfig.borderColor}`}
      aria-label="Kill Switch Control"
    >
      {/* Header */}
      <div className={`border-b ${stateConfig.borderColor} p-4 ${stateConfig.bgColor}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl" aria-hidden="true">{stateConfig.icon}</span>
            <div>
              <h2 className={`text-lg font-bold ${stateConfig.color}`}>
                Kill Switch: {stateConfig.label}
              </h2>
              <p className="text-xs text-gray-400">{stateConfig.description}</p>
            </div>
          </div>

          {/* Auth Level Badge */}
          <div className="text-right">
            <span className="text-xs text-gray-500">Auth Level:</span>
            <div className={`text-sm font-medium ${authConfig.color}`}>
              {authConfig.label}
            </div>
          </div>
        </div>
      </div>

      {/* Status Details */}
      <div className="p-4">
        {/* Engaged Details */}
        {status.state === 'ENGAGED' && (
          <div
            className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg"
            role="alert"
            aria-live="assertive"
          >
            <div className="text-red-400 font-medium mb-2">
              ⚠️ EXECUTION HALTED
            </div>
            {status.engagedBy && (
              <div className="text-sm text-gray-300">
                <span className="text-gray-500">Engaged by: </span>
                {status.engagedBy}
              </div>
            )}
            {status.engagedAt && (
              <div className="text-sm text-gray-300">
                <span className="text-gray-500">Engaged at: </span>
                {new Date(status.engagedAt).toLocaleString()}
              </div>
            )}
            {status.engagementReason && (
              <div className="text-sm text-gray-300 mt-2">
                <span className="text-gray-500">Reason: </span>
                {status.engagementReason}
              </div>
            )}
          </div>
        )}

        {/* Cooldown Progress */}
        {status.state === 'COOLDOWN' && status.cooldownRemaining !== null && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-500">Cooldown remaining</span>
              <span className="text-blue-400">
                {Math.ceil(status.cooldownRemaining / 1000)}s
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-1000"
                style={{ width: `${Math.min(100, (status.cooldownRemaining / 30000) * 100)}%` }}
                role="progressbar"
                aria-valuenow={status.cooldownRemaining}
                aria-valuemin={0}
                aria-valuemax={30000}
              />
            </div>
          </div>
        )}

        {/* Affected PACs */}
        {status.affectedPacs.length > 0 && (
          <div className="mb-4">
            <span className="text-xs text-gray-500 block mb-2">Affected PACs:</span>
            <div className="flex flex-wrap gap-1">
              {status.affectedPacs.map((pacId) => (
                <span
                  key={pacId}
                  className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded font-mono"
                >
                  {pacId}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Control Buttons */}
        <div className="flex items-center gap-3 pt-4 border-t border-gray-700">
          {/* Arm Button */}
          {status.state === 'DISARMED' && (
            <button
              onClick={() => setConfirmAction('ARM')}
              disabled={!authConfig.canArm || loading || actionLoading}
              className={`
                flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors
                focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 focus:ring-offset-gray-900
                ${authConfig.canArm
                  ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                }
              `}
              aria-disabled={!authConfig.canArm}
            >
              {actionLoading ? 'Processing...' : '🟡 Arm'}
            </button>
          )}

          {/* Engage Button */}
          {status.state === 'ARMED' && (
            <>
              <button
                onClick={() => setConfirmAction('DISARM')}
                disabled={!authConfig.canArm || loading || actionLoading}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Disarm
              </button>
              <button
                onClick={() => setConfirmAction('ENGAGE')}
                disabled={!authConfig.canEngage || loading || actionLoading}
                className={`
                  flex-1 px-4 py-2 rounded-lg text-sm font-bold transition-colors
                  focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-gray-900
                  ${authConfig.canEngage
                    ? 'bg-red-600 hover:bg-red-700 text-white animate-pulse'
                    : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  }
                `}
                aria-disabled={!authConfig.canEngage}
              >
                {actionLoading ? 'Processing...' : '🔴 ENGAGE'}
              </button>
            </>
          )}

          {/* Disarm Button (when engaged) */}
          {status.state === 'ENGAGED' && (
            <button
              onClick={() => setConfirmAction('DISARM')}
              disabled={!authConfig.canEngage || loading || actionLoading}
              className={`
                flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors
                focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-gray-900
                ${authConfig.canEngage
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                }
              `}
            >
              {actionLoading ? 'Processing...' : '🟢 Disarm'}
            </button>
          )}

          {/* Cooldown state - no buttons */}
          {status.state === 'COOLDOWN' && (
            <div className="flex-1 text-center text-sm text-gray-500">
              System in cooldown — please wait
            </div>
          )}
        </div>

        {/* Authorization Notice */}
        {status.authLevel === 'UNAUTHORIZED' && (
          <div className="mt-4 p-3 bg-gray-800 rounded text-xs text-gray-500">
            <span className="text-yellow-500">⚠️</span> You do not have authorization to control the kill switch.
            Contact a system administrator for access.
          </div>
        )}
      </div>

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={confirmAction !== null}
        action={confirmAction || 'ARM'}
        onConfirm={handleConfirm}
        onCancel={() => setConfirmAction(null)}
      />
    </section>
  );
};

export default KillSwitchUI;
