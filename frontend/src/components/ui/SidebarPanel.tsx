/**
 * SidebarPanel Component
 *
 * Displays location thumbnail image (click to expand) and navigation buttons
 * for Witnesses, Evidence, and Spell Book in the sidebar.
 *
 * @module components/ui/SidebarPanel
 */

import { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useTheme } from '../../context/useTheme';
import { backdropVariants, contentVariants, reducedMotionVariants } from '../../utils/modalAnimations';
import { Modal } from './Modal';
import { LocationIllustrationImage } from "../LocationHeaderBar";

// ============================================
// Types
// ============================================

interface SidebarPanelProps {
  locationId: string;
  locationName: string;
  witnessCount: number;
  evidenceCount: number;
  onOpenWitnesses: () => void;
  onOpenEvidence: () => void;
  onOpenHandbook: () => void;
  hintsEnabled?: boolean;
}

// ============================================
// Image Fullscreen Modal (restored from LocationHeaderBar)
// ============================================

function ImageModal({
  isOpen,
  onClose,
  locationId,
  locationName,
}: {
  isOpen: boolean;
  onClose: () => void;
  locationId: string;
  locationName: string;
}) {
  const { theme } = useTheme();

  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape" && isOpen) onClose();
  }, [isOpen, onClose]);

  useEffect(() => {
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [handleEscape]);

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

  const prefersReducedMotion = useReducedMotion();
  const motionBackdrop = prefersReducedMotion ? reducedMotionVariants : backdropVariants;
  const motionContent = prefersReducedMotion ? reducedMotionVariants : contentVariants;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="image-modal-backdrop"
          className={`${theme.components.modal.overlay} flex items-center justify-center p-4 md:p-8`}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-labelledby="illustration-modal-title"
          variants={motionBackdrop}
          initial="initial"
          animate="animate"
          exit="exit"
        >
          <motion.div
            className={`relative w-[calc(100vw-2rem)] md:w-[80vw] h-[calc(100dvh-2rem)] md:h-[90vh] ${theme.colors.bg.primary} border ${theme.colors.border.default} shadow-2xl cursor-pointer lg:cursor-default`}
            onClick={(e) => {
              // On mobile: tap image to close. On desktop: only close via backdrop/button.
              if (window.innerWidth < 1024) { onClose(); } else { e.stopPropagation(); }
            }}
            variants={motionContent}
          >
        <button
          onClick={onClose}
          className={`absolute -top-10 right-0 min-w-[44px] min-h-[44px] flex items-center justify-end ${theme.colors.text.tertiary} ${theme.colors.text.primaryHover} ${theme.fonts.ui} text-sm uppercase tracking-wider transition-colors`}
        >
          <span className="hidden md:inline">[ESC] </span>CLOSE
        </button>

        <div
          className={`w-full h-full bg-black border ${theme.colors.border.default} p-[1px] shadow-lg relative group`}
        >
          <div className={theme.effects.cornerBrackets.topLeft}></div>
          <div className={theme.effects.cornerBrackets.topRight}></div>
          <div className={theme.effects.cornerBrackets.bottomLeft}></div>
          <div className={theme.effects.cornerBrackets.bottomRight}></div>

          <LocationIllustrationImage
            locationId={locationId}
            locationName={locationName}
            lazy={true}
            priority={false}
          />
        </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

// ============================================
// Quick Help Sub-components
// ============================================

function QuickHelpContent() {
  const { theme } = useTheme();
  return (
    <ul className={`${theme.colors.text.muted} text-sm ${theme.fonts.ui} space-y-1`}>
      <li>{theme.symbols.bullet} Type actions in the text box below</li>
      <li>{theme.symbols.bullet} Start with <span className={theme.colors.character.matthew.label}>Matthew,</span> to consult your spirit companion</li>
      <li>{theme.symbols.bullet} Interview witnesses and collect evidence</li>
      <li>{theme.symbols.bullet} Perform rites from the Lantern Compendium</li>
      <li>{theme.symbols.bullet} Adjust narrator style in Settings</li>
    </ul>
  );
}

function QuickHelpButton() {
  const { theme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className={`lg:hidden ${theme.components.button.terminalAction} !py-2 !px-3 !text-xs w-full justify-center`}
        type="button"
      >
        <span className={`${theme.colors.text.muted} font-bold`}>{theme.symbols.bullet}</span>
        QUICK HELP
      </button>
      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="QUICK HELP" variant="terminal" maxWidth="max-w-sm">
        <QuickHelpContent />
      </Modal>
    </>
  );
}

// ============================================
// Component
// ============================================

export function SidebarPanel({
  locationId,
  locationName,
  witnessCount,
  evidenceCount,
  onOpenWitnesses,
  onOpenEvidence,
  onOpenHandbook,
  hintsEnabled = true,
}: SidebarPanelProps) {
  const { theme } = useTheme();
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Keyboard shortcuts: 5=Witnesses, 6=Evidence, 7=Spell Book
  const handleKeydown = useCallback(
    (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) return;
      if (document.querySelector('[role="dialog"]')) return;

      if (e.key === '5') { e.preventDefault(); onOpenWitnesses(); }
      else if (e.key === '6') { e.preventDefault(); onOpenEvidence(); }
      else if (e.key === '7') { e.preventDefault(); onOpenHandbook(); }
    },
    [onOpenWitnesses, onOpenEvidence, onOpenHandbook],
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeydown);
    return () => document.removeEventListener('keydown', handleKeydown);
  }, [handleKeydown]);

  return (
    <>
      <div className="space-y-3">
        {/* Location Image Thumbnail — click to expand */}
        <button
          onClick={() => setIsModalOpen(true)}
          className={`w-full aspect-[16/9] bg-black border ${theme.colors.border.default} p-[1px] shadow-lg relative group cursor-pointer ${theme.colors.interactive.borderHover} transition-colors overflow-hidden`}
          type="button"
          aria-label="View location illustration fullscreen"
        >
          <div className={theme.effects.cornerBrackets.topLeft}></div>
          <div className={theme.effects.cornerBrackets.topRight}></div>
          <div className={theme.effects.cornerBrackets.bottomLeft}></div>
          <div className={theme.effects.cornerBrackets.bottomRight}></div>

          <LocationIllustrationImage
            locationId={locationId}
            locationName={locationName}
            lazy={false}
            priority={true}
          />
        </button>

        {/* Navigation Buttons — horizontal on mobile, vertical on desktop */}
        <div className="flex flex-row lg:flex-col gap-2">
          <button
            onClick={onOpenWitnesses}
            className={`${theme.components.button.terminalAction} flex-1 lg:flex-none !py-2 !px-2.5 !gap-1.5 !text-xs lg:!py-2.5 lg:!px-4 lg:!gap-3`}
            type="button"
          >
            <span className={`${theme.colors.text.muted} font-bold`}>
              {theme.symbols.bullet}
            </span>
            <span className="lg:hidden">WITNESSES</span>
            <span className="hidden lg:inline">WITNESSES ({witnessCount})</span>
            <span className={`hidden lg:inline ${theme.colors.text.separator} text-xs ml-auto`}>[5]</span>
          </button>

          <button
            onClick={onOpenEvidence}
            className={`${theme.components.button.terminalAction} flex-1 lg:flex-none !py-2 !px-2.5 !gap-1.5 !text-xs lg:!py-2.5 lg:!px-4 lg:!gap-3`}
            type="button"
          >
            <span className={`${theme.colors.text.muted} font-bold`}>
              {theme.symbols.bullet}
            </span>
            <span className="lg:hidden">EVIDENCE</span>
            <span className="hidden lg:inline">EVIDENCE ({evidenceCount})</span>
            <span className={`hidden lg:inline ${theme.colors.text.separator} text-xs ml-auto`}>[6]</span>
          </button>

          <button
            onClick={onOpenHandbook}
            className={`${theme.components.button.terminalAction} ${theme.colors.interactive.borderHover} flex-1 lg:flex-none !py-2 !px-2.5 !gap-1.5 !text-xs lg:!py-2.5 lg:!px-4 lg:!gap-3`}
            type="button"
          >
            <span className={`${theme.colors.character.system.prefix} font-bold`}>
              {theme.symbols.bullet}
            </span>
            <span className="lg:hidden">RITES</span>
            <span className="hidden lg:inline">COMPENDIUM</span>
            <span className={`hidden lg:inline ${theme.colors.text.separator} text-xs ml-auto`}>[7]</span>
          </button>
        </div>

        {/* Quick Help — inline on desktop, button→modal on mobile */}
        {hintsEnabled && (
          <>
            {/* Desktop: inline help */}
            <div className={`hidden lg:block ${theme.colors.bg.semiTransparent} rounded p-3 space-y-2`}>
              <p className={`${theme.colors.text.tertiary} text-sm ${theme.fonts.ui} uppercase tracking-wider font-bold`}>
                Quick Help
              </p>
              <QuickHelpContent />
            </div>
            {/* Mobile: button to open modal */}
            <QuickHelpButton />
          </>
        )}
      </div>

      {/* Fullscreen Image Modal */}
      <ImageModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        locationId={locationId}
        locationName={locationName}
      />
    </>
  );
}
