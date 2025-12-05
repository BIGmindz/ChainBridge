/**
 * Deep Linking Utilities
 *
 * URL parameter handling for cross-page navigation between OC and ChainPay.
 * Enables:
 * - /chainpay?intent=abc123&highlight=ready
 * - /oc?shipment=xyz789&panel=money
 * - Auto-selection, scroll-to-view, keyboard focus
 */

import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * Hook for handling payment intent deep links in ChainPay
 *
 * Usage:
 * const { intentId, highlight } = useChainPayDeepLink();
 *
 * URL examples:
 * - /chainpay?intent=abc123 - Selects intent abc123
 * - /chainpay?intent=abc123&highlight=ready - Selects + highlights
 */
export function useChainPayDeepLink() {
  const [searchParams, setSearchParams] = useSearchParams();

  const intentId = searchParams.get("intent");
  const highlight = searchParams.get("highlight");

  const clearDeepLink = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("intent");
    newParams.delete("highlight");
    setSearchParams(newParams, { replace: true });
  };

  return { intentId, highlight, clearDeepLink };
}

/**
 * Hook for handling shipment deep links in Operator Console
 *
 * Usage:
 * const { shipmentId, panel } = useOCDeepLink();
 *
 * URL examples:
 * - /oc?shipment=xyz789 - Selects shipment xyz789
 * - /oc?shipment=xyz789&panel=money - Selects + focuses money view panel
 */
export function useOCDeepLink() {
  const [searchParams, setSearchParams] = useSearchParams();

  const shipmentId = searchParams.get("shipment");
  const panel = searchParams.get("panel") as "queue" | "money" | null;

  const clearDeepLink = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("shipment");
    newParams.delete("panel");
    setSearchParams(newParams, { replace: true });
  };

  return { shipmentId, panel, clearDeepLink };
}

/**
 * Scroll element into view with smooth animation
 */
export function scrollIntoView(element: HTMLElement | null, options?: ScrollIntoViewOptions) {
  if (!element) return;

  element.scrollIntoView({
    behavior: "smooth",
    block: "center",
    ...options,
  });
}

/**
 * Focus element with keyboard support
 */
export function focusElement(element: HTMLElement | null) {
  if (!element) return;

  // Ensure element is focusable
  if (!element.hasAttribute("tabindex")) {
    element.setAttribute("tabindex", "-1");
  }

  element.focus({ preventScroll: true });
}

/**
 * Auto-select row based on deep link parameters
 *
 * @param items - Array of items (intents or shipments)
 * @param deepLinkId - ID from URL parameter
 * @param onSelect - Selection callback
 * @param idKey - Key to extract ID from items (default: "id")
 * @returns Selected item or null
 */
export function useAutoSelect<T extends { id: string }>(
  items: T[],
  deepLinkId: string | null,
  onSelect: (id: string) => void,
  idKey: keyof T = "id" as keyof T
) {
  useEffect(() => {
    if (!deepLinkId || items.length === 0) return;

    // Find matching item
    const matchingItem = items.find((item) => item[idKey] === deepLinkId);

    if (matchingItem) {
      onSelect(matchingItem[idKey] as string);

      // Scroll to item after selection
      setTimeout(() => {
        const element = document.querySelector(`[data-id="${deepLinkId}"]`) as HTMLElement;
        scrollIntoView(element);
        focusElement(element);
      }, 100);
    }
  }, [deepLinkId, items, onSelect, idKey]);
}

/**
 * Generate deep link URL for cross-page navigation
 */
export function buildDeepLink(
  basePath: "/chainpay" | "/oc" | "/operator",
  params: Record<string, string | undefined>
): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });

  const query = searchParams.toString();
  return query ? `${basePath}?${query}` : basePath;
}
