/**
 * BriefingQuestion Component
 *
 * Displays a single teaching question slide with multiple choice inputs.
 * Part of the Briefing Initiate.
 *
 * @module components/BriefingQuestion
 */

import { useTheme } from '../context/useTheme';
import { renderInlineMarkdown } from '../utils/renderInlineMarkdown';
import type { TeachingQuestion } from '../types/investigation';

interface BriefingQuestionProps {
    /** Current teaching question to display */
    question: TeachingQuestion;
    /** Callback when player selects a choice */
    onSelectChoice: (choiceId: string) => void;
    /** Currently selected choice ID (null if none selected) */
    selectedChoiceId: string | null;
    /** Graves's response to the selected choice */
    choiceResponse: string | null;
    /** Callback when player continues to next step */
    onContinue: () => void;
}

export function BriefingQuestion({
    question,
    onSelectChoice,
    selectedChoiceId,
    choiceResponse,
    onContinue,
}: BriefingQuestionProps) {
    const { theme } = useTheme();

    return (
        <div className="flex flex-col h-full animate-fadeIn">
            {/* Header Removed (Managed by Parent Window) */}

            {/* Question Prompt */}
            <div className={`mb-8 p-4 ${theme.colors.bg.semiTransparent} border-l-2 ${theme.colors.border.default}`}>
                <div className={`${theme.typography.caption} mb-2`}>
                    GRAVES'S QUERY:
                </div>
                <div className={theme.typography.body}>
                    "{question.prompt}"
                </div>
            </div>

            {/* Choices Grid */}
            <div className="grid grid-cols-1 gap-4 mb-8">
                {question.choices.map((choice) => {
                    const isSelected = selectedChoiceId === choice.id;
                    const isDimmed = selectedChoiceId !== null && !isSelected;

                    return (
                        <button
                            key={choice.id}
                            onClick={() => !selectedChoiceId && onSelectChoice(choice.id)}
                            disabled={selectedChoiceId !== null}
                            aria-pressed={isSelected}
                            aria-label={`Choice ${String.fromCharCode(65 + question.choices.indexOf(choice))}: ${choice.text}`}
                            className={`
                text-left p-4 border rounded transition-all duration-200
                ${isSelected
                                    ? `${theme.colors.bg.active} ${theme.colors.border.hover}`
                                    : `${theme.colors.bg.semiTransparent} ${theme.colors.border.default} ${theme.colors.interactive.borderHover} ${theme.colors.interactive.hover} ${theme.colors.bg.hoverClass}`
                                }
                ${isDimmed ? 'opacity-40 grayscale' : ''}
              `}
                        >
                            <div className="flex items-start">
                                <span className={`${theme.typography.caption} mr-3 mt-0.5`}>
                                    [{String.fromCharCode(65 + question.choices.indexOf(choice))}]
                                </span>
                                <span className={theme.typography.body}>{choice.text}</span>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Feedback & Continue */}
            {selectedChoiceId && (
                <div className="mt-auto animate-fadeIn">
                    {/* Graves's Response */}
                    {choiceResponse && (
                        <div className={`mb-4 p-4 ${theme.colors.bg.primary} border ${theme.colors.border.default}`}>
                            <span className={`${theme.typography.caption} mr-2`}>GRAVES:</span>
                            <span className={theme.typography.body}>{renderInlineMarkdown(choiceResponse)}</span>
                        </div>
                    )}

                    {/* Concept Summary */}
                    <div className={`mb-6 p-4 border-l-2 ${theme.colors.border.default} ${theme.colors.bg.semiTransparent}`}>
                        <div className={`${theme.typography.caption} mb-1`}>
                            CORE CONCEPT: {question.concept_summary}
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <button
                            onClick={onContinue}
                            className={`${theme.components.button.base} w-auto px-8 py-3 ${theme.colors.bg.semiTransparent} ${theme.colors.interactive.text} border ${theme.colors.interactive.border} hover:brightness-90 font-bold tracking-widest uppercase transition-all duration-200 group`}
                        >
                            <span className="mr-2 group-hover:mr-4 transition-all">PROCEED</span>
                            {theme.symbols.current}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
