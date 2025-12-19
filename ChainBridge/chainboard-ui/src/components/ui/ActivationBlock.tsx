/**
 * ActivationBlock — PAC-BENSON-SONNY-ACTIVATION-BLOCK-UI-ENFORCEMENT-02
 *
 * Standard UI component for surfacing agent identity and execution context.
 * Text-only. Monospace. No icons. No colors. No semantic signals.
 *
 * CONSTRAINTS:
 * - Agent name, GID, role displayed neutrally
 * - Execution context (live vs demo) displayed explicitly
 * - No colors, icons, or animations
 * - Monospace font throughout
 * - No validation, completion, or enforcement language
 *
 * @see PAC-BENSON-SONNY-ACTIVATION-BLOCK-UI-ENFORCEMENT-02
 */

import { classNames } from '../../utils/classNames';

export interface ActivationBlockProps {
  /** Agent name (e.g., "SONNY", "BENSON") */
  agentName: string;
  /** Agent GID (e.g., "GID-02") */
  gid: string;
  /** Agent role (e.g., "Senior Frontend Engineer") */
  role?: string;
  /** Execution context: true = live backend, false = demo/unlinked */
  isLive?: boolean;
  /** Optional className */
  className?: string;
}

/**
 * ActivationBlock component.
 * Neutral identity/context disclosure. No semantic signals.
 */
export function ActivationBlock({
  agentName,
  gid,
  role,
  isLive = false,
  className,
}: ActivationBlockProps): JSX.Element {
  return (
    <div
      className={classNames(
        'border border-slate-700/50 bg-slate-900/50 px-4 py-3 font-mono text-xs',
        className
      )}
      data-testid="activation-block"
    >
      {/* Execution context disclosure */}
      <div className="border-b border-slate-800/50 pb-2 mb-2">
        <span className="text-slate-600 uppercase tracking-wider">
          execution_context:
        </span>
        <span className="text-slate-400 ml-2">
          {isLive ? 'live' : 'demo / unlinked'}
        </span>
      </div>

      {/* Agent identity fields */}
      <div className="space-y-1">
        <div className="flex">
          <span className="text-slate-600 w-24">agent:</span>
          <span className="text-slate-400">{agentName}</span>
        </div>
        <div className="flex">
          <span className="text-slate-600 w-24">gid:</span>
          <span className="text-slate-400">{gid}</span>
        </div>
        {role && (
          <div className="flex">
            <span className="text-slate-600 w-24">role:</span>
            <span className="text-slate-400">{role}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default ActivationBlock;
