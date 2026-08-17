/**
 * useGameModals — centralizes all modal open/close state for InvestigationView.
 *
 * @module hooks/useGameModals
 */

import { useState, useCallback } from "react";

export function useGameModals() {
  const [briefingModalOpen, setBriefingModalOpen] = useState(false);
  const [witnessModalOpen, setWitnessModalOpen] = useState(false);
  const [verdictModalOpen, setVerdictModalOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [witnessesModalOpen, setWitnessesModalOpen] = useState(false);
  const [evidenceListModalOpen, setEvidenceListModalOpen] = useState(false);
  const [showRestartConfirm, setShowRestartConfirm] = useState(false);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [loadModalOpen, setLoadModalOpen] = useState(false);
  const [handbookTrigger, setHandbookTrigger] = useState(0);

  const openHandbook = useCallback(() => {
    setHandbookTrigger((t) => t + 1);
  }, []);

  return {
    briefingModalOpen,
    setBriefingModalOpen,
    witnessModalOpen,
    setWitnessModalOpen,
    verdictModalOpen,
    setVerdictModalOpen,
    menuOpen,
    setMenuOpen,
    settingsOpen,
    setSettingsOpen,
    witnessesModalOpen,
    setWitnessesModalOpen,
    evidenceListModalOpen,
    setEvidenceListModalOpen,
    showRestartConfirm,
    setShowRestartConfirm,
    saveModalOpen,
    setSaveModalOpen,
    loadModalOpen,
    setLoadModalOpen,
    handbookTrigger,
    openHandbook,
  };
}
