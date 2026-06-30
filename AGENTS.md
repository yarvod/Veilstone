<!-- headroom:rtk-instructions -->
# RTK (Rust Token Killer) - Token-Optimized Commands

When running shell commands, always prefix with `rtk`. This reduces context usage
with no intended behavior change. If `rtk` has no filter for a command, it passes
through unchanged.

## Key Commands

```bash
# Git
rtk git status
rtk git diff
rtk git log

# Files and search
rtk ls <path>
rtk read <file>
rtk grep <pattern>
rtk find <pattern>
rtk diff <file>

# Tests and checks
rtk uv run pytest
rtk uv run pytest -m unit
rtk uv run ruff check .
rtk uv run ruff format --check .
rtk uv run pyright
rtk uv run lint-imports
```

## RTK Rules

- In command chains, prefix each segment: `rtk git add . && rtk git commit -m "msg"`.
- For debugging or exact unfiltered output, raw commands are acceptable.
- `rtk proxy <cmd>` runs a command without filtering but tracks usage.
<!-- /headroom:rtk-instructions -->

# Project Knowledge — Veilstone

These instructions apply to Claude, Codex, and any other coding agent working in
this repository. `CLAUDE.md` and `AGENTS.md` intentionally contain the same
operating rules so either entry point has complete context.

## Purpose

Veilstone is a Python voxel sandbox engine prototype built with Pyglet,
ModernGL, NumPy, and `uv`.

This file is stable project guidance, not project history and not the active
workplan. Detailed current state belongs in:

- `docs/WORKPLAN.md` — current phase, next actions, active refactor plan.
- `docs/BUGS.md` — known bugs, regressions, flaky tests, unresolved issues.
- `docs/CHANGELOG.md` — completed meaningful changes.
- `docs/ARCHITECTURE.md` — target architecture, dependency direction, ownership,
  composition root, and import-linter contracts.

Do not store fast-changing implementation details here unless they are stable
project rules.

## Startup / Continue Protocol

When a session starts, or the user says "начинай", "продолжай", "работай
дальше", or asks to continue the current phase:

1. Read root `CLAUDE.md` or `AGENTS.md`.
2. Check current project state in `docs/WORKPLAN.md`, `docs/BUGS.md`,
   `docs/CHANGELOG.md`, and relevant docs in `docs/`.
3. Check `rtk git status --short` and recent diff if the current task/phase is
   unclear.
4. Infer the next step from `WORKPLAN.md`, docs, code, tests, and git state.
5. If docs contradict each other, resolve obvious docs state conflicts before
   starting new code work.
6. Work in small coherent phases.
7. Before finishing a phase:
   - run relevant tests/checks;
   - review git diff;
   - update `docs/WORKPLAN.md` if active state changed;
   - update `docs/BUGS.md` if bugs were discovered, fixed, reclassified, or
     proven obsolete;
   - update `docs/CHANGELOG.md` for completed user-visible, architectural, or
     phase-level changes.
8. Commit only completed coherent phases with relevant passing checks. Never add
   Claude/Codex/AI attribution.

## Architecture Overview

Dependency direction should be explicit and mostly inward:

```text
domain       — pure block/item/inventory/biome/crafting/progression data/rules
engine       — chunks, generation, ECS, physics, lighting, fluids, authority
application  — sessions, use cases, ports, composition-facing orchestration
infrastructure — storage, logging, settings/resource loading implementations
presentation/render — Pyglet window, UI, camera, ModernGL render adapters
network      — server, client, discovery, protocol/session adapters
audio        — bus, director, backend adapters
tests        — unit, integration, smoke, performance coverage
```

Current package names still include `app`, `engine`, and `render`; do not rename
large trees casually. Use `docs/ARCHITECTURE.md` as the target architecture for
gradual stabilization.

Rules:

- Keep `domain/` pure and independent from rendering, IO, networking, app
  bootstrap, storage, and settings files.
- Avoid upward dependencies and cross-layer shortcuts unless explicitly
  justified.
- Prefer extracting focused modules over growing large orchestration classes.
- Avoid adding responsibility to historically large classes, especially
  `GameWindow` and `DemoWorldRenderer`.
- New controllers/use cases must not accept the full `GameWindow`; pass narrow
  dependencies or protocol ports.
- Do not introduce Dishka during Phase A. Start with manual composition root.

## Content Assets

New game textures and sounds must be added as Minecraft-style resource-pack
content under `resource_packs/default/assets/<namespace>/textures|sounds/...`
and referenced with resource locations such as `minecraft:block/stone`,
`minecraft:entity/cow/cow`, or `minecraft:player/hurt`. Do not add gameplay
art/audio to ad-hoc `assets/audio` or `assets/entities`; reserve `assets/` for
launcher/app branding and other non-resource-pack files.

## Docs Workflow

The `docs/` directory is the source of truth for current project state and useful
history.

### `docs/WORKPLAN.md`

Use for:

- current phase;
- next steps;
- acceptance criteria;
- progress checklist;
- active refactor plan;
- current implementation strategy.

Update when:

- phase starts or completes;
- task priority changes;
- acceptance criteria change;
- next action changes.

Keep only active plans here. Move completed history to `docs/CHANGELOG.md`.

### `docs/BUGS.md`

Use for:

- known bugs;
- regressions;
- flaky tests;
- reproducible issues;
- suspected issues needing verification;
- known red quality gates.

For bug entries, prefer:

- short title;
- status: `open`, `investigating`, `fixed`, `wontfix`, or `obsolete`;
- reproduction steps if known;
- affected module;
- linked test if available;
- fix notes when resolved.

### `docs/CHANGELOG.md`

Use for completed meaningful changes:

- user-visible feature changes;
- bug fixes;
- architecture changes;
- phase completions;
- meaningful tests/tooling behavior changes.

Do not put noisy implementation details into changelog. Keep it useful to humans.

### Docs Consistency

`docs/WORKPLAN.md`, `docs/BUGS.md`, and `docs/CHANGELOG.md` must not contradict
each other. If one says a bug is fixed while another marks it open, verify and
update the stale doc before starting new work.

## Checks

Useful commands:

```bash
rtk uv run lint-imports
rtk uv run ruff check .
rtk uv run ruff format --check .
rtk uv run pytest
rtk uv run pytest -m unit
rtk uv run pytest -m integration
rtk uv run pytest -m smoke
rtk uv run pyright
```

For focused work, run narrow relevant tests first. Before committing completed
phases, run at least:

```bash
rtk uv run lint-imports
rtk uv run ruff check .
rtk uv run ruff format --check .
rtk uv run pytest -m unit
```

Run `rtk uv run pyright` for signature, architecture, public API, or cross-module
changes. Do not attempt to fix unrelated project-wide Pyright failures unless
they were caused by the current change or explicitly requested. If Pyright is
known red, keep the reason in `docs/BUGS.md`.

## Tooling Policy

Use simple local tools first. Prefer short, precise commands with compact output
over broad exploration.

Recommended discovery flow:

1. Use `rtk grep` / `rg` for targeted text search.
2. Use `rtk sed`, `rtk read`, or small focused reads for surrounding context.
3. Avoid reading large files whole unless necessary.
4. Use tests, Ruff, Pyright, import-linter, and git diff as the feedback loop.

Examples:

```bash
rtk grep "InventoryController|GameWindow|execute_command" src tests
rtk git status --short
rtk git diff --stat
rtk uv run ruff check .
rtk uv run pytest -m unit
```

## Context Discipline

Tool outputs stay in context. Use tools precisely.

Avoid repeated:

- full-project searches;
- broad references on generic symbols;
- huge raw logs;
- full-file reads of large files;
- unnecessary repeated reads of unchanged docs/configs.

After large exploration phases:

1. summarize useful findings;
2. compact if available;
3. continue implementation using focused code context.

Recommended rhythm:

```text
focused discovery → implementation → tests/checks → docs updates → commit
```

## Work Style

Work in small coherent phases.

Before editing:

1. Understand the task.
2. Check `docs/WORKPLAN.md`, `docs/BUGS.md`, and `docs/CHANGELOG.md`.
3. Use targeted search/read commands to locate code.
4. Inspect tests related to target behavior.

During implementation:

- preserve existing architecture style;
- avoid unrelated rewrites;
- avoid large diffs unless the phase explicitly requires it;
- prefer focused extraction over adding more responsibility to large classes;
- keep domain layer pure;
- avoid introducing upward dependencies;
- avoid fixing unrelated project-wide debt unless requested or blocking.

After implementation:

- run relevant tests/checks;
- run broader checks when the phase touches shared systems;
- review `rtk git diff`;
- update docs if project state changed.

## Commit Workflow

Commits are allowed when a coherent phase is complete:

- implementation is done;
- relevant tests were added or updated where appropriate;
- relevant tests/checks pass, except documented pre-existing failures;
- diff has been reviewed;
- docs were updated when phase/project state changed.

Use concise human conventional commits:

- `feat: ...`
- `fix: ...`
- `test: ...`
- `refactor: ...`
- `docs: ...`
- `chore: ...`

Never add to commit messages, PR descriptions, or docs:

- `Co-Authored-By: Claude`
- `Generated-By`
- `AI-assisted`
- Claude/Codex metadata
- tool metadata
- any AI attribution trailer

Before committing, inspect:

- `rtk git status --short`
- `rtk git diff --cached --stat`
- tests/checks passed

After committing, report:

- commit hash
- commit message
- final `rtk git status --short`

## Known Recurring Pitfalls

Keep this section short. Move detailed issue tracking to `docs/BUGS.md`.

- Large orchestration files/classes should not keep growing.
- Avoid expensive filesystem state reads in per-frame paths.
- Avoid long command-dispatch `if/elif` chains when registry/table-based dispatch
  is practical.
- Avoid scattering magic numbers across rendering, physics, and engine systems.
- Avoid direct cross-system method calls that bypass application use cases or
  explicit ports.
