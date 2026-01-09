/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Accessibility Utilities — LIRA's Accessibility Enforcement
 * PAC-BENSON-P23-C: Parallel Platform Hardening (Corrective)
 *
 * Provides accessibility utilities and audit helpers:
 * - ARIA attribute generators
 * - Screen reader announcements
 * - Focus management
 * - Keyboard navigation helpers
 * - Color contrast validation
 *
 * INVARIANTS:
 * - INV-UI-004: Accessibility compliance
 * - WCAG 2.1 AA compliance
 *
 * Author: LIRA (GID-09) — Accessibility Lead
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// ARIA ATTRIBUTE GENERATORS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Generate ARIA attributes for status indicators.
 */
export function getStatusAriaProps(
  status: string,
  label: string,
): Record<string, string> {
  return {
    role: 'status',
    'aria-label': label,
    'aria-live': status === 'error' ? 'assertive' : 'polite',
    'aria-atomic': 'true',
  };
}

/**
 * Generate ARIA attributes for interactive lists.
 */
export function getListAriaProps(
  label: string,
  itemCount: number,
): Record<string, string | number> {
  return {
    role: 'list',
    'aria-label': label,
    'aria-setsize': itemCount,
  };
}

/**
 * Generate ARIA attributes for list items.
 */
export function getListItemAriaProps(
  position: number,
  total: number,
): Record<string, string | number> {
  return {
    role: 'listitem',
    'aria-posinset': position,
    'aria-setsize': total,
  };
}

/**
 * Generate ARIA attributes for progress indicators.
 */
export function getProgressAriaProps(
  value: number,
  max: number,
  label: string,
): Record<string, string | number> {
  return {
    role: 'progressbar',
    'aria-valuenow': value,
    'aria-valuemin': 0,
    'aria-valuemax': max,
    'aria-valuetext': `${Math.round((value / max) * 100)}%`,
    'aria-label': label,
  };
}

/**
 * Generate ARIA attributes for tabs.
 */
export function getTabAriaProps(
  tabId: string,
  panelId: string,
  isSelected: boolean,
): Record<string, string | boolean> {
  return {
    role: 'tab',
    id: tabId,
    'aria-controls': panelId,
    'aria-selected': isSelected,
    tabIndex: isSelected ? 0 : -1,
  };
}

/**
 * Generate ARIA attributes for tab panels.
 */
export function getTabPanelAriaProps(
  panelId: string,
  tabId: string,
): Record<string, string | number> {
  return {
    role: 'tabpanel',
    id: panelId,
    'aria-labelledby': tabId,
    tabIndex: 0,
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// SCREEN READER ANNOUNCEMENTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Announce message to screen readers.
 */
export function announceToScreenReader(
  message: string,
  priority: 'polite' | 'assertive' = 'polite',
): void {
  const announcer = document.getElementById('sr-announcer') || createAnnouncer();
  announcer.setAttribute('aria-live', priority);
  announcer.textContent = '';
  
  // Trigger announcement
  requestAnimationFrame(() => {
    announcer.textContent = message;
  });
}

/**
 * Create screen reader announcer element.
 */
function createAnnouncer(): HTMLElement {
  const announcer = document.createElement('div');
  announcer.id = 'sr-announcer';
  announcer.className = 'sr-only';
  announcer.setAttribute('aria-live', 'polite');
  announcer.setAttribute('aria-atomic', 'true');
  document.body.appendChild(announcer);
  return announcer;
}

/**
 * Announce state change for entity.
 */
export function announceStateChange(
  entityType: string,
  entityId: string,
  oldState: string,
  newState: string,
): void {
  const message = `${entityType} ${entityId} changed from ${oldState} to ${newState}`;
  announceToScreenReader(message, newState === 'error' || newState === 'failed' ? 'assertive' : 'polite');
}

// ═══════════════════════════════════════════════════════════════════════════════
// FOCUS MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Focus trap for modal dialogs.
 */
export class FocusTrap {
  private container: HTMLElement;
  private firstFocusable: HTMLElement | null = null;
  private lastFocusable: HTMLElement | null = null;
  private previousFocus: HTMLElement | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
    this.updateFocusableElements();
  }

  private updateFocusableElements(): void {
    const focusableSelectors = [
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      'a[href]',
      '[tabindex]:not([tabindex="-1"])',
    ].join(', ');

    const elements = this.container.querySelectorAll<HTMLElement>(focusableSelectors);
    this.firstFocusable = elements[0] || null;
    this.lastFocusable = elements[elements.length - 1] || null;
  }

  activate(): void {
    this.previousFocus = document.activeElement as HTMLElement;
    this.container.addEventListener('keydown', this.handleKeyDown);
    this.firstFocusable?.focus();
  }

  deactivate(): void {
    this.container.removeEventListener('keydown', this.handleKeyDown);
    this.previousFocus?.focus();
  }

  private handleKeyDown = (event: KeyboardEvent): void => {
    if (event.key !== 'Tab') return;

    this.updateFocusableElements();

    if (event.shiftKey) {
      if (document.activeElement === this.firstFocusable) {
        event.preventDefault();
        this.lastFocusable?.focus();
      }
    } else {
      if (document.activeElement === this.lastFocusable) {
        event.preventDefault();
        this.firstFocusable?.focus();
      }
    }
  };
}

/**
 * Move focus to element with announcement.
 */
export function moveFocusTo(
  element: HTMLElement,
  announcement?: string,
): void {
  element.focus();
  if (announcement) {
    announceToScreenReader(announcement);
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// KEYBOARD NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Key codes for navigation.
 */
export const Keys = {
  ENTER: 'Enter',
  SPACE: ' ',
  ESCAPE: 'Escape',
  TAB: 'Tab',
  ARROW_UP: 'ArrowUp',
  ARROW_DOWN: 'ArrowDown',
  ARROW_LEFT: 'ArrowLeft',
  ARROW_RIGHT: 'ArrowRight',
  HOME: 'Home',
  END: 'End',
} as const;

/**
 * Handle arrow key navigation in list.
 */
export function handleListNavigation(
  event: KeyboardEvent,
  currentIndex: number,
  itemCount: number,
  onIndexChange: (newIndex: number) => void,
): void {
  let newIndex = currentIndex;

  switch (event.key) {
    case Keys.ARROW_DOWN:
      event.preventDefault();
      newIndex = (currentIndex + 1) % itemCount;
      break;
    case Keys.ARROW_UP:
      event.preventDefault();
      newIndex = (currentIndex - 1 + itemCount) % itemCount;
      break;
    case Keys.HOME:
      event.preventDefault();
      newIndex = 0;
      break;
    case Keys.END:
      event.preventDefault();
      newIndex = itemCount - 1;
      break;
    default:
      return;
  }

  onIndexChange(newIndex);
}

/**
 * Handle tab navigation.
 */
export function handleTabNavigation(
  event: KeyboardEvent,
  currentIndex: number,
  tabCount: number,
  onIndexChange: (newIndex: number) => void,
): void {
  let newIndex = currentIndex;

  switch (event.key) {
    case Keys.ARROW_LEFT:
      event.preventDefault();
      newIndex = (currentIndex - 1 + tabCount) % tabCount;
      break;
    case Keys.ARROW_RIGHT:
      event.preventDefault();
      newIndex = (currentIndex + 1) % tabCount;
      break;
    case Keys.HOME:
      event.preventDefault();
      newIndex = 0;
      break;
    case Keys.END:
      event.preventDefault();
      newIndex = tabCount - 1;
      break;
    default:
      return;
  }

  onIndexChange(newIndex);
}

// ═══════════════════════════════════════════════════════════════════════════════
// COLOR CONTRAST
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Calculate relative luminance of a color.
 */
function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculate contrast ratio between two colors.
 */
export function getContrastRatio(
  color1: { r: number; g: number; b: number },
  color2: { r: number; g: number; b: number },
): number {
  const l1 = getLuminance(color1.r, color1.g, color1.b);
  const l2 = getLuminance(color2.r, color2.g, color2.b);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if contrast meets WCAG AA requirements.
 */
export function meetsWCAGAA(
  contrastRatio: number,
  textSize: 'normal' | 'large' = 'normal',
): boolean {
  const threshold = textSize === 'large' ? 3 : 4.5;
  return contrastRatio >= threshold;
}

/**
 * Check if contrast meets WCAG AAA requirements.
 */
export function meetsWCAGAAA(
  contrastRatio: number,
  textSize: 'normal' | 'large' = 'normal',
): boolean {
  const threshold = textSize === 'large' ? 4.5 : 7;
  return contrastRatio >= threshold;
}

// ═══════════════════════════════════════════════════════════════════════════════
// SKIP LINKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Create skip link for main content.
 */
export function createSkipLink(targetId: string, label = 'Skip to main content'): HTMLAnchorElement {
  const link = document.createElement('a');
  link.href = `#${targetId}`;
  link.className = 'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-gray-800 focus:text-white focus:px-4 focus:py-2 focus:rounded';
  link.textContent = label;
  return link;
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

export default {
  getStatusAriaProps,
  getListAriaProps,
  getListItemAriaProps,
  getProgressAriaProps,
  getTabAriaProps,
  getTabPanelAriaProps,
  announceToScreenReader,
  announceStateChange,
  FocusTrap,
  moveFocusTo,
  Keys,
  handleListNavigation,
  handleTabNavigation,
  getContrastRatio,
  meetsWCAGAA,
  meetsWCAGAAA,
  createSkipLink,
};
