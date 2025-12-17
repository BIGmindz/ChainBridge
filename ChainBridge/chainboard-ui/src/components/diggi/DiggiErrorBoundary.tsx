/**
 * Diggi Error Boundary — CRC v1
 *
 * Error boundary component for Diggi correction UI.
 * Catches rendering errors and displays a fail-closed message.
 *
 * CONSTRAINTS:
 * - Must fail closed — no partial renders
 * - Must display hard error message
 * - Must not attempt recovery or retry
 *
 * @see PAC-DIGGI-03 — Correction Rendering Contract
 */

import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

import { Card, CardContent } from '../ui/Card';

interface DiggiErrorBoundaryProps {
  children: ReactNode;
  /** Optional fallback message */
  fallbackMessage?: string;
}

interface DiggiErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary for Diggi correction components.
 * Displays a hard error message when rendering fails.
 */
export class DiggiErrorBoundary extends Component<
  DiggiErrorBoundaryProps,
  DiggiErrorBoundaryState
> {
  constructor(props: DiggiErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): DiggiErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log to console for debugging — production would log to monitoring
    console.error('[Diggi] Correction rendering failed:', error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      const message =
        this.props.fallbackMessage || 'Governance response invalid';

      return (
        <Card className="border-rose-500/40 bg-rose-500/5">
          <CardContent className="flex items-center gap-3 py-6">
            <AlertTriangle className="h-6 w-6 text-rose-400 flex-shrink-0" />
            <div className="space-y-1">
              <p className="text-sm font-semibold text-rose-300">
                Correction Rendering Failed
              </p>
              <p className="text-xs text-rose-400/80">{message}</p>
              {this.state.error && (
                <p className="text-xs font-mono text-rose-500/60 mt-2">
                  {this.state.error.message}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
