# UI Performance Upgrade Backlog

## Phase 0

### UPERF-001: Phase 0 - Baseline profiling before changes
Status: done
Priority: P0
Area: docs, render, ui

#### Problem
Need to stop guessing performance bottlenecks and measure real frame times.

#### Hypothesis
Adding a frame profiler will show where CPU time is spent.

#### Plan
- [x] Add frame timing fields
- [x] Add disable_hud flag
- [x] Display in debug overlay

## Phase 1

### UPERF-002: UI/HUD performance triage
Status: done
Priority: P0
Area: ui, render

#### Problem
The UI and HUD might be taking too much CPU due to frequent text updates and unbatched rendering.

#### Hypothesis
Batching static UI elements and throttling text updates to 5Hz will reduce the CPU overhead significantly.

#### Plan
- [x] Throttle debug and HUD text updates to 0.2s.
- [x] Create a `pyglet.graphics.Batch` for the HUD.
- [x] Convert hotbar, crosshair, and labels to use the batch.
- [x] Fix smoke tests (flaky text rendering on Retina screens).

#### Acceptance
- [x] Visuals are the same.
- [x] Tests pass (`uv run pytest -m smoke` green).

## Phase 2

### UPERF-003: New Game UI Toolkit
Status: doing
Priority: P0
Area: ui

#### Problem
Menu drawing is hardcoded, manual, and doesn't scale well for complex settings, world cards, and styling.

#### Hypothesis
A simple UI framework (Theme, Widgets, Layouts, Screens) will allow much richer menus and interactive UI.

#### Plan
- [ ] Create UI foundation (`theme.py`, `geometry.py`).
- [ ] Create core `widgets.py` (Label, Button, Panel, ListBox).
- [ ] Create `layout.py` helpers (VBox, HBox).
- [ ] Refactor existing `menu.py` into new `screens.py` using the widgets.
- [x] Implement Main Menu redesign.
- [x] Implement World Selection Cards.

#### Acceptance
- [x] UI looks polished and game-ready.
- [x] Mouse and keyboard interactions work.
- [x] All tests pass.

### UPERF-004: Fast Frustum Culling

Status: done
Priority: P0
Area: render

#### Problem
Frustum culling is allocating NumPy arrays or objects per chunk section per frame, creating heavy CPU overhead.

#### Hypothesis
Eliminating per-frame allocations during culling will drop frame latency and improve overall FPS at high render distances.

#### Plan
- [x] Optimize math in `AABB.in_frustum()` / `Frustum` checks.
- [x] Remove `numpy` allocations in tight inner loops.
- [x] Benchmark rendering performance.

#### Acceptance
- [x] Performance improved.
- [x] Tests pass.

### UPERF-005: Separate Render from Streaming/Update

Status: done
Priority: P1
Area: streaming

#### Problem
The render path performs heavy streaming/update work (chunk generation/mesh loading scheduling), causing stuttering and inconsistent frame times.

#### Hypothesis
Moving heavy tasks like `streamer.update()` out of `on_draw` and into a fixed-rate update loop (or throttling them) will stabilize the frame rate.

#### Plan
- [x] Move `streamer.update` to fixed update or throttle it.
- [x] Ensure `on_draw` only dispatches rendering and light GPU uploads.

#### Acceptance
- [x] `on_draw` is free of chunk streaming logic.
- [x] Frame rate is visibly smoother during movement.
- [x] All tests pass.

### UPERF-006: Fast Singleplayer Mode

Status: done
Priority: P1
Area: network

#### Problem
Singleplayer uses the local LAN server via sockets (`LanServer` and `ClientSession`). This introduces IPC overhead, packet serialization, and context switching even for local standalone gameplay, reducing performance on weak CPUs.

#### Hypothesis
Bypassing the network layer and directly mutating the local world state via a `LocalWorldAuthority` will significantly reduce latency and save CPU cycles.

#### Plan
- [x] Implement `WorldAuthority` interface (`LocalWorldAuthority` vs `NetworkWorldAuthority`).
- [x] Use `LocalWorldAuthority` by default for singleplayer, skipping socket initialization until "Open to LAN" is invoked.
- [x] Retain existing `ClientSession` approach for true multiplayer modes.

#### Acceptance
- [x] Singleplayer world loads without creating a local network session.
- [x] Multiplayer / "Open to LAN" remains functional.
- [x] Existing protocol and multiplayer tests pass.

### UPERF-007: Remesh/Relight Granularity

Status: done
Priority: P2
Area: render

#### Problem
Changing a single block indiscriminately triggers relighting or remeshing for entire 3x3 chunk neighborhoods, causing major spikes in frame time during building/mining.

#### Hypothesis
Using dirty section queues to carefully selectively remesh only the modified section (and adjacent sections if the block touches a border) without full chunk relights for non-light-emitting blocks will eliminate spikes during block placement/breaking.

#### Plan
- [x] Implement dirty section queue (`dirty_opaque_sections`, `dirty_water_sections`). (We mapped this to `mesh_worker.submit` queue directly).
- [x] Only mark neighbor sections dirty if a block touches their border.
- [x] Skip lighting update if a block change (solid -> air) does not affect light sources or transparency.
- [x] Process dirty queues incrementally per frame.

#### Acceptance
- [x] Breaking/placing blocks does not cause a massive FPS spike.
- [x] Visual boundaries update correctly.
- [x] Lighting rules stay intact for skylight/lanterns.

### UPERF-008: Mesh task batching

Status: done
Priority: P2
Area: render

#### Problem
Section-level process tasks may be too fine-grained. IPC and serialization can negate multiprocessing benefits.

#### Hypothesis
Batching sections into chunks (`submit_chunk`) will reduce IPC overhead and improve overall sections/sec generated, especially on process backend.

#### Plan
- [x] Update `benchmark_mesher` to support testing section vs chunk batching across backends.
- [x] Run benchmarks.
- [x] Implement `submit_chunk` in `SectionMeshWorker` returning multiple sections.
- [x] Switch `_schedule_chunk` to use `submit_chunk`.

#### Acceptance
- [x] Fewer futures generated.
- [x] IPC overhead reduced, proven by benchmarks (process batching -> 1718 sections/sec vs 1650).
- [x] Tests pass without regression.

