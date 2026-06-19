# Veilstone Architecture Stabilization

This document is the working architecture target for Veilstone. It is not a demand to move every file immediately. The goal is to keep every PR small, keep the game runnable after each step, and make future gameplay work testable without a Pyglet window or OpenGL context.

## Current Map

Current package responsibilities are already partly separated:

- `voxel_sandbox.app`: process entry points, settings, paths, command parsing, crash/package bootstrapping.
- `voxel_sandbox.domain`: block, item, inventory, biome, crafting, progression data and pure rules.
- `voxel_sandbox.engine`: chunk data, physics, fluids, generation, lighting, events, ECS, authority, game state, gameplay constants.
- `voxel_sandbox.infrastructure`: storage and logging implementations.
- `voxel_sandbox.network`: LAN server/client/session messages, discovery, interpolation.
- `voxel_sandbox.audio`: audio bus, backend, director, event mapping.
- `voxel_sandbox.render`: Pyglet/ModernGL window, world scene, UI, controllers, camera, texture packs, meshes, shaders.
- `tests`: already includes unit, integration, and smoke markers.

The main instability is ownership, not missing packages. Several outer-adapter objects still construct or mutate application and simulation dependencies directly.

## Current Hotspots

`GameWindow` in `render/window.py` is still the practical composition root. It creates or owns settings-derived renderer configuration, audio runtime, camera, world renderer, player controller, key state, item registry, inventory, hotbar, recipe book, entity simulation, structure world, entity renderer, sky renderer, controllers, network session, LAN server, authority, persistence restore, autosave, chunk streaming, population maintenance, input, update, and draw coordination.

Controllers still receive the whole window:

- `GameplayController(self)` parses commands and mutates `world_renderer`, `settings`, persisted settings, player position, LAN structures, texture packs, renderer mesh caches, and UI status.
- `HudController(self)` reads many window fields and owns Pyglet labels directly.
- `NetworkController(self)` mutates network session, authority, structure world, remote chunks, entities, menu state, status text, and renderer remote mode.

`DemoWorldRenderer` in `render/world_scene.py` owns more than rendering. It loads block and biome registries, creates `WorldStorage`, creates `TerrainGenerator`, owns `ChunkStreamer`, runs fluid and lighting updates, imports texture packs, creates mesh workers, owns GPU resources, performs raycasts and block mutation, drives streaming, and handles autosave. This makes rendering hard to test and makes world simulation depend on a GPU-facing class.

Resource pack application is spread across command/UI/render boundaries. The target is one application use case so `/resourcepack`, Settings UI, and future pack reload commands all call the same workflow.

## Target Direction

Dependencies point inward:

```text
domain
  <- simulation/engine
  <- application
  <- presentation, infrastructure, audio, network adapters
```

Rules:

- `domain` contains pure data and rules. It does not import `render`, `app`, `network`, `infrastructure`, `audio`, Pyglet, ModernGL, storage, or user settings files.
- `simulation` or the current `engine` owns player/world/fluids/mobs/generation systems. It does not import window, UI, render controllers, Pyglet, or ModernGL.
- `application` owns sessions, use cases, orchestration, and ports. It may know domain and simulation abstractions, but not Pyglet or ModernGL.
- `presentation` is the outer adapter for Pyglet window, input, UI, render, camera, and GPU resources. It calls application use cases and renders snapshots/view data.
- `infrastructure` implements storage, settings persistence, resource loading, and future resource-pack cache ports.
- `audio` and `network` are external subsystems. Application code talks to them through useful ports rather than concrete window-owned services.
- Composition root is the only place concrete implementations are assembled.

This is not enterprise layering for its own sake. It should make water movement testable without a window, terrain generation testable without a renderer, mob spawning testable without GPU state, and resource pack application shared between UI and commands.

## Target Packages

Do not move everything at once. Use this as the destination shape:

- `domain`: clean block/item/inventory/biome/crafting/progression data and pure rules.
- `simulation`: player, world, fluids, mobs, generation, lighting, spawning, and deterministic systems. The existing `engine` package can migrate toward this role gradually.
- `application`: `GameSession`, `WorldSession`, use cases, commands, ports, and runtime factories.
- `infrastructure`: storage, settings store, file/resource loading, resource-pack discovery/cache implementations.
- `presentation`: Pyglet window, input, UI, render, camera, scene renderers, HUD, menu screens.
- `audio`: audio adapter plus `AudioPort` implementation.
- `network`: session/server/client adapters plus `NetworkPort` or `SessionPort` implementation.
- `app/composition.py`: manual wiring root and runtime contexts.

## Lifetime And Ownership

`AppRuntime` is application-lifetime state. It should own settings, paths, event bus, audio, content registries, texture pack service, and settings store.

`WorldRuntime` is active-world state. It should own active world storage, block registry, generation, streaming, player state, entity world, simulation systems, and a renderer facade/port for presentation updates.

`GameWindow` should receive an already-built runtime and delegate update/draw/input. During migration, `GameWindow` can keep compatibility properties, but new construction should move into factories behind `app/composition.py`.

## Ports

Use protocols only where they remove real coupling:

- `AudioPort`: emit sound/music events and update listener state.
- `EventSink` / `EventBus`: publish game events.
- `SettingsStorePort`: load/save user settings.
- `WorldStoragePort`: load/save chunks, player, metadata, structures.
- `BlockWorldPort`: read/write block ids for simulation systems.
- `CollisionWorld`: solidity/fluid checks and collision queries.
- `WorldQuery`: terrain height, biome, light, spawn checks, nearby entities.
- `WorldRenderPort`: remesh, apply atlas, update remote/local render mode, present world snapshots.
- `TexturePackServicePort`: discover, validate, load, cache, and apply packs.
- `NetworkPort` / `SessionPort`: connect, send input/actions, consume messages.
- `ClockPort`: deterministic time source where tests need it.

Do not create interfaces for pure functions, dataclasses, or one-line helpers.

## Controller Migration

New controllers and use cases must not accept `GameWindow`.

Examples:

- `ApplyResourcePackUseCase(TexturePackServicePort, WorldRenderPort, SettingsStorePort)` returns an application result with status and warnings.
- `SwitchWorldUseCase(WorldStorageFactory, WorldRuntimeFactory, CurrentWorldState)` returns the new `WorldRuntime`.
- `PlayerMovementSystem(PlayerState, PlayerInput, CollisionWorld)` updates simulation state without Pyglet.
- `MobSpawnSystem(SpawnRules, WorldQuery, EntityWorld)` spawns entities without render imports.

UI should call a use case and display the result. It should not directly mutate renderer internals, settings persistence, storage, or network sessions.

## Renderer Boundary

Split `DemoWorldRenderer` gradually:

- `WorldRuntime` / simulation owns storage, generator, streamer, fluids, lighting, block registry, and world mutation.
- `WorldSceneRenderer` owns GPU resources, shaders, mesh caches, draw calls, shadows, sky-facing render state, and camera-facing draw inputs.
- `TexturePackService` owns resource pack discovery, loading, validation, cache lookup/write, and atlas creation.
- `MeshService` owns mesh generation, scheduling, worker lifecycle, and upload-ready mesh data.

The renderer draws the world. It should not create or own world persistence, terrain generation, chunk streaming, or gameplay registries.

## Import Linter

Run:

```bash
uv run lint-imports
```

Current enforced contract:

- `voxel_sandbox.domain` must not import `app`, `audio`, `infrastructure`, `network`, or `render`.

Staged contracts to add as migrations land:

1. `domain` remains independent from all external adapters. This is enforced now.
2. `engine` / future `simulation` must not import render window, menu UI, render controllers, Pyglet, or ModernGL.
3. `application` must not import Pyglet or ModernGL.
4. `presentation` may import `application`; `application` must not import `presentation`.
5. `domain` and `simulation` must not import `infrastructure` directly. Storage and settings access goes through ports wired in composition.

If a future contract finds existing violations, add narrow temporary exceptions with a `TODO(architecture)` note and a named removal step in `docs/WORKPLAN.md`.

## Quality Checks

Architecture checks should run with the normal quality gate:

```bash
uv run lint-imports
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

CI should add `uv run lint-imports` before tests once the command is stable on all supported runners.

## Adding Features

For new gameplay work:

1. Put pure data and rules in `domain`.
2. Put deterministic state updates in `simulation` or the current `engine` package.
3. Add an application use case if the feature coordinates settings, storage, network, render, audio, or UI status.
4. Let presentation call the use case and render snapshots.
5. Test the system without `GameWindow` first. Add integration tests only for the wiring.

Examples:

- Water movement: test fluid steps against a `BlockWorldPort` fake.
- Twilight-like generation: test generator/pipeline output without `DemoWorldRenderer`.
- Mob spawning: test spawn rules using a `WorldQuery` fake and `EntityWorld`.
- 3D player: render adapter consumes player snapshot; movement remains a simulation test.
- Resource packs: UI and commands both call `ApplyResourcePackUseCase`.

## Dishka

Do not add Dishka during Phase A. Manual composition should be enough while ownership is still moving. Reconsider a DI container only after `AppRuntime`, `WorldRuntime`, factories, and use cases exist and manual wiring becomes repetitive enough to justify the dependency.
