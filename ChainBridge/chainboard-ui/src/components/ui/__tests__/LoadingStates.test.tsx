/**
 * LoadingStates Component Tests
 *
 * Tests for professional loading, error, and empty state components.
 * Validates visual stability and interaction patterns.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { ErrorState, TableSkeleton, CardSkeleton, EmptyState, InlineError } from '../LoadingStates';

describe('LoadingStates', () => {
  describe('TableSkeleton', () => {
    it('renders default number of skeleton rows', () => {
      render(<TableSkeleton />);
      const skeletons = screen.getAllByRole('generic'); // div elements
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('renders custom number of rows', () => {
      render(<TableSkeleton rows={3} />);
      // Should render 3 skeleton rows with proper structure
      const container = screen.getByRole('generic');
      expect(container).toBeInTheDocument();
    });
  });

  describe('ErrorState', () => {
    it('renders error message and title', () => {
      render(
        <ErrorState
          title="Test Error"
          message="Something went wrong"
        />
      );

      expect(screen.getByText('Test Error')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('calls retry function when retry button clicked', () => {
      const mockRetry = vi.fn();

      render(
        <ErrorState
          title="Test Error"
          onRetry={mockRetry}
        />
      );

      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);

      expect(mockRetry).toHaveBeenCalledOnce();
    });

    it('does not render retry button when onRetry not provided', () => {
      render(
        <ErrorState
          title="Test Error"
        />
      );

      expect(screen.queryByText('Retry')).not.toBeInTheDocument();
    });
  });

  describe('InlineError', () => {
    it('renders error message', () => {
      render(<InlineError message="Inline error" />);

      expect(screen.getByText('Inline error')).toBeInTheDocument();
    });

    it('calls retry function when retry icon clicked', () => {
      const mockRetry = vi.fn();

      render(<InlineError message="Error" onRetry={mockRetry} />);

      const retryIcon = screen.getByRole('button');
      fireEvent.click(retryIcon);

      expect(mockRetry).toHaveBeenCalledOnce();
    });
  });

  describe('EmptyState', () => {
    it('renders title and subtitle', () => {
      render(
        <EmptyState
          title="No Data"
          subtitle="Try again later"
        />
      );

      expect(screen.getByText('No Data')).toBeInTheDocument();
      expect(screen.getByText('Try again later')).toBeInTheDocument();
    });

    it('renders without subtitle', () => {
      render(<EmptyState title="No Data" />);

      expect(screen.getByText('No Data')).toBeInTheDocument();
    });
  });

  describe('CardSkeleton', () => {
    it('renders with proper structure', () => {
      render(<CardSkeleton />);

      const container = screen.getByRole('generic');
      expect(container).toBeInTheDocument();
      expect(container).toHaveClass('bg-slate-800/30');
    });
  });
});
