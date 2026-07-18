/**
 * useGameActions — centralizes all action handlers for InvestigationView.
 *
 * Extracts evidence inspection, witness interaction, Matthew chat, verdict flow,
 * save/load, restart, and menu handlers out of the god component.
 *
 * @module hooks/useGameActions
 */

import { useState, useCallback, useEffect } from "react";
import { getEvidenceDetails, resetCase } from "../api/client";
import type { EvidenceDetails, InvestigationState, Message } from "../types/investigation";
import type { useGameModals } from "./useGameModals";

// ---------- Toast interface (matches InvestigationView's inline toast) ----------

interface Toast {
  setToastMessage: (msg: string | null) => void;
  setToastVariant: (v: "success" | "error" | "info") => void;
}

// ---------- Param interfaces (duck-typed from hook returns) ----------

interface InvestigationSlice {
  state: InvestigationState | null;
  handleEvidenceDiscovered: (ids: string[]) => void;
  restoredMessages: Message[] | null;
}

interface WitnessSlice {
  selectWitness: (id: string) => Promise<void>;
  clearConversation: () => void;
}

interface VerdictSlice {
  reset: () => void;
  confirmConfrontation: () => void;
}

interface BriefingSlice {
  loadBriefing: () => Promise<{ briefing_completed?: boolean } | null>;
  markComplete: () => Promise<void>;
}

interface MatthewSlice {
  checkAutoComment: (isCritical: boolean) => Promise<Message | null>;
  sendMessage: (msg: string) => Promise<Message>;
}

interface SaveSlotsSlice {
  saveToSlot: (slot: string, state: InvestigationState) => Promise<boolean>;
  loadFromSlot: (slot: string) => Promise<{ case_id: string } | null>;
  refreshSlots: () => Promise<void>;
  error: string | null;
}

export interface UseGameActionsParams {
  caseId: string;
  playerId: string;
  modals: ReturnType<typeof useGameModals>;
  toast: Toast;
  investigation: InvestigationSlice;
  witnesses: WitnessSlice;
  verdict: VerdictSlice;
  briefing: BriefingSlice;
  matthew: MatthewSlice;
  saveSlots: SaveSlotsSlice;
}

export function useGameActions({
  caseId,
  playerId: _playerId,
  modals,
  toast,
  investigation,
  witnesses,
  verdict,
  briefing,
  matthew,
  saveSlots,
}: UseGameActionsParams) {
  // ---- Evidence detail modal state ----
  const [selectedEvidence, setSelectedEvidence] =
    useState<EvidenceDetails | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  // ---- Inline messages (Matthew spirit companion) ----
  const [inlineMessages, setInlineMessages] = useState<Message[]>([]);

  // ---- Restart loading ----
  const [restartLoading, setRestartLoading] = useState(false);

  // ---- Hints (persisted in localStorage) ----
  const [hintsEnabled, setHintsEnabled] = useState(() =>
    localStorage.getItem("lantern-hints-enabled") !== "false",
  );

  // Restore conversation messages on case load
  useEffect(() => {
    if (investigation.restoredMessages) {
      setInlineMessages(investigation.restoredMessages);
    } else {
      setInlineMessages([]);
    }
  }, [investigation.restoredMessages]);

  // Load briefing on mount
  useEffect(() => {
    const initBriefing = async () => {
      const content = await briefing.loadBriefing();
      if (content && !content.briefing_completed) {
        modals.setBriefingModalOpen(true);
      }
    };
    void initBriefing();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- Briefing ----
  const handleBriefingDismiss = useCallback(() => {
    modals.setBriefingModalOpen(false);
  }, [modals]);

  const handleBriefingComplete = useCallback(async () => {
    await briefing.markComplete();
    modals.setBriefingModalOpen(false);
  }, [briefing, modals]);

  // ---- Matthew integration ----
  const handleEvidenceDiscoveredWithMatthew = useCallback(
    async (evidenceIds: string[]) => {
      investigation.handleEvidenceDiscovered(evidenceIds);
      try {
        const isCritical = evidenceIds.length > 1;
        const matthewMessage = await matthew.checkAutoComment(isCritical);
        if (matthewMessage) {
          setInlineMessages((prev) => [...prev, matthewMessage]);
        }
      } catch (error) {
        console.error("Matthew auto-comment failed:", error);
      }
    },
    [investigation, matthew],
  );

  const handleMatthewMessage = useCallback(
    async (message: string) => {
      const companionName = investigation.state?.language === "ru" ? "Матвей" : "Matthew";
      const userMessage: Message = {
        type: "player",
        text: `${companionName}, ${message}`,
        timestamp: Date.now(),
      };
      setInlineMessages((prev) => [...prev, userMessage]);
      try {
        const matthewResponse = await matthew.sendMessage(message);
        setInlineMessages((prev) => [...prev, matthewResponse]);
      } catch (error) {
        console.error("Matthew chat error:", error);
        const errorMessage: Message = {
          type: "matthew_ghost",
          text:
            investigation.state?.language === "ru"
              ? "Шёпот Матвея тает — сейчас его не разобрать."
              : "Matthew's whisper fades — too faint to hear right now.",
          timestamp: Date.now(),
        };
        setInlineMessages((prev) => [...prev, errorMessage]);
      }
    },
    [investigation.state?.language, matthew],
  );

  // ---- Witness ----
  const handleWitnessClick = useCallback(
    async (witnessId: string) => {
      await witnesses.selectWitness(witnessId);
      modals.setWitnessModalOpen(true);
    },
    [witnesses, modals],
  );

  const handleWitnessModalClose = useCallback(() => {
    modals.setWitnessModalOpen(false);
    witnesses.clearConversation();
  }, [witnesses, modals]);

  // ---- Evidence detail ----
  const handleEvidenceClick = useCallback(
    async (evidenceId: string) => {
      setEvidenceLoading(true);
      setEvidenceError(null);
      try {
        const details = await getEvidenceDetails(evidenceId, caseId);
        setSelectedEvidence(details);
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Failed to load evidence details";
        setEvidenceError(msg);
      } finally {
        setEvidenceLoading(false);
      }
    },
    [caseId],
  );

  const handleEvidenceModalClose = useCallback(() => {
    setSelectedEvidence(null);
    setEvidenceError(null);
  }, []);

  // ---- Verdict ----
  const handleOpenVerdictModal = useCallback(() => {
    modals.setVerdictModalOpen(true);
  }, [modals]);

  const handleCloseVerdictModal = useCallback(() => {
    modals.setVerdictModalOpen(false);
  }, [modals]);

  const handleVerdictRetry = useCallback(() => {
    verdict.reset();
  }, [verdict]);

  const handleConfrontationClose = useCallback(() => {
    modals.setVerdictModalOpen(false);
    verdict.reset();
  }, [verdict, modals]);

  // ---- Restart ----
  const handleRestartCase = useCallback(async () => {
    setRestartLoading(true);
    try {
      await resetCase(caseId);
      try {
        localStorage.removeItem(`lantern_game_location_${caseId}`);
      } catch (e) {
        console.warn("Failed to clear location from localStorage:", e);
      }
      window.location.reload();
    } catch (error) {
      console.error("Error resetting case:", error);
      modals.setShowRestartConfirm(false);
      setRestartLoading(false);
    }
  }, [caseId, modals]);

  // ---- Menu shortcuts ----
  const handleMenuRestart = useCallback(() => {
    modals.setMenuOpen(false);
    modals.setShowRestartConfirm(true);
  }, [modals]);

  const handleMenuSave = useCallback(() => {
    modals.setMenuOpen(false);
    modals.setSaveModalOpen(true);
    void saveSlots.refreshSlots();
  }, [modals, saveSlots]);

  const handleMenuLoad = useCallback(() => {
    modals.setMenuOpen(false);
    modals.setLoadModalOpen(true);
    void saveSlots.refreshSlots();
  }, [modals, saveSlots]);

  const handleMenuSettings = useCallback(() => {
    modals.setMenuOpen(false);
    modals.setSettingsOpen(true);
  }, [modals]);

  // ---- Save/Load ----
  const handleSaveToSlot = useCallback(
    async (slot: string) => {
      if (!investigation.state) {
        toast.setToastVariant("error");
        toast.setToastMessage("No game state to save");
        return;
      }
      const success = await saveSlots.saveToSlot(slot, investigation.state);
      if (success) {
        toast.setToastVariant("success");
        toast.setToastMessage(`Saved to ${slot.replace("_", " ")}`);
        modals.setSaveModalOpen(false);
      } else {
        toast.setToastVariant("error");
        toast.setToastMessage(saveSlots.error ?? "Save failed");
      }
    },
    [investigation.state, saveSlots, toast, modals],
  );

  const handleLoadFromSlotInGame = useCallback(
    async (slot: string) => {
      const loadedState = await saveSlots.loadFromSlot(slot);
      if (loadedState) {
        toast.setToastVariant("success");
        toast.setToastMessage(`Loaded from ${slot.replace("_", " ")}`);
        modals.setLoadModalOpen(false);
        window.location.reload();
      } else {
        toast.setToastVariant("error");
        toast.setToastMessage(saveSlots.error ?? "Load failed");
      }
    },
    [saveSlots, toast, modals],
  );

  // ---- Hints ----
  const handleHintsChange = useCallback((v: boolean) => {
    setHintsEnabled(v);
    localStorage.setItem("lantern-hints-enabled", String(v));
  }, []);

  return {
    // Evidence detail state
    selectedEvidence,
    evidenceLoading,
    evidenceError,
    // Inline messages
    inlineMessages,
    // Restart
    restartLoading,
    // Hints
    hintsEnabled,
    handleHintsChange,
    // Handlers
    handleBriefingDismiss,
    handleBriefingComplete,
    handleEvidenceDiscoveredWithMatthew,
    handleMatthewMessage,
    handleWitnessClick,
    handleWitnessModalClose,
    handleEvidenceClick,
    handleEvidenceModalClose,
    handleOpenVerdictModal,
    handleCloseVerdictModal,
    handleVerdictRetry,
    handleConfrontationClose,
    handleRestartCase,
    handleMenuRestart,
    handleMenuSave,
    handleMenuLoad,
    handleMenuSettings,
    handleSaveToSlot,
    handleLoadFromSlotInGame,
  };
}
