/**
 * FocusMode Context - ADHD-Optimized UI State Management
 *
 * Three focus modes designed for different cognitive states:
 * - NEUROCALM: Minimal distractions, soft colors, reduced motion
 * - SIGNAL_INTENSITY: Highlight KPIs, emphasize critical data
 * - BATTLE: War-room high contrast, maximum visibility, alerts priority
 *
 * WCAG AA compliant with reduced motion support.
 *
 * @module core/focus/FocusModeContext
 */

import React, {
  createContext,
  useContext,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import { create } from "zustand";
import { persist } from "zustand/middleware";

// =============================================================================
// TYPES
// =============================================================================

export type FocusModeType = "NEUROCALM" | "SIGNAL_INTENSITY" | "BATTLE";

export interface FocusModeConfig {
  /** Display name for UI */
  label: string;
  /** Short description */
  description: string;
  /** Icon name for mode selector */
  icon: "brain" | "activity" | "zap";
  /** Animation intensity (0-1) */
  animationIntensity: number;
  /** Enable/disable sound effects */
  soundEnabled: boolean;
  /** Color saturation multiplier */
  saturation: number;
  /** Contrast level */
  contrast: "normal" | "high" | "ultra";
  /** Show non-critical notifications */
  showNonCriticalAlerts: boolean;
  /** Auto-refresh interval in ms (0 = manual only) */
  autoRefreshInterval: number;
  /** Maximum visible items in lists */
  maxListItems: number;
  /** Enable decorative elements */
  showDecorative: boolean;
  /** Typography scale */
  fontScale: number;
  /** Enable pulsing/breathing animations */
  pulsingAnimations: boolean;
  /** Background complexity */
  backgroundComplexity: "minimal" | "normal" | "rich";
}

export interface FocusModeState {
  /** Current active focus mode */
  currentMode: FocusModeType;
  /** Override reduced motion preference */
  forceReducedMotion: boolean;
  /** Custom mode configurations */
  customConfigs: Partial<Record<FocusModeType, Partial<FocusModeConfig>>>;
}

export interface FocusModeActions {
  /** Set the active focus mode */
  setMode: (mode: FocusModeType) => void;
  /** Toggle reduced motion override */
  toggleReducedMotion: () => void;
  /** Update custom config for a mode */
  updateModeConfig: (mode: FocusModeType, config: Partial<FocusModeConfig>) => void;
  /** Reset to default configuration */
  resetToDefaults: () => void;
  /** Cycle to next mode */
  cycleMode: () => void;
}

// =============================================================================
// DEFAULT CONFIGURATIONS
// =============================================================================

export const FOCUS_MODE_CONFIGS: Record<FocusModeType, FocusModeConfig> = {
  NEUROCALM: {
    label: "Neurocalm",
    description: "Calm focus — minimal motion, soft contrast",
    icon: "brain",
    animationIntensity: 0.15, // Very subtle animations only
    soundEnabled: false,
    saturation: 0.65, // Slightly desaturated for reduced visual stress
    contrast: "normal",
    showNonCriticalAlerts: false,
    autoRefreshInterval: 90000, // 90 seconds — less frequent updates reduce anxiety
    maxListItems: 5,
    showDecorative: false,
    fontScale: 1.0,
    pulsingAnimations: false,
    backgroundComplexity: "minimal",
  },
  SIGNAL_INTENSITY: {
    label: "Signal Intensity",
    description: "Highlight KPIs and critical data",
    icon: "activity",
    animationIntensity: 0.7,
    soundEnabled: true,
    saturation: 1.0,
    contrast: "high",
    showNonCriticalAlerts: true,
    autoRefreshInterval: 30000, // 30 seconds
    maxListItems: 10,
    showDecorative: true,
    fontScale: 1.0,
    pulsingAnimations: true,
    backgroundComplexity: "normal",
  },
  BATTLE: {
    label: "Battle Mode",
    description: "War-room high contrast ops",
    icon: "zap",
    animationIntensity: 1.0,
    soundEnabled: true,
    saturation: 1.2,
    contrast: "ultra",
    showNonCriticalAlerts: true,
    autoRefreshInterval: 15000, // 15 seconds
    maxListItems: 20,
    showDecorative: true,
    fontScale: 1.1,
    pulsingAnimations: true,
    backgroundComplexity: "rich",
  },
};

const MODE_ORDER: FocusModeType[] = ["NEUROCALM", "SIGNAL_INTENSITY", "BATTLE"];

// =============================================================================
// ZUSTAND STORE
// =============================================================================

const STORAGE_KEY = "chainbridge.focus-mode";

const initialState: FocusModeState = {
  currentMode: "SIGNAL_INTENSITY",
  forceReducedMotion: false,
  customConfigs: {},
};

interface FocusModeStore extends FocusModeState, FocusModeActions {}

export const useFocusModeStore = create<FocusModeStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setMode: (mode) => set({ currentMode: mode }),

      toggleReducedMotion: () =>
        set((state) => ({ forceReducedMotion: !state.forceReducedMotion })),

      updateModeConfig: (mode, config) =>
        set((state) => ({
          customConfigs: {
            ...state.customConfigs,
            [mode]: { ...state.customConfigs[mode], ...config },
          },
        })),

      resetToDefaults: () => set(initialState),

      cycleMode: () => {
        const { currentMode } = get();
        const currentIndex = MODE_ORDER.indexOf(currentMode);
        const nextIndex = (currentIndex + 1) % MODE_ORDER.length;
        set({ currentMode: MODE_ORDER[nextIndex] });
      },
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({
        currentMode: state.currentMode,
        forceReducedMotion: state.forceReducedMotion,
        customConfigs: state.customConfigs,
      }),
    }
  )
);

// =============================================================================
// REACT CONTEXT
// =============================================================================

interface FocusModeContextValue {
  /** Current mode type */
  mode: FocusModeType;
  /** Resolved configuration (defaults + custom overrides) */
  config: FocusModeConfig;
  /** Whether reduced motion is active */
  reducedMotion: boolean;
  /** All available modes */
  availableModes: FocusModeType[];
  /** Actions */
  setMode: (mode: FocusModeType) => void;
  cycleMode: () => void;
  toggleReducedMotion: () => void;
  updateConfig: (config: Partial<FocusModeConfig>) => void;
}

const FocusModeContext = createContext<FocusModeContextValue | undefined>(undefined);

// =============================================================================
// PROVIDER COMPONENT
// =============================================================================

interface FocusModeProviderProps {
  children: ReactNode;
  /** Initial mode override */
  initialMode?: FocusModeType;
}

export function FocusModeProvider({
  children,
  initialMode,
}: FocusModeProviderProps): JSX.Element {
  const store = useFocusModeStore();

  // Initialize mode if provided
  React.useEffect(() => {
    if (initialMode && initialMode !== store.currentMode) {
      store.setMode(initialMode);
    }
  }, [initialMode, store]);

  // Compute resolved config
  const config = useMemo((): FocusModeConfig => {
    const defaultConfig = FOCUS_MODE_CONFIGS[store.currentMode];
    const customConfig = store.customConfigs[store.currentMode] ?? {};
    return { ...defaultConfig, ...customConfig };
  }, [store.currentMode, store.customConfigs]);

  // Check browser reduced motion preference
  const systemReducedMotion = useMemo(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }, []);

  const reducedMotion = store.forceReducedMotion || systemReducedMotion;

  const updateConfig = useCallback(
    (newConfig: Partial<FocusModeConfig>) => {
      store.updateModeConfig(store.currentMode, newConfig);
    },
    [store]
  );

  const value = useMemo(
    (): FocusModeContextValue => ({
      mode: store.currentMode,
      config,
      reducedMotion,
      availableModes: MODE_ORDER,
      setMode: store.setMode,
      cycleMode: store.cycleMode,
      toggleReducedMotion: store.toggleReducedMotion,
      updateConfig,
    }),
    [store, config, reducedMotion, updateConfig]
  );

  return (
    <FocusModeContext.Provider value={value}>
      {children}
    </FocusModeContext.Provider>
  );
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook to access focus mode context.
 */
export function useFocusMode(): FocusModeContextValue {
  const ctx = useContext(FocusModeContext);
  if (!ctx) {
    throw new Error("useFocusMode must be used inside FocusModeProvider");
  }
  return ctx;
}

/**
 * Hook to get just the current mode config.
 */
export function useFocusModeConfig(): FocusModeConfig {
  const { config } = useFocusMode();
  return config;
}

/**
 * Hook to check if animations should be reduced.
 */
export function useShouldReduceMotion(): boolean {
  const { reducedMotion, config } = useFocusMode();
  return reducedMotion || config.animationIntensity < 0.3;
}

/**
 * Hook to get animation duration based on mode.
 */
export function useAnimationDuration(baseDuration: number): number {
  const { config, reducedMotion } = useFocusMode();
  if (reducedMotion) return 0;
  return baseDuration * config.animationIntensity;
}
