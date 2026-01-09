// ═══════════════════════════════════════════════════════════════════════════════
// ChainBoard Error Boundary
// PAC-BENSON-P20-B: Frontend Hardening (SONNY GID-02 / LIRA GID-09)
//
// Global error boundary for graceful failure handling.
// Prevents full application crash on component errors.
// ═══════════════════════════════════════════════════════════════════════════════

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Global ErrorBoundary for ChainBoard application.
 * 
 * INVARIANT: UI must not crash silently — display clear error state.
 * GOVERNANCE: INV-UI-001 — Graceful degradation required.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] Caught error:', error);
    console.error('[ErrorBoundary] Component stack:', errorInfo.componentStack);
    this.setState({ errorInfo });
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div
          className="min-h-screen bg-gray-950 flex items-center justify-center p-6"
          role="alert"
          aria-live="assertive"
        >
          <div className="max-w-lg w-full bg-gray-900 border border-red-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-900/50 rounded-full flex items-center justify-center">
                <span className="text-red-400 text-xl" aria-hidden="true">⚠</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-red-100">
                  Application Error
                </h1>
                <p className="text-xs text-red-400">
                  ChainBoard encountered an unexpected error
                </p>
              </div>
            </div>

            <div className="bg-gray-950 rounded-lg p-4 mb-4">
              <p className="text-sm text-gray-300 font-mono break-all">
                {this.state.error?.message || 'Unknown error'}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900"
                aria-label="Try again"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="flex-1 bg-red-800 hover:bg-red-700 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-gray-900"
                aria-label="Reload application"
              >
                Reload App
              </button>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-800">
              <p className="text-xs text-gray-500">
                If this error persists, contact your system administrator.
                Error details have been logged to the console.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
