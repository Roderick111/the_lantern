import type { GameLanguage, NarratorVerbosity } from '../components/SettingsModal';

const STORAGE_KEY = 'lantern-game-preferences';

export interface GamePreferences {
  language: GameLanguage;
  narratorVerbosity: NarratorVerbosity;
}

const DEFAULT_PREFERENCES: GamePreferences = {
  language: 'en',
  narratorVerbosity: 'storyteller',
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
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function saveGamePreferences(preferences: GamePreferences): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
}

export function updateGamePreferences(patch: Partial<GamePreferences>): GamePreferences {
  const next = { ...getGamePreferences(), ...patch };
  saveGamePreferences(next);
  return next;
}
