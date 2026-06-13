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

### In progress

- [ ] Phase 2 shader loading and hot reload.

### Failed checks

None recorded.

### Performance notes

The empty client shell runs with a fixed 60 Hz update and a variable render loop.
Meshing performance is not applicable until Phase 4.

### Known bugs

None recorded.

### Next recommended tasks

- Add shader loading and development hot reload.
- Start block registry, coordinate types, and chunk storage.
