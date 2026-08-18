/**
 * BriefingDossier Component
 *
 * Displays structured case information (Dossier) as the first slide
 * of the standardized briefing initiate.
 *
 * @module components/BriefingDossier
 */

import { useTheme } from '../context/useTheme';
import { renderInlineMarkdown } from '../utils/renderInlineMarkdown';
import type { BriefingContent } from '../types/investigation';
import { Button } from './ui/Button';

interface BriefingDossierProps {
    dossier: BriefingContent['dossier'];
    onContinue: () => void;
    continueLabel?: string;
}

export function BriefingDossier({
    dossier,
    onContinue,
    continueLabel = "ACKNOWLEDGE & CONTINUE",
}: BriefingDossierProps) {
    const { theme } = useTheme();

    return (
        <div className="flex flex-col h-full animate-fadeIn">
            {/* Header Removed (Managed by Parent Window) */}

            {/* Grid Layout for Data Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 mb-6">

                {/* Victim */}
                <div className="space-y-1">
                    <div className={`${theme.typography.caption} font-bold ${theme.colors.text.primary}`}>VICTIM</div>
                    <div className={`${theme.typography.bodySm} border-l-2 ${theme.colors.border.default} pl-3`}>
                        {dossier.victim}
                    </div>
                </div>

                {/* Location */}
                <div className="space-y-1">
                    <div className={`${theme.typography.caption} font-bold ${theme.colors.text.primary}`}>LOCATION</div>
                    <div className={`${theme.typography.bodySm} border-l-2 ${theme.colors.border.default} pl-3`}>
                        {dossier.location}
                    </div>
                </div>

                {/* Time */}
                <div className="space-y-1">
                    <div className={`${theme.typography.caption} font-bold ${theme.colors.text.primary}`}>TIME OF INCIDENT</div>
                    <div className={`${theme.typography.bodySm} border-l-2 ${theme.colors.border.default} pl-3`}>
                        {dossier.time}
                    </div>
                </div>

                {/* Status */}
                <div className="space-y-1">
                    <div className={`${theme.typography.caption} font-bold ${theme.colors.text.primary}`}>CURRENT STATUS</div>
                    <div className={`${theme.typography.bodySm} border-l-2 ${theme.colors.border.default} pl-3`}>
                        {dossier.status}
                    </div>
                </div>
            </div>

            {/* Synopsis / Description */}
            <div className={`flex-grow border-t ${theme.colors.border.default} pt-4`}>
                <div className={`${theme.typography.caption} font-bold ${theme.colors.text.primary} mb-3`}>
                    WHAT HAPPENED
                </div>
                <div className={`${theme.typography.body} text-sm md:text-base leading-relaxed whitespace-pre-wrap max-w-3xl`}>
                    {renderInlineMarkdown(dossier.synopsis)}
                </div>
            </div>

            {/* Footer / Action */}
            <div className={`mt-6 pt-4 border-t ${theme.colors.border.default} flex justify-end`}>
                <Button
                    onClick={onContinue}
                    variant="terminal-primary"
                    size="md"
                    className="w-full justify-center font-bold"
                >
                    <span>{theme.symbols.doubleArrowRight} {continueLabel}</span>
                </Button>
            </div>
        </div>
    );
}
