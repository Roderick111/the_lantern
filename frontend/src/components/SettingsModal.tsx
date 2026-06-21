/**
 * SettingsModal Component
 *
 * Compact settings modal with segmented controls, collapsible AI section,
 * and dense audio controls. Matches System Menu aesthetic.
 *
 * @module components/SettingsModal
 */

import * as Dialog from '@radix-ui/react-dialog';
import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { backdropVariants, dialogContentVariants, reducedMotionVariants } from '../utils/modalAnimations';
import { useTheme } from '../context/useTheme';
import { useMusic } from '../hooks/useMusic';
import {
  getLLMSettings,
  saveLLMSettings,
  clearLLMSettings,
  verifyApiKey,
  getAvailableModels,
  getActiveModel,
  updateSettings,
  type ModelInfo,
} from '../api/client';

// ============================================
// Types
// ============================================

export type NarratorVerbosity = 'concise' | 'storyteller' | 'atmospheric';

export type GameLanguage = 'en' | 'ru' | 'fr' | 'es' | 'de' | 'pt' | 'zh' | 'ja' | 'ko' | 'it';

const LANGUAGE_OPTIONS: { value: GameLanguage; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'it', label: 'Italiano' },
  { value: 'ru', label: 'Русский' },
  { value: 'fr', label: 'Français' },
  { value: 'es', label: 'Español' },
  { value: 'de', label: 'Deutsch' },
  { value: 'pt', label: 'Português' },
  { value: 'zh', label: '中文' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
];

export interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  playerId: string;
  narratorVerbosity: NarratorVerbosity;
  onVerbosityChange?: (v: NarratorVerbosity) => void;
  language: GameLanguage;
  onLanguageChange?: (v: GameLanguage) => void;
  hintsEnabled: boolean;
  onHintsChange: (v: boolean) => void;
}

// ============================================
// Segmented Control
// ============================================

interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  disabled,
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (v: T) => void;
  disabled?: boolean;
}) {
  const { theme } = useTheme();

  return (
    <div className={`flex border rounded-sm ${theme.colors.border.default} overflow-hidden`}>
      {options.map((opt, i) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          disabled={disabled}
          className={`flex-1 py-1.5 px-3 ${theme.fonts.ui} text-sm uppercase tracking-wider transition-all duration-150
            ${i > 0 ? `border-l ${theme.colors.border.default}` : ''}
            ${value === opt.value
              ? `${theme.colors.bg.hover} ${theme.colors.interactive.text} font-bold`
              : `${theme.colors.text.muted} ${theme.colors.bg.hoverClass}`
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// ============================================
// Component
// ============================================

export function SettingsModal({
  isOpen,
  onClose,
  caseId,
  playerId: _playerId,
  narratorVerbosity,
  onVerbosityChange,
  language,
  onLanguageChange,
  hintsEnabled,
  onHintsChange,
}: SettingsModalProps) {
  const { mode, toggleTheme, theme } = useTheme();
  const [updating, setUpdating] = useState(false);

  const {
    volume: musicVolume,
    muted: musicMuted,
    enabled: musicEnabled,
    isPlaying: musicPlaying,
    tracks,
    currentTrackName,
    setVolume: setMusicVolume,
    toggleMute: toggleMusicMute,
    setEnabled: setMusicEnabled,
    togglePlayback: toggleMusicPlayback,
    nextTrack,
    prevTrack,
  } = useMusic();

  // LLM / BYOK state
  const [llmProvider, setLlmProvider] = useState<string>('');
  const [llmApiKey, setLlmApiKey] = useState<string>('');
  const [llmModel, setLlmModel] = useState<string>('');
  const [showKey, setShowKey] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verified, setVerified] = useState<boolean | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [freeModelName, setFreeModelName] = useState<string>('Free tier');
  const [aiExpanded, setAiExpanded] = useState(true);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    const saved = getLLMSettings();
    if (saved) {
      setLlmProvider(saved.provider ?? '');
      setLlmApiKey(saved.apiKey ?? '');
      setLlmModel(saved.model ?? '');
      // Auto-expand if user has a custom key configured
      if (saved.provider) setAiExpanded(true);
    }
    void getAvailableModels().then(setAvailableModels);
    void getActiveModel().then((m) => {
      if (m) setFreeModelName(`${m.model_name}`);
    });
  }, []);

  const handleVerifyKey = async () => {
    if (!llmApiKey || !llmProvider) return;
    setVerifying(true);
    setVerified(null);
    setVerifyError(null);
    const result = await verifyApiKey(llmProvider, llmApiKey, llmModel || undefined);
    setVerified(result.valid);
    if (!result.valid) setVerifyError(result.error ?? 'Verification failed');
    setVerifying(false);
  };

  const handleSaveLLM = async () => {
    if (llmApiKey && llmProvider) {
      if (verified !== true) {
        setVerifying(true);
        setVerifyError(null);
        const result = await verifyApiKey(llmProvider, llmApiKey, llmModel || undefined);
        setVerifying(false);
        if (!result.valid) {
          setVerified(false);
          setVerifyError(result.error ?? 'Verify your API key before saving');
          return;
        }
        setVerified(true);
      }
      saveLLMSettings({ provider: llmProvider, apiKey: llmApiKey, model: llmModel || null });
    } else {
      clearLLMSettings();
    }
    setVerified(null);
  };

  const handleClearLLM = () => {
    clearLLMSettings();
    setLlmProvider('');
    setLlmApiKey('');
    setLlmModel('');
    setVerified(null);
    setVerifyError(null);
  };

  const handleVolumeChange = useCallback((newVolume: number) => {
    setMusicVolume(newVolume);
  }, [setMusicVolume]);

  const handleMusicToggle = useCallback(() => {
    setMusicEnabled(!musicEnabled);
  }, [musicEnabled, setMusicEnabled]);

  const handlePlayPause = useCallback(() => {
    toggleMusicPlayback();
  }, [toggleMusicPlayback]);

  const handleNextTrack = useCallback(() => {
    nextTrack();
  }, [nextTrack]);

  const handlePrevTrack = useCallback(() => {
    prevTrack();
  }, [prevTrack]);

  const selectedVerbosity = narratorVerbosity;

  const handleVerbosityChange = async (newVerbosity: NarratorVerbosity) => {
    if (newVerbosity === selectedVerbosity || updating) return;
    setUpdating(true);
    try {
      const data = await updateSettings({
        case_id: caseId,
        narrator_verbosity: newVerbosity,
      });
      if (data.success) {
        onVerbosityChange?.(newVerbosity);
      } else {
        console.error('Failed to update verbosity:', data.message);
      }
    } catch (error) {
      console.error('Error updating verbosity:', error);
    } finally {
      setUpdating(false);
    }
  };

  const handleLanguageChange = async (newLang: GameLanguage) => {
    if (newLang === language || updating) return;
    setUpdating(true);
    try {
      const data = await updateSettings({
        case_id: caseId,
        language: newLang,
      });
      if (data.success) {
        onLanguageChange?.(newLang);
      } else {
        console.error('Failed to update language:', data.message);
      }
    } catch (error) {
      console.error('Error updating language:', error);
    } finally {
      setUpdating(false);
    }
  };

  // Section header style
  const sectionLabel = `${theme.colors.text.tertiary} ${theme.fonts.ui} text-sm font-bold uppercase tracking-wider`;

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <AnimatePresence>
        {isOpen && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div className={theme.components.modal.overlay}
                variants={prefersReducedMotion ? reducedMotionVariants : backdropVariants}
                initial="initial" animate="animate" exit="exit" />
            </Dialog.Overlay>

            <Dialog.Content asChild forceMount onEscapeKeyDown={onClose}>
              <motion.div
                className={`fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50
                           ${theme.colors.bg.primary} border ${theme.colors.interactive.border} rounded-sm
                           w-[calc(100%-2rem)] max-w-sm shadow-2xl max-h-[calc(100dvh-2rem)] flex flex-col
                           focus:outline-none`}
                variants={prefersReducedMotion ? reducedMotionVariants : dialogContentVariants}
                initial="initial" animate="animate" exit="exit"
              >
          {/* Header */}
          <div className={`border-b ${theme.colors.interactive.border} px-5 py-3 flex items-center justify-between ${theme.colors.bg.semiTransparent} shrink-0`}>
            <Dialog.Title className={`${theme.typography.headerLg} ${theme.colors.interactive.text}`}>
              SETTINGS
            </Dialog.Title>
            <Dialog.Description className="sr-only">
              Configure game settings including theme and narrator style
            </Dialog.Description>
          </div>

          {/* Scrollable Content */}
          <div className="px-5 py-5 space-y-5 overflow-y-auto flex-1">

            {/* Display Mode — single row with segmented toggle */}
            <div className="flex items-center justify-between gap-3">
              <span className={sectionLabel}>Display</span>
              <SegmentedControl
                options={[
                  { value: 'dark' as const, label: 'Dark' },
                  { value: 'light' as const, label: 'Light' },
                ]}
                value={mode}
                onChange={(v) => v !== mode && toggleTheme()}
              />
            </div>

            <div className={`border-t ${theme.colors.border.separator}`} />

            {/* Hints Toggle */}
            <div className="flex items-center justify-between gap-3">
              <span className={sectionLabel}>Hints</span>
              <SegmentedControl
                options={[
                  { value: 'on' as const, label: 'On' },
                  { value: 'off' as const, label: 'Off' },
                ]}
                value={hintsEnabled ? 'on' : 'off'}
                onChange={(v) => onHintsChange(v === 'on')}
              />
            </div>

            <div className={`border-t ${theme.colors.border.separator}`} />

            {/* Narrator Style — label + 3-segment control */}
            <div className="space-y-2">
              <span className={sectionLabel}>Narrator</span>
              <SegmentedControl
                options={[
                  { value: 'concise' as const, label: 'Concise' },
                  { value: 'storyteller' as const, label: 'Story' },
                  { value: 'atmospheric' as const, label: 'Atmospheric' },
                ]}
                value={selectedVerbosity}
                onChange={(v) => void handleVerbosityChange(v)}
                disabled={updating}
              />
            </div>

            <div className={`border-t ${theme.colors.border.separator}`} />

            {/* Language */}
            <div className="space-y-2">
              <span className={sectionLabel}>AI Response Language</span>
              <select
                value={language}
                onChange={(e) => void handleLanguageChange(e.target.value as GameLanguage)}
                disabled={updating}
                className={`w-full py-1.5 px-2 border rounded-sm ${theme.fonts.input} text-sm
                  ${theme.colors.bg.primary} ${theme.colors.border.default} ${theme.colors.text.primary}
                  ${updating ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {LANGUAGE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              {language !== 'en' && (
                <p className={`${theme.typography.helper} ${theme.colors.text.muted} text-xs italic`}>
                  Non-English may affect evidence detection and some game mechanics.
                </p>
              )}
            </div>

            <div className={`border-t ${theme.colors.border.separator}`} />

            {/* AI Model — collapsible */}
            <div className="space-y-2">
              <button
                onClick={() => setAiExpanded(!aiExpanded)}
                className={`flex items-center justify-between w-full group`}
              >
                <span className={sectionLabel}>AI Model</span>
                <span className={`${theme.typography.helper} flex items-center gap-1.5`}>
                  <span className={theme.colors.text.tertiary}>
                    {llmProvider ? `${llmProvider}` : freeModelName}
                  </span>
                  <span className={`${theme.colors.text.muted} text-xs transition-transform duration-150 ${aiExpanded ? 'rotate-180' : ''}`}>
                    ▾
                  </span>
                </span>
              </button>

              {aiExpanded && (
                <div className="space-y-2 pt-1">
                  {/* Provider */}
                  <select
                    value={llmProvider}
                    onChange={(e) => { setLlmProvider(e.target.value); setVerified(null); }}
                    className={`w-full py-1.5 px-2 border rounded-sm ${theme.fonts.input} text-sm
                      ${theme.colors.bg.primary} ${theme.colors.border.default} ${theme.colors.text.primary}`}
                  >
                    <option value="">None (Free Tier)</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="openai">OpenAI</option>
                    <option value="google">Google</option>
                  </select>

                  {llmProvider && (
                    <>
                      <p className={`${theme.typography.helper} ${theme.colors.text.muted}`}>
                        Your API key is stored only for this browser tab and cleared when you close it.
                      </p>

                      {/* API Key */}
                      <div className="flex gap-1">
                        <input
                          type={showKey ? 'text' : 'password'}
                          value={llmApiKey}
                          onChange={(e) => { setLlmApiKey(e.target.value); setVerified(null); }}
                          placeholder="API key..."
                          className={`flex-1 py-1.5 px-2 border rounded-sm ${theme.fonts.input} text-sm
                            ${theme.colors.bg.primary} ${theme.colors.border.default} ${theme.colors.text.primary}`}
                        />
                        <button
                          onClick={() => setShowKey(!showKey)}
                          className={`px-2 border rounded-sm ${theme.fonts.ui} text-xs uppercase
                            ${theme.colors.border.default} ${theme.colors.text.muted}`}
                          type="button"
                        >
                          {showKey ? 'Hide' : 'Show'}
                        </button>
                      </div>

                      {/* Model select */}
                      <select
                        value={llmModel}
                        onChange={(e) => setLlmModel(e.target.value)}
                        className={`w-full py-1.5 px-2 border rounded-sm ${theme.fonts.input} text-sm
                          ${theme.colors.bg.primary} ${theme.colors.border.default} ${theme.colors.text.primary}`}
                      >
                        <option value="">Default for provider</option>
                        {availableModels
                          .filter((m) => !llmProvider || m.provider === llmProvider)
                          .map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.name}{m.free ? ' (Free)' : ''}
                            </option>
                          ))}
                      </select>

                      {/* Actions row */}
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => void handleVerifyKey()}
                          disabled={!llmApiKey || verifying}
                          className={`flex-1 py-1.5 px-2 border rounded-sm ${theme.fonts.ui} text-xs uppercase tracking-wider transition-all duration-150
                            ${llmApiKey && !verifying
                              ? `${theme.colors.border.default} ${theme.colors.text.muted} ${theme.colors.border.hoverClass}`
                              : 'opacity-50 cursor-not-allowed'
                            }`}
                        >
                          {verifying ? 'Verifying...' : 'Verify'}
                        </button>
                        <button
                          onClick={() => { void handleSaveLLM(); }}
                          disabled={!llmApiKey}
                          className={`flex-1 py-1.5 px-2 border rounded-sm ${theme.fonts.ui} text-xs uppercase tracking-wider transition-all duration-150
                            ${llmApiKey
                              ? `${theme.colors.interactive.border} ${theme.colors.interactive.text}`
                              : 'opacity-50 cursor-not-allowed'
                            }`}
                        >
                          Save
                        </button>
                        <button
                          onClick={handleClearLLM}
                          className={`py-1.5 px-2 border rounded-sm ${theme.fonts.ui} text-xs uppercase tracking-wider transition-all duration-150
                            ${theme.colors.border.default} ${theme.colors.text.muted} ${theme.colors.border.hoverClass}`}
                        >
                          Clear
                        </button>
                      </div>

                      {/* Status */}
                      {verified === true && (
                        <p className={`${theme.typography.helper} text-green-500`}>Key verified</p>
                      )}
                      {verified === false && verifyError && (
                        <p className={`${theme.typography.helper} text-red-500`}>{verifyError}</p>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>

            <div className={`border-t ${theme.colors.border.separator}`} />

            {/* Audio — compact layout */}
            <div className="space-y-2.5">
              <span className={sectionLabel}>Audio</span>

              {/* Row 1: Music toggle + track navigation */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleMusicToggle}
                  className={`px-2.5 py-1 border rounded-sm ${theme.fonts.ui} text-xs uppercase tracking-wider transition-all duration-150 shrink-0
                    ${musicEnabled
                      ? `${theme.colors.interactive.border} ${theme.colors.interactive.text}`
                      : `${theme.colors.border.default} ${theme.colors.text.muted}`
                    }`}
                  aria-label={musicEnabled ? 'Disable music' : 'Enable music'}
                >
                  {musicEnabled ? 'ON' : 'OFF'}
                </button>
                <button
                  onClick={handlePrevTrack}
                  disabled={!musicEnabled || tracks.length <= 1}
                  className={`px-1.5 py-1 ${theme.fonts.ui} text-xs ${theme.colors.text.muted} disabled:opacity-30`}
                  aria-label="Previous track"
                >
                  ◀
                </button>
                <span
                  className={`${theme.typography.helper} truncate flex-1 text-center`}
                  title={currentTrackName}
                >
                  {currentTrackName}
                </span>
                <button
                  onClick={handleNextTrack}
                  disabled={!musicEnabled || tracks.length <= 1}
                  className={`px-1.5 py-1 ${theme.fonts.ui} text-xs ${theme.colors.text.muted} disabled:opacity-30`}
                  aria-label="Next track"
                >
                  ▶
                </button>
              </div>

              {/* Row 2: Volume slider */}
              <div className="flex items-center gap-2">
                <span className={`${theme.typography.helper} shrink-0 w-8`}>Vol</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={musicVolume}
                  onChange={(e) => handleVolumeChange(parseInt(e.target.value, 10))}
                  disabled={!musicEnabled}
                  className={`flex-1 h-1.5 rounded-sm appearance-none cursor-pointer
                    ${musicEnabled ? theme.colors.bg.hover : 'opacity-40 cursor-not-allowed'}
                    [&::-webkit-slider-thumb]:appearance-none
                    [&::-webkit-slider-thumb]:w-3
                    [&::-webkit-slider-thumb]:h-3
                    [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:bg-amber-500
                    [&::-webkit-slider-thumb]:cursor-pointer
                    [&::-moz-range-thumb]:w-3
                    [&::-moz-range-thumb]:h-3
                    [&::-moz-range-thumb]:rounded-full
                    [&::-moz-range-thumb]:bg-amber-500
                    [&::-moz-range-thumb]:border-0
                    [&::-moz-range-thumb]:cursor-pointer`}
                  aria-label="Music volume"
                />
                <span className={`${theme.typography.helper} tabular-nums shrink-0 w-7 text-right`}>
                  {musicVolume}%
                </span>
              </div>

              {/* Row 3: Play/Pause + Mute */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={handlePlayPause}
                  disabled={!musicEnabled}
                  className={`flex-1 py-1.5 px-2 border rounded-sm ${theme.fonts.ui} text-xs uppercase tracking-wider transition-all duration-150
                    ${musicEnabled
                      ? `${theme.colors.border.default} ${theme.colors.text.muted} ${theme.colors.border.hoverClass}`
                      : 'opacity-40 cursor-not-allowed'
                    }`}
                  aria-label={musicPlaying ? 'Pause music' : 'Play music'}
                >
                  {musicPlaying ? 'Pause' : 'Play'}
                </button>
                <button
                  onClick={toggleMusicMute}
                  disabled={!musicEnabled}
                  className={`py-1.5 px-3 border rounded-sm ${theme.fonts.ui} text-xs uppercase tracking-wider transition-all duration-150
                    ${musicMuted && musicEnabled
                      ? `${theme.colors.interactive.border} ${theme.colors.interactive.text}`
                      : musicEnabled
                        ? `${theme.colors.border.default} ${theme.colors.text.muted} ${theme.colors.border.hoverClass}`
                        : 'opacity-40 cursor-not-allowed'
                    }`}
                  aria-label={musicMuted ? 'Unmute music' : 'Mute music'}
                >
                  {musicMuted ? 'Muted' : 'Mute'}
                </button>
              </div>
            </div>
          </div>

          {/* Footer — hidden on mobile */}
          <div className={`hidden md:block border-t ${theme.colors.interactive.border} px-5 py-2.5 ${theme.colors.bg.semiTransparent} shrink-0`}>
            <p className={`text-center ${theme.colors.text.muted} text-xs ${theme.fonts.ui} uppercase tracking-widest`}>
              Press ESC to close
            </p>
          </div>

          {/* Close button (X) */}
          <Dialog.Close asChild>
            <button
              className={`absolute top-3 right-4 ${theme.colors.text.muted} ${theme.colors.text.primaryHover}
                         focus-visible:outline-none
                         transition-colors ${theme.fonts.ui} text-base`}
              aria-label="Close settings"
            >
              {theme.symbols.closeButton}
            </button>
          </Dialog.Close>
            </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
