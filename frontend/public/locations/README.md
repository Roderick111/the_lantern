# Location Illustrations

This directory contains location illustrations for the The Lantern game.

## Modern Format Support (2025) ✅

All images have been converted to modern formats with automatic fallback:

```
locations/
  library.avif             # AVIF - Best compression (63-133KB, ~93-96% smaller)
  library.webp             # WebP - Good compression (99-127KB, ~93-94% smaller)
  library.png              # PNG - Legacy fallback (1.5-2.0MB)
```

**Conversion completed:**
- Run `bun run convert-images` to update optimized formats after adding new images
- Script automatically converts both `/locations/` and `/portraits/` directories
- Uses Sharp library for high-quality conversion (AVIF q75, WebP q85)

## Convention

Name images by their location ID:

```
locations/
  library.{avif,webp,png}              # Library Main Hall
  restricted_section.{avif,webp,png}   # The Sealed Stacks - Crime Scene
  study_alcove.{avif,webp,png}         # Study Alcove (Hidden)
  librarian_office.{avif,webp,png}     # Miss Hawthorne's Office
```

## Auto-Loading

The `LocationIllustrationImage` component automatically loads illustrations with format fallback:
1. Tries AVIF first (best compression)
2. Falls back to WebP (good compression)
3. Falls back to PNG (legacy support)
4. Shows placeholder if none exist

## Image Specifications

- **Format**: AVIF (preferred) → WebP → PNG (fallback)
- **Aspect Ratio**: Landscape/rectangular (16:9 or similar)
- **Size**:
  - AVIF: < 150KB (excellent compression)
  - WebP: < 200KB (good compression)
  - PNG: < 500KB (fallback only)
- **Dimensions**: 1200x800px recommended (will be responsive)
- **Quality**: 75-85 for AVIF/WebP, 90 for PNG
- **Style**: Match the magical detective aesthetic with terminal/noir vibes

## Performance Features

- **Modern formats**: AVIF and WebP reduce file size by 30-70%
- **Native lazy loading**: Modal images load only when opened
- **Priority loading**: Header thumbnail loads immediately (above-fold)
- **Async decoding**: Non-blocking image decode
- **Scanline overlay**: Applied automatically for terminal aesthetic
- **Corner brackets**: Terminal theme decoration
- **Fallback support**: Graceful degradation to PNG
