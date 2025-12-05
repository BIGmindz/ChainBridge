/**
 * Control Tower Cache Store
 *
 * Lightweight in-memory cache with stale-while-revalidate support.
 * No external dependencies—just a simple, production-ready cache layer.
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  staleTime: number; // milliseconds until data is considered stale
  cacheTime: number; // milliseconds until data is garbage collected
}

interface CacheConfig {
  staleTime?: number; // default: 30 seconds
  cacheTime?: number; // default: 5 minutes
}

const DEFAULT_STALE_TIME = 30 * 1000; // 30 seconds
const DEFAULT_CACHE_TIME = 5 * 60 * 1000; // 5 minutes

/**
 * In-memory cache store with stale-while-revalidate semantics.
 */
class CacheStore {
  private cache = new Map<string, CacheEntry<unknown>>();
  private gcInterval: ReturnType<typeof setInterval>;

  constructor() {
    // Garbage collect expired entries every minute
    this.gcInterval = setInterval(() => this.garbageCollect(), 60 * 1000);
  }

  /**
   * Get cached data if available and not expired.
   */
  get<T>(key: string): T | undefined {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;

    if (!entry) {
      return undefined;
    }

    const now = Date.now();
    const age = now - entry.timestamp;

    // Data expired beyond cache time → remove it
    if (age > entry.cacheTime) {
      this.cache.delete(key);
      return undefined;
    }

    return entry.data;
  }

  /**
   * Check if cached data exists and is still fresh (not stale).
   */
  isFresh(key: string): boolean {
    const entry = this.cache.get(key);

    if (!entry) {
      return false;
    }

    const now = Date.now();
    const age = now - entry.timestamp;

    return age <= entry.staleTime;
  }

  /**
   * Check if cached data exists but is stale (needs revalidation).
   */
  isStale(key: string): boolean {
    const entry = this.cache.get(key);

    if (!entry) {
      return false;
    }

    const now = Date.now();
    const age = now - entry.timestamp;

    return age > entry.staleTime && age <= entry.cacheTime;
  }

  /**
   * Set data in cache with optional config.
   */
  set<T>(key: string, data: T, config?: CacheConfig): void {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      staleTime: config?.staleTime ?? DEFAULT_STALE_TIME,
      cacheTime: config?.cacheTime ?? DEFAULT_CACHE_TIME,
    };

    this.cache.set(key, entry as CacheEntry<unknown>);

    if (import.meta.env.DEV) {
      console.log(`[cache] SET ${key}`, { fresh: entry.staleTime / 1000, ttl: entry.cacheTime / 1000 });
    }
  }

  /**
   * Invalidate (delete) a specific cache entry.
   */
  invalidate(key: string): void {
    const deleted = this.cache.delete(key);

    if (import.meta.env.DEV && deleted) {
      console.log(`[cache] INVALIDATE ${key}`);
    }
  }

  /**
   * Invalidate all cache entries matching a prefix.
   * Useful for invalidating all variants of a query (e.g., all shipments filters).
   */
  invalidatePrefix(prefix: string): void {
    let count = 0;

    for (const key of this.cache.keys()) {
      if (key.startsWith(prefix)) {
        this.cache.delete(key);
        count++;
      }
    }

    if (import.meta.env.DEV && count > 0) {
      console.log(`[cache] INVALIDATE PREFIX ${prefix} (${count} entries)`);
    }
  }

  /**
   * Clear entire cache.
   */
  clear(): void {
    this.cache.clear();

    if (import.meta.env.DEV) {
      console.log("[cache] CLEAR ALL");
    }
  }

  /**
   * Garbage collect expired entries.
   */
  private garbageCollect(): void {
    const now = Date.now();
    let collected = 0;

    for (const [key, entry] of this.cache.entries()) {
      const age = now - entry.timestamp;

      if (age > entry.cacheTime) {
        this.cache.delete(key);
        collected++;
      }
    }

    if (import.meta.env.DEV && collected > 0) {
      console.log(`[cache] GC: collected ${collected} expired entries`);
    }
  }

  /**
   * Get cache stats (for debugging).
   */
  getStats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }

  /**
   * Cleanup on unmount/disposal.
   */
  dispose(): void {
    clearInterval(this.gcInterval);
    this.cache.clear();
  }
}

/**
 * Singleton cache instance for the Control Tower.
 */
export const cacheStore = new CacheStore();

/**
 * Helper to get cache key from query key array.
 */
export function getCacheKey(queryKey: readonly unknown[]): string {
  return JSON.stringify(queryKey);
}
