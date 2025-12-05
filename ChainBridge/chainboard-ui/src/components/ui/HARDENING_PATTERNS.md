# ChainBoard UI Hardening Patterns

**Last Updated**: 2025-11-26
**Owner**: Sonny (GID-02)
**Status**: ✅ Implemented

## Overview

This document defines the professional UI hardening patterns for ChainBridge Operator Console components. All components must implement these patterns for enterprise-grade reliability and trust.

## Core Principles

1. **Layout Stability**: Skeletons preserve content shape to prevent jarring shifts
2. **Localized Errors**: Failures don't crash entire views, only affected components
3. **Professional Messaging**: Error text is operator-facing, not developer-facing
4. **Retry Capability**: Users can recover from transient failures
5. **Performance**: 60 FPS maintained, no unnecessary re-renders

## Component Patterns

### Loading States

```tsx
// ✅ CORRECT: Content-shaped skeleton
if (isLoading) {
  return <TableSkeleton rows={expectedRows} />;
}

// ❌ WRONG: Generic spinner
if (isLoading) {
  return <div>Loading...</div>;
}
```

### Error States

```tsx
// ✅ CORRECT: Localized error with retry
if (error) {
  return (
    <ErrorState
      title="Intel data temporarily unavailable"
      message="Network issue detected. Retry to refresh."
      onRetry={() => refetch()}
    />
  );
}

// ❌ WRONG: Raw error exposure
if (error) {
  return <div>Error: {error.message}</div>;
}
```

### Empty States

```tsx
// ✅ CORRECT: Contextual empty state
if (data.length === 0) {
  return (
    <EmptyState
      title="No at-risk shipments"
      subtitle="All systems nominal — queue is clear"
      icon={<CheckCircle className="h-12 w-12 text-emerald-500" />}
    />
  );
}
```

## Hook Patterns

### React Query Enhancement

```tsx
export function useData() {
  const query = useQuery({
    queryKey: ['data'],
    queryFn: fetchData,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
    refetchOnWindowFocus: false,
  });

  const retry = useCallback(() => {
    query.refetch();
  }, [query]);

  return {
    ...query,
    retry,
    isInitialLoading: query.isLoading && !query.data,
    isRefreshing: query.isFetching && !!query.data,
    hasError: !!query.error,
  };
}
```

## Available Components

### Skeletons
- `<TableSkeleton rows={5} />` - For queue tables
- `<CardSkeleton />` - For KPI cards
- `<KPISkeleton count={4} />` - For KPI grids

### Error States
- `<ErrorState title="..." message="..." onRetry={...} />` - Full error panel
- `<InlineError message="..." onRetry={...} />` - Compact error for tables

### Empty States
- `<EmptyState title="..." subtitle="..." icon={...} />` - Professional empty data

## Testing Requirements

Every hardened component must test:

```tsx
describe('ComponentName', () => {
  it('renders loading skeleton', () => {
    render(<Component isLoading={true} />);
    // Assert skeleton presence
  });

  it('renders error state with retry', () => {
    const mockRetry = vi.fn();
    render(<Component error={new Error('Test')} onRetry={mockRetry} />);

    fireEvent.click(screen.getByText('Retry'));
    expect(mockRetry).toHaveBeenCalled();
  });

  it('renders empty state', () => {
    render(<Component data={[]} />);
    // Assert empty state message
  });
});
```

## Performance Guidelines

1. **Memoization**: Use `useMemo` for expensive computations
2. **Virtualization**: Use windowing for lists > 100 items
3. **Debouncing**: Debounce rapid state changes
4. **Error Boundaries**: Prevent cascading failures

## Implementation Checklist

For each component:

- [ ] Loading skeleton implemented
- [ ] Error state with retry implemented
- [ ] Empty state implemented
- [ ] Null safety guards in place
- [ ] Tests for all states written
- [ ] Performance validated (no unnecessary re-renders)
- [ ] Visual stability confirmed (no layout shifts)

## Commercial Impact

This hardening transforms the OC from a "hacky dashboard" into a "serious control tower" that:

- **Builds investor confidence** during demos
- **Reduces operator frustration** during failures
- **Maintains professionalism** under all conditions
- **Enables reliable operations** for enterprise customers

Code quality directly impacts revenue potential.
