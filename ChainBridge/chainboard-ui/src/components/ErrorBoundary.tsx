/**
 * Global Error Boundary
 *
 * Catches React errors and prevents entire app crashes.
 * Provides user-friendly recovery UI with retry functionality.
 */

import React, { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: (error: Error, retry: () => void) => ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

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
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error details for debugging
    console.error("[ErrorBoundary] Caught error:", error);
    console.error("[ErrorBoundary] Error info:", errorInfo);

    this.setState({
      errorInfo,
    });

    // In production, you would send this to an error tracking service
    // Example: Sentry, LogRocket, etc.
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    const { hasError, error } = this.state;
    const { children, fallback } = this.props;

    if (hasError && error) {
      if (fallback) {
        return fallback(error, this.handleReset);
      }

      return <DefaultErrorFallback error={error} onReset={this.handleReset} />;
    }

    return children;
  }
}

/**
 * Default error fallback UI
 */
interface FallbackProps {
  error: Error;
  onReset: () => void;
}

function DefaultErrorFallback({ error, onReset }: FallbackProps): JSX.Element {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
      <div className="w-full max-w-2xl space-y-6 rounded-2xl border border-danger-500/40 bg-danger-500/10 p-8">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-500/20">
              <svg
                className="h-6 w-6 text-danger-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-danger-200">
                Control Tower Error
              </h1>
              <p className="text-sm text-danger-300">
                Something went wrong in the ChainBoard UI
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Error Details
          </p>
          <p className="font-mono text-sm text-danger-200">{error.message}</p>
        </div>

        {import.meta.env.DEV && error.stack && (
          <details className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
            <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-slate-500">
              Stack Trace (Dev Only)
            </summary>
            <pre className="mt-3 overflow-x-auto text-xs text-slate-400">
              {error.stack}
            </pre>
          </details>
        )}

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onReset}
            className="flex-1 rounded-xl bg-danger-500 px-6 py-3 font-semibold text-white transition hover:bg-danger-600 focus:outline-none focus:ring-2 focus:ring-danger-400 focus:ring-offset-2 focus:ring-offset-slate-950"
          >
            Try Again
          </button>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-6 py-3 font-semibold text-slate-200 transition hover:border-slate-600 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 focus:ring-offset-slate-950"
          >
            Reload Page
          </button>
        </div>

        <div className="border-t border-slate-800 pt-4">
          <p className="text-center text-xs text-slate-500">
            If this error persists, contact your ChainBridge administrator
          </p>
        </div>
      </div>
    </div>
  );
}
