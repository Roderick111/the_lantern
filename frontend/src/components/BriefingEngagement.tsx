/**
 * BriefingEngagement Component
 *
 * Final slide of the Briefing Initiate.
 * Allows Q&A with Graves and initiating the investigation.
 *
 * @module components/BriefingEngagement
 */

import { useTheme } from '../context/useTheme';
import { renderInlineMarkdown } from '../utils/renderInlineMarkdown';
import { BriefingMessage } from './BriefingMessage';
import type { BriefingConversation } from '../types/investigation';
import { useState, useCallback, type FormEvent, type KeyboardEvent } from 'react';

interface BriefingEngagementProps {
    conversation: BriefingConversation[];
    transitionText: string;
    onAskQuestion: (question: string) => Promise<void>;
    onComplete: () => void;
    loading: boolean;
}

export function BriefingEngagement({
    conversation,
    transitionText,
    onAskQuestion,
    onComplete,
    loading,
}: BriefingEngagementProps) {
    const { theme } = useTheme();
    const [question, setQuestion] = useState('');

    // Core submission logic (no event required)
    const submitQuestion = useCallback(async () => {
        if (!question.trim() || loading) return;

        const q = question;
        setQuestion('');
        try {
            await onAskQuestion(q);
        } catch (err) {
            // Error handling is managed by parent component
            console.error('[BriefingEngagement] Failed to ask question:', err);
        }
    }, [question, loading, onAskQuestion]);

    // Form submit handler
    const handleSubmit = useCallback(
        async (e: FormEvent) => {
            e.preventDefault();
            await submitQuestion();
        },
        [submitQuestion]
    );

    // Keyboard handler
    const handleKeyDown = useCallback(
        (e: KeyboardEvent<HTMLTextAreaElement>) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void submitQuestion();
            }
        },
        [submitQuestion]
    );

    return (
        <div className="flex flex-col h-full animate-fadeIn">
            {/* Header Removed (Managed by Parent Window) */}

            {/* Conversation History / Chat Feed */}
            <div className={`max-h-80 overflow-y-auto mb-6 pr-2 space-y-3 scrollbar-thin ${theme.colors.bg.primary}`}>
                {/* Default Start Message */}
                <BriefingMessage
                    speaker="graves"
                    text="Any questions before I send you in, recruit? Don't ask me to solve it for you."
                />

                {conversation.map((msg, i) => (
                    <div key={i} className="animate-fadeIn">
                        <BriefingMessage speaker="player" text={msg.question} />
                        <BriefingMessage speaker="graves" text={msg.answer} />
                    </div>
                ))}

                {loading && (
                    <div className={`flex items-center space-x-2 ${theme.typography.helper} p-2`}>
                        <span className="animate-spin">⟳</span>
                        <span>Waiting for response...</span>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="mt-auto">
                <form onSubmit={(e) => void handleSubmit(e)} className="mb-6">
                    <div className={theme.components.input.wrapper}>
                        <div className={theme.components.input.prefix}>
                            {theme.symbols.inputPrefix}
                        </div>
                        <textarea
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="ask Graves a question..."
                            disabled={loading}
                            rows={3}
                            className={`${theme.components.input.field} ${theme.components.input.borderDefault}`}
                        />
                        <button
                            type="submit"
                            disabled={loading || !question.trim()}
                            aria-label="Send Message"
                            className={theme.components.input.sendButton}
                        >
                            SEND
                        </button>
                    </div>
                </form>

                {/* Transition / Start Button */}
                <div className={`border-t ${theme.colors.border.default} pt-6`}>
                    <div className="flex flex-col space-y-4">
                        {transitionText && (
                            <div>
                                <div className={`${theme.typography.caption} mb-2`}>
                                    FINAL BRIEFING
                                </div>
                                <div className={`${theme.typography.body} ${theme.colors.bg.semiTransparent} p-4 border ${theme.colors.border.default} rounded leading-relaxed whitespace-pre-wrap`}>
                                    {renderInlineMarkdown(transitionText)}
                                </div>
                            </div>
                        )}

                        <button
                            onClick={onComplete}
                            aria-label="Start Investigation"
                            className={`${theme.components.button.base} w-full px-8 py-3 ${theme.colors.bg.semiTransparent} ${theme.colors.interactive.text} border ${theme.colors.interactive.border} hover:brightness-90 font-bold tracking-widest uppercase transition-all duration-200 group`}
                        >
                            <span className="mr-2 group-hover:mr-4 transition-all">START INVESTIGATION</span>
                            {theme.symbols.current}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
