/**
 * App Component
 *
 * Main application layout with URL-based routing.
 * `/` → LandingPage, `/case/:caseId` → Investigation game.
 *
 * Player ID resolution is lazy (inside React via usePlayerId hook) to avoid
 * top-level side effects on module import (e.g. during JSDOM tests).
 *
 * @module App
 * @since Phase 1, updated Phase 7 (URL routing)
 */

import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { Routes, Route, Navigate, useParams, useNavigate } from "react-router-dom";
import { LandingPage } from "./components/LandingPage";
import { LocationView } from "./components/LocationView";
import { EvidenceModal } from "./components/EvidenceModal";
import { WitnessInterview } from "./components/WitnessInterview";
import { VerdictSubmission } from "./components/VerdictSubmission";
import { MentorFeedback } from "./components/MentorFeedback";
import { ConfrontationDialogue } from "./components/ConfrontationDialogue";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { BriefingModal } from "./components/BriefingModal";
import { MainMenu } from "./components/MainMenu";
import { LocationHeaderBar } from "./components/LocationHeaderBar";
import { InvestigationLayout } from "./components/layout/InvestigationLayout";
import { SaveLoadModal } from "./components/SaveLoadModal";
import { SettingsModal } from "./components/SettingsModal";
import { MusicPlayer } from "./components/MusicPlayer";
import { SidebarPanel } from "./components/ui/SidebarPanel";
import { WitnessesModal } from "./components/WitnessesModal";
import { EvidenceListModal } from "./components/EvidenceListModal";
import { Modal } from "./components/ui/Modal";
import { Button } from "./components/ui/Button";
import { Toast } from "./components/ui/Toast";
import { useInvestigation } from "./hooks/useInvestigation";
import { useWitnessInterrogation } from "./hooks/useWitnessInterrogation";
import { useVerdictFlow } from "./hooks/useVerdictFlow";
import { useBriefing } from "./hooks/useBriefing";
import { useMatthewChat } from "./hooks/useMatthewChat";
import { useLocation } from "./hooks/useLocation";
import { useSaveSlots } from "./hooks/useSaveSlots";
import { useGameModals } from "./hooks/useGameModals";
import { useGameActions } from "./hooks/useGameActions";
import { useTheme } from "./context/useTheme";
import { logSessionStart } from "./api/telemetry";
import { usePlayerId } from "./utils/playerId";
import type { ChangeLocationResponse } from "./types/investigation";

// ============================================
// App (Router)
// ============================================

export default function App() {
  // Telemetry consent banner (auto-dismiss)
  const [showConsent, setShowConsent] = useState(
    () => !localStorage.getItem("telemetry_consent_shown"),
  );

  // B2: global-ish session toast via event (from api/base 401 handling)
  const [sessionToast, setSessionToast] = useState<string | null>(null);

  useEffect(() => {
    logSessionStart();
    if (showConsent) {
      const timer = setTimeout(() => {
        localStorage.setItem("telemetry_consent_shown", "1");
        setShowConsent(false);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for 401 session expiry events from base.ts
  useEffect(() => {
    const handler = (e: CustomEvent<{ message?: string }>) => {
      const detail = e.detail ?? {};
      const msg = detail.message ?? "Session expired — refreshing";
      setSessionToast(msg);
      setTimeout(() => setSessionToast(null), 2500);
    };
    window.addEventListener("lantern-session-expired", handler as EventListener);
    return () => window.removeEventListener("lantern-session-expired", handler as EventListener);
  }, []);

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingRoute />} />
        <Route path="/case/:caseId" element={<GameRoute />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {showConsent && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 text-amber-200/40 text-xs z-50 animate-pulse">
          Anonymous data collected to improve the game
        </div>
      )}

      {/* B2 session toast root level */}
      {sessionToast && (
        <Toast
          message={sessionToast}
          variant="info"
          onClose={() => setSessionToast(null)}
        />
      )}
    </>
  );
}

// ============================================
// Landing Route
// ============================================

function navigateWithTransition(nav: ReturnType<typeof useNavigate>, to: string) {
  if (document.startViewTransition) {
    document.startViewTransition(() => { void nav(to); });
  } else {
    void nav(to);
  }
}

function LandingRoute() {
  const navigate = useNavigate();
  const [loadModalOpen, setLoadModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastVariant, setToastVariant] = useState<"success" | "error" | "info">("success");

  // Lazy player ID resolution inside React (no top-level)
  const playerId = usePlayerId();

  // Default case for save slots listing on landing page
  const defaultCaseId = "case_001";

  const {
    slots,
    loading: saveSlotsLoading,
    error: saveSlotsError,
    loadFromSlot,
    refreshSlots,
  } = useSaveSlots(defaultCaseId, playerId);

  const handleLoadGameFromLanding = useCallback(() => {
    setLoadModalOpen(true);
    void refreshSlots();
  }, [refreshSlots]);

  const handleLoadFromSlot = useCallback(
    async (slot: string) => {
      const loadedState = await loadFromSlot(slot);
      if (loadedState) {
        setToastVariant("success");
        setToastMessage(`Loaded from ${slot.replace("_", " ")}`);
        setLoadModalOpen(false);
        navigateWithTransition(navigate, `/case/${loadedState.case_id}`);
      } else {
        setToastVariant("error");
        setToastMessage(saveSlotsError ?? "Load failed");
      }
    },
    [loadFromSlot, saveSlotsError, navigate],
  );

  return (
    <>
      <LandingPage onLoadGame={handleLoadGameFromLanding} />

      <SaveLoadModal
        isOpen={loadModalOpen}
        onClose={() => setLoadModalOpen(false)}
        mode="load"
        onSave={() => Promise.resolve()}
        onLoad={handleLoadFromSlot}
        slots={slots}
        loading={saveSlotsLoading}
        caseId={defaultCaseId}
        playerId={playerId}
        onImportSuccess={() => void refreshSlots()}
      />

      {toastMessage && (
        <Toast
          message={toastMessage}
          variant={toastVariant}
          onClose={() => setToastMessage(null)}
        />
      )}
    </>
  );
}

// ============================================
// Game Route
// ============================================

function GameRoute() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  // Lazy resolution (MUST be before any early return — rules of hooks)
  const playerId = usePlayerId();

  if (!caseId) {
    return <Navigate to="/" replace />;
  }

  return (
    <InvestigationView
      caseId={caseId}
      playerId={playerId}
      onExitToMainMenu={() => navigateWithTransition(navigate, "/")}
    />
  );
}

// ============================================
// Investigation View Component
// ============================================

interface InvestigationViewProps {
  caseId: string;
  playerId: string;
  onExitToMainMenu: () => void;
}

function InvestigationView({
  caseId,
  playerId,
  onExitToMainMenu,
}: InvestigationViewProps) {
  // Toast state
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastVariant, setToastVariant] = useState<"success" | "error" | "info">("success");
  const handleToastClose = useCallback(() => setToastMessage(null), []);

  // B3/B1: ref for cross-hook location change handler (to sync apply without circular hook init)
  const locationChangeHandlerRef = useRef<((id: string, resp: ChangeLocationResponse) => void) | null>(null);

  // Domain hooks
  // B1: pass slot to useLocation (was missing), B3: wire onChange via ref for apply
  const locationHook = useLocation({
    caseId,
    playerId,
    slot: "autosave",
    onLocationChange: (id, resp) => {
      locationChangeHandlerRef.current?.(id, resp);
    },
  });
  const { locations, currentLocationId, visitedLocations, loading: locationLoading, changing: locationChanging, error: locationError, handleLocationChange } = locationHook;

  const investigation = useInvestigation({ caseId, locationId: currentLocationId, playerId, slot: "autosave" });
  const { state, location, loading, error, clearError, setNarratorVerbosity, setLanguage, applyLocationChange } = investigation;

  // wire after both hooks defined (ref holds latest)
  locationChangeHandlerRef.current = (_id, resp) => {
    applyLocationChange(resp);
  };

  const witnessHook = useWitnessInterrogation({ caseId, playerId, autoLoad: true });
  const { state: witnessState, askQuestion, presentEvidenceToWitness } = witnessHook;

  const verdictHook = useVerdictFlow({ caseId, playerId });
  const { state: verdictState, submitVerdict, confirmConfrontation } = verdictHook;

  const briefingHook = useBriefing({ caseId, playerId });
  const { briefing, conversation: briefingConversation, selectedChoice: briefingSelectedChoice, choiceResponse: briefingChoiceResponse, loading: briefingLoading, selectChoice: selectBriefingChoice, resetChoice: resetBriefingChoice, askQuestion: askBriefingQuestion } = briefingHook;

  const matthewHook = useMatthewChat({ caseId, playerId });

  const saveSlots = useSaveSlots(caseId, playerId);
  const { slots, loading: saveSlotsLoading } = saveSlots;

  // Centralized modal state
  const modals = useGameModals();

  // Centralized action handlers
  const actions = useGameActions({
    caseId,
    playerId,
    modals,
    toast: { setToastMessage, setToastVariant },
    investigation: { state, handleEvidenceDiscovered: investigation.handleEvidenceDiscovered, restoredMessages: investigation.restoredMessages },
    witnesses: { selectWitness: witnessHook.selectWitness, clearConversation: witnessHook.clearConversation },
    verdict: { reset: verdictHook.reset, confirmConfrontation },
    briefing: { loadBriefing: briefingHook.loadBriefing, markComplete: briefingHook.markComplete },
    matthew: { checkAutoComment: matthewHook.checkAutoComment, sendMessage: matthewHook.sendMessage },
    saveSlots: { saveToSlot: saveSlots.saveToSlot, loadFromSlot: saveSlots.loadFromSlot, refreshSlots: saveSlots.refreshSlots, error: saveSlots.error },
  });

  // Derived data
  const suspects = useMemo(() => witnessState.witnesses.map((w) => ({ id: w.id, name: w.name })), [witnessState.witnesses]);
  const discoveredEvidenceWithNames = useMemo(() => (state?.discovered_evidence ?? []).map((id) => ({ id, name: id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) })), [state?.discovered_evidence]);

  // Theme
  const { theme } = useTheme();

  // B1: single source slot const (standardize autosave)
  const currentSlot = "autosave";

  return (
    <div className={`min-h-screen ${theme.colors.bg.primary} ${theme.colors.text.secondary}`}>
      {/* Background Music Player — always mounted to prevent track restart */}
      <MusicPlayer caseId={caseId} />

      {loading ? (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className={`animate-pulse ${theme.colors.text.secondary} ${theme.fonts.ui} text-xl mb-2`}>
              Initializing Investigation...
            </div>
            <div className={`${theme.colors.text.muted} text-sm ${theme.fonts.ui}`}>
              Loading case files...
            </div>
          </div>
        </div>
      ) : (
      <>

      {/* Full-width Header Bar — scrolls on mobile, sticky on desktop */}
      <header className={`w-full py-2 px-3 md:py-4 md:px-6 lg:sticky lg:top-0 z-30 ${theme.colors.bg.primary}`}>
        {/* Row 1: Logo + desktop location tabs + action buttons */}
        <div className="flex items-center justify-between lg:justify-start">
          {/* Logo — opens system menu */}
          <button
            onClick={() => modals.setMenuOpen(true)}
            className={`text-lg lg:text-xl font-bold ${theme.colors.text.primary} ${theme.fonts.ui} tracking-widest shrink-0 lg:mr-8 hover:opacity-80 active:opacity-70 transition-opacity cursor-pointer`}
            type="button"
            aria-label="Open system menu"
          >
            THE LANTERN
          </button>

          {/* Location Tabs — large screens only, fills center */}
          <div className="hidden lg:flex lg:justify-center flex-1 min-w-0">
            <LocationHeaderBar
              locations={locations}
              currentLocationId={currentLocationId}
              locationData={location}
              onSelectLocation={(id) => void handleLocationChange(id)}
              changing={locationChanging}
              visitedLocations={visitedLocations}
              loading={locationLoading}
              error={locationError}
            />
          </div>

          {/* Action Buttons — far right */}
          <div className="flex items-center gap-2 shrink-0 lg:ml-8">
            <button
              onClick={() => modals.setSettingsOpen(true)}
              className={`w-11 h-11 lg:w-10 lg:h-10 rounded-full ${theme.colors.bg.hover} ${theme.colors.text.tertiary} hover:${theme.colors.text.primary} flex items-center justify-center transition-all hover:brightness-125 active:opacity-70`}
              type="button"
              aria-label="Open settings"
              title="Settings"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
            <Button
              onClick={actions.handleOpenVerdictModal}
              variant="terminal-primary"
              size="md"
            >
              Verdict
            </Button>
          </div>
        </div>

        {/* Row 2: Location tabs — mobile/tablet, horizontally scrollable */}
        <div className="lg:hidden mt-2 -mx-3 px-3 overflow-x-auto scrollbar-thin">
          <LocationHeaderBar
            locations={locations}
            currentLocationId={currentLocationId}
            locationData={location}
            onSelectLocation={(id) => void handleLocationChange(id)}
            changing={locationChanging}
            visitedLocations={visitedLocations}
            loading={locationLoading}
            error={locationError}
          />
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="max-w-6xl mx-auto px-4 mt-4">
          <div className={`p-3 ${theme.colors.state.error.bg} border ${theme.colors.state.error.border} rounded flex items-center justify-between`}>
            <span className={`${theme.colors.state.error.text} text-sm ${theme.fonts.ui}`}>{error}</span>
            <button
              onClick={clearError}
              className={`${theme.colors.state.error.text} hover:opacity-80 ${theme.fonts.ui} text-sm`}
              aria-label="Dismiss error"
            >
              [X]
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 pt-4 pb-2">
        <InvestigationLayout
          mainContent={
            <LocationView
              caseId={caseId}
              playerId={playerId}
              locationId={currentLocationId}
              locationData={location}
              onEvidenceDiscovered={(ids) =>
                void actions.handleEvidenceDiscoveredWithMatthew(ids)
              }
              discoveredEvidence={[...(state?.discovered_evidence ?? [])]}
              inlineMessages={actions.inlineMessages}
              onMatthewMessage={(msg) => void actions.handleMatthewMessage(msg)}
              matthewLoading={matthewHook.loading}
              showLocationHeader={false}
              hintsEnabled={actions.hintsEnabled}
              isFirstLocation={currentLocationId === locations[0]?.id}
              handbookTrigger={modals.handbookTrigger}
              onEvidenceClick={(id) => void actions.handleEvidenceClick(id)}
              onLocationChanged={(id) => void handleLocationChange(id)}
              slot={currentSlot}
            />
          }
          sidebar={
            <SidebarPanel
              locationId={currentLocationId}
              locationName={location?.name ?? ''}
              witnessCount={witnessState.witnesses.length}
              evidenceCount={state?.discovered_evidence?.length ?? 0}
              onOpenWitnesses={() => modals.setWitnessesModalOpen(true)}
              onOpenEvidence={() => modals.setEvidenceListModalOpen(true)}
              onOpenHandbook={modals.openHandbook}
              hintsEnabled={actions.hintsEnabled}
            />
          }
        />
      </main>


      {/* Briefing Modal */}
      {modals.briefingModalOpen && briefing && (
        <Modal
          isOpen={modals.briefingModalOpen}
          onClose={() => void actions.handleBriefingComplete()}
          variant="terminal"
          hideHeader={true}
          frameless={true}
          noPadding={true}
        >
          <BriefingModal
            briefing={briefing}
            conversation={briefingConversation}
            selectedChoice={briefingSelectedChoice}
            choiceResponse={briefingChoiceResponse}
            onSelectChoice={selectBriefingChoice}
            onResetChoice={resetBriefingChoice}
            onAskQuestion={askBriefingQuestion}
            onComplete={() => void actions.handleBriefingComplete()}
            loading={briefingLoading}
            onClose={() => void actions.handleBriefingComplete()}
          />
        </Modal>
      )}

      {/* Witness Interview Modal */}
      {modals.witnessModalOpen && witnessState.currentWitness && (
        <Modal
          isOpen={modals.witnessModalOpen}
          onClose={actions.handleWitnessModalClose}
          title={`INTERROGATING: ${witnessState.currentWitness.name.toUpperCase()}`}
          maxWidth="max-w-6xl"
          noPadding={true}
          variant="terminal"
        >
          <WitnessInterview
            witness={witnessState.currentWitness}
            conversation={witnessState.conversation}
            trust={witnessState.trust}
            secretsRevealed={witnessState.secretsRevealed}
            discoveredEvidence={discoveredEvidenceWithNames}
            loading={witnessState.loading}
            error={witnessState.error}
            onAskQuestion={askQuestion}
            onPresentEvidence={presentEvidenceToWitness}
          />
        </Modal>
      )}

      {/* Evidence Details Modal */}
      <EvidenceModal
        evidence={actions.selectedEvidence}
        onClose={actions.handleEvidenceModalClose}
        onBack={() => {
          actions.handleEvidenceModalClose();
          modals.setEvidenceListModalOpen(true);
        }}
        error={actions.evidenceError}
      />

      {/* Sidebar Witnesses Modal */}
      <WitnessesModal
        isOpen={modals.witnessesModalOpen}
        onClose={() => modals.setWitnessesModalOpen(false)}
        witnesses={witnessState.witnesses}
        loading={witnessState.loading}
        error={witnessState.error}
        onSelectWitness={(id) => void actions.handleWitnessClick(id)}
      />

      {/* Sidebar Evidence List Modal */}
      <EvidenceListModal
        isOpen={modals.evidenceListModalOpen}
        onClose={() => modals.setEvidenceListModalOpen(false)}
        evidence={[...(state?.discovered_evidence ?? [])]}
        caseId={caseId}
        onEvidenceClick={(id) => void actions.handleEvidenceClick(id)}
      />

      {/* Verdict Flow Modals */}
      {modals.verdictModalOpen && (
        <>
          {/* Step 1: Verdict Submission (before submission or retry) */}
          {!verdictState.submitted && (
            <Modal
              isOpen={true}
              onClose={actions.handleCloseVerdictModal}
              variant="terminal"
              title="Submit Verdict"
            >
              <VerdictSubmission
                suspects={suspects}
                discoveredEvidence={discoveredEvidenceWithNames}
                onSubmit={submitVerdict}
                loading={verdictState.submitting}
                disabled={
                  verdictState.attemptsRemaining === 0 ||
                  verdictState.caseSolved
                }
                attemptsRemaining={verdictState.attemptsRemaining}
              />
            </Modal>
          )}

          {/* Step 2: Mentor Feedback (after check, before confrontation) */}
          {verdictState.submitted &&
            verdictState.feedback &&
            (!verdictState.confrontation ||
              !verdictState.confrontationConfirmed) && (
              <Modal
                isOpen={true}
                onClose={actions.handleCloseVerdictModal}
                variant="terminal"
                title="Graves's Feedback"
              >
                <MentorFeedback
                  feedback={verdictState.feedback}
                  correct={verdictState.correct}
                  attemptsRemaining={verdictState.attemptsRemaining}
                  wrongSuspectResponse={verdictState.wrongSuspectResponse}
                  onRetry={
                    verdictState.attemptsRemaining > 0
                      ? actions.handleVerdictRetry
                      : undefined
                  }
                  onConfront={
                    verdictState.confrontation
                      ? confirmConfrontation
                      : undefined
                  }
                  confrontLabel={
                    verdictState.correct ? 'Arrest the Culprit' : 'Proceed'
                  }
                />

                {/* Reveal section (after max attempts) */}
                {verdictState.reveal && (
                  <div className={`mt-4 bg-gray-800 border border-red-700 rounded p-4 ${theme.fonts.ui}`}>
                    <h3 className="text-red-400 font-bold mb-2">
                      [Correct Answer]
                    </h3>
                    <p className="text-gray-300 text-sm">
                      {verdictState.reveal}
                    </p>
                  </div>
                )}
              </Modal>
            )}

          {/* Step 3: Confrontation Dialogue (after manual confirmation) */}
          {verdictState.submitted &&
            verdictState.confrontation &&
            verdictState.confrontationConfirmed && (
              <Modal
                isOpen={true}
                onClose={actions.handleConfrontationClose}
                variant="terminal"
                title="Confrontation"
              >
                <ConfrontationDialogue
                  dialogue={verdictState.confrontation.dialogue}
                  aftermath={verdictState.confrontation.aftermath}
                  onClose={actions.handleConfrontationClose}
                  caseSolvedCorrectly={verdictState.correct}
                />
              </Modal>
            )}
        </>
      )}

      {/* Main Menu Modal (Phase 5.1) */}
      <MainMenu
        isOpen={modals.menuOpen}
        onClose={() => modals.setMenuOpen(false)}
        onRestart={actions.handleMenuRestart}
        onLoad={actions.handleMenuLoad}
        onSave={actions.handleMenuSave}
        onSettings={actions.handleMenuSettings}
        onExitToMainMenu={() => {
          modals.setMenuOpen(false);
          modals.setShowExitConfirm(true);
        }}
        loading={actions.restartLoading}
      />

      {/* Settings Modal (Phase 5.7) */}
      <SettingsModal
        isOpen={modals.settingsOpen}
        onClose={() => modals.setSettingsOpen(false)}
        caseId={caseId}
        playerId={playerId}
        narratorVerbosity={state?.narrator_verbosity ?? 'storyteller'}
        onVerbosityChange={setNarratorVerbosity}
        language={(state?.language ?? 'en') as import('./components/SettingsModal').GameLanguage}
        onLanguageChange={setLanguage}
        hintsEnabled={actions.hintsEnabled}
        onHintsChange={actions.handleHintsChange}
      />

      {/* Save/Load Modals (Phase 5.3) */}
      <SaveLoadModal
        isOpen={modals.saveModalOpen}
        onClose={() => modals.setSaveModalOpen(false)}
        mode="save"
        onSave={actions.handleSaveToSlot}
        onLoad={actions.handleLoadFromSlotInGame}
        slots={slots}
        loading={saveSlotsLoading}
        caseId={caseId}
        playerId={playerId}
        onImportSuccess={() => void saveSlots.refreshSlots()}
      />

      <SaveLoadModal
        isOpen={modals.loadModalOpen}
        onClose={() => modals.setLoadModalOpen(false)}
        mode="load"
        onSave={actions.handleSaveToSlot}
        onLoad={actions.handleLoadFromSlotInGame}
        slots={slots}
        loading={saveSlotsLoading}
        caseId={caseId}
        playerId={playerId}
        onImportSuccess={() => void saveSlots.refreshSlots()}
      />

      {/* Toast Notification (Phase 5.3) */}
      {toastMessage && (
        <Toast
          message={toastMessage}
          variant={toastVariant}
          onClose={handleToastClose}
        />
      )}

      {/* Restart Case Confirmation Dialog */}
      <ConfirmDialog
        open={modals.showRestartConfirm}
        title="Restart Case"
        message="Reset all progress? Evidence, witnesses, and verdicts will be lost."
        confirmText={actions.restartLoading ? "Restarting..." : "Restart"}
        cancelText="Cancel"
        destructive={true}
        onConfirm={() => void actions.handleRestartCase()}
        onCancel={() => modals.setShowRestartConfirm(false)}
      />

      {/* Exit to Main Menu Confirmation Dialog (Phase 5.3.1) */}
      <ConfirmDialog
        open={modals.showExitConfirm}
        title="Exit to Main Menu"
        message="Return to main menu? Any unsaved progress will be lost."
        confirmText="Exit"
        cancelText="Cancel"
        destructive={true}
        onConfirm={() => {
          modals.setShowExitConfirm(false);
          onExitToMainMenu();
        }}
        onCancel={() => modals.setShowExitConfirm(false)}
      />

      </>
      )}
    </div>
  );
}
