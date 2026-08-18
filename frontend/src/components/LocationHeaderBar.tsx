/**
 * LocationHeaderBar Component
 *
 * Displays location context and horizontal navigation tabs.
 * - Location name and description (unframed)
 * - Placeholder for future location illustration
 * - Horizontal location tabs with keyboard shortcuts
 *
 * Preserves existing keyboard shortcuts (1-9) from LocationSelector.
 *
 * @module components/LocationHeaderBar
 * @since Phase 6.5
 */

import { useEffect, useCallback, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useTheme } from '../context/useTheme';
import type { LocationInfo, LocationResponse } from "../types/investigation";

// ============================================
// Types
// ============================================

interface LocationHeaderBarProps {
  /** Array of available locations */
  locations: LocationInfo[];
  /** Current location ID */
  currentLocationId: string;
  /** Location data (name, description) */
  locationData: LocationResponse | null;
  /** Callback when location is selected */
  onSelectLocation: (locationId: string) => void;
  /** Whether location change is in progress */
  changing?: boolean;
  /** Array of visited location IDs */
  visitedLocations?: string[];
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
  /** Show the first-use location navigation animation */
  showNavigationHint?: boolean;
}

// ============================================
// Sub-components
// ============================================

/**
 * Location illustration image component with convention-based auto-loading.
 * Loads illustrations from /locations/{locationId}.{format}
 * Uses modern formats (AVIF → WebP → PNG) with fallbacks.
 * Falls back to placeholder if image doesn't exist.
 */
interface LocationIllustrationImageProps {
  locationId: string;
  locationName: string;
  className?: string;
  /** Whether to lazy load (default: true for modal, false for thumbnail) */
  lazy?: boolean;
  /** Priority loading for above-fold images */
  priority?: boolean;
}

export function LocationIllustrationImage({
  locationId,
  locationName,
  className = "",
  lazy = true,
  priority = false,
}: LocationIllustrationImageProps) {
  const [hasError, setHasError] = useState(false);
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const { theme } = useTheme();

  // Try formats in order: AVIF → WebP → PNG
  // Using useEffect to probe for available formats
  useEffect(() => {
    setHasError(false);
    setImgSrc(null);

    const formats = [
      { ext: 'avif', type: 'image/avif' },
      { ext: 'webp', type: 'image/webp' },
      { ext: 'png', type: 'image/png' },
    ];

    let cancelled = false;

    const tryFormat = async (index: number) => {
      if (cancelled || index >= formats.length) {
        if (!cancelled && index >= formats.length) {
          setHasError(true);
        }
        return;
      }

      const format = formats[index];
      const url = `/locations/${locationId}.${format.ext}`;

      try {
        const response = await fetch(url, { method: 'HEAD' });
        const contentType = response.headers.get('Content-Type') ?? '';
        // Check both response.ok AND that Content-Type is an image
        // (Vite returns 200 with text/html for missing files)
        if (!cancelled && response.ok && contentType.startsWith('image/')) {
          setImgSrc(url);
          return;
        }
      } catch {
        // Format not available, try next
      }

      if (!cancelled) {
        void tryFormat(index + 1);
      }
    };

    void tryFormat(0);

    return () => {
      cancelled = true;
    };
  }, [locationId]);

  if (hasError) {
    return (
      <div
        className={`w-full h-full flex items-center justify-center ${theme.colors.bg.semiTransparent} ${className}`}
      >
        <span className={`${theme.colors.text.separator} text-xs ${theme.fonts.ui} uppercase tracking-wider`}>
          NO VISUAL RECORD
        </span>
      </div>
    );
  }

  if (!imgSrc) {
    return (
      <div
        className={`w-full h-full flex items-center justify-center ${theme.colors.bg.semiTransparent} ${className}`}
      >
        <span className={`${theme.colors.text.separator} text-xs ${theme.fonts.ui} uppercase tracking-wider animate-pulse`}>
          LOADING...
        </span>
      </div>
    );
  }

  return (
    <div className={`w-full h-full overflow-hidden relative ${className}`}>
      <img
        src={imgSrc}
        alt={locationName}
        className="w-full h-full object-cover object-center transition-all duration-500"
        style={{ width: '100%', height: '100%' }}
        loading={priority ? "eager" : lazy ? "lazy" : "eager"}
        decoding="async"
        onError={() => setHasError(true)}
      />

      {/* Scanline overlay */}
      <div
        className={`absolute inset-0 ${theme.effects.scanlines}`}
      ></div>
    </div>
  );
}

interface LocationTabProps {
  location: LocationInfo;
  isSelected: boolean;
  index: number;
  onClick: () => void;
  disabled?: boolean;
}

function LocationTab({
  location,
  isSelected,
  index,
  onClick,
  disabled = false,
}: LocationTabProps) {
  const { theme } = useTheme();

  return (
    <button
      onClick={onClick}
      disabled={disabled || isSelected}
      data-location-id={location.id}
      className={`
        px-4 py-2 ${theme.fonts.ui} text-sm uppercase tracking-wide transition-all duration-200
        border-b-2 active:opacity-80
        ${
          isSelected
            ? `${theme.colors.interactive.border} ${theme.colors.text.secondary} font-bold cursor-default`
            : `border-transparent ${theme.colors.text.tertiary} ${theme.colors.interactive.hover} ${theme.colors.border.hoverClass}`
        }
        ${disabled && !isSelected ? "opacity-50 cursor-not-allowed" : ""}
        focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:outline-none
      `}
      aria-pressed={isSelected}
      aria-label={`${isSelected ? "Current location" : "Go to"} ${location.name}`}
    >
      <div className="flex items-center gap-2">
        {/* Location name */}
        <span>{location.name}</span>
        {/* Keyboard shortcut hint — hidden on mobile */}
        <span className={`hidden lg:inline ${theme.colors.text.separator} text-xs`}>[{index + 1}]</span>
      </div>
    </button>
  );
}

interface LocationFootstepHintProps {
  locations: LocationInfo[];
  currentLocationId: string;
  containerRef: RefObject<HTMLDivElement | null>;
  visible: boolean;
}

interface FootstepPath {
  startX: number;
  endX: number;
}

interface FootstepPoint {
  x: number;
  y: number;
  angle: number;
}

const FOOTPRINT_INTERVAL_SECONDS = 1;
const FOOTPRINT_LIFETIME_SECONDS = 4;
const FOOTSTEP_PAUSE_SECONDS = 3;
const MIN_FOOTPRINT_SPACING = 26;
const FOOTSTEP_WAYPOINTS = [
  { x: 0, y: -6 },
  { x: 0.15, y: -15 },
  { x: 0.31, y: -8 },
  { x: 0.48, y: -16 },
  { x: 0.65, y: -7 },
  { x: 0.82, y: -15 },
  { x: 1, y: -8 },
];

function pointOnFootstepCurve(progress: number, path: FootstepPath) {
  const segmentCount = FOOTSTEP_WAYPOINTS.length - 1;
  const scaledProgress = Math.min(progress, 0.999999) * segmentCount;
  const index = Math.floor(scaledProgress);
  const t = scaledProgress - index;
  const p0 = FOOTSTEP_WAYPOINTS[Math.max(0, index - 1)];
  const p1 = FOOTSTEP_WAYPOINTS[index];
  const p2 = FOOTSTEP_WAYPOINTS[index + 1];
  const p3 = FOOTSTEP_WAYPOINTS[Math.min(FOOTSTEP_WAYPOINTS.length - 1, index + 2)];
  const t2 = t * t;
  const t3 = t2 * t;
  const interpolate = (a: number, b: number, c: number, d: number) =>
    0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
  const normalizedX = interpolate(p0.x, p1.x, p2.x, p3.x);

  return {
    x: path.startX + (path.endX - path.startX) * normalizedX,
    y: interpolate(p0.y, p1.y, p2.y, p3.y),
  };
}

function sampleFootstepPath(path: FootstepPath) {
  const resolution = 240;
  const curve = Array.from({ length: resolution + 1 }, (_, index) =>
    pointOnFootstepCurve(index / resolution, path),
  );
  const cumulativeLengths = [0];

  for (let index = 1; index < curve.length; index += 1) {
    const previous = curve[index - 1];
    const current = curve[index];
    cumulativeLengths.push(cumulativeLengths[index - 1] + Math.hypot(current.x - previous.x, current.y - previous.y));
  }

  const totalLength = cumulativeLengths[cumulativeLengths.length - 1];
  const footprintCount = Math.max(10, Math.min(22, Math.floor(totalLength / MIN_FOOTPRINT_SPACING) + 1));
  return Array.from({ length: footprintCount }, (_, footprintIndex): FootstepPoint => {
    const targetLength = totalLength * footprintIndex / (footprintCount - 1);
    let curveIndex = cumulativeLengths.findIndex((length) => length >= targetLength);
    if (curveIndex <= 0) curveIndex = 1;
    const previousLength = cumulativeLengths[curveIndex - 1];
    const nextLength = cumulativeLengths[curveIndex];
    const segmentProgress = nextLength === previousLength ? 0 : (targetLength - previousLength) / (nextLength - previousLength);
    const previous = curve[curveIndex - 1];
    const next = curve[curveIndex];
    const x = previous.x + (next.x - previous.x) * segmentProgress;
    const y = previous.y + (next.y - previous.y) * segmentProgress;
    const angle = Math.atan2(next.y - previous.y, next.x - previous.x);
    const strideOffset = footprintIndex % 2 === 0 ? -3.5 : 3.5;

    return {
      x: x - Math.sin(angle) * strideOffset,
      y: y + Math.cos(angle) * strideOffset,
      angle: angle * 180 / Math.PI + 90,
    };
  });
}

function FootprintMark({ side }: { side: 1 | -1 }) {
  return (
    <svg
      aria-hidden="true"
      data-footprint-mark="true"
      className="h-[18px] w-2"
      viewBox="0 0 12 24"
      fill="currentColor"
      style={{
        transform: `scaleX(${side})`,
        transformOrigin: 'center',
      }}
    >
      <path
        data-footprint-part="forefoot"
        d="M6.2.8C9.3.8 11 3.2 10.5 6.7c-.4 3-2.2 5.3-4.7 5.1-2.7-.2-4.6-2.5-4.3-5.7C1.8 2.9 3.4.8 6.2.8Z"
      />
      <path
        data-footprint-part="heel"
        d="M3.4 15.2c.8-1.5 4.4-1.5 5.2 0 .9 1.7 1.1 4.9.2 6.8-.8 1.6-4.8 1.6-5.6 0-.9-1.9-.7-5.1.2-6.8Z"
      />
    </svg>
  );
}

function LocationFootstepHint({
  locations,
  currentLocationId,
  containerRef,
  visible,
}: LocationFootstepHintProps) {
  const { isDark } = useTheme();
  const prefersReducedMotion = useReducedMotion();
  const [path, setPath] = useState<FootstepPath | null>(null);

  const currentIndex = locations.findIndex((location) => location.id === currentLocationId);
  const startIndex = currentIndex >= 0 ? currentIndex : 0;
  const targetIndex = startIndex === locations.length - 1 ? startIndex - 1 : startIndex + 1;
  const startLocationId = locations[startIndex]?.id ?? '';
  const targetLocationId = locations[targetIndex]?.id ?? '';

  useLayoutEffect(() => {
    if (!visible || prefersReducedMotion || !startLocationId || !targetLocationId) {
      setPath(null);
      return;
    }

    const updatePath = () => {
      const container = containerRef.current;
      if (!container) return;

      const buttons = Array.from(container.querySelectorAll<HTMLButtonElement>('[data-location-id]'));
      const startButton = buttons.find((button) => button.dataset.locationId === startLocationId);
      const targetButton = buttons.find((button) => button.dataset.locationId === targetLocationId);
      if (!startButton || !targetButton) return;

      const containerRect = container.getBoundingClientRect();
      const startRect = startButton.getBoundingClientRect();
      const targetRect = targetButton.getBoundingClientRect();
      const movingRight = targetRect.left > startRect.left;
      setPath(movingRight
        ? {
            startX: startRect.left - containerRect.left + startRect.width * 0.18,
            endX: targetRect.left - containerRect.left + targetRect.width * 0.72,
          }
        : {
            startX: startRect.right - containerRect.left - startRect.width * 0.18,
            endX: targetRect.right - containerRect.left - targetRect.width * 0.72,
          });
    };

    updatePath();
    const retryMeasurement = window.setTimeout(updatePath, 0);
    window.addEventListener('resize', updatePath);

    let resizeObserver: ResizeObserver | undefined;
    if (typeof ResizeObserver !== 'undefined') {
      const container = containerRef.current;
      if (container) {
        resizeObserver = new ResizeObserver(updatePath);
        resizeObserver.observe(container);
      }
    }

    return () => {
      window.clearTimeout(retryMeasurement);
      window.removeEventListener('resize', updatePath);
      resizeObserver?.disconnect();
    };
  }, [containerRef, prefersReducedMotion, startLocationId, targetLocationId, visible]);

  if (!visible || prefersReducedMotion || !path) return null;

  const footprints = sampleFootstepPath(path);
  const cycleSeconds = 0.3 + (footprints.length - 1) * FOOTPRINT_INTERVAL_SECONDS
    + FOOTPRINT_LIFETIME_SECONDS + FOOTSTEP_PAUSE_SECONDS;

  return (
    <div
      aria-hidden="true"
      data-testid="location-footstep-hint"
      data-footprint-interval-seconds={FOOTPRINT_INTERVAL_SECONDS}
      data-footprint-lifetime-seconds={FOOTPRINT_LIFETIME_SECONDS}
      className={`absolute inset-0 z-10 pointer-events-none ${isDark ? 'text-gray-300' : 'text-gray-700'}`}
    >
      {footprints.map((footprint, index) => {
        const revealStart = 0.3 + index * FOOTPRINT_INTERVAL_SECONDS;
        const revealEnd = revealStart + 0.2;
        const fadeStart = revealStart + 3;
        const fadeEnd = revealStart + FOOTPRINT_LIFETIME_SECONDS;

        return (
          <motion.div
            key={`${startLocationId}-${targetLocationId}-${index}`}
            data-footprint-position="true"
            data-footprint-x={footprint.x}
            data-footprint-y={footprint.y}
            data-footprint-angle={footprint.angle}
            className="absolute left-0 top-0 -translate-x-1/2 -translate-y-1/2"
            style={{ x: footprint.x, y: footprint.y, rotate: footprint.angle }}
            animate={{ opacity: [0, 0, 0.58, 0.58, 0, 0] }}
            transition={{
              duration: cycleSeconds,
              repeat: Infinity,
              ease: 'linear',
              times: [0, revealStart / cycleSeconds, revealEnd / cycleSeconds, fadeStart / cycleSeconds, fadeEnd / cycleSeconds, 1],
            }}
          >
            <FootprintMark side={index % 2 === 0 ? -1 : 1} />
          </motion.div>
        );
      })}
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function LocationHeaderBar({
  locations,
  currentLocationId,
  locationData,
  onSelectLocation,
  changing = false,
  visitedLocations: _visitedLocations = [],
  loading = false,
  error = null,
  showNavigationHint = false,
}: LocationHeaderBarProps) {
  const { theme } = useTheme();
  const tabsContainerRef = useRef<HTMLDivElement>(null);

  // Keyboard shortcuts: 1-9 to select locations
  const handleKeydown = useCallback(
    (e: KeyboardEvent) => {
      // Ignore if user is typing in an input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      // Ignore if a modal is open (common role="dialog")
      if (document.querySelector('[role="dialog"]')) {
        return;
      }

      // Only handle number keys 1-9
      const num = parseInt(e.key, 10);
      if (num >= 1 && num <= 9 && num <= locations.length) {
        e.preventDefault();
        const targetLocation = locations[num - 1];
        if (targetLocation && targetLocation.id !== currentLocationId) {
          onSelectLocation(targetLocation.id);
        }
      }
    },
    [locations, currentLocationId, onSelectLocation],
  );

  // Register keyboard listener
  useEffect(() => {
    document.addEventListener("keydown", handleKeydown);
    return () => document.removeEventListener("keydown", handleKeydown);
  }, [handleKeydown]);

  // Loading state for location data
  if (!locationData && loading) {
    return (
      <div className={`${theme.colors.bg.primary} p-4`}>
        <div className={`animate-pulse ${theme.colors.text.tertiary} ${theme.fonts.ui}`}>
          Loading location...
        </div>
      </div>
    );
  }

  // Error state
  if (error && !locationData) {
    return (
      <div className={`${theme.colors.bg.primary} p-4`}>
        <span className={`${theme.colors.state.error.text} ${theme.fonts.ui} text-sm`}>Error: {error}</span>
      </div>
    );
  }

  return (
    <div className={`${theme.colors.bg.primary}`}>
      {/* Horizontal Location Tabs */}
      <div className="-mt-3 flex items-start justify-center gap-1 overflow-x-auto pt-5">
        {locations.length === 0 ? (
          <span className={`${theme.colors.text.muted} text-sm ${theme.fonts.ui} py-2`}>
            No locations available
          </span>
        ) : (
          <div ref={tabsContainerRef} className="relative flex min-w-max items-center justify-center gap-1 lg:min-w-full">
            {locations.map((location, index) => (
              <LocationTab
                key={location.id}
                location={location}
                isSelected={currentLocationId === location.id}
                index={index}
                onClick={() => onSelectLocation(location.id)}
                disabled={changing}
              />
            ))}

            {/* Changing indicator */}
            {changing && (
              <span className={`ml-4 ${theme.colors.text.tertiary} text-sm ${theme.fonts.ui} animate-pulse`}>
                Traveling...
              </span>
            )}
            <LocationFootstepHint
              locations={locations}
              currentLocationId={currentLocationId}
              containerRef={tabsContainerRef}
              visible={showNavigationHint && !changing && locations.length > 1}
            />
          </div>
        )}
      </div>
    </div>
  );
}
