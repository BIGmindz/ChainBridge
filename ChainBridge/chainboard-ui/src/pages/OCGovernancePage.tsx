/**
 * OC Governance Page — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * Operator Console route for governance ledger visibility.
 * Provides operator-grade access to:
 * - Governance Ledger (append-only audit trail)
 * - PAC Registry with lineage
 * - Correction cycle visualization
 * - Positive closure tracking
 *
 * UX RULES (FAIL-CLOSED):
 * - blocked_means_disabled: BLOCKED PACs are visually distinct
 * - closure_requires_badge: Every closure shows appropriate badge
 * - corrections_must_show_lineage: Correction history is visible
 * - no_green_without_positive_closure: Only POSITIVE_CLOSURE = green
 * - hover_explains_violation_codes: Tooltips explain violations
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import { GovernanceLedgerPanel } from '../components/governance';

export default function OCGovernancePage(): JSX.Element {
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Governance Ledger
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">
              /oc/governance — Operator Console
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200 rounded-full">
              READ-ONLY
            </span>
            <span className="px-3 py-1 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200 rounded-full">
              FAIL-CLOSED
            </span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        <GovernanceLedgerPanel
          pollInterval={30000}
          className="h-full"
        />
      </main>
    </div>
  );
}
