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
