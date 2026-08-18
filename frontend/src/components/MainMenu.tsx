/**
 * MainMenu Component
 *
 * In-game menu modal accessible via ESC key or MENU button.
 * Uses Radix UI Dialog for accessibility (focus management, ESC handling).
 * Minimal B&W terminal aesthetic with keyboard navigation (1-5 number keys).
 *
 * Phase 5.1: Restart, Load, Save functional. Settings disabled.
 * Phase 5.3.1: Added "Exit to Main Menu" (button 5).
 * Phase 5.7: Settings enabled with theme toggle.
 *
 * @module components/MainMenu
 * @since Phase 5.1, updated Phase 5.7
 */

import * as Dialog from '@radix-ui/react-dialog';
import { useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { backdropVariants, dialogContentVariants, reducedMotionVariants } from '../utils/modalAnimations';
import { useTheme } from '../context/useTheme';

// ============================================
// Types
// ============================================

export interface MainMenuProps {
  /** Whether the menu is open */
  isOpen: boolean;
  /** Callback when menu should close */
  onClose: () => void;
  /** Callback when "Restart Case" is selected (triggers confirmation) */
  onRestart: () => void;
  /** Callback when "Load Game" is selected (Phase 5.3) */
  onLoad: () => void;
  /** Callback when "Save Game" is selected (Phase 5.3) */
  onSave: () => void;
  /** Callback when "Settings" is selected (Phase 5.7) */
  onSettings?: () => void;
  /** Callback when "Exit to Main Menu" is selected (Phase 5.3.1) */
  onExitToMainMenu?: () => void;
  /** Loading state (disables buttons during async operations) */
  loading?: boolean;
}

// ============================================
// Component
// ============================================

export function MainMenu({
  isOpen,
  onClose,
  onRestart,
  onLoad,
  onSave,
  onSettings,
  onExitToMainMenu,
  loading = false,
}: MainMenuProps) {
  const { theme } = useTheme();

  // Number key shortcuts (1-5)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // ESC: Close menu
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      // Number key shortcuts (1-5)
      if (loading) return; // Disable all shortcuts when loading

      if (e.key === '1') {
        e.preventDefault();
        onSave();
      } else if (e.key === '2') {
        e.preventDefault();
        onLoad();
      } else if (e.key === '3' && onSettings) {
        // Key 3: Settings (Phase 5.7)
        e.preventDefault();
        onSettings();
      } else if (e.key === '4') {
        e.preventDefault();
        onRestart();
      } else if (e.key === '5' && onExitToMainMenu) {
        // Key 5: Exit to Main Menu (Phase 5.3.1)
        e.preventDefault();
        onExitToMainMenu();
      } else if (e.key === 'Enter' && onExitToMainMenu) {
        // Enter: Exit to Main Menu
        e.preventDefault();
        onExitToMainMenu();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onRestart, onLoad, onSave, onSettings, onExitToMainMenu, onClose, loading]);

  // Common button class for consistency (rounded-sm for terminal-style sharp corners)
  const prefersReducedMotion = useReducedMotion();
  const menuButtonClass =`w-full text-left ${theme.fonts.ui} text-sm font-bold uppercase tracking-wider py-3 px-4 border rounded-sm transition-all duration-200 flex items-center gap-3 active:opacity-80`;

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <AnimatePresence>
        {isOpen && (
          <Dialog.Portal forceMount>
            {/* Backdrop overlay */}
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className={theme.components.modal.overlay}
                variants={prefersReducedMotion ? reducedMotionVariants : backdropVariants}
                initial="initial" animate="animate" exit="exit"
              />
            </Dialog.Overlay>

            {/* Menu content */}
            <Dialog.Content asChild forceMount
              onEscapeKeyDown={onClose}
            >
              <motion.div
                className={`fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50
                           ${theme.colors.bg.primary} border ${theme.colors.interactive.border} rounded-sm
                           w-[calc(100%-2rem)] max-w-sm shadow-2xl max-h-[calc(100dvh-2rem)] overflow-y-auto
                           focus:outline-none`}
                variants={prefersReducedMotion ? reducedMotionVariants : dialogContentVariants}
                initial="initial" animate="animate" exit="exit"
              >
          {/* Menu title */}
          <div className={`border-b ${theme.colors.interactive.border} px-6 py-4 flex items-center justify-between ${theme.colors.bg.semiTransparent}`}>
            <Dialog.Title className={`${theme.typography.headerLg} ${theme.colors.interactive.text}`}>
              SYSTEM MENU
            </Dialog.Title>
            <Dialog.Description className="sr-only">
              Game menu with save, load, settings, and restart options
            </Dialog.Description>
          </div>

          {/* Menu options */}
          <div className="p-6 space-y-3">
            {/* 1. Save Game - FUNCTIONAL (Phase 5.3) */}
            <button
              onClick={onSave}
              disabled={loading}
              className={`${menuButtonClass} ${theme.colors.bg.semiTransparent} ${theme.colors.border.default} ${theme.colors.text.secondary} ${theme.colors.interactive.borderHover} ${theme.colors.interactive.hover} ${theme.colors.bg.hoverClass} disabled:opacity-50`}
            >
              <span className={`${theme.colors.text.muted} font-normal`}>[1]</span>
              <span className={theme.colors.interactive.text}>{theme.symbols.current}</span>
              SAVE GAME
            </button>

            {/* 2. Load Game - FUNCTIONAL (Phase 5.3) */}
            <button
              onClick={onLoad}
              disabled={loading}
              className={`${menuButtonClass} ${theme.colors.bg.semiTransparent} ${theme.colors.border.default} ${theme.colors.text.secondary} ${theme.colors.interactive.borderHover} ${theme.colors.interactive.hover} ${theme.colors.bg.hoverClass} disabled:opacity-50`}
            >
              <span className={`${theme.colors.text.muted} font-normal`}>[2]</span>
              <span className={theme.colors.interactive.text}>{theme.symbols.current}</span>
              LOAD GAME
            </button>

            {/* 3. Settings - FUNCTIONAL (Phase 5.7) */}
            <button
              onClick={onSettings}
              disabled={loading || !onSettings}
              className={`${menuButtonClass} ${theme.colors.bg.semiTransparent} ${theme.colors.border.default} ${theme.colors.text.secondary} ${theme.colors.interactive.borderHover} ${theme.colors.interactive.hover} ${theme.colors.bg.hoverClass} disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <span className={`${theme.colors.text.muted} font-normal`}>[3]</span>
              <span className={theme.colors.interactive.text}>{theme.symbols.current}</span>
              SETTINGS
            </button>

            {/* Divider */}
            <div className={`border-t ${theme.colors.border.separator} my-2`}></div>

            {/* 4. Restart Case - FUNCTIONAL (RED WARNING) */}
            <button
              onClick={onRestart}
              disabled={loading}
              className={`${menuButtonClass} ${theme.components.button.danger} disabled:opacity-50`}
            >
              <span className="opacity-60 font-normal">[4]</span>
              <span>{theme.symbols.warning}</span>
              RESTART CASE
            </button>

            {/* 5. Exit to Main Menu - FUNCTIONAL (Phase 5.3.1) */}
            {onExitToMainMenu && (
              <button
                onClick={onExitToMainMenu}
                disabled={loading}
                className={`${menuButtonClass} ${theme.colors.bg.semiTransparent} ${theme.colors.border.default} ${theme.colors.text.tertiary} ${theme.colors.interactive.borderHover} ${theme.colors.interactive.hover} ${theme.colors.bg.hoverClass} disabled:opacity-50`}
              >
                <span className={`${theme.colors.text.muted} font-normal`}>[5]</span>
                <span className={theme.colors.text.muted}>{theme.symbols.cross}</span>
                EXIT TO TITLE
              </button>
            )}
          </div>

          {/* Keyboard hint — hidden on mobile */}
          <div className={`hidden md:block border-t ${theme.colors.interactive.border} px-6 py-3 ${theme.colors.bg.semiTransparent}`}>
            <p className={`text-center ${theme.colors.text.muted} text-xs ${theme.fonts.ui} uppercase tracking-widest`}>
              Press ESC to close
            </p>
          </div>

          {/* Close button (X) */}
          <Dialog.Close asChild>
            <button
              className={`absolute top-4 right-4 ${theme.colors.text.muted} ${theme.colors.text.primaryHover}
                         focus-visible:outline-none
                         transition-colors ${theme.fonts.ui} text-base`}
              aria-label="Close menu"
            >
              {theme.symbols.closeButton}
            </button>
          </Dialog.Close>
            </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}