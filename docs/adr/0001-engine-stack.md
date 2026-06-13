# ADR 0001: Engine stack and boundaries

## Status

Accepted

## Decision

Use Python 3.13 managed exclusively through `uv`. Use pyglet for the window and input,
ModernGL for OpenGL 3.3 rendering, and NumPy arrays for voxel data and mesh buffers.

Application and domain boundaries use typed Python APIs. Per-frame world and rendering
hot paths use data-oriented arrays and avoid dependency injection and per-voxel objects.

