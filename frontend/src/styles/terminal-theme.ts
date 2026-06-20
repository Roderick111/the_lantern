/**
 * Terminal Theme Design Tokens
 *
 * Centralized design system for consistent minimal B&W terminal aesthetic.
 * All panels should use these tokens for colors, spacing, and typography.
 * Supports dark (CRT) and light (LCARS) modes.
 *
 * @module styles/terminal-theme
 * @since Phase 5.3.1 (Design System)
 */

// ============================================
// Theme Mode Type
// ============================================

export type ThemeMode = "dark" | "light";

// ============================================
// Dark Theme (CRT Terminal)
// ============================================

export const TERMINAL_THEME_DARK = {
  fonts: {
    /** UI elements: buttons, labels, headers, menus, navigation */
    ui: "font-sans",
    /** Narrative text: conversations, story, dialogue */
    narrative: "font-serif",
    /** Small labels, tags, tracking text */
    label: "font-sans",
    /** Form inputs, selects, textareas */
    input: "font-sans",
    /** Monospace: code, evidence IDs, system output */
    code: "font-mono",
  },
  colors: {
    text: {
      /** Primary text - headers, important content */
      primary: "text-white",
      /** Primary hover class */
      primaryHover: "hover:text-white",
      /** Secondary text - body content */
      secondary: "text-gray-200",
      /** Tertiary text - supporting content */
      tertiary: "text-gray-400",
      /** Muted text - helper/footer text */
      muted: "text-gray-500",
      /** Separator line color */
      separator: "text-gray-600",
    },
    bg: {
      /** Primary background */
      primary: "bg-gray-900",
      /** Hover state background */
      hover: "bg-gray-800",
      /** Hover class with prefix (for dynamic usage) */
      hoverClass: "hover:bg-gray-800",
      /** Active/selected state */
      active: "bg-gray-700",
      /** Semi-transparent background (cards) - transparent to match page */
      semiTransparent: "bg-transparent",
    },
    /** Gradient utilities for fade effects */
    gradient: {
      /** from-* matching bg.primary for fade overlays */
      fromBg: "from-gray-900",
    },
    border: {
      /** Default border */
      default: "border-gray-700",
      /** Hover state border */
      hover: "border-gray-500",
      /** Hover class with prefix (for dynamic usage) */
      hoverClass: "hover:border-gray-500",
      /** Separator line */
      separator: "border-gray-700",
    },
    /** Amber/gold for interactive elements (magical terminal style) */
    interactive: {
      /** Amber text for clickable items */
      text: "text-amber-400",
      /** Brighter amber on hover */
      hover: "hover:text-amber-300",
      /** Amber border */
      border: "border-amber-500/50",
      /** Amber border on hover */
      borderHover: "hover:border-amber-400",
    },
    /** Character-specific colors for dialogue differentiation */
    character: {
      /** Blue for the Detective (Player) */
      detective: {
        text: "text-blue-300",
        prefix: "text-blue-500",
        border: "border-blue-500",
        bg: "bg-blue-900/10",
      },
      /** Amber for Witnesses */
      witness: {
        text: "text-amber-400",
        prefix: "text-amber-500",
        border: "border-amber-600",
        bg: "bg-amber-900/10",
      },
      /** Purple for System/Secrets */
      system: {
        text: "text-purple-300",
        prefix: "text-purple-500",
        border: "border-purple-900",
        bg: "bg-purple-900/10",
      },
      /** Narrator (gray) */
      narrator: {
        text: "text-gray-300",
        border: "border-gray-400",
        bg: "bg-gray-800/30",
      },
      /** Matthew spirit companion (amber with special styling) */
      matthew: {
        text: "text-gray-300",
        prefix: "text-amber-500",
        border: "border-amber-600",
        bg: "bg-amber-900/20",
        label: "text-amber-500",
      },
    },
    /** State-based colors for feedback */
    state: {
      /** Error states */
      error: {
        text: "text-red-400",
        border: "border-red-700",
        bg: "bg-red-900/30",
        bgLight: "bg-red-900/10",
      },
      /** Success states */
      success: {
        text: "text-green-400",
        border: "border-green-700",
        bg: "bg-green-900/30",
      },
      /** Warning states */
      warning: {
        text: "text-yellow-400",
        border: "border-yellow-700",
        bg: "bg-yellow-900/30",
      },
    },
  },
  spacing: {
    /** Gap between major panels */
    panelGap: "mb-4 md:mb-6",
    /** Gap between sections within a panel */
    sectionGap: "mb-3",
    /** Gap between individual items */
    itemGap: "mb-2",
    /** Internal padding for panels */
    panelPadding: "p-3 md:p-4",
  },
  typography: {
    /** Panel headers - uppercase, white, tracking */
    header: "text-white font-sans uppercase text-sm tracking-wide",
    /** Large headers */
    headerLg: "text-white font-sans uppercase text-xl font-bold tracking-wide",
    /** Body text — serif for narrative/conversations */
    body: "text-gray-200 font-serif text-base leading-[28px] tracking-[0.1px]",
    /** Small body text */
    bodySm: "text-gray-200 font-serif text-sm",
    /** Caption/label text — sans for UI */
    caption: "text-gray-400 font-sans text-sm uppercase tracking-wider",
    /** Helper/footer text */
    helper: "text-gray-500 font-sans text-sm",
    /** Separator line text */
    separator: "text-gray-600 font-sans text-sm",
  },
  symbols: {
    /** Current/active item indicator */
    current: "\u25b8", // ▸
    /** Inactive/other item indicator */
    other: "\u00b7", // ·
    /** Bullet point */
    bullet: "\u2022", // •
    /** Prefix symbol for list items */
    prefix: "\u25b8", // ▸
    /** Block symbol for headers/titles */
    block: "\u2588", // █
    /** Cross/X symbol for exit/close actions */
    cross: "\u00d7", // ×
    /** Bracket close for terminal patterns */
    closeButton: "[X]",
    /** Input prefix for player actions */
    inputPrefix: ">",
    /** Separator line (32 chars) */
    separator: "\u2500".repeat(32), // ────────────────────────────────
    /** Short separator (20 chars) */
    separatorShort: "\u2500".repeat(20),
    /** Filled block for progress bars */
    blockFilled: "\u2588", // █
    /** Empty block for progress bars */
    blockEmpty: "\u2591", // ░
    /** Arrow up */
    arrowUp: "\u2191", // ↑
    /** Arrow down */
    arrowDown: "\u2193", // ↓
    /** Arrow right */
    arrowRight: "\u2192", // →
    /** Double arrow right */
    doubleArrowRight: "\u00bb", // »
    /** Checkmark */
    checkmark: "\u2713", // ✓
    /** Warning */
    warning: "\u26a0", // ⚠
  },
  /** Speaker label formats for consistent dialogue */
  speakers: {
    /** Player/Detective format */
    detective: {
      prefix: ">",
      label: "DETECTIVE",
      format: (text: string) => `> ${text}`,
    },
    /** Witness format */
    witness: {
      format: (name: string) => `:: ${name.toUpperCase()} ::`,
    },
    /** Spirit companion format */
    matthew: {
      prefix: "MATTHEW:",
      label: "SPIRIT",
    },
    /** System messages */
    system: {
      prefix: "!",
    },
  },
  /** System message templates */
  messages: {
    /** Error message format */
    error: (msg: string) => `[ SYSTEM_ERROR ] ${msg}`,
    /** Secret discovered format */
    secretDiscovered: "[ SECRET DISCOVERED ]",
    /** Spirit resonance format */
    spiritResonance: (_name: string) => `[ SPIRIT RESONANCE ]`,
    /** Evidence discovered format */
    evidenceDiscovered: (id: string) => `+ Evidence: ${id}`,
  },
  /** Visual effects */
  effects: {
    /** Scanline overlay for CRT effect */
    scanlines:
      "bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%)] bg-[length:100%_4px] pointer-events-none opacity-50",
    /** Corner bracket decorations */
    cornerBrackets: {
      topLeft:
        "absolute top-0 left-0 w-2 h-2 border-t border-l border-gray-400",
      topRight:
        "absolute top-0 right-0 w-2 h-2 border-t border-r border-gray-400",
      bottomLeft:
        "absolute bottom-0 left-0 w-2 h-2 border-b border-l border-gray-400",
      bottomRight:
        "absolute bottom-0 right-0 w-2 h-2 border-b border-r border-gray-400",
    },
    /** Text glow effects */
    glow: {
      amber: "terminal-glow-amber",
      green: "terminal-glow-green",
    },
  },
  /** Animation classes */
  animation: {
    /** Fade in */
    fadeIn: "animate-fadeIn",
    /** Pulse subtle */
    pulse: "animate-pulse",
    /** Pulse very subtle */
    pulseSubtle: "animate-pulse-subtle",
    /** Cursor blink */
    cursorBlink: "animate-cursor-blink",
    /** Screen flicker */
    screenFlicker: "animate-screen-flicker",
    /** Slide up (for dropups) */
    slideUp: "animate-slide-up",
  },
  /** Component-specific styles */
  components: {
    /** Button base styles */
    button: {
      base: "w-full text-left p-3 rounded border transition-colors",
      default:
        "bg-gray-800/50 border-gray-700 hover:border-gray-500 hover:bg-gray-800",
      selected: "bg-gray-800 border-gray-500 cursor-default",
      disabled: "opacity-50 cursor-not-allowed",
      focus:
        "focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:outline-none",
      /** Terminal-style action button */
      terminalAction:
        "py-3 md:py-2.5 px-4 flex items-center gap-3 border border-gray-600 bg-gray-900 text-gray-300 transition-all duration-200 font-sans text-xs uppercase tracking-widest group hover:border-amber-500/50 hover:text-amber-400 hover:bg-gray-800 active:brightness-90 rounded-sm",
      /** Danger/destructive button style */
      danger:
        "border-red-600 bg-red-900/30 text-red-400 hover:bg-red-900/50 hover:border-red-500 hover:text-red-300",
    },
    /** Card/Panel base styles */
    card: {
      base: "font-sans bg-gray-900 text-gray-100 border-gray-700",
    },
    /** Input field with terminal prefix */
    input: {
      /** Container wrapper */
      wrapper: "relative group w-full",
      /** Prefix styling (absolute positioned) */
      prefix: "absolute top-3 left-3 text-gray-500 font-bold select-none",
      /** Base textarea/input field */
      field:
        "w-full bg-gray-900 text-gray-100 border rounded-sm p-3 pl-8 pr-10 placeholder-gray-600 focus:outline-none resize-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 text-base font-sans tracking-wide",
      /** Default border state */
      borderDefault: "border-gray-600 focus:border-gray-400 focus:bg-gray-800",
      /** Special border (Matthew/amber) */
      borderSpecial:
        "border-amber-600/50 focus:border-amber-500 focus:bg-gray-800",
      /** Send button */
      sendButton:
        "absolute right-2 bottom-2 md:right-3 md:bottom-3 px-4 py-2.5 md:px-3 md:py-1 border border-gray-600 rounded-sm bg-gray-800 text-gray-400 hover:border-amber-500 hover:text-amber-400 hover:bg-gray-800 active:opacity-80 text-xs uppercase font-bold tracking-wide disabled:opacity-0 transition-all duration-200",
    },
    /** Message bubbles for conversations */
    message: {
      /** Player message */
      player: {
        wrapper: "py-1",
        text: "text-blue-400/70 text-base font-serif leading-[28px] tracking-[0.1px]",
        prefix: "text-gray-500",
      },
      /** Narrator message */
      narrator: {
        wrapper: "py-1",
        text: "text-gray-200 text-base font-serif leading-[28px] tracking-[0.1px] whitespace-pre-line text-justify",
      },
      /** Matthew spirit companion message */
      matthew: {
        wrapper: "border-l border-amber-600/40 pl-3 py-1",
        text: "text-base font-serif leading-[28px] tracking-[0.1px] text-gray-200 text-justify",
        label: "text-amber-500 font-sans font-bold mr-2",
      },
      /** Evidence tag */
      evidence: {
        wrapper: "border-l border-gray-700/40 pl-3 py-1",
        tag: "inline-block bg-gray-800 text-gray-200 px-2 py-1.5 md:py-0.5 rounded border border-gray-600 mr-1 font-sans",
      },
      /** Witness conversation bubble */
      witness: {
        wrapperPlayer: "max-w-[85%] pl-3 py-1",
        wrapperWitness: "max-w-[85%] py-1",
        label: "text-xs uppercase tracking-widest font-bold font-sans",
        text: "text-base text-gray-200 font-serif leading-[28px] tracking-[0.1px] whitespace-pre-line text-justify",
      },
    },
    /** Section separator with centered label */
    sectionSeparator: {
      wrapper: "flex items-center gap-3 mb-2 opacity-60",
      line: "h-px bg-gray-600 flex-1",
      label: "text-xs text-gray-400 uppercase tracking-widest font-bold",
    },
    /** Trust meter thresholds */
    trustMeter: {
      /** Get color based on trust level */
      getColor: (level: number): string => {
        if (level < 30) return "text-red-400";
        if (level < 70) return "text-yellow-400";
        return "text-green-400";
      },
      wrapper: "w-full font-sans mt-4 mb-6 text-center",
      container:
        "text-xs text-gray-500 tracking-widest border border-gray-700 bg-gray-800/30 p-2 rounded",
      label: "font-bold mr-2 text-gray-400",
    },
    /** Modal overlay/backdrop */
    modal: {
      /** Standard backdrop overlay for all modals */
      overlay: "fixed inset-0 z-50 bg-black/80 backdrop-blur-[4px]",
      /** Just the visual style (for nested absolute positioning) */
      overlayStyle: "bg-black/80 backdrop-blur-[4px]",
    },
  },
} as const;

/**
 * Helper to generate ASCII progress bar
 * @param value - Current value (0-100)
 * @param total - Total segments (default 10)
 * @returns ASCII bar like "████░░░░░░"
 * @example
 * generateAsciiBar(75, 10) // "███████░░░"
 */
// ============================================
// Light Theme (LCARS Modern)
// ============================================

export const TERMINAL_THEME_LIGHT = {
  fonts: TERMINAL_THEME_DARK.fonts,
  colors: {
    text: {
      /** Primary text - headers, important content */
      primary: "text-gray-900",
      /** Primary hover class */
      primaryHover: "hover:text-gray-900",
      /** Secondary text - body content - 1 tone darker for better contrast */
      secondary: "text-gray-900",
      /** Tertiary text - supporting content */
      tertiary: "text-gray-700",
      /** Muted text - helper/footer text */
      muted: "text-gray-600",
      /** Separator line color */
      separator: "text-gray-500",
    },
    bg: {
      /** Primary background */
      primary: "bg-gray-100",
      /** Hover state background - stronger contrast */
      hover: "bg-gray-200",
      /** Hover class with prefix (for dynamic usage) */
      hoverClass: "hover:bg-gray-200",
      /** Active/selected state */
      active: "bg-gray-200",
      /** Semi-transparent background (cards) - transparent to match page */
      semiTransparent: "bg-transparent",
    },
    /** Gradient utilities for fade effects */
    gradient: {
      /** from-* matching bg.primary for fade overlays */
      fromBg: "from-gray-100",
    },
    border: {
      /** Default border */
      default: "border-gray-300",
      /** Hover state border - stronger contrast */
      hover: "border-gray-500",
      /** Hover class with prefix (for dynamic usage) */
      hoverClass: "hover:border-gray-500",
      /** Separator line */
      separator: "border-gray-200",
    },
    /** Indigo for interactive elements (high contrast on light backgrounds) */
    interactive: {
      /** Indigo text for clickable items */
      text: "text-indigo-600",
      /** Darker indigo on hover - stronger contrast */
      hover: "hover:text-indigo-900",
      /** Indigo border */
      border: "border-indigo-400",
      /** Indigo border on hover - stronger contrast */
      borderHover: "hover:border-indigo-700",
    },
    /** Character-specific colors for dialogue differentiation */
    character: {
      /** Blue for the Detective (Player) */
      detective: {
        text: "text-blue-700",
        prefix: "text-blue-600",
        border: "border-blue-400",
        bg: "bg-blue-50",
      },
      /** Amber for Witnesses */
      witness: {
        text: "text-amber-700",
        prefix: "text-amber-600",
        border: "border-amber-400",
        bg: "bg-amber-50",
      },
      /** Purple for System/Secrets */
      system: {
        text: "text-purple-700",
        prefix: "text-purple-600",
        border: "border-purple-300",
        bg: "bg-purple-50",
      },
      /** Narrator (gray) */
      narrator: {
        text: "text-gray-700",
        border: "border-gray-400",
        bg: "bg-gray-100/50",
      },
      /** Matthew spirit companion (amber with special styling) */
      matthew: {
        text: "text-gray-700",
        prefix: "text-amber-600",
        border: "border-amber-400",
        bg: "bg-amber-50/50",
        label: "text-amber-600",
      },
    },
    /** State-based colors for feedback */
    state: {
      /** Error states */
      error: {
        text: "text-red-600",
        border: "border-red-300",
        bg: "bg-red-100/50",
        bgLight: "bg-red-50",
      },
      /** Success states */
      success: {
        text: "text-green-600",
        border: "border-green-300",
        bg: "bg-green-100/50",
      },
      /** Warning states */
      warning: {
        text: "text-yellow-600",
        border: "border-yellow-300",
        bg: "bg-yellow-100/50",
      },
    },
  },
  spacing: TERMINAL_THEME_DARK.spacing,
  typography: {
    /** Panel headers - uppercase, dark, tracking */
    header: "text-gray-900 font-sans uppercase text-sm tracking-wide",
    /** Large headers */
    headerLg:
      "text-gray-900 font-sans uppercase text-xl font-bold tracking-wide",
    /** Body text — serif for narrative/conversations */
    body: "text-gray-900 font-serif text-base leading-[28px] tracking-[0.1px]",
    /** Small body text */
    bodySm: "text-gray-900 font-serif text-sm",
    /** Caption/label text — sans for UI */
    caption: "text-gray-600 font-sans text-sm uppercase tracking-wider",
    /** Helper/footer text */
    helper: "text-gray-500 font-sans text-sm",
    /** Separator line text */
    separator: "text-gray-400 font-sans text-sm",
  },
  symbols: TERMINAL_THEME_DARK.symbols,
  speakers: TERMINAL_THEME_DARK.speakers,
  messages: TERMINAL_THEME_DARK.messages,
  /** Visual effects - reduced for light mode */
  effects: {
    /** No scanlines in light mode */
    scanlines: "pointer-events-none opacity-0",
    /** Corner bracket decorations - darker for light bg */
    cornerBrackets: {
      topLeft:
        "absolute top-0 left-0 w-2 h-2 border-t border-l border-gray-400",
      topRight:
        "absolute top-0 right-0 w-2 h-2 border-t border-r border-gray-400",
      bottomLeft:
        "absolute bottom-0 left-0 w-2 h-2 border-b border-l border-gray-400",
      bottomRight:
        "absolute bottom-0 right-0 w-2 h-2 border-b border-r border-gray-400",
    },
    /** Text glow effects - disabled in light mode */
    glow: {
      amber: "",
      green: "",
    },
  },
  animation: TERMINAL_THEME_DARK.animation,
  /** Component-specific styles */
  components: {
    /** Button base styles */
    button: {
      base: "w-full text-left p-3 rounded border transition-colors",
      default:
        "bg-gray-100/50 border-gray-300 hover:border-gray-400 hover:bg-gray-100",
      selected: "bg-gray-100 border-gray-400 cursor-default",
      disabled: "opacity-50 cursor-not-allowed",
      focus:
        "focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:outline-none",
      /** Terminal-style action button - stronger hover contrast */
      terminalAction:
        "py-3 md:py-2.5 px-4 flex items-center gap-3 border border-gray-300 bg-transparent text-gray-700 transition-all duration-200 font-sans text-xs uppercase tracking-widest group hover:border-indigo-500 hover:text-indigo-700 hover:bg-gray-100 active:brightness-90 rounded-sm",
      /** Danger/destructive button style - high visibility red */
      danger:
        "border-red-500 bg-red-50 text-red-700 hover:bg-red-100 hover:border-red-600 hover:text-red-800",
    },
    /** Card/Panel base styles */
    card: {
      base: "font-sans text-gray-900 border-gray-300",
    },
    /** Input field with terminal prefix */
    input: {
      /** Container wrapper */
      wrapper: "relative group w-full",
      /** Prefix styling (absolute positioned) */
      prefix: "absolute top-3 left-3 text-gray-400 font-bold select-none",
      /** Base textarea/input field */
      field:
        "w-full bg-white text-gray-900 border rounded-sm p-3 pl-8 pr-10 placeholder-gray-400 focus:outline-none resize-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 text-base font-sans tracking-wide",
      /** Default border state */
      borderDefault: "border-gray-300 focus:border-gray-400 focus:bg-white",
      /** Special border (Matthew/amber) */
      borderSpecial:
        "border-amber-400/50 focus:border-amber-500 focus:bg-amber-50/20",
      /** Send button */
      sendButton:
        "absolute right-2 bottom-2 md:right-3 md:bottom-3 px-4 py-2.5 md:px-3 md:py-1 border border-gray-300 rounded-sm bg-gray-100 text-gray-500 hover:border-amber-400 hover:text-amber-600 hover:bg-amber-50 active:opacity-80 text-xs uppercase font-bold tracking-wide disabled:opacity-0 transition-all duration-200",
    },
    /** Message bubbles for conversations */
    message: {
      /** Player message */
      player: {
        wrapper: "py-1",
        text: "text-blue-800 text-base font-serif leading-[28px] tracking-[0.1px]",
        prefix: "text-gray-500",
      },
      /** Narrator message */
      narrator: {
        wrapper: "py-1",
        text: "text-gray-900 text-base font-serif leading-[28px] tracking-[0.1px] whitespace-pre-line text-justify",
      },
      /** Matthew spirit companion message */
      matthew: {
        wrapper: "border-l border-amber-400/40 pl-3 py-1",
        text: "text-base font-serif leading-[28px] tracking-[0.1px] text-gray-900 text-justify",
        label: "text-amber-700 font-sans font-bold mr-2",
      },
      /** Evidence tag */
      evidence: {
        wrapper: "border-l border-gray-300/40 pl-3 py-1",
        tag: "inline-block bg-gray-100 text-gray-900 px-2 py-1.5 md:py-0.5 rounded border border-gray-300 mr-1 font-sans",
      },
      /** Witness conversation bubble */
      witness: {
        wrapperPlayer: "max-w-[85%] pl-3 py-1",
        wrapperWitness: "max-w-[85%] py-1",
        label: "text-xs uppercase tracking-widest font-bold font-sans",
        text: "text-base text-gray-900 font-serif leading-[28px] tracking-[0.1px] whitespace-pre-line text-justify",
      },
    },
    /** Section separator with centered label */
    sectionSeparator: {
      wrapper: "flex items-center gap-3 mb-2 opacity-60",
      line: "h-px bg-gray-300 flex-1",
      label: "text-xs text-gray-600 uppercase tracking-widest font-bold",
    },
    /** Trust meter thresholds */
    trustMeter: {
      /** Get color based on trust level */
      getColor: (level: number): string => {
        if (level < 30) return "text-red-600";
        if (level < 70) return "text-yellow-600";
        return "text-green-600";
      },
      wrapper: "w-full font-sans mt-4 mb-6 text-center",
      container:
        "text-xs text-gray-500 tracking-widest border border-gray-300 bg-gray-100/50 p-2 rounded",
      label: "font-bold mr-2 text-gray-500",
    },
    /** Modal overlay/backdrop */
    modal: {
      /** Standard backdrop overlay for all modals */
      overlay: "fixed inset-0 z-50 bg-black/30 backdrop-blur-[4px]",
      /** Just the visual style (for nested absolute positioning) */
      overlayStyle: "bg-black/30 backdrop-blur-[4px]",
    },
  },
} as const;

// ============================================
// Default Theme (backward compatibility)
// ============================================

// ============================================
// Theme Getter
// ============================================

/** Get theme by mode */
export function getTheme(mode: ThemeMode) {
  return mode === "light" ? TERMINAL_THEME_LIGHT : TERMINAL_THEME_DARK;
}

// ============================================
// Helpers
// ============================================

/**
 * Helper to generate ASCII progress bar
 * @param value - Current value (0-100)
 * @param total - Total segments (default 10)
 * @returns ASCII bar like "████░░░░░░"
 * @example
 * generateAsciiBar(75, 10) // "███████░░░"
 */
export function generateAsciiBar(value: number, total = 10): string {
  const filled = Math.floor((value / 100) * total);
  const empty = total - filled;
  return (
    TERMINAL_THEME_DARK.symbols.blockFilled.repeat(filled) +
    TERMINAL_THEME_DARK.symbols.blockEmpty.repeat(empty)
  );
}

export type TerminalTheme =
  | typeof TERMINAL_THEME_DARK
  | typeof TERMINAL_THEME_LIGHT;
