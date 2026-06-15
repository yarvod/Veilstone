# Changelog

## [Unreleased]
### Added
- Player names rendered above remote players' heads in multiplayer.
- Visual representation of the active item in hand.
- "Twilight Forest" related references integrated in TZ.

### Fixed
- Fixed bug causing random teleportation due to overly strict bounds.
- Fixed `TypeError` crash in `on_key_press` with `NoneType` symbol.
- Fixed active hotbar slot selection border (now visibly yellow and prominent).
- Fixed menu font overlapping on Windows by defaulting to `Consolas` instead of `Arial`.
- Fixed mob texture UV mapping being inverted (upside down and backwards).
- Re-assigned remote player geometry to a humanoid form (temporarily using zombie skin).
