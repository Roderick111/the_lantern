/**
 * WitnessInterview Component
 *
 * Main witness interrogation interface with a dual-pane layout:
 * - Left Pane: Conversation history and input
 * - Right Pane: Witness profile, trust meter, and quick actions
 *
 * Uses strict TerminalPanel styling with formalized character colors.
 *
 * @module components/WitnessInterview
 * @since Phase 2 (Refactored Phase 5.3.1)
 */

import React, { useState, useCallback, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { renderInlineMarkdown } from "../utils/renderInlineMarkdown";
import { stripTrustTags } from "../hooks/useWitnessInterrogation";
import type {
  WitnessInfo,
  WitnessConversationItem,
} from "../types/investigation";
import { generateAsciiBar } from "../styles/terminal-theme";
import { useTheme } from "../context/useTheme";
import { backdropVariants, contentVariants, reducedMotionVariants } from "../utils/modalAnimations";

// ============================================
// Types
// ============================================

interface WitnessInterviewProps {
  /** Currently selected witness */
  witness: WitnessInfo;
  /** Conversation history */
  conversation: WitnessConversationItem[];
  /** Current trust level (0-100) */
  trust: number;
  /** Secrets revealed in current session */
  secretsRevealed: string[];
  /** Available evidence to present */
  discoveredEvidence: { id: string; name: string }[];
  /** Loading state */
  loading: boolean;
  /** Slow-provider warning state */
  slowWarning?: boolean;
  /** Error message */
  error: string | null;
  /** Callback when player asks a question */
  onAskQuestion: (question: string) => Promise<void>;
  /** Callback when player presents evidence */
  onPresentEvidence: (
    evidenceId: string,
    evidenceName: string,
  ) => Promise<void>;
  onRetryFailed?: (item: WitnessConversationItem) => Promise<void>;
  onDismissFailed?: () => void;
  /** Callback to clear error */
  onClearError?: () => void;
}

// ============================================
// Sub-components
// ============================================

interface TrustMeterProps {
  trust: number;
}

function TrustMeter({ trust }: TrustMeterProps) {
  const { theme } = useTheme();
  return (
    <div className={theme.components.trustMeter.wrapper}>
      <div className={theme.components.trustMeter.container}>
        <span className={theme.components.trustMeter.label}>TRUST LEVEL:</span>
        <span className={theme.components.trustMeter.getColor(trust)}>
          {generateAsciiBar(trust, 12)} {trust}%
        </span>
      </div>
    </div>
  );
}

/**
 * Portrait image component with convention-based auto-loading.
 * Loads portraits from /portraits/{witnessId}.{avif,webp,png}
 * Uses modern formats with automatic fallback.
 * Falls back to placeholder if image doesn't exist.
 */
interface PortraitImageProps {
  witnessId: string;
  witnessName: string;
  onOpenFullscreen?: () => void;
  onImageResolved?: (src: string) => void;
}

function PortraitImage({ witnessId, witnessName, onOpenFullscreen, onImageResolved }: PortraitImageProps) {
  const { theme } = useTheme();
  const [hasError, setHasError] = React.useState(false);
  const [imgSrc, setImgSrc] = React.useState<string | null>(null);

  // Try formats in order: AVIF → WebP → PNG
  React.useEffect(() => {
    setHasError(false);
    setImgSrc(null);

    const formats = ["avif", "webp", "png"];
    let cancelled = false;

    const tryFormat = async (index: number) => {
      if (cancelled || index >= formats.length) {
        if (!cancelled && index >= formats.length) {
          setHasError(true);
        }
        return;
      }

      const url = `/portraits/${witnessId}.${formats[index]}`;

      try {
        const response = await fetch(url, { method: "HEAD" });
        const contentType = response.headers.get("Content-Type") ?? "";
        // Check both response.ok AND that Content-Type is an image
        // (Vite returns 200 with text/html for missing files)
        if (!cancelled && response.ok && contentType.startsWith("image/")) {
          setImgSrc(url);
          onImageResolved?.(url);
          return;
        }
      } catch {
        // Format not available, try next
      }

      if (!cancelled) {
        void tryFormat(index + 1);
      }
    };

    void tryFormat(0);

    return () => {
      cancelled = true;
    };
  }, [onImageResolved, witnessId]);

  if (hasError) {
    return (
      <div
        className={`w-full h-full flex items-center justify-center ${theme.colors.bg.primary}`}
      >
        <span
          className={`text-3xl ${theme.colors.text.muted} ${theme.fonts.ui}`}
        >
          ?
        </span>
      </div>
    );
  }

  if (!imgSrc) {
    return (
      <div
        className={`w-full h-full flex items-center justify-center ${theme.colors.bg.primary}`}
      >
        <span
          className={`text-xl ${theme.colors.text.muted} ${theme.fonts.ui} animate-pulse`}
        >
          ...
        </span>
      </div>
    );
  }

  const imageContent = (
    <div className="w-full h-full overflow-hidden relative">
      <img
        src={imgSrc}
        alt={witnessName}
        className="w-full h-full object-cover transition-all duration-500"
        onError={() => setHasError(true)}
      />
      {/* Scanline overlay */}
      <div className={`absolute inset-0 ${theme.effects.scanlines}`}></div>
    </div>
  );

  if (onOpenFullscreen) {
    return (
      <button
        type="button"
        onClick={onOpenFullscreen}
        className="w-full h-full cursor-zoom-in focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-current"
        aria-label={`View ${witnessName} portrait fullscreen`}
      >
        {imageContent}
      </button>
    );
  }

  return imageContent;
}

function PortraitFullscreenModal({
  isOpen,
  onClose,
  imageSrc,
  witnessName,
}: {
  isOpen: boolean;
  onClose: () => void;
  imageSrc: string | null;
  witnessName: string;
}) {
  const { theme, isDark } = useTheme();
  const prefersReducedMotion = useReducedMotion();
  const motionBackdrop = prefersReducedMotion ? reducedMotionVariants : backdropVariants;
  const motionContent = prefersReducedMotion ? reducedMotionVariants : contentVariants;

  const handleEscape = useCallback((event: KeyboardEvent) => {
    if (event.key === "Escape" && isOpen) onClose();
  }, [isOpen, onClose]);

  useEffect(() => {
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [handleEscape]);

  useEffect(() => {
    if (!isOpen) return;
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
    };
  }, [isOpen]);

  if (!imageSrc) return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="portrait-modal-backdrop"
          className="fixed inset-0 z-[60] bg-black/20 backdrop-blur-[4px] flex items-center justify-center p-4 md:p-8"
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-labelledby="portrait-modal-title"
          variants={motionBackdrop}
          initial="initial"
          animate="animate"
          exit="exit"
        >
          <motion.div
            className={`relative w-[min(80vw,72vh)] h-[min(80vw,72vh)] ${theme.colors.bg.primary} border ${theme.colors.border.default} shadow-2xl cursor-pointer lg:cursor-default`}
            onClick={(event) => {
              if (window.innerWidth < 1024) onClose();
              else event.stopPropagation();
            }}
            variants={motionContent}
          >
            <h2 id="portrait-modal-title" className="sr-only">{witnessName} portrait</h2>
            <button
              type="button"
              onClick={onClose}
              className={`absolute -top-10 right-0 z-10 min-w-[44px] min-h-[44px] px-2 flex items-center justify-end ${isDark ? `${theme.colors.text.tertiary} ${theme.colors.text.primaryHover}` : "text-black hover:text-black"} ${theme.fonts.ui} text-sm font-bold uppercase tracking-wider transition-colors`}
              aria-label="Close portrait fullscreen"
            >
              <span className="hidden md:inline">[ESC] </span>CLOSE
            </button>
            <div className={`w-full h-full bg-black border ${theme.colors.border.default} p-[1px] shadow-lg relative`}>
              <div className={theme.effects.cornerBrackets.topLeft}></div>
              <div className={theme.effects.cornerBrackets.topRight}></div>
              <div className={theme.effects.cornerBrackets.bottomLeft}></div>
              <div className={theme.effects.cornerBrackets.bottomRight}></div>
              <img src={imageSrc} alt={witnessName} className="w-full h-full object-contain" />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

interface ConversationBubbleProps {
  item: WitnessConversationItem;
  witnessName: string;
}

function ConversationBubble({ item, witnessName, onRetry, onDismiss }: ConversationBubbleProps & {
  onRetry?: (item: WitnessConversationItem) => void;
  onDismiss?: () => void;
}) {
  const { theme } = useTheme();
  const charTheme = theme.colors.character;
  const msgTheme = theme.components.message.witness;

  return (
    <div className={`space-y-4 ${theme.animation.fadeIn}`}>
      {/* Player message (right-aligned) */}
      <div className="flex justify-end group">
        <div className={msgTheme.wrapperPlayer}>
          <div>
            <span
              className={`${msgTheme.label} ${charTheme.detective.prefix} mb-1 block`}
            >
              {theme.speakers.detective.prefix} {theme.speakers.detective.label}
            </span>
            <span className={`${msgTheme.text} ${theme.colors.text.secondary}`}>
              "{item.question}"
            </span>
          </div>
        </div>
      </div>

      {/* Witness message (left-aligned) */}
      <div className="flex justify-start">
        <div className={msgTheme.wrapperWitness}>
          <div className="flex justify-between items-baseline mb-1">
            <span className={`${msgTheme.label} ${charTheme.witness.prefix}`}>
              {theme.speakers.witness.format(witnessName)}
            </span>
            {item.trust_delta !== undefined && item.trust_delta !== 0 && (
              <span
                className={`text-xs ml-2 ${item.trust_delta > 0 ? theme.colors.state.success.text : theme.colors.state.error.text}`}
              >
                [{item.trust_delta > 0 ? "+" : ""}
                {item.trust_delta}]
              </span>
            )}
          </div>
          <p className={msgTheme.text}>{renderInlineMarkdown(stripTrustTags(item.response))}</p>
          {item.failure && (
            <div className="mt-3 flex items-center gap-2 text-xs">
              <span className={theme.colors.state.error.text}>{item.failure.message}</span>
              {item.failure.retryable && item.requestId && onRetry && (
                <button type="button" className={theme.components.button.terminalAction} onClick={() => onRetry(item)}>
                  RETRY
                </button>
              )}
              {onDismiss && (
                <button type="button" className={theme.components.button.terminalAction} onClick={onDismiss}>
                  DISMISS
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface SecretRevealedToastProps {
  secrets: string[];
}

function formatSecretName(id: string): string {
  return id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function SecretRevealedToast({ secrets }: SecretRevealedToastProps) {
  const { theme } = useTheme();
  if (secrets.length === 0) return null;
  const sysTheme = theme.colors.character.system;

  return (
    <div className={`${theme.animation.fadeIn}`}>
      <div className={`border-t border-b ${sysTheme.border} py-3 px-4`}>
        <p
          className={`text-center text-xs ${sysTheme.prefix} font-bold uppercase tracking-[0.25em] mb-2 opacity-70`}
        >
          Discovered Secrets
        </p>
        <div className="space-y-1">
          {secrets.map((secret) => (
            <p
              key={secret}
              className={`text-center text-sm ${sysTheme.text} ${theme.fonts.narrative} italic`}
            >
              {formatSecretName(secret)}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function WitnessInterview({
  witness,
  conversation,
  trust,
  secretsRevealed,
  discoveredEvidence,
  loading,
  slowWarning = false,
  error,
  onAskQuestion,
  onPresentEvidence,
  onRetryFailed,
  onDismissFailed,
  onClearError,
}: WitnessInterviewProps) {
  const { theme } = useTheme();
  const [inputValue, setInputValue] = useState("");
  const [showEvidenceMenu, setShowEvidenceMenu] = useState(false);
  const [showMobileProfile, setShowMobileProfile] = useState(false);
  const [showPortraitFullscreen, setShowPortraitFullscreen] = useState(false);
  const [portraitImageSrc, setPortraitImageSrc] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const historyEndRef = useRef<HTMLDivElement>(null);
  const historyContainerRef = useRef<HTMLDivElement>(null);

  // Lock body scroll when mobile profile modal is open (html + body for iOS Safari)
  useEffect(() => {
    if (!showMobileProfile) return;
    const prevBody = document.body.style.overflow;
    const prevHtml = document.documentElement.style.overflow;
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevBody;
      document.documentElement.style.overflow = prevHtml;
    };
  }, [showMobileProfile]);

  // Auto-scroll to latest message (including during streaming)
  useEffect(() => {
    if (historyContainerRef.current) {
      historyContainerRef.current.scrollTo({
        top: historyContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [conversation]);

  // Handle question submission
  const handleSubmit = useCallback(async () => {
    const trimmedInput = inputValue.trim();
    if (!trimmedInput || loading) return;

    setInputValue("");
    try {
      await onAskQuestion(trimmedInput);
    } catch (err) {
      // Error handling is managed by parent component via error prop
      // Re-throw to allow parent to catch if needed, or log silently
      console.error("[WitnessInterview] Failed to submit question:", err);
    }
    inputRef.current?.focus();
  }, [inputValue, loading, onAskQuestion]);

  // Handle keyboard submit (Enter to submit, Shift+Enter for newline)
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey && !loading) {
        e.preventDefault();
        void handleSubmit();
      }
    },
    [handleSubmit, loading],
  );

  // Handle evidence presentation
  const handlePresentEvidence = useCallback(
    async (evidenceId: string) => {
      setShowEvidenceMenu(false);
      const ev = discoveredEvidence.find((e) => e.id === evidenceId);
      try {
        await onPresentEvidence(evidenceId, ev?.name ?? evidenceId);
      } catch (err) {
        // Error handling is managed by parent component via error prop
        console.error("[WitnessInterview] Failed to present evidence:", err);
      }
    },
    [onPresentEvidence, discoveredEvidence],
  );

  return (
    <div
      className={`${theme.fonts.ui} ${theme.colors.text.secondary} flex flex-col md:flex-row h-full gap-0 ${theme.colors.bg.primary} w-full shadow-lg`}
    >
      {/* LEFT PANE: Chat Interface */}
      <div
        className={`flex-1 flex flex-col min-w-0 min-h-0 md:border-r ${theme.colors.border.default} ${theme.colors.bg.primary} relative overflow-hidden`}
      >
        {/* Mobile Chat Header — avatar + name, tap to open profile */}
        <button
          type="button"
          onClick={() => setShowMobileProfile(true)}
          className={`md:hidden flex items-center gap-3 px-4 py-3 border-b ${theme.colors.border.default} ${theme.colors.bg.semiTransparent} active:opacity-80 transition-opacity`}
        >
          <div className={`w-12 h-12 shrink-0 rounded-full overflow-hidden border-2 ${theme.colors.border.default}`}>
            <PortraitImage witnessId={witness.id} witnessName={witness.name} />
          </div>
          <div className="flex-1 min-w-0 text-left">
            <span className={`${theme.typography.header} text-sm tracking-[0.15em] block truncate`}>
              {witness.name}
            </span>
            <span className={`text-sm ${theme.components.trustMeter.getColor(trust)}`}>
              Trust: {trust}%
            </span>
          </div>
          <span className={`text-xs ${theme.colors.text.muted} ${theme.fonts.ui} uppercase`}>Profile &rsaquo;</span>
        </button>

        {/* Conversation History */}
        <div
          ref={historyContainerRef}
          className={`flex-1 min-h-0 overflow-y-auto p-3 md:p-6 space-y-8 scrollbar-thin ${theme.colors.bg.primary}`}
        >
          {conversation.length === 0 ? (
            <div
              className={`h-full flex flex-col items-center justify-center ${theme.colors.text.muted} space-y-4`}
            >
              <span className="text-4xl font-bold opacity-10">
                {theme.symbols.blockFilled}
              </span>
              <div className="text-center">
                <p
                  className={`text-sm ${theme.fonts.narrative} italic opacity-50 mb-1`}
                >
                  The quill hovers above blank parchment, waiting...
                </p>
                <p
                  className={`text-sm ${theme.colors.text.separator} ${theme.fonts.narrative} italic`}
                >
                  Ask your first question to begin the interrogation.
                </p>
              </div>
            </div>
          ) : (
            <>
              {conversation.map((item, index) => (
                <ConversationBubble
                  key={`${item.timestamp}-${index}`}
                  item={item}
                  witnessName={witness.name}
                  onRetry={onRetryFailed ? (failedItem) => { void onRetryFailed(failedItem); } : undefined}
                  onDismiss={onDismissFailed}
                />
              ))}
              <div ref={historyEndRef} />
            </>
          )}
        </div>

        {/* Secrets Toast - above input area */}
        <SecretRevealedToast secrets={secretsRevealed} />

        {/* Error Display - above input area */}
        {error && (
          <div
            className={`mx-4 mb-2 p-2 border ${theme.colors.state.error.border} ${theme.colors.state.error.bgLight} flex justify-between items-center ${theme.animation.fadeIn}`}
          >
            <span
              className={`${theme.colors.state.error.text} text-xs ${theme.fonts.ui} uppercase`}
            >
              <span className="font-bold">{theme.messages.error("")}</span>
              {error}
            </span>
            {onClearError && (
              <button
                onClick={onClearError}
                className={`${theme.colors.state.error.text} hover:brightness-90 px-2 font-bold text-xs`}
              >
                DISMISS
              </button>
            )}
          </div>
        )}

        {/* Input Area - Docked to bottom */}
        <div className="mt-auto pt-5 pb-5 px-4">
          {slowWarning && (
            <p className={`mb-2 text-center text-xs ${theme.colors.text.muted} ${theme.fonts.ui} uppercase tracking-wider`}>
              Still working — witness response is slow...
            </p>
          )}
          {/* Mobile Present Evidence button */}
          <div className="md:hidden mb-2 relative">
            <button
              onClick={() => setShowEvidenceMenu(!showEvidenceMenu)}
              disabled={loading || discoveredEvidence.length === 0}
              className={`w-full py-2.5 px-4 flex items-center justify-between border transition-all duration-200 ${theme.fonts.ui} text-xs uppercase tracking-widest
                ${
                  showEvidenceMenu
                    ? `${theme.colors.bg.hover} ${theme.colors.border.hover} ${theme.colors.text.primary} shadow-lg`
                    : `${theme.colors.bg.primary} ${theme.colors.border.default} ${theme.colors.text.tertiary} ${theme.colors.interactive.borderHover} ${theme.colors.interactive.hover}`
                }
                disabled:opacity-50 disabled:cursor-not-allowed active:opacity-80`}
            >
              <span className="font-bold flex items-center gap-2">
                {theme.symbols.current} PRESENT EVIDENCE
              </span>
              <span
                className={`${theme.colors.bg.semiTransparent} px-2 py-0.5 text-xs border ${theme.colors.border.default} ${theme.colors.text.muted}`}
              >
                {discoveredEvidence.length.toString().padStart(2, "0")}
              </span>
            </button>
            {/* Mobile Dropup Menu */}
            {showEvidenceMenu && (
              <div
                className={`absolute bottom-full left-0 right-0 mb-2 ${theme.colors.bg.primary} border ${theme.colors.border.default} shadow-xl z-20 max-h-60 overflow-y-auto ${theme.animation.slideUp}`}
              >
                <div
                  className={`sticky top-0 ${theme.colors.bg.hover} p-2 border-b ${theme.colors.border.default} text-xs ${theme.colors.text.secondary} uppercase tracking-widest text-center font-bold`}
                >
                  SELECT EVIDENCE ITEM
                </div>
                {discoveredEvidence.map((ev) => (
                  <button
                    key={ev.id}
                    onClick={() => void handlePresentEvidence(ev.id)}
                    disabled={loading}
                    className={`w-full px-4 py-3 text-left text-xs ${theme.fonts.ui} ${theme.colors.text.tertiary} ${theme.colors.bg.primary} ${theme.colors.bg.hoverClass} ${theme.colors.interactive.hover} border-b ${theme.colors.border.default} last:border-0 transition-colors uppercase tracking-wider flex items-center gap-3 active:opacity-80`}
                  >
                    <span className={`${theme.colors.text.muted} text-xs`}>{theme.symbols.bullet}</span>
                    {ev.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className={theme.components.input.wrapper}>
            <div className={theme.components.input.prefix}>
              {theme.symbols.inputPrefix}
            </div>
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`What would you like to ask ${witness.name.split(" ")[0]}?`}
              rows={2}
              disabled={loading}
              className={`${theme.components.input.field} ${theme.components.input.borderDefault} pr-20`}
            />
            <button
              onClick={() => void handleSubmit()}
              disabled={loading || !inputValue.trim()}
              className={theme.components.input.sendButton}
            >
              SEND
            </button>
          </div>
        </div>
      </div>
      {/* Mobile Profile Modal */}
      {showMobileProfile && (
        <div className="md:hidden fixed inset-0 z-50 flex items-end justify-center">
          <div
            className={`absolute inset-0 ${theme.components.modal.overlayStyle}`}
            onClick={() => setShowMobileProfile(false)}
          />
          <div className={`relative w-full max-h-[85dvh] overflow-y-auto ${theme.colors.bg.primary} border-t ${theme.colors.border.default} rounded-t-xl shadow-2xl animate-slide-up`}>
            {/* Close handle */}
            <div className="flex justify-center pt-2 pb-1">
              <div className={`w-10 h-1 rounded-full ${theme.colors.bg.hover}`} />
            </div>
            {/* Profile content */}
            <div className="p-4 flex flex-col items-center">
              <div className={`w-32 h-32 mb-3 ${theme.colors.bg.primary} border ${theme.colors.border.default} p-[1px] shadow-lg relative`}>
                <div className={theme.effects.cornerBrackets.topLeft}></div>
                <div className={theme.effects.cornerBrackets.topRight}></div>
                <div className={theme.effects.cornerBrackets.bottomLeft}></div>
                <div className={theme.effects.cornerBrackets.bottomRight}></div>
                <PortraitImage
                  witnessId={witness.id}
                  witnessName={witness.name}
                  onOpenFullscreen={() => setShowPortraitFullscreen(true)}
                  onImageResolved={setPortraitImageSrc}
                />
              </div>
              <h2 className={`${theme.typography.header} tracking-[0.2em] mb-1`}>{witness.name}</h2>
              <TrustMeter trust={trust} />
            </div>
            {witness.personality && (
              <div className="px-4 pb-2">
                <p className={`text-sm ${theme.colors.text.muted} leading-relaxed ${theme.fonts.ui} italic text-justify`}>
                  &ldquo;{witness.personality}&rdquo;
                </p>
              </div>
            )}
            {/* Actions */}
            <div className="px-4 pb-4">
              <div className={theme.components.sectionSeparator.wrapper}>
                <div className={theme.components.sectionSeparator.line}></div>
                <span className={theme.components.sectionSeparator.label}>ACTIONS</span>
                <div className={theme.components.sectionSeparator.line}></div>
              </div>
              <button
                onClick={() => setShowMobileProfile(false)}
                className={`w-full py-3 px-4 mt-2 border rounded-sm ${theme.fonts.ui} text-sm font-bold uppercase tracking-wider ${theme.colors.bg.hover} ${theme.colors.border.default} ${theme.colors.text.primary} active:opacity-80 transition-all`}
              >
                Back to Conversation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RIGHT PANE: Profile & Actions — desktop only */}
      <div
        className={`hidden md:flex w-full md:w-[320px] lg:w-[380px] ${theme.colors.bg.primary} flex-col`}
      >
        {/* Profile Header */}
        <div
          className={`p-3 md:p-6 flex flex-col items-center ${theme.colors.bg.semiTransparent} border-b ${theme.colors.border.default}`}
        >
          {/* Portrait using standardized styles */}
          <div
            className={`w-32 h-32 md:w-48 md:h-48 mb-3 ${theme.colors.bg.primary} border ${theme.colors.border.default} p-[1px] shadow-lg relative group`}
          >
            {/* Corner brackets decoration */}
            <div className={theme.effects.cornerBrackets.topLeft}></div>
            <div className={theme.effects.cornerBrackets.topRight}></div>
            <div className={theme.effects.cornerBrackets.bottomLeft}></div>
            <div className={theme.effects.cornerBrackets.bottomRight}></div>

            {/* Portrait - auto-generated from witness ID */}
            <PortraitImage
              witnessId={witness.id}
              witnessName={witness.name}
              onOpenFullscreen={() => setShowPortraitFullscreen(true)}
              onImageResolved={setPortraitImageSrc}
            />
          </div>

          <h2 className={`${theme.typography.header} tracking-[0.2em] mb-1`}>
            {witness.name}
          </h2>

          <TrustMeter trust={trust} />
        </div>

        {/* Personality - Simple text, no box */}
        <div className="flex-1 p-4 overflow-y-auto">
          {witness.personality && (
            <p
              className={`text-sm ${theme.colors.text.muted} leading-relaxed ${theme.fonts.ui} italic text-justify`}
            >
              "{witness.personality}"
            </p>
          )}
        </div>

        {/* Footer Actions - Single container for bottom alignment */}
        <div className="mt-auto pt-5">
          {/* ACTIONS Header */}
          <div className="px-4">
            <div className={theme.components.sectionSeparator.wrapper}>
              <div className={theme.components.sectionSeparator.line}></div>
              <span className={theme.components.sectionSeparator.label}>
                ACTIONS
              </span>
              <div className={theme.components.sectionSeparator.line}></div>
            </div>
          </div>

          {/* Button - extra bottom padding to bottom-align with taller textarea */}
          <div className="pb-9 px-4">
            <div className="relative">
              <button
                onClick={() => setShowEvidenceMenu(!showEvidenceMenu)}
                disabled={loading || discoveredEvidence.length === 0}
                className={`w-full py-3 px-4 flex items-center justify-between border transition-all duration-200 ${theme.fonts.ui} text-xs uppercase tracking-widest group
                  ${
                    showEvidenceMenu
                      ? `${theme.colors.bg.hover} ${theme.colors.border.hover} ${theme.colors.text.primary} shadow-lg transform -translate-y-px`
                      : `${theme.colors.bg.primary} ${theme.colors.border.default} ${theme.colors.text.tertiary} ${theme.colors.interactive.borderHover} ${theme.colors.interactive.hover} hover:brightness-90`
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <span className="font-bold flex items-center gap-2">
                  {theme.symbols.current} PRESENT EVIDENCE
                </span>
                <span
                  className={`${theme.colors.bg.semiTransparent} px-2 py-0.5 text-xs border ${theme.colors.border.default} transition-colors ${theme.colors.text.muted}`}
                >
                  {discoveredEvidence.length.toString().padStart(2, "0")}
                </span>
              </button>

              {/* Dropup Menu */}
              {showEvidenceMenu && (
                <div
                  className={`absolute bottom-full left-0 right-0 mb-2 ${theme.colors.bg.primary} border ${theme.colors.border.default} shadow-xl z-20 max-h-60 overflow-y-auto ${theme.animation.slideUp}`}
                >
                  <div
                    className={`sticky top-0 ${theme.colors.bg.hover} p-2 border-b ${theme.colors.border.default} text-xs ${theme.colors.text.secondary} uppercase tracking-widest text-center font-bold`}
                  >
                    SELECT EVIDENCE ITEM
                  </div>
                  {discoveredEvidence.map((ev) => (
                    <button
                      key={ev.id}
                      onClick={() => void handlePresentEvidence(ev.id)}
                      disabled={loading}
                      className={`w-full px-4 py-3 text-left text-xs ${theme.fonts.ui} ${theme.colors.text.tertiary} ${theme.colors.bg.primary} ${theme.colors.bg.hoverClass} ${theme.colors.interactive.hover} border-b ${theme.colors.border.default} last:border-0 transition-colors uppercase tracking-wider flex items-center gap-3 group`}
                    >
                      <span
                        className={`${theme.colors.text.muted} ${theme.colors.interactive.hover} text-xs transition-colors`}
                      >
                        {theme.symbols.bullet}
                      </span>
                      {ev.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>{" "}
      {/* Close mt-auto wrapper */}
      <PortraitFullscreenModal
        isOpen={showPortraitFullscreen}
        onClose={() => setShowPortraitFullscreen(false)}
        imageSrc={portraitImageSrc}
        witnessName={witness.name}
      />
    </div>
  );
}
