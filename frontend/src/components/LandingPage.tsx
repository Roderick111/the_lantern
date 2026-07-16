/**
 * LandingPage Component
 *
 * First-visit onboarding above a two-pane terminal case selector.
 * Minimal B&W aesthetic, scalable to multiple cases.
 *
 * Phase 5.4: Dynamic case loading from backend API.
 *
 * Keyboard shortcuts:
 * - 1-9: Select case by number
 * - Enter: Start selected case
 * - L: Load Game
 *
 * @module components/LandingPage
 * @since Phase 5.3.1
 */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCases, resetCase } from '../api/client';
import { useTheme } from '../context/useTheme';
import type { CaseMetadata, ApiCaseMetadata } from '../types/investigation';

// ============================================
// Types
// ============================================

export interface LandingPageProps {
  /** Callback when player clicks Load Game */
  onLoadGame: () => void;
  /** Callback when player opens general settings */
  onOpenSettings?: () => void;
  /** Disable landing keyboard shortcuts while a modal is open */
  shortcutsEnabled?: boolean;
  /** Apply browser-wide preferences before starting a fresh case */
  onPrepareStartCase?: (caseId: string) => Promise<void>;
}

// ============================================
// Helpers
// ============================================

/**
 * Map backend difficulty to frontend display format
 */
function mapDifficulty(
  backendDifficulty: 'beginner' | 'intermediate' | 'advanced'
): 'Easy' | 'Medium' | 'Hard' {
  const mapping: Record<string, 'Easy' | 'Medium' | 'Hard'> = {
    beginner: 'Easy',
    intermediate: 'Medium',
    advanced: 'Hard',
  };
  return mapping[backendDifficulty] ?? 'Medium';
}

/**
 * Transform backend case metadata to frontend format
 */
function transformCase(apiCase: ApiCaseMetadata): CaseMetadata {
  return {
    id: apiCase.id,
    name: apiCase.title,
    difficulty: mapDifficulty(apiCase.difficulty),
    // Only case_001 is playable for now; others show as "Coming Soon"
    status: apiCase.id === 'case_001' ? 'unlocked' : 'locked',
    description: apiCase.description || 'No description available.',
  };
}

// ============================================
// Component
// ============================================

export function LandingPage({ onLoadGame, onOpenSettings, shortcutsEnabled = true, onPrepareStartCase }: LandingPageProps) {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [showOnboarding, setShowOnboarding] = useState(
    () => localStorage.getItem('lantern-onboarding-seen') !== 'true',
  );

  // Dynamic case state (Phase 5.4)
  const [cases, setCases] = useState<CaseMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected case (default to first)
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selectedCase = cases[selectedIndex];

  // Fetch cases from backend on mount
  const fetchCases = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getCases();

      // Transform backend format to frontend format
      const transformedCases = response.cases.map(transformCase);
      setCases(transformedCases);

      // Log warnings if some cases failed to load
      if (response.errors && response.errors.length > 0) {
        console.warn('Some cases failed to load:', response.errors);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load cases';
      setError(message);
      console.error('Case loading error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchCases();
  }, [fetchCases]);

  // Start case handler — always reset so "Start Case" is a fresh investigation
  const handleStartCase = useCallback(async (caseId: string) => {
    await resetCase(caseId).catch(() => undefined);
    await onPrepareStartCase?.(caseId);
    void navigate(`/case/${caseId}`);
  }, [navigate, onPrepareStartCase]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!shortcutsEnabled) return;
      // Ignore if user is typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      // Arrow Up / W: Previous case
      if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : cases.length - 1));
      }
      // Arrow Down / S: Next case
      else if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev < cases.length - 1 ? prev + 1 : 0));
      }
      // Number keys 1-9: Select case
      else if (e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        const index = parseInt(e.key) - 1;
        if (index < cases.length) {
          setSelectedIndex(index);
        }
      }
      // Enter: Start selected case
      else if (e.key === 'Enter') {
        e.preventDefault();
        if (selectedCase?.status === 'unlocked') {
          void handleStartCase(selectedCase.id);
        }
      }
      // L: Load game
      else if (e.key === 'l' || e.key === 'L') {
        e.preventDefault();
        onLoadGame();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleStartCase, onLoadGame, cases, selectedCase, selectedIndex, shortcutsEnabled]);

  // ============================================
  // Loading State
  // ============================================
  if (loading) {
    return (
      <div className={`min-h-screen ${theme.colors.bg.primary} ${theme.colors.text.secondary} flex flex-col items-center justify-center p-8`}>
        <div className="text-center">
          <h1 className={`text-4xl font-bold ${theme.colors.text.primary} ${theme.fonts.ui} tracking-widest mb-1`}>
            THE LANTERN
          </h1>
          <p className={`${theme.colors.text.muted} text-sm ${theme.fonts.ui} mb-8`}>
            Case Investigation System v1.0
          </p>
          <p className={`${theme.colors.text.tertiary} text-sm ${theme.fonts.ui} animate-pulse`}>
            {theme.symbols.block} Loading cases...
          </p>
        </div>
      </div>
    );
  }

  // ============================================
  // Error State
  // ============================================
  if (error) {
    return (
      <div className={`min-h-screen ${theme.colors.bg.primary} ${theme.colors.text.secondary} flex flex-col items-center justify-center p-8`}>
        <div className="text-center max-w-md">
          <h1 className={`text-4xl font-bold ${theme.colors.text.primary} ${theme.fonts.ui} tracking-widest mb-1`}>
            THE LANTERN
          </h1>
          <p className={`${theme.colors.text.muted} text-sm ${theme.fonts.ui} mb-8`}>
            Case Investigation System v1.0
          </p>
          <p className={`${theme.colors.state.error.text} text-sm ${theme.fonts.ui} mb-4`}>
            {theme.symbols.warning} {error}
          </p>
          <button
            onClick={() => void fetchCases()}
            className={`px-4 py-2 ${theme.colors.bg.hover} ${theme.colors.text.primary} ${theme.fonts.ui} text-sm border ${theme.colors.border.default} ${theme.colors.interactive.borderHover} ${theme.colors.interactive.hover} transition-colors uppercase tracking-wider`}
          >
            {theme.symbols.doubleArrowRight} RETRY
          </button>
        </div>
      </div>
    );
  }

  // ============================================
  // Empty State
  // ============================================
  if (cases.length === 0) {
    return (
      <div className={`min-h-screen ${theme.colors.bg.primary} ${theme.colors.text.secondary} flex flex-col items-center justify-center p-8`}>
        <div className="text-center">
          <h1 className={`text-4xl font-bold ${theme.colors.text.primary} ${theme.fonts.ui} tracking-widest mb-1`}>
            THE LANTERN
          </h1>
          <p className={`${theme.colors.text.muted} text-sm ${theme.fonts.ui} mb-8`}>
            Case Investigation System v1.0
          </p>
          <p className={`${theme.colors.text.tertiary} text-sm ${theme.fonts.ui} mb-4`}>
            {theme.symbols.bullet} No cases available.
          </p>
          <p className={`${theme.colors.text.separator} text-sm ${theme.fonts.ui}`}>
            Add case files to backend/src/case_store/ to get started.
          </p>
        </div>
      </div>
    );
  }

  // ============================================
  // Main Render
  // ============================================
  return (
    <div className={`relative min-h-screen ${theme.colors.bg.primary} ${theme.colors.text.secondary} flex flex-col items-center justify-start xl:justify-center p-4 md:p-8`}>
      {onOpenSettings && (
        <button
          onClick={onOpenSettings}
          className={`absolute top-4 right-4 md:top-8 md:right-8 z-10 flex items-center gap-2 ${theme.colors.text.tertiary} ${theme.colors.text.primaryHover} ${theme.fonts.ui} text-xs md:text-sm transition-colors`}
          type="button"
          aria-label="Open settings"
          title="Settings"
        >
          <span>Settings</span>
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
      )}
      {/* Title */}
      <div className="w-full max-w-5xl text-center mb-4 md:mb-8">
        <h1 className={`text-2xl md:text-4xl font-bold ${theme.colors.text.primary} ${theme.fonts.ui} tracking-widest mb-1`}>
          THE LANTERN
        </h1>
        <p className={`${theme.colors.text.muted} text-sm ${theme.fonts.ui}`}>
          Case Investigation System v1.0
        </p>
        {!showOnboarding && (
          <button
            onClick={() => setShowOnboarding(true)}
            className={`mt-3 ${theme.colors.interactive.text} ${theme.colors.interactive.hover} ${theme.fonts.ui} text-sm font-bold uppercase tracking-wider transition-colors`}
            type="button"
          >
            What is The Lantern?
          </button>
        )}
      </div>

      {showOnboarding && (
        <section className={`relative max-w-5xl w-full border ${theme.colors.border.default} mb-4 md:mb-6`} aria-labelledby="onboarding-title">
          <button
            onClick={() => {
              localStorage.setItem('lantern-onboarding-seen', 'true');
              setShowOnboarding(false);
            }}
            className={`absolute top-3 right-4 z-10 ${theme.colors.text.muted} ${theme.colors.text.primaryHover} ${theme.fonts.ui} text-sm`}
            type="button"
            aria-label="Close onboarding"
          >
            [X]
          </button>
          <div className={`grid grid-cols-1 md:grid-cols-2 ${theme.colors.bg.primary}`}>
            <div className={`p-4 md:p-6 md:border-r ${theme.colors.border.default}`}>
              <h2 id="onboarding-title" className={`${theme.typography.header} font-bold mb-3 pr-8`}>
                Your own way through mysteries
              </h2>
              <p className={`${theme.typography.bodySm} leading-relaxed mb-4 md:mb-6`}>
                You are a novice inspector in an old occult academy. Describe what you do in natural language, and the world responds.
              </p>
              <ol className={`${theme.typography.bodySm} leading-relaxed list-decimal pl-5 space-y-2`}>
                <li>Interrogate suspects and uncover their secrets.</li>
                <li>Investigate every room to find evidence.</li>
                <li>Piece together what happened.</li>
              </ol>
            </div>
            <div className="p-4 md:p-6 flex flex-col justify-center">
              <div className="space-y-3 md:space-y-4 md:px-2">
                <p className={`${theme.components.message.witness.label} ${theme.colors.character.detective.prefix} mb-3`}>
                  {theme.symbols.inputPrefix} INSPECTOR
                </p>
                <p className={`${theme.typography.bodySm} leading-relaxed mb-3`}>
                  “I kneel beside the locked window and hold the Lantern over the dust.”
                </p>
                <div className={`border-t ${theme.colors.border.default} pt-4`}>
                  <p className={`${theme.components.message.witness.label} ${theme.colors.character.narrator.text} mb-2`}>NARRATOR</p>
                  <p className={`${theme.typography.bodySm} leading-relaxed`}>
                    “Light gathers in a thin trail across the floorboards. Someone crossed here after midnight.”
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Two-Pane Layout */}
      <div className={`max-w-5xl w-full border ${theme.colors.border.default} ${theme.colors.bg.primary}`}>
        {/* Header — hidden on mobile (content is self-explanatory when stacked) */}
        <div className={`hidden md:grid md:grid-cols-2 border-b ${theme.colors.border.default}`}>
          <div className={`px-4 py-2 md:border-r ${theme.colors.border.default}`}>
            <h2 className={`text-sm font-bold ${theme.colors.text.primary} ${theme.fonts.ui} uppercase tracking-wider`}>
              {theme.symbols.block} Available Cases
            </h2>
          </div>
          <div className="px-4 py-2">
            <h2 className={`text-sm font-bold ${theme.colors.text.primary} ${theme.fonts.ui} uppercase tracking-wider`}>
              {theme.symbols.block} Case Details
            </h2>
          </div>
        </div>

        {/* Content Panes */}
        <div className="grid grid-cols-1 md:grid-cols-2 min-h-0 md:min-h-[400px]">
          {/* Left Pane: Case List */}
          <div className={`border-b md:border-b-0 md:border-r ${theme.colors.border.default}`}>
            {cases.map((caseItem, index) => {
              const isSelected = index === selectedIndex;
              const isLocked = caseItem.status === 'locked';
              const caseNumber = String(index + 1).padStart(3, '0');

              return (
                <button
                  key={caseItem.id}
                  onClick={() => setSelectedIndex(index)}
                  className={`w-full text-left px-4 ${theme.fonts.ui} text-sm transition-colors border-b ${theme.colors.border.default} min-h-[72px] flex items-center active:opacity-90 ${
                    isSelected
                      ? `${theme.colors.bg.hover} border-l-2 ${theme.colors.interactive.border}`
                      : `${theme.colors.bg.hoverClass}`
                  }`}
                >
                  <div className="flex items-start leading-tight">
                    <span className={isSelected ? `${theme.colors.interactive.text} w-4 flex-shrink-0` : `${theme.colors.text.separator} w-4 flex-shrink-0`}>
                      {isSelected ? theme.symbols.current : theme.symbols.other}
                    </span>
                    <div className="flex-1">
                      <div className={`leading-tight ${isSelected ? `${theme.colors.text.primary} font-bold` : isLocked ? theme.colors.text.separator : theme.colors.text.tertiary}`}>
                        {caseNumber}. {caseItem.name}
                      </div>
                      <div className={`text-xs mt-1 leading-tight ${isSelected ? theme.colors.text.tertiary : theme.colors.text.separator}`}>
                        {isLocked ? 'Coming Soon' : caseItem.difficulty}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right Pane: Case Details */}
          <div className="p-6 flex flex-col">
            {selectedCase ? (
              <>
                <div className="flex items-baseline justify-between gap-4 mb-4">
                  <h3 className={`text-sm font-bold ${theme.colors.text.primary} ${theme.fonts.ui} uppercase tracking-wider`}>
                    {theme.symbols.prefix} {selectedCase.name}
                  </h3>
                  <span className={`text-sm ${theme.fonts.ui} ${theme.colors.text.muted} whitespace-nowrap`}>
                    {selectedCase.status === 'unlocked' ? 'Available' : 'Coming Soon'}
                  </span>
                </div>
                <p className={`${theme.colors.text.tertiary} text-sm ${theme.fonts.narrative} leading-relaxed mb-6 flex-1`}>
                  {selectedCase.description}
                </p>
                <div className={`text-sm ${theme.fonts.ui} ${theme.colors.text.muted} mb-6`}>
                  {theme.symbols.bullet} Difficulty: {selectedCase.difficulty}
                </div>
                <div className={`border-t ${theme.colors.border.default} pt-6 mt-6`}>
                  <button
                    onClick={() => void handleStartCase(selectedCase.id)}
                    disabled={selectedCase.status === 'locked'}
                    className={`w-full py-2 ${theme.fonts.ui} text-sm text-left font-bold transition-colors uppercase tracking-wider ${
                      selectedCase.status === 'locked'
                        ? theme.colors.text.separator
                        : `${theme.colors.interactive.text} ${theme.colors.interactive.hover}`
                    } disabled:cursor-not-allowed`}
                  >
                    {selectedCase.status === 'locked'
                      ? `${theme.symbols.doubleArrowRight} COMING SOON`
                      : `${theme.symbols.doubleArrowRight} [ENTER] START CASE`}
                  </button>
                </div>
              </>
            ) : (
              <div className={`${theme.colors.text.separator} text-sm ${theme.fonts.ui}`}>
                No case selected
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className={`border-t ${theme.colors.border.default} p-4`}>
          <button
            onClick={onLoadGame}
            className={`w-full py-2 ${theme.fonts.ui} text-sm text-left font-bold ${theme.colors.interactive.text} ${theme.colors.interactive.hover} transition-colors uppercase tracking-wider`}
          >
            {theme.symbols.doubleArrowRight} [L] LOAD GAME
          </button>
        </div>
      </div>

      {/* Keyboard Hint — hidden on mobile */}
      <p className={`hidden md:block text-center ${theme.colors.text.separator} text-sm ${theme.fonts.ui} mt-4`}>
        {theme.symbols.arrowUp}{theme.symbols.arrowDown} or W/S: Navigate {theme.symbols.bullet} 1-9: Select Case {theme.symbols.bullet} Enter: Start {theme.symbols.bullet} L: Load Game
      </p>
    </div>
  );
}
