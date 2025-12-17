/**
 * ApprovalErrorBoundary — HAM v1
 *
 * Fail-closed error boundary for the Human Approval Modal.
 * Any rendering error blocks approval and displays hard error.
 *
 * @see PAC-DIGGI-04 — Human Approval Modal
 */

import { Component, type ReactNode } from 'react';
import { AlertTriangle, ShieldX } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary that fails closed — blocks all approval actions on error.
 * This prevents any approval from proceeding if the UI is in an invalid state.
 */
export class ApprovalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log to audit trail — approval rendering failed
    console.error('[HAM] Approval rendering failed:', error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      const { fallbackMessage = 'Approval interface unavailable. Contact system administrator.' } =
        this.props;

      return (
        <div className="rounded-lg border-2 border-red-500 bg-red-950/80 p-6">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <ShieldX className="h-8 w-8 text-red-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-300">
                Approval Blocked
              </h3>
              <p className="mt-1 text-sm text-red-200">
                {fallbackMessage}
              </p>
              <div className="mt-4 rounded-md bg-red-900/50 p-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                  <span className="text-xs font-medium text-red-300">
                    No actions available
                  </span>
                </div>
                <p className="mt-2 text-xs text-red-400">
                  The approval interface encountered an error and cannot proceed.
                  All approval actions have been disabled for safety.
                </p>
                {this.state.error && (
                  <p className="mt-2 font-mono text-xs text-red-500">
                    Error: {this.state.error.message}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
