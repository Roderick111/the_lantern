import type { AssistanceMode, GameLanguage, NarratorVerbosity } from '../components/SettingsModal';

const STORAGE_KEY = 'lantern-game-preferences';

export interface GamePreferences {
  language: GameLanguage;
  narratorVerbosity: NarratorVerbosity;
  assistanceMode: AssistanceMode;
}

const DEFAULT_PREFERENCES: GamePreferences = {
  language: 'en',
  narratorVerbosity: 'storyteller',
  assistanceMode: 'normal',
};

export function getGamePreferences(): GamePreferences {
  if (typeof window === 'undefined') return DEFAULT_PREFERENCES;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    const parsed = JSON.parse(raw) as Partial<GamePreferences>;
    return {
      language: parsed.language ?? DEFAULT_PREFERENCES.language,
      narratorVerbosity: parsed.narratorVerbosity ?? DEFAULT_PREFERENCES.narratorVerbosity,
      assistanceMode: parsed.assistanceMode === 'easy' ? 'easy' : DEFAULT_PREFERENCES.assistanceMode,
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function saveGamePreferences(preferences: GamePreferences): void {
  const persisted = preferences.assistanceMode === 'normal'
    ? { language: preferences.language, narratorVerbosity: preferences.narratorVerbosity }
    : preferences;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(persisted));
}

export function updateGamePreferences(patch: Partial<GamePreferences>): GamePreferences {
  const next = { ...getGamePreferences(), ...patch };
  saveGamePreferences(next);
  return next;
}
