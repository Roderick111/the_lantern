import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, screen } from '@testing-library/react';
import { render } from '../../test/render';
import { SettingsModal } from '../SettingsModal';

vi.mock('../../hooks/useMusic', () => ({
  useMusic: () => ({
    volume: 50,
    muted: false,
    enabled: true,
    isPlaying: false,
    tracks: [],
    currentTrackName: 'No track',
    setVolume: vi.fn(),
    toggleMute: vi.fn(),
    setEnabled: vi.fn(),
    togglePlayback: vi.fn(),
    nextTrack: vi.fn(),
    prevTrack: vi.fn(),
  }),
}));

vi.mock('../../api/client', () => ({
  getLLMSettings: vi.fn(() => null),
  saveLLMSettings: vi.fn(),
  clearLLMSettings: vi.fn(),
  verifyApiKey: vi.fn(() => Promise.resolve({ valid: true })),
  getAvailableModels: vi.fn(() => Promise.resolve([])),
  getActiveModel: vi.fn(() => Promise.resolve(null)),
  updateSettings: vi.fn(() => Promise.resolve({ success: true, message: 'ok' })),
}));

describe('SettingsModal general mode', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows only general settings', () => {
    render(
      <SettingsModal
        mode="general"
        isOpen
        onClose={vi.fn()}
        narratorVerbosity="storyteller"
        language="en"
      />,
    );

    expect(screen.getByText('Display')).toBeInTheDocument();
    expect(screen.getByText('Narrator')).toBeInTheDocument();
    expect(screen.getByText('AI Model')).toBeInTheDocument();
    expect(screen.getByText('AI Response Language')).toBeInTheDocument();
    expect(screen.queryByText('Hints')).not.toBeInTheDocument();
    expect(screen.queryByText('Audio')).not.toBeInTheDocument();
  });

  it('stores language and narrator defaults locally', () => {
    render(
      <SettingsModal
        mode="general"
        isOpen
        onClose={vi.fn()}
        narratorVerbosity="storyteller"
        language="en"
      />,
    );

    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'fr' } });
    fireEvent.click(screen.getByRole('button', { name: 'Atmospheric' }));

    expect(localStorage.getItem('lantern-game-preferences')).toBe(
      JSON.stringify({ language: 'fr', narratorVerbosity: 'atmospheric' }),
    );
  });
});
