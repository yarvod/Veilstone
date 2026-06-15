# Changelog

## Unreleased

### Added

- Original deterministic player skin and articulated remote-player presentation.
- Remote-player name tags, replicated facing yaw, and a two-window multiplayer avatar smoke test.
- Pixel-heart health HUD, first-person hand/item presentation, and an original normalized hurt sound.
- Mob hit knockback and passive flee response.
- `docs/BUGS.md` as the short operational bug registry.

### Changed

- Entity cubes now use explicit per-face UV orientation instead of one shared quad mapping.
- Entity and shadow shaders use the same yaw convention as AI forward movement.
- Cow grazing lowers the head with the correct rotation sign.
- Windows UI labels select Segoe UI through one platform-font policy.
- The player list omits the duplicated local network snapshot.
- Menu text now renders with alpha blending and depth test disabled during menu rendering on Windows.

### Fixed

- Prevented `on_key_press` from crashing when Pyglet supplies a `None` key symbol.
- Stopped delayed echoed local snapshots from moving the player back toward an old position.
- Removed the second bottom-left FPS counter while retaining the normal upper-left HUD.
- Corrected upside-down, mirrored, and backward mob/player face presentation.
- Made passive and hostile mobs spawn at their actual species maximum health.

### Verification

- `uv run ruff check src tests scripts`
- `uv run pyright`
- `uv run pytest -q` (`191 passed`)
- Rendered entity/HUD QA used only original generated assets.

No Minecraft textures, sounds, models, or source code were copied.
