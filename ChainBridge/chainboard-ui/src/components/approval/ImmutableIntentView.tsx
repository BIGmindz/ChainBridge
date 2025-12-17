/**
 * ImmutableIntentView — HAM v1
 *
 * Read-only, monospaced display of the canonical intent.
 * No truncation, no editing, scrollable only.
 *
 * @see PAC-DIGGI-04 — Human Approval Modal
 */

import { Lock } from 'lucide-react';
import type { CanonicalIntent } from '../../types/approval';

interface Props {
  /** The canonical intent to display — immutable */
  intent: CanonicalIntent;
}

/**
 * Displays the canonical intent as read-only JSON.
 * This view is IMMUTABLE — no user can edit the intent being approved.
 */
export function ImmutableIntentView({ intent }: Props): JSX.Element {
  // Create display object with explicit field ordering for clarity
  const displayIntent: Record<string, unknown> = {
    verb: intent.verb,
    target: intent.target,
  };

  // Add optional fields in consistent order
  if (intent.amount !== undefined) {
    displayIntent.amount = intent.amount;
  }
  if (intent.environment !== undefined) {
    displayIntent.environment = intent.environment;
  }
  displayIntent.requested_by = intent.requested_by;
  displayIntent.correlation_id = intent.correlation_id;

  // Add metadata if present
  if (intent.metadata && Object.keys(intent.metadata).length > 0) {
    displayIntent.metadata = intent.metadata;
  }

  const jsonString = JSON.stringify(displayIntent, null, 2);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-700 px-4 py-2">
        <div className="flex items-center gap-2">
          <Lock className="h-4 w-4 text-slate-500" />
          <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Intent Details
          </span>
        </div>
        <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-500">
          READ-ONLY
        </span>
      </div>

      {/* JSON Content — scrollable, no truncation */}
      <div className="max-h-64 overflow-auto p-4">
        <pre
          className="font-mono text-sm leading-relaxed text-slate-300"
          style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
        >
          {jsonString}
        </pre>
      </div>

      {/* Footer — immutability notice */}
      <div className="border-t border-slate-700 bg-slate-900/50 px-4 py-2">
        <p className="text-xs text-slate-500">
          This intent cannot be modified. Review carefully before authorizing.
        </p>
      </div>
    </div>
  );
}
