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
