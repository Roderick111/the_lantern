/**
 * LanternCompendium Component
 *
 * Read-only modal displaying the 7 investigation rites available to Lantern Inspectors.
 * NO action buttons - this is purely a reference modal.
 * Players must perform rites via text input, not from this modal.
 *
 * @module components/LanternCompendium
 * @since Phase 4.5
 */

import { useEffect, useCallback } from "react";
import { Modal } from "./ui/Modal";
import type { SpellDefinition } from "../types/spells";

type RiteLanguage = "en" | "ru";

// ============================================
// Spell Definitions (from backend)
// ============================================

/**
 * Static spell definitions matching backend/src/spells/definitions.py
 * Read-only reference data - no API call needed
 */
const SPELL_DEFINITIONS: SpellDefinition[] = [
  {
    id: "unveil",
    name: "Veil, dissolve",
    legacyName: "Unveil",
    description: "Reveals hidden writing, concealments, and a thing's true form.",
    example: "Veil, dissolve over this desk.",
    safetyLevel: "safe",
    category: "detection",
  },
  {
    id: "sense_presence",
    name: "Presence, answer",
    legacyName: "Sense Presence",
    description: "Detects someone nearby, even through walls or concealment.",
    example: "Presence, answer beyond this wall.",
    safetyLevel: "safe",
    category: "detection",
  },
  {
    id: "identify_substance",
    name: "Essence, speak",
    legacyName: "Identify Substance",
    description: "Reveals the nature of a potion, poison, cursed object, or magical residue.",
    example: "Essence, speak in this vial.",
    safetyLevel: "safe",
    category: "analysis",
  },
  {
    id: "raise_the_lamp",
    name: "Trace, gleam",
    legacyName: "Raise the Lamp",
    description: "Draws blood, burns, and things hiding in shadow into view.",
    example: "Trace, gleam in the alcove.",
    safetyLevel: "safe",
    category: "detection",
  },
  {
    id: "echo_reading",
    name: "Echo, speak",
    legacyName: "Echo Reading",
    description: "Reveals the last magical traces stored in a focus held in hand.",
    example: "Echo, speak on Elena's focus.",
    safetyLevel: "safe",
    category: "analysis",
  },
  {
    id: "mend",
    name: "Shards, unite",
    legacyName: "Mend",
    description: "Restores a broken object and leaves clues about how it broke.",
    example: "Shards, unite.",
    safetyLevel: "safe",
    category: "restoration",
  },
  {
    id: "mnemonic_delving",
    name: "Memory, open",
    legacyName: "Mnemonic Delving",
    description: "Enters another person's memory. Intrusion can be noticed and carries consequences.",
    example: "Memory, open on Elena's recollection of the archive.",
    safetyLevel: "restricted",
    category: "mental",
  },
];

const SPELL_DEFINITIONS_RU: SpellDefinition[] = [
  {
    id: "unveil",
    name: "Скрытое, явись",
    legacyName: "Снять покров",
    description: "Проявляет скрытые записи, маскировку и подлинный вид вещей.",
    example: "Скрытое, явись на этом столе.",
    safetyLevel: "safe",
    category: "detection",
  },
  {
    id: "sense_presence",
    name: "Присутствие, отзовись",
    legacyName: "Ощутить присутствие",
    description: "Обнаруживает присутствие рядом, даже за стеной или под маскировкой.",
    example: "Присутствие, отзовись за этой стеной.",
    safetyLevel: "safe",
    category: "detection",
  },
  {
    id: "identify_substance",
    name: "Суть, откройся",
    legacyName: "Опознать вещество",
    description: "Раскрывает природу зелья, яда, проклятой вещи или магического следа.",
    example: "Суть, откройся в этом флаконе.",
    safetyLevel: "safe",
    category: "analysis",
  },
  {
    id: "raise_the_lamp",
    name: "Свет, укажи след",
    legacyName: "Поднять лампу",
    description: "Выводит на свет кровь, ожоги и то, что прячется в тени.",
    example: "Свет, укажи след в нише.",
    safetyLevel: "safe",
    category: "detection",
  },
  {
    id: "echo_reading",
    name: "Отзвук чар, явись",
    legacyName: "Чтение эха",
    description: "Показывает последние чары, оставшиеся на фокусе в руке.",
    example: "Отзвук чар, явись на фокусе Елены.",
    safetyLevel: "safe",
    category: "analysis",
  },
  {
    id: "mend",
    name: "Разбитое, сойдись",
    legacyName: "Починить",
    description: "Восстанавливает разбитую вещь и оставляет следы того, как она сломалась.",
    example: "Разбитое стекло, сойдись.",
    safetyLevel: "safe",
    category: "restoration",
  },
  {
    id: "mnemonic_delving",
    name: "Чужая память, отворись",
    legacyName: "Погружение в память",
    description: "Позволяет войти в чужую память. Вторжение могут заметить, и оно имеет последствия.",
    example: "Чужая память, отворись на воспоминание Елены о библиотеке.",
    safetyLevel: "restricted",
    category: "mental",
  },
];

function getSpellDefinitions(language: RiteLanguage = "en"): SpellDefinition[] {
  return language === "ru" ? SPELL_DEFINITIONS_RU : SPELL_DEFINITIONS;
}

// ============================================
// Types
// ============================================

interface LanternCompendiumProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback when modal is closed */
  onClose: () => void;
  /** Content language for formulas, descriptions, and instructions. */
  language?: RiteLanguage;
  /** Callback when a spell is selected for casting */
  onSelectSpell?: (spellName: string) => void;
}

// ============================================
// Helper Components
// ============================================

import { useTheme } from '../context/useTheme';
import type { TerminalTheme } from "../styles/terminal-theme";

/**
 * Category badge with neutral styling
 */
function CategoryBadge({ category, language, theme }: { category: string; language: RiteLanguage; theme: TerminalTheme }) {
  const labels: Record<string, string> = language === "ru"
    ? { detection: "обнаружение", analysis: "анализ", restoration: "восстановление", mental: "ментальное" }
    : { detection: "detection", analysis: "analysis", restoration: "restoration", mental: "mental" };
  return (
    <span className={`inline-block px-1.5 py-0.5 text-xs ${theme.colors.bg.hover} ${theme.colors.text.tertiary} border ${theme.colors.border.default} uppercase tracking-wider ${theme.fonts.label}`}>
      {labels[category] ?? category}
    </span>
  );
}

/**
 * Individual spell card (read-only display)
 */
function SpellCard({
  spell,
  onSelect,
  language,
  theme,
}: {
  spell: SpellDefinition;
  onSelect?: (spellName: string) => void;
  language: RiteLanguage;
  theme: TerminalTheme;
}) {
  const isRestricted = spell.safetyLevel === "restricted";
  const isClickable = !isRestricted && onSelect;

  return (
    <div
      onClick={() => isClickable && onSelect?.(spell.name)}
      className={`p-4 border group transition-all duration-200 relative ${
        isRestricted
          ? `${theme.colors.state.error.border} ${theme.colors.state.error.bg} cursor-not-allowed opacity-80`
          : isClickable
            ? `${theme.colors.border.default} ${theme.colors.bg.primary} ${theme.colors.interactive.borderHover} ${theme.colors.bg.hoverClass} cursor-pointer shadow-sm hover:shadow-md`
            : `${theme.colors.border.default} ${theme.colors.bg.primary} ${theme.colors.bg.hoverClass}`
      }`}
      data-testid={`spell-card-${spell.id}`}
    >
      {/* Click hint for non-restricted spells */}
      {isClickable && (
        <div className={`absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity text-xs ${theme.colors.interactive.text} ${theme.fonts.label} uppercase tracking-widest font-bold`}>
          [CLICK TO CAST]
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <h3
          className={`${theme.fonts.ui} font-bold uppercase tracking-wider text-sm flex items-center gap-2 ${
            isRestricted ? theme.colors.state.error.text : theme.colors.text.primary
          }`}
        >
          <span className={isRestricted ? theme.colors.state.error.text : theme.colors.text.muted}>
            {theme.symbols.bullet}
          </span>
          {spell.name}
        </h3>
        {isRestricted && (
          <span className={`text-xs ${theme.colors.state.error.text} border ${theme.colors.state.error.border} px-1 font-bold uppercase tracking-widest`}>
            {language === "ru" ? "ЗАПРЕТНЫЙ" : "RESTRICTED"}
          </span>
        )}
      </div>

      {/* Description */}
      <p className={`${theme.colors.text.tertiary} text-sm mb-3 leading-relaxed ${theme.fonts.narrative} pl-5 opacity-90 group-hover:opacity-100 transition-opacity`}>
        {spell.description}
      </p>

      <p className={`${theme.colors.text.muted} text-xs mb-3 pl-5 ${theme.fonts.ui}`}>
        {spell.example}
      </p>

      {/* Footer info */}
      <div className="pl-5 flex gap-2">
        <CategoryBadge category={spell.category} language={language} theme={theme} />
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

/**
 * Lantern Compendium - Read-only rite reference modal
 *
 * Displays all 7 investigation rites with descriptions.
 * NO action buttons - players perform rites via text input.
 * Multi-column layout for spell cards.
 */
export function LanternCompendium({
  isOpen,
  onClose,
  language = "en",
  onSelectSpell,
}: LanternCompendiumProps) {
  const { theme } = useTheme();
  const spells = getSpellDefinitions(language);
  const labels = language === "ru"
    ? { title: "СВЕТОЧ // ИНДЕКС ОБРЯДОВ", footer: "ТАЙНЫЙ ПРИКАЗ / ОТДЕЛ РАССЛЕДОВАНИЙ СВЕТОЧА", confidential: "СЕКРЕТНО" }
    : { title: "LANTERN COMPENDIUM // RITE INDEX", footer: "CROWN OCCULT BUREAU / LANTERN INVESTIGATIONS DIVISION", confidential: "CONFIDENTIAL" };

  // Keyboard shortcut handler for Cmd/Ctrl+H
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "h") {
        e.preventDefault();
        if (isOpen) {
          onClose();
        }
        // Opening is handled by parent component
      }
    },
    [isOpen, onClose],
  );

  // Register keyboard shortcut
  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={labels.title}
      variant="terminal"
    >
      <div className="space-y-4">
        {/* Instructions */}
        <div className={`border-b ${theme.colors.border.default} pb-3 mb-2`}>
          <p className={`${theme.colors.text.muted} text-sm ${theme.fonts.ui}`}>
            <span className={theme.colors.text.tertiary}>
              {theme.symbols.prefix}
            </span>{" "}
            {language === "ru"
              ? "Обряды требуют явной словесной формулы. Напишите формулу отдельно или добавьте после неё цель."
              : "Rites use spoken formulas. Type a formula by itself or add a target after it."}
            <br />
            <span className={theme.colors.text.tertiary}>
              {theme.symbols.prefix}
            </span>{" "}
            {language === "ru"
              ? "Обычные вопросы и описания действий обряд не вызывают."
              : "Questions and ordinary descriptions do not perform rites."}
          </p>
        </div>

        {/* Categories / Sections if we wanted, but flat list is fine for 7 rites */}

        {/* Spell Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[60vh] overflow-y-auto pr-2 scrollbar-thin">
          {spells.map((spell) => (
            <SpellCard key={spell.id} spell={spell} onSelect={onSelectSpell} language={language} theme={theme} />
          ))}
        </div>

        {/* Footer */}
        <div className={`pt-2 border-t ${theme.colors.border.default} flex justify-between items-center text-xs ${theme.colors.text.muted} uppercase tracking-widest`}>
          <span>{labels.footer}</span>
          <span>{labels.confidential}</span>
        </div>
      </div>
    </Modal>
  );
}

// Export spell definitions for use in quick actions
 
export { SPELL_DEFINITIONS };
