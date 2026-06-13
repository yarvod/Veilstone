# Progress

## Phase 01 - Project skeleton

### Completed

- [x] Project metadata targets Python 3.13 and uses `uv`.
- [x] Ruff, pytest, and Pyright are configured.
- [x] Modular package, settings, logging, and CLI commands are present.
- [x] Placeholder server and host modes have automated smoke paths.
- [x] Base project skeleton committed as `3e51c4b phase-01.items-01-03`.
- [x] Pyglet window creates a ModernGL 3.3 context and clears the frame.
- [x] Fixed-rate camera movement, mouse look, and FPS/debug overlays are implemented.
- [x] Client shell committed as `5e0ee3c phase-01.items-04-06`.
- [x] Client, server, and host smoke paths pass on macOS with OpenGL 4.1 Metal.
- [x] Phase gate passes: 9 tests, Ruff, Ruff format check, and Pyright.

### Failed checks

None recorded.

### Performance notes

The empty client shell runs with a fixed 60 Hz update and a variable render loop.
Meshing performance is not applicable until Phase 4.

### Known bugs

None recorded.

### Next recommended tasks

- Start block registry, coordinate types, and chunk storage.

## Phase 02 - OpenGL client shell

### Completed

- [x] Shader files load from package resources.
- [x] GLSL programs compile through the active ModernGL context.
- [x] Development hot reload checks timestamps and keeps the previous program on failure.
- [x] `F5` forces a shader reload.
- [x] Client smoke test compiles the debug shader on macOS OpenGL 4.1 Metal.
- [x] Shader layer committed as `39abdea phase-02.items-01-03`.

### In progress

- [ ] Phase 3 block registry and chunk storage.

### Failed checks

None recorded.

## Phase 17 - UI polish and settings (foundation pulled forward)

### Completed

- [x] `uv run python -m voxel_sandbox` is the player-facing entry point.
- [x] Public CLI no longer exposes a separate player-facing `host` mode.
- [x] Developer CLI retains `server`, `client --connect`, and benchmark commands.
- [x] Entry-point contract corrected in `8a46ce0 refactor.phase-17.item-01`.
- [x] Main Menu exposes Singleplayer, Multiplayer, Settings, and Exit.
- [x] Singleplayer exposes Create World and Load World prototype actions.
- [x] Multiplayer exposes Join LAN World and Direct Connect placeholders.
- [x] Gameplay `Escape` opens a Pause Menu with Open to LAN.
- [x] Menu transitions are covered by unit tests.

### In progress

- [ ] Real world creation/loading, settings controls, and networking remain in their phases.
- [ ] Singleplayer local authoritative server composition remains for Phase 13.

### Known bugs

None recorded.

### Performance notes

Automatic shader timestamp checks run twice per second and do no source reads when unchanged.

### Known bugs

None recorded.
