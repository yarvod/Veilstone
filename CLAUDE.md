# Project Knowledge — Veilstone

## Purpose

Veilstone is a Python voxel sandbox engine prototype built with Pyglet, ModernGL, NumPy, and `uv`.

This file is not the project history and not the active workplan. Keep it stable and high-level.

Detailed current state belongs in:

- `docs/WORKPLAN.md` — current phase, next actions, active refactor plan;
- `docs/BUGS.md` — known bugs, regressions, flaky tests, unresolved issues;
- `docs/CHANGELOG.md` — completed meaningful changes.

Do not store fast-changing implementation details in this file unless they are stable project rules.

---

## Startup / "начинай" protocol

When the session starts, or when the user says "начинай", "продолжай", "работай дальше", or asks to continue the current phase:

1. Read this root `CLAUDE.md`.
2. Check the current project state in:
   - `docs/WORKPLAN.md`
   - `docs/BUGS.md`
   - `docs/CHANGELOG.md`
   - any other relevant docs in `docs/`
3. Check `git status` and recent diff if the current task/phase is unclear.
4. Infer the next step from `WORKPLAN.md`, docs, code, tests, and git state before asking the user.
5. If docs contradict each other, resolve obvious docs state conflicts before starting new code work.
6. Work in small coherent phases.
7. Before finishing a phase:
   - run relevant tests/checks;
   - review git diff;
   - update `docs/WORKPLAN.md` if the active state changed;
   - update `docs/BUGS.md` if bugs were discovered, fixed, reclassified, or proven obsolete;
   - update `docs/CHANGELOG.md` for completed user-visible, architectural, or phase-level changes.
8. Commit only completed coherent phases with passing relevant checks. Never add Claude/AI attribution.

---

## Architecture Overview

Python voxel sandbox built with Pyglet, ModernGL, NumPy, and `uv`.

### Layer Structure

Dependency flow should go downward:

```text
app/             — bootstrap, settings, commands, paths
render/          — window, world scene, meshes, UI, entities, shaders
engine/          — chunks, generation, ECS, physics, lighting, water
domain/          — blocks, items, inventory, crafting; pure domain layer
infrastructure/  — storage, logging, assets, profiling adapters
network/         — server, client, discovery, protocol
audio/           — bus, director, backend
tests/           — unit, integration, smoke, performance coverage
```

Rules:

- Keep `domain/` pure and independent from rendering, IO, networking, and app bootstrap.
- Avoid upward dependencies.
- Avoid cross-layer shortcuts unless explicitly justified.
- Prefer extracting focused modules over growing large orchestration classes.
- Avoid adding more responsibility to historically large classes.

---

## Docs workflow

The `docs/` directory is the source of truth for current project state and project history.

### `docs/WORKPLAN.md`

Use for:

- current phase;
- next steps;
- acceptance criteria;
- progress checklist;
- active refactor plan;
- current implementation strategy.

Update it when:

- a phase starts;
- a phase completes;
- task priority changes;
- acceptance criteria change;
- the next action changes.

### `docs/BUGS.md`

Use for:

- known bugs;
- regressions;
- flaky tests;
- reproducible issues;
- suspected issues that need verification.

For each bug, prefer:

- short title;
- status: `open`, `investigating`, `fixed`, `wontfix`, or `obsolete`;
- reproduction steps if known;
- affected module;
- linked test if available;
- fix notes when resolved.

If the file becomes tiny or redundant, it is acceptable to merge bug tracking into `WORKPLAN.md`, but do not lose active bug state.

### `docs/CHANGELOG.md`

Use for completed meaningful changes.

Update it when:

- a user-visible feature changes;
- a bug is fixed;
- architecture changes;
- a phase completes;
- tests or tooling behavior changes in a meaningful way.

Do not put noisy implementation details into changelog. Keep it useful for humans.

---

## Docs consistency policy

`docs/WORKPLAN.md`, `docs/BUGS.md`, and `docs/CHANGELOG.md` must not contradict each other.

If `WORKPLAN.md` or `CHANGELOG.md` says a bug is fixed, but `BUGS.md` still marks it open, update `BUGS.md`.

If `BUGS.md` says an issue is open, but tests/code show it is fixed, verify the current behavior and update `BUGS.md`.

If current code/tests contradict docs, trust code/tests, then update docs.

On "начинай", resolve obvious docs state conflicts before starting new code work.

---

## Project command policy

This project uses `uv`. Prefer `uv run ...` commands over direct `.venv/bin/python ...`.

Primary checks:

```bash
uv run pytest
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m smoke
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

For focused work, run the narrow relevant test first.

Before committing a completed phase, run at least:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Run `uv run pyright` for signature, architecture, public API, or cross-module changes.

Do not attempt to fix unrelated project-wide Pyright/Ruff failures unless they are caused by the current change or explicitly requested.

---

## Tooling policy

Use simple local tools first. Prefer short, precise commands and compact outputs over broad exploration.

Recommended discovery flow:

1. Use `rg`/`grep` for targeted text search.
2. Use `sed`, `python`, or focused `Read` for small surrounding context.
3. Avoid reading large files whole unless necessary.
4. Use tests, Ruff, Pyright, and git diff as the main feedback loop.

Examples:

```bash
rg "InventoryController|GameWindow|execute_command" src tests
git status --short
git diff --stat
uv run ruff check .
uv run pytest -m unit
```

---

## MCP Tools — Usage Policy

### Session launch

Prefer launching Claude Code through Headroom:

```bash
headroom wrap claude
```

### Headroom

Headroom is used for token/context efficiency.

- `headroom wrap claude` is the automatic compression path.
- If Headroom MCP tools are available, use them for large logs, JSON, diffs, generated outputs, and long tool results.
- When output contains a compression marker or hash, use `mcp__headroom__headroom_retrieve` instead of repeating the original expensive command.
- Use `mcp__headroom__headroom_stats` when diagnosing context/token pressure.
- If compressed context is insufficient for precise edits, retrieve the original before changing code.

---

## Context discipline

Tool outputs stay in context. Use tools precisely.

Do not repeatedly call broad tools when a narrower query is possible.

Avoid repeated:

- full-project searches;
- broad references on generic symbols;
- huge raw logs;
- full-file reads of large files;
- unnecessary repeated reads of unchanged docs/configs.

After large exploration phases:

1. summarize the useful findings;
2. run `/compact`;
3. continue with implementation using the summary and focused code context.

Recommended rhythm:

```text
focused discovery
→ summary
→ /compact
→ implementation
→ tests/checks
→ docs updates if needed
→ commit
```

---

## Work style

Work in small coherent phases.

Before editing:

1. Understand the task.
2. Check `docs/WORKPLAN.md`, `docs/BUGS.md`, and `docs/CHANGELOG.md`.
3. Use targeted search/read commands to locate code.
4. Inspect tests related to the target behavior.

During implementation:

- preserve existing architecture and style;
- avoid unrelated rewrites;
- avoid large diffs unless the phase explicitly requires it;
- prefer focused extraction over adding more responsibility to large classes;
- keep domain layer pure;
- avoid introducing upward dependencies;
- avoid "fixing everything" outside the current task.

After implementation:

- run relevant tests/checks;
- run broader checks when the phase touches shared systems;
- review `git diff`;
- update docs if project state changed.

---

## Commit workflow

Commits are allowed after a coherent phase is complete.

A phase is complete only when:

- implementation is done;
- relevant tests are added or updated when appropriate;
- relevant tests/checks pass, except for documented pre-existing failures;
- diff has been reviewed;
- docs are updated if phase/project state changed.

Use concise human conventional commits where appropriate:

- `feat: ...`
- `fix: ...`
- `test: ...`
- `refactor: ...`
- `docs: ...`
- `chore: ...`

Never add to commit messages or PR descriptions:

- `Co-Authored-By: Claude`
- `Generated-By`
- `AI-assisted`
- Claude metadata
- tool metadata
- any AI attribution trailer

Before committing, show:

- `git status`
- summary of changed files
- tests/checks that passed

After committing, show:

- commit hash
- commit message
- final `git status`

---

## Known recurring pitfalls

Keep this section short. Move detailed issue tracking to `docs/BUGS.md`.

- Large orchestration files/classes should not keep growing.
- Avoid filesystem or expensive state reads in per-frame paths.
- Avoid long command-dispatch `if/elif` chains when a registry/table-based dispatch is possible.
- Avoid scattering magic numbers across rendering, physics, and engine systems.
- Avoid direct cross-system method calls when an event/state abstraction is more appropriate.
- Never add AI attribution, `Co-Authored-By` trailers, `Generated-By` text, or Claude-related metadata to commit messages or pull request descriptions.
