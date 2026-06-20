/**
 * BriefingModal Component
 *
 * Main container for the sequential briefing initiate.
 * MANAGED STEPS:
 * 1. Dossier (Case Details)
 * 2. Questions (1..N)
 * 3. Engagement (Q&A + Start)
 *
 * @module components/BriefingModal
 * @since Phase 3.6 (Redesign Phase 5.x)
 */

import { useState, useCallback, useEffect } from "react";
import { BriefingDossier } from "./BriefingDossier";
import { BriefingQuestion } from "./BriefingQuestion";
import { BriefingEngagement } from "./BriefingEngagement";
import { SKIP_BRIEFING_CALIBRATION_AND_ENGAGEMENT } from "../config/gameFeatures";
import { useTheme } from '../context/useTheme';
import type {
  BriefingContent,
  BriefingConversation as BriefingConversationType,
} from "../types/investigation";

// ============================================
// Types
// ============================================

export interface BriefingModalProps {
  /** Briefing content from backend */
  briefing: BriefingContent;
  /** Q&A conversation history */
  conversation: BriefingConversationType[];
  /** Selected choice ID */
  selectedChoice: string | null;
  /** Graves's response to selected choice */
  choiceResponse: string | null;
  /** Callback when player selects a choice */
  onSelectChoice: (choiceId: string, questionIndex: number) => void;
  /** Callback to reset choice when moving to next question */
  onResetChoice: () => void;
  /** Callback when player asks a question */
  onAskQuestion: (question: string) => Promise<void>;
  /** Callback when player clicks "Start Investigation" */
  onComplete: () => void;
  /** Whether an API call is in progress */
  loading: boolean;
  /** Optional callback to close the modal */
  onClose?: () => void;
  /** Initial step index (for testing/debugging) */
  initialStep?: number;
}

export function BriefingModal({
  briefing,
  conversation,
  selectedChoice,
  choiceResponse,
  onSelectChoice,
  onResetChoice,
  onAskQuestion,
  onComplete,
  loading,
  onClose,
  initialStep = 0,
}: BriefingModalProps) {
  const { theme } = useTheme();
  // Step state: 0 = Dossier, 1+ = Questions, Last = Engagement
  const [currentStep, setCurrentStep] = useState(initialStep);

  // Sync step with props (useful for testing and reset)
  useEffect(() => {
    setCurrentStep(initialStep);
  }, [briefing, initialStep]);

  const totalQuestions = briefing.teaching_questions.length;

  // Helper to determine dynamic window title
  const getHeaderTitle = () => {
    if (currentStep === 0) {
      return `CASE DOSSIER: ${briefing.dossier.title}`;
    }
    if (currentStep >= 1 && currentStep <= totalQuestions) {
      return "RATIONALITY CALIBRATION";
    }
    return "FINAL INSTRUCTIONS";
  };

  // Handle step Navigation
  const handleContinue = useCallback(() => {
    if (SKIP_BRIEFING_CALIBRATION_AND_ENGAGEMENT && currentStep === 0) {
      onComplete();
      return;
    }

    // If moving from a question to next step, reset choice
    if (currentStep >= 1 && currentStep <= totalQuestions) {
      onResetChoice();
    }
    setCurrentStep((prev) => prev + 1);
  }, [currentStep, totalQuestions, onResetChoice, onComplete]);

  // Render content based on current step
  const renderContent = () => {
    // Step 0: Dossier
    if (currentStep === 0) {
      return (
        <BriefingDossier
          dossier={briefing.dossier}
          onContinue={handleContinue}
          continueLabel={
            SKIP_BRIEFING_CALIBRATION_AND_ENGAGEMENT
              ? "START INVESTIGATION"
              : "ACKNOWLEDGE & CONTINUE"
          }
        />
      );
    }

    // Step 1 to N: Teaching Questions
    if (currentStep >= 1 && currentStep <= totalQuestions) {
      const questionIndex = currentStep - 1;
      const question = briefing.teaching_questions[questionIndex];

      return (
        <BriefingQuestion
          question={question}
          onSelectChoice={(choiceId) => onSelectChoice(choiceId, questionIndex)}
          selectedChoiceId={selectedChoice}
          choiceResponse={choiceResponse}
          onContinue={handleContinue}
        />
      );
    }

    // Step N+1: Engagement (Final)
    return (
      <BriefingEngagement
        conversation={conversation}
        transitionText={briefing.transition ?? "Trust nothing unseen."}
        onAskQuestion={onAskQuestion}
        onComplete={onComplete}
        loading={loading}
      />
    );
  };

  return (
    <div
      className={`
      relative w-full min-h-[250px] md:min-h-[500px] flex flex-col ${theme.fonts.narrative} ${theme.colors.text.secondary}
      ${theme.colors.bg.primary} border ${theme.colors.border.default} rounded-lg
      ${theme.typography.body}
    `}
    >
      {/* Unified Folder Header */}
      <div className={`flex items-center justify-between px-4 md:px-6 py-3 md:py-4 border-b ${theme.colors.border.default} ${theme.colors.bg.semiTransparent}`}>
        <h2 className={`${theme.typography.headerLg} ${theme.colors.interactive.text}`}>
          {getHeaderTitle()}
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            className={`${theme.colors.text.muted} ${theme.colors.text.primaryHover} transition-colors ${theme.fonts.ui} text-base`}
            aria-label="Close Case Briefing"
          >
            [X]
          </button>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-grow p-4 md:p-8">{renderContent()}</div>
    </div>
  );
}
