# Changelog

## [Unreleased]

### Fixed
- **Font crash on Windows** — replaced hardcoded "Minecraft" font with platform font (Segoe UI / Menlo)
- **World selection buttons broken** — "Create New World" and "Cancel" passed strings instead of MenuCommand enum
- **Enter key doesn't load world** — on Singleplayer screen, Enter now loads selected world
- **World list keyboard navigation** — Up/Down arrows were trapped in text_input block
- **Chunk lighting seams** — neighbor chunks now remeshed when new chunk loads
- **WorldCard selection not visible** — added background + text color change for selected state
- **Label.color not propagating** — added property setter to update underlying pyglet label
- **Draw order flicker** — world list now updates before draw() call

---

## Format

### Added — new features
### Changed — changes in existing functionality
### Fixed — bug fixes
### Removed — removed features
### Security — vulnerability fixes
