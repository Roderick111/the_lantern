/**
 * MusicContext
 *
 * Provides music state management for background audio playback.
 * Persists volume/mute preferences to localStorage.
 * Supports track selecting with manifest-based track list.
 *
 * @module context/MusicContext
 * @since Phase 6.5 (Music Ambience)
 */

import {
  createContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
  type MutableRefObject,
} from "react";

// ============================================
// Constants
// ============================================

const STORAGE_KEY_VOLUME = "lantern-music-volume";
const STORAGE_KEY_MUTED = "lantern-music-muted";
const STORAGE_KEY_ENABLED = "lantern-music-enabled";
const STORAGE_KEY_TRACK_PREFIX = "lantern-music-track-";

const DEFAULT_VOLUME = 15;

// ============================================
// Types
// ============================================

/** Track metadata from manifest */
export interface Track {
  id: string;
  name: string;
  file: string;
}

/** Manifest file structure */
interface MusicManifest {
  tracks: Track[];
}

interface MusicContextValue {
  /** Current volume (0-100) */
  volume: number;
  /** Whether music is muted */
  muted: boolean;
  /** Whether music playback is enabled */
  enabled: boolean;
  /** Whether audio is currently playing */
  isPlaying: boolean;
  /** Current track path (e.g., /music/case_001_default.mp3) */
  currentTrack: string | null;
  /** Available tracks from manifest */
  tracks: Track[];
  /** Current track index in tracks array */
  currentTrackIndex: number;
  /** Current track display name */
  currentTrackName: string;
  /** Set volume (0-100) */
  setVolume: (volume: number) => void;
  /** Set muted state */
  setMuted: (muted: boolean) => void;
  /** Toggle mute on/off */
  toggleMute: () => void;
  /** Enable/disable music */
  setEnabled: (enabled: boolean) => void;
  /** Set current track path */
  setTrack: (trackPath: string | null) => void;
  /** Set playing state (used by MusicPlayer) */
  setIsPlaying: (playing: boolean) => void;
  /** Play music */
  play: () => void;
  /** Pause music */
  pause: () => void;
  /** Toggle play/pause */
  togglePlayback: () => void;
  /** Register audio element for direct playback control */
  registerAudio: (element: HTMLAudioElement | null) => void;
  /** Audio element ref (for MusicPlayer to access) */
  audioRef: MutableRefObject<HTMLAudioElement | null>;
  /** Go to next track */
  nextTrack: () => void;
  /** Go to previous track */
  prevTrack: () => void;
  /** Load track manifest */
  loadManifest: () => Promise<void>;
  /** Select track by index and persist for current case */
  selectTrack: (index: number, caseId: string) => void;
  /** Get saved track for a case from localStorage */
  getSavedTrackForCase: (caseId: string) => string | null;
  /** Current case ID (for track persistence) */
  currentCaseId: string | null;
  /** Set current case ID */
  setCaseId: (caseId: string | null) => void;
}

interface MusicProviderProps {
  children: ReactNode;
}

// ============================================
// Context
// ============================================

const MusicContext = createContext<MusicContextValue | null>(null);

// ============================================
// Helper Functions
// ============================================

/** Get initial volume from localStorage or default */
function getInitialVolume(): number {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY_VOLUME);
    if (stored !== null) {
      const parsed = parseInt(stored, 10);
      if (!isNaN(parsed) && parsed >= 0 && parsed <= 100) {
        return parsed;
      }
    }
  }
  return DEFAULT_VOLUME;
}

/** Get initial muted state from localStorage or default */
function getInitialMuted(): boolean {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY_MUTED);
    return stored === "true";
  }
  return false;
}

/** Get initial enabled state from localStorage or default */
function getInitialEnabled(): boolean {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY_ENABLED);
    // Default to true if not set
    return stored !== "false";
  }
  return true;
}

/** Get saved track ID for a case from localStorage */
function getSavedTrackId(caseId: string): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem(`${STORAGE_KEY_TRACK_PREFIX}${caseId}`);
  }
  return null;
}

/** Save track ID for a case to localStorage */
function saveTrackId(caseId: string, trackId: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(`${STORAGE_KEY_TRACK_PREFIX}${caseId}`, trackId);
  }
}

// ============================================
// Provider Component
// ============================================

export function MusicProvider({ children }: MusicProviderProps) {
  const [volume, setVolumeState] = useState<number>(getInitialVolume);
  const [muted, setMutedState] = useState<boolean>(getInitialMuted);
  const [enabled, setEnabledState] = useState<boolean>(getInitialEnabled);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTrack, setCurrentTrack] = useState<string | null>(null);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [currentTrackIndex, setCurrentTrackIndex] = useState<number>(0);
  const [currentCaseId, setCurrentCaseId] = useState<string | null>(null);

  // Ref to audio element for direct synchronous playback control
  // This bypasses React's async state updates to respect browser autoplay policies
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Derive current track name from tracks and index
  const currentTrackName =
    tracks.length > 0 && currentTrackIndex < tracks.length
      ? tracks[currentTrackIndex].name
      : "No track loaded";

  // Load manifest from server
  const loadManifest = useCallback(async () => {
    try {
      const response = await fetch("/music/manifest.json");
      if (!response.ok) {
        console.warn(
          "[MusicContext] Failed to load manifest:",
          response.status,
        );
        return;
      }
      const manifest: MusicManifest = (await response.json()) as MusicManifest;
      setTracks(manifest.tracks);
    } catch (error) {
      console.warn("[MusicContext] Error loading manifest:", error);
    }
  }, []);

  // Get saved track for case
  const getSavedTrackForCase = useCallback((caseId: string): string | null => {
    return getSavedTrackId(caseId);
  }, []);

  // Select track by index and update audio
  const selectTrack = useCallback(
    (index: number, caseId: string) => {
      if (tracks.length === 0 || index < 0 || index >= tracks.length) return;

      const track = tracks[index];
      const trackPath = `/music/${track.file}`;

      setCurrentTrackIndex(index);
      setCurrentTrack(trackPath);

      // Save selection for this case
      saveTrackId(caseId, track.id);

      // Update audio source and play if was playing
      const audio = audioRef.current;
      if (audio) {
        const wasPlaying = !audio.paused;
        audio.src = trackPath;
        audio.load();
        if (wasPlaying && enabled) {
          audio.play().catch(() => {
            setIsPlaying(false);
          });
        }
      }
    },
    [tracks, enabled],
  );

  // Go to next track
  const nextTrack = useCallback(() => {
    if (tracks.length === 0 || !currentCaseId) return;
    const newIndex = (currentTrackIndex + 1) % tracks.length;
    selectTrack(newIndex, currentCaseId);
  }, [tracks, currentTrackIndex, currentCaseId, selectTrack]);

  // Go to previous track
  const prevTrack = useCallback(() => {
    if (tracks.length === 0 || !currentCaseId) return;
    const newIndex = (currentTrackIndex - 1 + tracks.length) % tracks.length;
    selectTrack(newIndex, currentCaseId);
  }, [tracks, currentTrackIndex, currentCaseId, selectTrack]);

  // Set case ID and initialize track for that case
  const setCaseId = useCallback((caseId: string | null) => {
    setCurrentCaseId(caseId);
  }, []);

  // Persist volume to localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY_VOLUME, String(volume));
    }
  }, [volume]);

  // Persist muted to localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY_MUTED, String(muted));
    }
  }, [muted]);

  // Persist enabled to localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY_ENABLED, String(enabled));
    }
  }, [enabled]);

  const setVolume = useCallback((newVolume: number) => {
    const clamped = Math.max(0, Math.min(100, newVolume));
    setVolumeState(clamped);
  }, []);

  const setMuted = useCallback((newMuted: boolean) => {
    setMutedState(newMuted);
  }, []);

  const toggleMute = useCallback(() => {
    setMutedState((prev) => !prev);
  }, []);

  const setEnabled = useCallback((newEnabled: boolean) => {
    setEnabledState(newEnabled);
    if (!newEnabled) {
      setIsPlaying(false);
    }
  }, []);

  const setTrack = useCallback((trackPath: string | null) => {
    setCurrentTrack(trackPath);
  }, []);

  // Register audio element for direct control
  const registerAudio = useCallback((element: HTMLAudioElement | null) => {
    audioRef.current = element;
  }, []);

  // Play music - calls audio.play() SYNCHRONOUSLY to respect browser autoplay policy
  // Must be called within a user gesture (click handler) to work
  const play = useCallback(() => {
    if (!enabled) {
      return;
    }

    // Direct synchronous playback - this is the key fix!
    // Browser autoplay policies require play() to be called synchronously
    // within a user gesture context, not in a useEffect callback
    const audio = audioRef.current;
    if (audio?.src) {
      audio
        .play()
        .then(() => {
          setIsPlaying(true);
        })
        .catch((error) => {
          // Playback blocked (shouldn't happen with user gesture)
          console.error("[MusicContext] audio.play() FAILED:", error);
          setIsPlaying(false);
        });
    }
  }, [enabled]);

  // Pause music - calls audio.pause() directly for immediate response
  const pause = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
    }
    setIsPlaying(false);
  }, []);

  const togglePlayback = useCallback(() => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  }, [isPlaying, play, pause]);

  const value: MusicContextValue = {
    volume,
    muted,
    enabled,
    isPlaying,
    currentTrack,
    tracks,
    currentTrackIndex,
    currentTrackName,
    setVolume,
    setMuted,
    toggleMute,
    setEnabled,
    setTrack,
    setIsPlaying,
    play,
    pause,
    togglePlayback,
    registerAudio,
    audioRef,
    nextTrack,
    prevTrack,
    loadManifest,
    selectTrack,
    getSavedTrackForCase,
    currentCaseId,
    setCaseId,
  };

  return (
    <MusicContext.Provider value={value}>{children}</MusicContext.Provider>
  );
}

// ============================================
// Exports
// ============================================

// Hook is exported from useMusic.ts to satisfy react-refresh
export { MusicContext };
export type { MusicContextValue, MusicProviderProps };
