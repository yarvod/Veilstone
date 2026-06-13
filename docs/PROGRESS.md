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

## Phase 03 - Blocks and chunks

### Completed

- [x] Immutable `BlockDef` and validated read-only `BlockRegistry`.
  - commit: `a846ccb phase-03.items-01-02`
- [x] `ChunkCoord`, `SectionCoord`, and negative world coordinate conversion.
- [x] NumPy-backed `ChunkSection` arrays for blocks, lighting, and metadata.
- [x] Dirty flags, revision tracking, `Chunk`, `World` protocol, and `InMemoryWorld`.
  - commit: `b93c292 phase-03.items-03-08`
- [x] Block registry, coordinate, chunk storage, and world get/set tests.

### In progress

- [ ] Phase 4 visible-face meshing and first rendered section.

### Failed checks

None recorded.

## Phase 04 - Basic meshing and rendering

### Completed

- [x] Visible-face mesher emits indexed position/UV/normal vertex data.
  - commit: `6c9da62 phase-04.items-01-02`
- [x] Programmatically generated original block atlas with stone, dirt, and grass tiles.
- [x] ModernGL VBO/IBO upload and one draw call for a generated section.
  - commit: `757a957 phase-04.items-03-07`
- [x] Section-keyed GPU mesh cache and AABB frustum culling.
  - commit: `7ff01f2 phase-04.items-08-09`
- [x] Debug overlay reports faces, triangles, and draw calls.
- [x] Hidden client smoke renders both the menu and 3D world paths.

### In progress

- [ ] Phase 5 deterministic terrain generation and chunk streaming.

### Failed checks

None recorded.

### Performance notes

Visible-face benchmark for a half-solid `16^3` section: approximately 5.2 ms average,
1024 faces, and 2048 triangles on the current Apple Silicon development machine.
This exceeds the 2 ms target and is tracked as optimization debt before broad streaming.

### Known bugs

- Visible-face meshing is correct but currently above its target CPU budget.

### Performance notes

Voxel storage uses dense NumPy arrays: `uint16` block IDs and `uint8` auxiliary fields.
No Python object is created per voxel.

### Known bugs

None recorded.

### Performance notes

Automatic shader timestamp checks run twice per second and do no source reads when unchanged.

### Known bugs

None recorded.
