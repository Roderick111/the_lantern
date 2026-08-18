/**
 * LocationView Component
 *
 * Main investigation interface with terminal UI aesthetic.
 * Displays location description, freeform input for player actions,
 * conversation history, and LLM narrator responses.
 *
 * @module components/LocationView
 * @since Phase 1
 */

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { Card } from "./ui/Card";
import { investigateStream, isApiError } from "../api/client";
import type { StreamFailure } from "../api/base";
import { logEvent } from "../api/telemetry";
import { LanternCompendium } from "./LanternCompendium";
import { renderInlineMarkdown } from "../utils/renderInlineMarkdown";
import {
  MATTHEW_QUICK_PROMPT,
  MATVEY_QUICK_PROMPT,
  isMatthewMessage,
  stripMatthewPrefix,
} from "../utils/matthewInput";
import { useTheme } from '../context/useTheme';
import type {
  LocationResponse,
  ConversationItem,
  Message,
  SaveSlotName,
} from "../types/investigation";

// ============================================
// Evidence Tag Helpers
// ============================================

const EVIDENCE_TAG_CAPTURE_RE = /\[EVIDENCE(?::\s*|_)([a-z0-9_]+)\s*\]/gi;
const RITE_CONTROL_MARKER_RE = /\s*\[(?:EVIDENCE[^\]]*|NO_EVIDENCE)\]/gi;
/** Matches a partial rite control marker building up during streaming. */
const RITE_CONTROL_PARTIAL_RE = /\s*\[(?:E[A-Z_: ]*|N[A-Z_]*)?$/i;

/** Strip valid, malformed, and partial rite control markers from player-visible text. */
function stripEvidenceTags(text: string): string {
  return text
    .replace(RITE_CONTROL_MARKER_RE, '')
    .replace(RITE_CONTROL_PARTIAL_RE, '')
    .trimEnd();
}

/** Extract evidence IDs from response text */
function extractEvidenceIds(text: string): string[] {
  const ids: string[] = [];
  for (const match of text.matchAll(EVIDENCE_TAG_CAPTURE_RE)) {
    ids.push(match[1].trim());
  }
  return ids;
}

// ============================================
// Message Types for Unified Rendering
// ============================================

/**
 * Unified message type for chronological rendering
 * Combines history items and inline messages into single sorted array
 */
interface UnifiedMessage {
  /** Unique key for React */
  key: string;
  /** Message type for rendering */
  type: "player" | "narrator" | "matthew_ghost" | "evidence";
  /** Message text */
  text: string;
  /** Timestamp for sorting */
  timestamp: number;
  /** Evidence IDs (for evidence type) */
  evidenceIds?: string[];
  /** Evidence ID → display name map */
  evidenceNames?: Record<string, string>;
  /** Matthew's tone (for matthew_ghost type) */
  tone?: "helpful" | "misleading";
  itemId?: string;
  status?: ConversationItem["status"];
  failure?: StreamFailure;
}

// ============================================
// Types
// ============================================

interface WitnessPresent {
  /** Witness ID */
  id: string;
  /** Witness name */
  name: string;
}

interface LocationViewProps {
  /** Current case ID */
  caseId: string;
  /** Current location ID */
  locationId: string;
  /** Location data from API */
  locationData: LocationResponse | null;
  /** Callback when new evidence is discovered */
  onEvidenceDiscovered: (evidenceIds: string[]) => void;
  /** Already discovered evidence (to prevent showing alerts for known evidence) */
  discoveredEvidence?: string[];
  /** Witnesses present at this location (unused - reserved for future feature) */
  _witnessesPresent?: WitnessPresent[];
  /** Callback when witness is clicked for interview (unused - reserved for future feature) */
  _onWitnessClick?: (witnessId: string) => void;
  /** Inline messages (player, narrator, matthew_ghost) for conversation feed */
  inlineMessages?: Message[];
  /** Callback when player sends message to the companion (Matthew/Матвей prefix). */
  onMatthewMessage?: (message: string) => void;
  /** Whether Matthew is currently processing a response */
  matthewLoading?: boolean;
  /** Whether to show the location header (name, description) - Phase 6.5 */
  showLocationHeader?: boolean;
  /** Player ID for API calls */
  playerId?: string;
  /** Whether to show hints/quick actions (default: true) */
  hintsEnabled?: boolean;
  /** Whether this is the first/starting location (shows quick action buttons) */
  isFirstLocation?: boolean;
  /** Trigger counter to open handbook from external source */
  handbookTrigger?: number;
  /** Callback when evidence notification is clicked */
  onEvidenceClick?: (evidenceId: string) => void;
  /** Callback when backend detects a natural language location change */
  onLocationChanged?: (locationId: string) => void;
  /** Save slot (defaults to "autosave") */
  slot?: SaveSlotName;
  /** Content language, used for localized quick actions. */
  language?: string;

}

// ============================================
// Constants
// ============================================

/** Maximum number of history items to display */
const MAX_HISTORY_LENGTH = 5;

// ============================================
// Component
// ============================================

export function LocationView({
  caseId,
  locationId,
  locationData,
  onEvidenceDiscovered,
  discoveredEvidence = [],
  inlineMessages = [],
  onMatthewMessage,
  matthewLoading = false,
  showLocationHeader = true,
  playerId: _playerId = 'default',
  hintsEnabled = true,
  isFirstLocation = false,
  handbookTrigger,
  onEvidenceClick,
  onLocationChanged,
  slot = 'autosave',
  language = 'en',

}: LocationViewProps) {
  // Theme hook for dynamic styling
  const { theme } = useTheme();

  // State
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slowWarning, setSlowWarning] = useState(false);
  const [history, setHistory] = useState<ConversationItem[]>([]);
  const [isHandbookOpen, setIsHandbookOpen] = useState(false);

  // Refs
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const historyEndRef = useRef<HTMLDivElement>(null);
  const historyContainerRef = useRef<HTMLDivElement>(null);
  // AbortController for in-flight investigate stream — aborted on unmount or
  // location change so user-initiated navigation doesn't keep burning LLM tokens.
  const streamControllerRef = useRef<AbortController | null>(null);
  const watchdogRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const pendingTextRef = useRef("");
  const frameRef = useRef<number | null>(null);

  const clearWatchdog = useCallback(() => {
    watchdogRef.current.forEach(clearTimeout);
    watchdogRef.current = [];
    setSlowWarning(false);
  }, []);

  const flushPendingText = useCallback((itemId: string) => {
    if (!pendingTextRef.current) return;
    const text = pendingTextRef.current;
    pendingTextRef.current = "";
    setHistory((prev) => prev.map((item) =>
      item.id === itemId ? { ...item, response: item.response + text } : item,
    ));
  }, []);

  const scheduleTextFlush = useCallback((itemId: string) => {
    if (frameRef.current !== null) return;
    const flush = () => {
      frameRef.current = null;
      flushPendingText(itemId);
    };
    if (typeof window.requestAnimationFrame === 'function') {
      frameRef.current = window.requestAnimationFrame(flush);
    } else {
      frameRef.current = window.setTimeout(flush, 16);
    }
  }, [flushPendingText]);

  // ============================================
  // Unified Message Array
  // ============================================

  /**
   * Combine history items and inline messages into a single sorted array
   * This fixes the bug where Matthew messages stack at the bottom
   * Now: User -> Narrator -> Matthew -> User -> Narrator -> Matthew (chronological)
   */
  const unifiedMessages = useMemo((): UnifiedMessage[] => {
    const messages: UnifiedMessage[] = [];

    // Convert history items to unified messages
    history.forEach((item) => {
      const baseTimestamp = item.timestamp.getTime();

      // Player action
      messages.push({
        key: `history-player-${item.id}`,
        type: "player",
        text: item.action,
        timestamp: baseTimestamp,
      });

      // Narrator response (slightly after player)
      messages.push({
        key: `history-narrator-${item.id}`,
        type: "narrator",
        text: item.response,
        timestamp: baseTimestamp + 1,
        itemId: item.id,
        status: item.status,
        failure: item.failure,
      });

      // Evidence discovered (slightly after narrator)
      // Derive from response text if evidence_discovered is empty (e.g. after reload)
      const evidenceIds = item.evidence_discovered.length > 0
        ? item.evidence_discovered
        : extractEvidenceIds(item.response);
      if (evidenceIds.length > 0) {
        messages.push({
          key: `history-evidence-${item.id}`,
          type: "evidence",
          text: "",
          evidenceIds,
          evidenceNames: item.evidence_names,
          timestamp: baseTimestamp + 2,
        });
      }
    });

    // Convert inline messages to unified messages
    inlineMessages.forEach((msg, index) => {
      // Use message timestamp if available, otherwise estimate based on index
      const timestamp =
        msg.timestamp ?? Date.now() - (inlineMessages.length - index) * 100;

      if (msg.type === "player") {
        messages.push({
          key: `inline-player-${index}-${timestamp}`,
          type: "player",
          text: msg.text,
          timestamp,
        });
      } else if (msg.type === "narrator") {
        messages.push({
          key: `inline-narrator-${index}-${timestamp}`,
          type: "narrator",
          text: msg.text,
          timestamp,
        });
        // Derive evidence notifications from restored narrator text
        const inlineEvidenceIds = extractEvidenceIds(msg.text);
        if (inlineEvidenceIds.length > 0) {
          messages.push({
            key: `inline-evidence-${index}-${timestamp}`,
            type: "evidence",
            text: "",
            evidenceIds: inlineEvidenceIds,
            timestamp: timestamp + 1,
          });
        }
      } else if (msg.type === "matthew_ghost") {
        messages.push({
          key: `inline-matthew-${index}-${timestamp}`,
          type: "matthew_ghost",
          text: msg.text,
          tone: msg.tone,
          timestamp,
        });
      }
    });

    // Sort by timestamp (chronological order)
    return messages.sort((a, b) => a.timestamp - b.timestamp);
  }, [history, inlineMessages]);

  // Auto-scroll to latest response, but NOT on initial load of a location
  // We want users to see the location description first
  const prevMessagesLengthRef = useRef(0);
  const initialLoadRef = useRef(true);

  useEffect(() => {
    // If location changed, reset the tracking ref so we don't auto-scroll initially
    prevMessagesLengthRef.current = 0;
    initialLoadRef.current = true;
    // Abort any in-flight stream from the previous location.
    if (streamControllerRef.current) {
      logEvent('stream_intentional_abort', { endpoint: 'investigate_stream' });
      streamControllerRef.current.abort();
    }
    streamControllerRef.current = null;
    clearWatchdog();
    pendingTextRef.current = "";
    // Clear local history when selecting locations (Phase 5.6)
    setHistory([]);
    setIsLoading(false);
    // Scroll to top of page/component to show description
    window.scrollTo({ top: 0, behavior: "instant" });
    // Keep initial load flag for 500ms to cover batched state updates
    const timer = setTimeout(() => { initialLoadRef.current = false; }, 500);
    return () => clearTimeout(timer);
  }, [locationId, clearWatchdog]);

  // Abort any in-flight stream when component unmounts.
  useEffect(() => {
    return () => {
      if (streamControllerRef.current) {
        logEvent('stream_intentional_abort', { endpoint: 'investigate_stream' });
        streamControllerRef.current.abort();
      }
      streamControllerRef.current = null;
      clearWatchdog();
      if (frameRef.current !== null) window.cancelAnimationFrame(frameRef.current);
    };
  }, [clearWatchdog]);

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    const currentLength = unifiedMessages.length;
    const prevLength = prevMessagesLengthRef.current;

    if (currentLength > prevLength) {
      const behavior = initialLoadRef.current ? "instant" : "smooth";
      setTimeout(() => {
        window.scrollTo({
          top: document.documentElement.scrollHeight,
          behavior,
        });
      }, 0);
    }

    // Update ref for next render
    prevMessagesLengthRef.current = currentLength;
  }, [unifiedMessages, locationId]);

  // Auto-scroll during streaming (content growing in last message)
  useEffect(() => {
    if (!isLoading) return;
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: 'smooth',
    });
  }, [isLoading, history]);

  // Keyboard shortcut for Lantern Compendium (Cmd/Ctrl+H) - Phase 4.5
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "h") {
        e.preventDefault();
        setIsHandbookOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // External handbook trigger (from sidebar) — only open on increment, not on mount
  const prevHandbookTrigger = useRef(handbookTrigger);
  useEffect(() => {
    if (handbookTrigger !== prevHandbookTrigger.current && handbookTrigger && handbookTrigger > 0) {
      setIsHandbookOpen(true);
    }
    prevHandbookTrigger.current = handbookTrigger;
  }, [handbookTrigger]);

  const isMatthewInput = useCallback(
    (input: string): boolean => isMatthewMessage(input),
    [],
  );

  const stripMatthewInputPrefix = useCallback(
    (input: string): string => stripMatthewPrefix(input),
    [],
  );

  const runInvestigation = useCallback(async (
    itemId: string,
    action: string,
    requestId: string,
  ) => {
    setIsLoading(true);
    setError(null);
    setSlowWarning(false);
    clearWatchdog();
    pendingTextRef.current = "";
    setHistory((prev) => prev.map((item) => item.id === itemId
      ? { ...item, response: "", evidence_discovered: [], status: "streaming", failure: undefined }
      : item));

    streamControllerRef.current?.abort();
    const controller = new AbortController();
    streamControllerRef.current = controller;
    const markFailed = (failure: StreamFailure) => {
      flushPendingText(itemId);
      setHistory((prev) => prev.map((item) => item.id === itemId
        ? { ...item, status: "failed", failure }
        : item));
      setIsLoading(false);
      clearWatchdog();
    };
    const slowTimer = window.setTimeout(() => setSlowWarning(true), 20_000);
    const noTextTimer = window.setTimeout(() => {
      logEvent('stream_watchdog_timeout', { endpoint: 'investigate_stream', phase: 'no_visible_text', request_id: requestId });
      controller.abort();
      markFailed({ message: "No response yet. Try again.", code: "llm_timeout", retryable: true, partial: false, requestId });
    }, 90_000);
    watchdogRef.current.push(slowTimer, noTextTimer);

    try {
      await investigateStream(
        { player_input: action, case_id: caseId, location_id: locationId, slot, request_id: requestId },
        {
          onChunk: (text) => {
            if (watchdogRef.current.includes(noTextTimer)) {
              clearTimeout(noTextTimer);
              const partialTimer = window.setTimeout(() => {
                logEvent('stream_watchdog_timeout', { endpoint: 'investigate_stream', phase: 'partial', request_id: requestId });
                controller.abort();
                markFailed({ message: "Response stopped before completion. Try again.", code: "partial_stream", retryable: true, partial: true, requestId });
              }, 120_000);
              watchdogRef.current.push(partialTimer);
            }
            pendingTextRef.current += text;
            scheduleTextFlush(itemId);
          },
          onDone: (data) => {
            flushPendingText(itemId);
            const newEvidence = (data.new_evidence as string[] | undefined) ?? [];
            const evidenceNames = (data.evidence_names as Record<string, string> | undefined) ?? {};
            setHistory((prev) => prev.map((item) => item.id === itemId
              ? { ...item, status: "complete", evidence_discovered: newEvidence, evidence_names: evidenceNames }
              : item));
            const toReport = newEvidence.filter((id) => !discoveredEvidence.includes(id));
            if (toReport.length > 0) onEvidenceDiscovered(toReport);
            const locationChanged = data.location_changed as string | undefined;
            if (locationChanged && onLocationChanged) onLocationChanged(locationChanged);
            setIsLoading(false);
            clearWatchdog();
          },
          onError: (failure) => markFailed(failure),
        },
        controller.signal,
      );
    } catch (err) {
      if (controller.signal.aborted) return;
      markFailed({
        message: isApiError(err) ? err.message : "Connection failed — try again.",
        code: "llm_connection",
        retryable: true,
        partial: Boolean(pendingTextRef.current),
        requestId,
      });
    } finally {
      if (streamControllerRef.current === controller) streamControllerRef.current = null;
    }
  }, [caseId, clearWatchdog, discoveredEvidence, flushPendingText, locationId, onEvidenceDiscovered, onLocationChanged, scheduleTextFlush, slot]);

  // Handle form submission (routes to Matthew or narrator)
  const handleSubmit = useCallback(async () => {
    const trimmedInput = inputValue.trim();
    if (!trimmedInput) {
      setError("Please enter an action to investigate.");
      return;
    }
    if (isMatthewInput(trimmedInput) && onMatthewMessage) {
      const matthewMessage = stripMatthewInputPrefix(trimmedInput);
      if (matthewMessage) {
        onMatthewMessage(matthewMessage);
        setInputValue("");
        inputRef.current?.focus();
        return;
      }
    }
    const itemId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const requestId = typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : itemId;
    const streamingItem: ConversationItem = {
      id: itemId,
      action: trimmedInput,
      response: "",
      evidence_discovered: [],
      timestamp: new Date(),
      requestId,
      status: "streaming",
    };
    setHistory((prev) => prev.length < MAX_HISTORY_LENGTH
      ? [...prev, streamingItem] : [...prev.slice(1), streamingItem]);
    setInputValue("");
    inputRef.current?.focus();
    await runInvestigation(itemId, trimmedInput, requestId);
  }, [inputValue, isMatthewInput, onMatthewMessage, runInvestigation, stripMatthewInputPrefix]);

  const retryInvestigation = useCallback((itemId: string) => {
    const item = history.find((candidate) => candidate.id === itemId);
    if (!item?.requestId || isLoading) return;
    void runInvestigation(item.id, item.action, item.requestId);
  }, [history, isLoading, runInvestigation]);

  const dismissInvestigation = useCallback((itemId: string) => {
    setHistory((prev) => prev.filter((item) => item.id !== itemId));
  }, []);

  // Handle keyboard submit (Enter to submit, Shift+Enter for newline)
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey && !isLoading) {
        e.preventDefault();
        void handleSubmit();
      }
    },
    [handleSubmit, isLoading],
  );

  // Handle quick action shortcut - fills input without submitting
  const handleQuickAction = useCallback((text: string) => {
    setInputValue(text);
    inputRef.current?.focus();
  }, []);

  // Handle spell selection from handbook (Phase 5.7)
  const handleSpellSelect = useCallback((spellFormula: string) => {
    setInputValue(spellFormula);
    setIsHandbookOpen(false);
    inputRef.current?.focus();
  }, []);

  // Loading state for location data
  if (!locationData) {
    return (
      <Card className={theme.components.card.base}>
        <div className="flex items-center justify-center py-8">
          <div className={`${theme.animation.pulse} ${theme.colors.text.tertiary}`}>Loading location...</div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={theme.components.card.base}>
      {/* Location Header - Conditionally shown (Phase 6.5: moved to LocationHeaderBar) */}
      {showLocationHeader && (
        <>
          <div className="mb-0">
            <h2 className={theme.typography.header}>
              {locationData.name}
            </h2>
            <p className={`${theme.typography.bodySm} ${theme.colors.text.muted} mt-2 whitespace-normal leading-relaxed`}>
              {locationData.description}
            </p>
          </div>

          <div className={`border-t ${theme.colors.border.separator} mt-3 mb-6`}></div>
        </>
      )}

      {/* Conversation History - Unified Message Rendering (Phase 4.1) */}
        <div
          ref={historyContainerRef}
          className="space-y-5 mb-4"
        >
          {/* Location description as first narrator message (only when header is hidden) */}
          {!showLocationHeader && locationData.description && (
            <div className={theme.components.message.narrator.wrapper}>
              <div className={`${theme.components.message.narrator.text} space-y-3`}>
                {locationData.description.split('\n').filter(Boolean).map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </div>
            </div>
          )}

          {/* Render all messages in chronological order */}
          {unifiedMessages.map((message) => {
            // Player action
            if (message.type === "player") {
              return (
                <div
                  key={message.key}
                  className={theme.components.message.player.wrapper}
                >
                  <p className={theme.components.message.player.text}>
                    <span className={theme.components.message.player.prefix}>{theme.symbols.inputPrefix}</span> {message.text}
                  </p>
                </div>
              );
            }

            // Narrator response
            if (message.type === "narrator") {
              const cleanText = stripEvidenceTags(message.text);
              const paragraphs = cleanText.split('\n').filter(Boolean);
              return (
                <div
                  key={message.key}
                  className={theme.components.message.narrator.wrapper}
                >
                  <div className={`${theme.components.message.narrator.text} space-y-3`}>
                    {paragraphs.map((para, i) => (
                      <p key={i}>{renderInlineMarkdown(para)}</p>
                    ))}
                  </div>
                  {message.failure && (
                    <div className="mt-3 flex items-center gap-3 text-xs">
                      <span className={theme.colors.state.error.text}>{message.failure.message}</span>
                      {message.failure.retryable && message.itemId && (
                        <button
                          type="button"
                          className={theme.components.button.terminalAction}
                          onClick={() => retryInvestigation(message.itemId!)}
                        >
                          RETRY
                        </button>
                      )}
                      {message.itemId && (
                        <button
                          type="button"
                          className={theme.components.button.terminalAction}
                          onClick={() => dismissInvestigation(message.itemId!)}
                        >
                          DISMISS
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            }

            // Evidence discovered
            if (message.type === "evidence" && message.evidenceIds) {
              return (
                <div
                  key={message.key}
                  className={theme.components.message.evidence.wrapper}
                >
                  <div className="text-xs">
                    {message.evidenceIds.map((evidenceId) => {
                      const displayName = message.evidenceNames?.[evidenceId]
                        ?? evidenceId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                      return (
                        <button
                          key={evidenceId}
                          type="button"
                          onClick={() => onEvidenceClick?.(evidenceId)}
                          className={`${theme.components.message.evidence.tag} ${onEvidenceClick ? 'cursor-pointer hover:brightness-125 transition-all' : ''}`}
                        >
                          {theme.messages.evidenceDiscovered(displayName)}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            }

            // Matthew spirit companion message
            if (message.type === "matthew_ghost") {
              return (
                <div
                  key={message.key}
                  className={theme.components.message.matthew.wrapper}
                >
                  <p className={theme.components.message.matthew.text}>
                    <span className={theme.components.message.matthew.label}>{theme.speakers.matthew.prefix}</span>
                    {renderInlineMarkdown(message.text)}
                  </p>
                </div>
              );
            }

            return null;
          })}

          <div ref={historyEndRef} />
        </div>

      {/* Error Display */}
      {error && (
        <div className={`mb-4 p-3 ${theme.colors.state.error.bg} border ${theme.colors.state.error.border} rounded ${theme.colors.state.error.text} text-sm uppercase tracking-widest flex justify-between items-center`}>
          <span>
            <span className="font-bold">{theme.messages.error("")}</span>{error}
          </span>
        </div>
      )}

      {/* Input Area — sticky bottom */}
      <div className={`relative sticky bottom-0 z-20 space-y-3 pt-2 md:pt-4 pb-2 ${theme.colors.bg.primary}`}>
        {/* Fade gradient above input — dissolves content into input area */}
        <div className={`pointer-events-none absolute left-0 right-0 bottom-full h-8 bg-gradient-to-t ${theme.colors.gradient.fromBg} to-transparent`} />
        {/* Matthew target indicator */}
        {isMatthewInput(inputValue) && (
          <div className="flex items-center justify-end">
            <span className={`text-xs ${theme.colors.character.matthew.label} ${theme.fonts.ui} ${theme.animation.pulse} uppercase tracking-widest font-bold`}>
              {theme.messages.spiritResonance("MATTHEW")}
            </span>
          </div>
        )}

        {/* Input with witness-style absolute prefix and dynamic border */}
        <div className={theme.components.input.wrapper}>
          <div className={theme.components.input.prefix}>
            {theme.symbols.inputPrefix}
          </div>
          <textarea
            ref={inputRef}
            id="action-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="describe your action, or question..."
            rows={2}
            disabled={isLoading || matthewLoading}
            className={`${theme.components.input.field} md:min-h-[5rem]
                       ${isMatthewInput(inputValue)
                ? theme.components.input.borderSpecial
                : theme.components.input.borderDefault
              }`}
            aria-label="Enter your investigation action or address Matthew"
          />
          <button
            onClick={() => void handleSubmit()}
            disabled={isLoading || matthewLoading || !inputValue.trim()}
            className={theme.components.input.sendButton}
            title="Submit Action (Enter)"
            aria-label="Submit Action"
          >
            SEND
          </button>
        </div>

        {/* Quick Actions (shown when hints enabled) */}
        {hintsEnabled && isFirstLocation && (
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => handleQuickAction("examine the desk")}
              className={`${theme.components.button.terminalAction} !py-1.5 !px-2.5 !gap-1.5 !text-[10px] md:!py-2.5 md:!px-4 md:!gap-3 md:!text-xs`}
              type="button"
            >
              <span className={`${theme.colors.text.muted} ${theme.colors.interactive.hover} transition-colors font-bold`}>
                {theme.symbols.bullet}
              </span>
              EXAMINE DESK
            </button>
            <button
              onClick={() => handleQuickAction("check the window")}
              className={`${theme.components.button.terminalAction} !py-1.5 !px-2.5 !gap-1.5 !text-[10px] md:!py-2.5 md:!px-4 md:!gap-3 md:!text-xs`}
              type="button"
            >
              <span className={`${theme.colors.text.muted} ${theme.colors.interactive.hover} transition-colors font-bold`}>
                {theme.symbols.bullet}
              </span>
              CHECK WINDOW
            </button>
            <button
              onClick={() =>
                handleQuickAction(language === 'ru' ? MATVEY_QUICK_PROMPT : MATTHEW_QUICK_PROMPT)
              }
              className={`${theme.components.button.terminalAction} !py-1.5 !px-2.5 !gap-1.5 !text-[10px] md:!py-2.5 md:!px-4 md:!gap-3 md:!text-xs`}
              type="button"
            >
              <span className={`${theme.colors.character.matthew.prefix} ${theme.colors.interactive.hover} transition-colors font-bold`}>
                {theme.symbols.bullet}
              </span>
              {language === 'ru' ? 'СПРОСИТЬ МАТВЕЯ' : 'ASK MATTHEW'}
            </button>
          </div>
        )}

        {/* Loading indicators */}
        <div className={`${theme.typography.helper} uppercase text-right`}>
          {matthewLoading ? (
            <span className={`${theme.colors.character.matthew.label} ${theme.animation.pulse}`}>
              Spirit resonance...
            </span>
          ) : isLoading ? (
            <span className={`${theme.colors.text.tertiary} ${theme.animation.pulse}`}>
              {slowWarning ? 'Still working — provider is slow...' : 'Analyzing...'}
            </span>
          ) : null}
        </div>
      </div>

      {/* Lantern Compendium Modal (Phase 4.5) */}
      <LanternCompendium
        isOpen={isHandbookOpen}
        onClose={() => setIsHandbookOpen(false)}
        language={language === 'ru' ? 'ru' : 'en'}
        onSelectSpell={handleSpellSelect}
      />
    </Card>
  );
}
