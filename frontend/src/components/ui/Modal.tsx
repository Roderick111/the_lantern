import React, { useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useTheme } from '../../context/useTheme';
import { backdropVariants, contentVariants, reducedMotionVariants } from '../../utils/modalAnimations';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  title?: string;
  /** Terminal variant for dark theme */
  variant?: 'default' | 'terminal';
  /** Optional max-width class override (default: max-w-4xl) */
  maxWidth?: string;
  /** Whether to remove default padding from content area */
  noPadding?: boolean;
  /** Whether to hide the default header bar */
  hideHeader?: boolean;
  /** Whether to remove the default window frame (border, bg, shadow) */
  frameless?: boolean;
}

export function Modal({
  isOpen,
  onClose,
  children,
  title,
  variant = 'default',
  maxWidth = 'max-w-4xl',
  noPadding = false,
  hideHeader = false,
  frameless = false,
}: ModalProps) {
  const { theme } = useTheme();
  const prefersReducedMotion = useReducedMotion();

  // ESC key listener for modal close
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  // Lock body scroll when modal is open (both html + body for iOS Safari)
  useEffect(() => {
    if (!isOpen) return;
    const prevBody = document.body.style.overflow;
    const prevHtml = document.documentElement.style.overflow;
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevBody;
      document.documentElement.style.overflow = prevHtml;
    };
  }, [isOpen]);

  const isTerminal = variant === 'terminal';
  const motionContent = prefersReducedMotion ? reducedMotionVariants : contentVariants;
  const motionBackdrop = prefersReducedMotion ? reducedMotionVariants : backdropVariants;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="modal-container"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial="initial"
          animate="animate"
          exit="exit"
        >
          {/* Backdrop */}
          <motion.div
            className={`absolute inset-0 ${theme.components.modal.overlayStyle}`}
            onClick={onClose}
            aria-hidden="true"
            variants={motionBackdrop}
          />

          {/* Modal content */}
          <motion.div
            className={`relative ${maxWidth} w-full max-h-[calc(100dvh-2rem)] md:max-h-[90vh] overflow-hidden ${frameless
              ? '' // Frameless: No border/bg/shadow
              : `rounded-lg shadow-xl border ${theme.colors.bg.primary} ${theme.colors.border.default}`
              }`}
            role="dialog"
            aria-modal="true"
            aria-labelledby={title ? 'modal-title' : undefined}
            variants={motionContent}
          >
            {/* Header */}
            {!hideHeader && (
              <div
                className={`sticky top-0 px-4 md:px-6 py-3 border-b flex items-center justify-between ${theme.colors.bg.primary} ${theme.colors.border.default}`}
              >
                {title && (
                  <h2
                    id="modal-title"
                    className={`${theme.fonts.ui} font-bold uppercase tracking-widest ${isTerminal
                      ? `${theme.colors.text.primary} text-sm`
                      : `${theme.colors.interactive.text} text-xl`
                      }`}
                  >
                    {title}
                  </h2>
                )}
                <button
                  onClick={onClose}
                  className={`${theme.fonts.ui} transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center ${isTerminal
                    ? `${theme.colors.text.muted} ${theme.colors.text.primaryHover} text-sm`
                    : `${theme.colors.interactive.text} ${theme.colors.interactive.hover} text-2xl`
                    }`}
                  aria-label="Close modal"
                >
                  {isTerminal ? '[X]' : <>&times;</>}
                </button>
              </div>
            )}

            {/* Body */}
            <div className={`${noPadding ? 'p-0 h-[calc(100dvh-6rem)] md:h-[calc(90vh-60px)]' : 'p-4 md:p-6 max-h-[calc(100dvh-6rem)] md:max-h-[calc(90vh-60px)]'} ${theme.fonts.ui} ${theme.colors.text.secondary} overflow-y-auto`}>
              {children}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
