# Project Knowledge — Veilstone (voxel_sandbox)

## Purpose

Veilstone is a Python voxel sandbox project built around a Minecraft-like world model.

This file is not the project history and not the active workplan. Keep it stable and high-level.
Detailed current state should live in `docs/WORKPLAN.md`, known issues in `docs/BUGS.md`, and completed changes in `docs/CHANGELOG.md`.

## Startup / "начинай" protocol

When the session starts, or when the user says "начинай", "продолжай", "работай дальше", or asks to continue the current phase:

1. Read this root `CLAUDE.md`.
2. Check the current project state in:
   - `docs/WORKPLAN.md`
   - `docs/BUGS.md`
   - `docs/CHANGELOG.md`
   - any other relevant docs in `docs/`
3. Activate Serena and call `mcp__serena__initial_instructions`.
4. List Serena memories and read only the relevant ones before touching code.
5. Check `git status` and recent diff if the current task/phase is unclear.
6. Infer the next step from `WORKPLAN.md`, docs, memories, and git state before asking the user.
7. Work in small coherent phases.
8. Before finishing a phase:
   - run relevant tests;
   - review git diff;
   - update `docs/WORKPLAN.md` if the active state changed;
   - update `docs/BUGS.md` if bugs were discovered, fixed, or reclassified;
   - update `docs/CHANGELOG.md` for completed user-visible, architectural, or phase-level changes;
   - if any Serena memory appears stale, verify it against code/docs/tests/git and update or delete it;
   - update Serena memories only if stable project knowledge changed;
   - refresh Serena index only after large refactors, file moves, module renames, or stale symbol results.
9. Commit only completed coherent phases with passing relevant checks. Never add Claude/AI attribution.

## Architecture Overview

Python voxel sandbox built with Pyglet, ModernGL, and NumPy.

### Layer Structure

Dependency flow should go downward:

```text
app/             — bootstrap, settings, commands, paths
render/          — window, world scene, meshes, UI, entities, shaders
engine/          — chunks, generation, ECS, physics, lighting, water
domain/          — blocks, items, inventory, crafting; pure domain layer
infrastructure/  — storage, logging
network/         — server, client, discovery, protocol
audio/           — bus, director, backend
```

Rules:

- Keep `domain/` pure and independent from rendering, IO, networking, and app bootstrap.
- Avoid upward dependencies.
- Avoid cross-layer shortcuts unless explicitly justified.
- Prefer extracting focused modules over growing large orchestration classes.

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

## MCP Tools — Usage Policy

### Session launch

Prefer launching Claude Code through Headroom and Serena prompt override:

```bash
headroom wrap claude --system-prompt="$(serena prompts print-cc-system-prompt-override)"
```

Recommended shell function:

```sh
hccs() {
  headroom wrap claude --system-prompt="$(serena prompts print-cc-system-prompt-override)" "$@"
}
```

Start from project root:

```bash
cd /path/to/voxel_sandbox
hccs
```

### Headroom

Headroom is used for token/context efficiency.

- `headroom wrap claude` is the automatic compression path.
- If Headroom MCP tools are available, use them for large logs, JSON, diffs, generated outputs, and long tool results.
- When output contains a compression marker or hash, use `mcp__headroom__headroom_retrieve` instead of repeating the original expensive command.
- Use `mcp__headroom__headroom_stats` when diagnosing context/token pressure.
- If compressed context is insufficient for precise edits, retrieve the original before changing code.

### Serena

Before coding work, call:

- `mcp__serena__initial_instructions`

Use Serena before broad `Read`/`Grep` exploration. Do not read large files whole when Serena can provide structured symbol context.

Prefer Serena for code navigation:

- `mcp__serena__get_symbols_overview` — file structure / symbol overview
- `mcp__serena__find_symbol` — find class/function/method by name
- `mcp__serena__find_declaration` — jump to declaration
- `mcp__serena__find_implementations` — find implementations
- `mcp__serena__find_referencing_symbols` — find usages/references
- `mcp__serena__get_diagnostics_for_file` — static diagnostics for a file

Use normal `Read`/`Grep` when:

- the file is small;
- the file is config/docs/non-code;
- exact surrounding text is required;
- Serena output is insufficient;
- debugging requires raw text/log context.

For targeted edits, prefer Serena symbolic edit tools when appropriate:

- `mcp__serena__replace_symbol_body`
- `mcp__serena__insert_after_symbol`
- `mcp__serena__insert_before_symbol`
- `mcp__serena__replace_content`
- `mcp__serena__safe_delete_symbol`
- `mcp__serena__rename_symbol`

Before changing public APIs, exported classes, widely used methods, or central systems, use `find_referencing_symbols`.

## Serena memory/index policy

Serena index and Serena memories are different things.

### Index

Use Serena index/symbol tools for code navigation.

Refresh/rebuild Serena project index only when needed:

- after large refactors;
- after file moves;
- after module renames;
- when symbol results look stale or missing.

Do not rebuild the index after every small edit.

### Memories

Serena memories are not a changelog and not a task tracker. They are durable project knowledge.

At session start, list Serena memories and read only the relevant ones.

Update Serena memories only when stable project knowledge changes.

Good memory candidates:

- architecture decisions;
- commands for tests/lint/build;
- coding conventions;
- important module responsibilities;
- recurring pitfalls;
- integration details that will matter later.

Do not write memories for:

- temporary task notes;
- secrets/tokens/credentials;
- noisy logs;
- one-off debugging observations;
- raw stack traces;
- obvious facts already visible from code;
- short-lived implementation details;
- detailed chronological history.

Project history belongs in `docs/CHANGELOG.md`.
Current plan belongs in `docs/WORKPLAN.md`.
Known bugs belong in `docs/BUGS.md`.

Before finishing a coherent phase, check whether stable project knowledge changed. If yes, update the relevant Serena memory before committing.

### Stale memory handling

Serena memories are useful hints, not the source of truth.

If Serena memories conflict with current code, tests, docs, or git state:

- trust current code/tests/docs/git over memory;
- mention the mismatch briefly;
- update, rewrite, or delete the stale memory before finishing the phase;
- do not continue relying on stale memory.

When reading a memory, verify task-critical claims against:

- current code via Serena symbol tools;
- `docs/WORKPLAN.md`;
- `docs/BUGS.md`;
- `docs/CHANGELOG.md`;
- relevant tests;
- `git status` / `git diff`.

If a memory contains outdated implementation details, replace them with stable architecture/convention-level knowledge or delete the memory.

## Work style

Work in small coherent phases.

Before editing:

1. Understand the task.
2. Check `docs/WORKPLAN.md`, `docs/BUGS.md`, and `docs/CHANGELOG.md`.
3. Read relevant Serena memories.
4. Use Serena symbol tools to locate code.
5. Inspect tests related to the target behavior.

During implementation:

- preserve existing architecture and style;
- avoid unrelated rewrites;
- avoid large diffs unless the phase explicitly requires it;
- prefer focused extraction over adding more responsibility to large classes;
- keep domain layer pure;
- avoid introducing upward dependencies.

After implementation:

- run relevant tests;
- run broader tests when the phase touches shared systems;
- review `git diff`;
- update docs if project state changed;
- update memories only if stable knowledge changed.

## Tests

Primary test command:

```bash
.venv/bin/python -m pytest tests/ -x -q
```

Use narrower test commands for focused work when appropriate.

If a test failure appears pre-existing, verify and document it in `docs/BUGS.md` or `docs/WORKPLAN.md` rather than ignoring it.

## Commit workflow

Commits are allowed after a coherent phase is complete.

A phase is complete only when:

- implementation is done;
- relevant tests are added or updated when appropriate;
- relevant tests pass, except for documented pre-existing failures;
- diff has been reviewed;
- docs are updated if phase/project state changed;
- Serena memories are updated if stable project knowledge changed.

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

## Known recurring pitfalls

Keep this section short. Move detailed issue tracking to `docs/BUGS.md`.

- Large orchestration files/classes should not keep growing.
- Avoid filesystem or expensive state reads in per-frame paths.
- Avoid long command-dispatch `if/elif` chains when a registry/table-based dispatch is possible.
- Avoid scattering magic numbers across rendering, physics, and engine systems.
- Avoid direct cross-system method calls when an event/state abstraction is more appropriate.
- Never add AI attribution, `Co-Authored-By` trailers, `Generated-By` text, or Claude-related metadata to commit messages or pull request descriptions.
