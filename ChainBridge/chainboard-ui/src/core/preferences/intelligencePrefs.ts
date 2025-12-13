/**
 * Intelligence Panel Preferences
 *
 * Simple localStorage-based preferences for showing/hiding intelligence panels.
 * No backend persistence in v1; operator preferences saved locally.
 */

export interface IntelligencePanelPrefs {
  alerts: boolean;
  risk: boolean;
  iot: boolean;
  settlements: boolean;
  recommendations: boolean;
}

const INTEL_PREFS_KEY = "chainbridge:intel_panel_prefs";

const DEFAULT_INTEL_PREFS: IntelligencePanelPrefs = {
  alerts: true,
  risk: true,
  iot: true,
  settlements: true,
  recommendations: true,
};

/**
 * Load intelligence panel preferences from localStorage
 * Falls back to defaults on any error
 */
export function loadIntelPrefs(): IntelligencePanelPrefs {
  try {
    const stored = localStorage.getItem(INTEL_PREFS_KEY);
    if (!stored) {
      return DEFAULT_INTEL_PREFS;
    }

    const parsed = JSON.parse(stored) as Partial<IntelligencePanelPrefs>;

    // Merge with defaults to handle missing keys
    return {
      ...DEFAULT_INTEL_PREFS,
      ...parsed,
    };
  } catch (error) {
    console.warn("[IntelPrefs] Failed to load preferences, using defaults:", error);
    return DEFAULT_INTEL_PREFS;
  }
}

/**
 * Save intelligence panel preferences to localStorage
 */
export function saveIntelPrefs(prefs: IntelligencePanelPrefs): void {
  try {
    localStorage.setItem(INTEL_PREFS_KEY, JSON.stringify(prefs));
  } catch (error) {
    console.error("[IntelPrefs] Failed to save preferences:", error);
  }
}
