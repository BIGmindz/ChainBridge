// ═══════════════════════════════════════════════════════════════════════════════
// ChainBoard Loading Spinner
// PAC-BENSON-P20-B: Frontend Hardening (SONNY GID-02 / LIRA GID-09)
//
// Consistent loading indicator with accessibility support.
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';

interface LoadingSpinnerProps {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Loading message for screen readers */
  label?: string;
  /** Additional class names */
  className?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-3',
};

/**
 * Accessible loading spinner component.
 * 
 * Usage:
 * <LoadingSpinner size="md" label="Loading data..." />
 */
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  label = 'Loading...',
  className = '',
}) => {
  return (
    <div
      className={`flex items-center justify-center ${className}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div
        className={`animate-spin rounded-full border-blue-500 border-t-transparent ${sizeClasses[size]}`}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </div>
  );
};

interface LoadingOverlayProps {
  /** Whether the overlay is visible */
  visible: boolean;
  /** Loading message */
  message?: string;
  /** Children to overlay */
  children: React.ReactNode;
}

/**
 * Loading overlay that covers content while loading.
 */
export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  visible,
  message = 'Loading...',
  children,
}) => {
  return (
    <div className="relative">
      {children}
      {visible && (
        <div
          className="absolute inset-0 bg-gray-950/80 flex flex-col items-center justify-center rounded-lg"
          role="status"
          aria-live="polite"
        >
          <LoadingSpinner size="lg" label={message} />
          <p className="mt-3 text-sm text-gray-400">{message}</p>
        </div>
      )}
    </div>
  );
};

interface SkeletonProps {
  /** Width class */
  width?: string;
  /** Height class */
  height?: string;
  /** Additional class names */
  className?: string;
}

/**
 * Skeleton placeholder for loading states.
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  width = 'w-full',
  height = 'h-4',
  className = '',
}) => {
  return (
    <div
      className={`${width} ${height} bg-gray-800 rounded animate-pulse ${className}`}
      aria-hidden="true"
    />
  );
};

/**
 * Panel skeleton for loading card-like content.
 */
export const PanelSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-900/80 p-4 ${className}`}
      role="status"
      aria-label="Loading content"
    >
      <Skeleton width="w-1/3" height="h-5" className="mb-3" />
      <Skeleton width="w-2/3" height="h-3" className="mb-2" />
      <Skeleton width="w-full" height="h-20" className="mb-2" />
      <Skeleton width="w-1/2" height="h-3" />
      <span className="sr-only">Loading panel content...</span>
    </div>
  );
};

export default LoadingSpinner;
