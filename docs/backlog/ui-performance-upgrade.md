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
