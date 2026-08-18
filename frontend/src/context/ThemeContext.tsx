/**
 * ThemeContext
 *
 * Provides theme state management for dark/light mode selecting.
 * Persists preference to localStorage and respects system preference.
 *
 * @module context/ThemeContext
 * @since Phase 5.7 (Theme Support)
 */

import {
  createContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import {
  type ThemeMode,
  type TerminalTheme,
  getTheme,
} from '../styles/terminal-theme';

// ============================================
// Constants
// ============================================

const STORAGE_KEY = 'lantern-theme';

// ============================================
// Types
// ============================================

interface ThemeContextValue {
  /** Current theme mode */
  mode: ThemeMode;
  /** Current theme object with all tokens */
  theme: TerminalTheme;
  /** Toggle between dark and light mode */
  toggleTheme: () => void;
  /** Set specific theme mode */
  setMode: (mode: ThemeMode) => void;
  /** Whether current mode is dark */
  isDark: boolean;
  /** Whether current mode is light */
  isLight: boolean;
}

interface ThemeProviderProps {
  children: ReactNode;
  /** Initial theme mode (overrides localStorage/system preference) */
  initialMode?: ThemeMode;
}

// ============================================
// Context
// ============================================

const ThemeContext = createContext<ThemeContextValue | null>(null);

// ============================================
// Helper Functions
// ============================================

/** Get initial theme from localStorage or system preference */
function getInitialTheme(): ThemeMode {
  // Check localStorage first
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') {
      return stored;
    }

    // Fall back to system preference
    if (window.matchMedia?.('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
  }

  // Default to dark (CRT terminal aesthetic)
  return 'dark';
}

// ============================================
// Provider Component
// ============================================

export function ThemeProvider({ children, initialMode }: ThemeProviderProps) {
  const [mode, setModeState] = useState<ThemeMode>(initialMode ?? getInitialTheme);

  // Persist to localStorage when mode changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, mode);
    }
  }, [mode]);

  // Apply theme class to document for global styles
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.remove('theme-dark', 'theme-light');
      document.documentElement.classList.add(`theme-${mode}`);

      // Also update body background for smooth transitions
      if (mode === 'light') {
        document.body.style.backgroundColor = '#f9fafb'; // gray-50
      } else {
        document.body.style.backgroundColor = '#111827'; // gray-900
      }
    }
  }, [mode]);

  const toggleTheme = useCallback(() => {
    setModeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode);
  }, []);

  const theme = getTheme(mode);

  const value: ThemeContextValue = {
    mode,
    theme,
    toggleTheme,
    setMode,
    isDark: mode === 'dark',
    isLight: mode === 'light',
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

// ============================================
// Exports
// ============================================

// Hook is exported from useTheme.ts to satisfy react-refresh
export { ThemeContext };
export type { ThemeMode, TerminalTheme, ThemeContextValue };
