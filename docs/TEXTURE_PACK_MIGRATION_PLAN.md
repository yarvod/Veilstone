# Veilstone Texture Pack Migration Plan

## Goal

Add a Minecraft-like texture/resource pack system to Veilstone.

The goal is not to ship Minecraft assets or any third-party texture pack inside the repository. The goal is to let the user place a local texture pack ZIP/folder into the project or user-data texture pack directory, then select and apply it in the game UI, including while a world is already open.

Example target pack for development/testing:

```text
resource_packs/Faithful-32x-1.21.11.zip
```

This plan uses Faithful-32x as an example because it follows the common Minecraft Java resource pack structure:

```text
pack.mcmeta
pack.png
assets/minecraft/textures/block/*.png
assets/minecraft/textures/item/*.png
```

Do not commit the Faithful ZIP or any extracted third-party textures to the repository unless the specific license explicitly allows redistribution and the project intentionally accepts that dependency.

---

## Non-goals

Do not implement the full Minecraft resource pack system in the first pass.

MVP does not need:

- blockstates;
- JSON block models;
- item models;
- entity textures;
- biome colormaps;
- animated texture playback;
- normal/specular/emissive maps;
- modded namespaces beyond basic detection;
- automatic online download of packs.

MVP should focus on:

- user-supplied ZIP/folder packs;
- Minecraft Java-like `assets/<namespace>/textures/block/*.png`;
- mapping external texture names to Veilstone texture keys;
- building a runtime atlas;
- selecting and applying packs from UI;
- fallback to existing generated/default textures.

---

## Legal / asset safety rules

Veilstone should support user-supplied texture packs, not redistribute third-party assets.

Rules:

- Do not commit user texture packs.
- Do not commit imported texture cache.
- Do not ship official Minecraft textures.
- Do not download official Minecraft assets automatically.
- User is responsible for ensuring they are allowed to use the pack locally.
- Veilstone should document that third-party texture packs remain owned by their authors.
- Imported caches are local-only and should be ignored by git.

Recommended `.gitignore` additions:

```gitignore
resource_packs/*
!resource_packs/README.md

saves/texture_cache/*
*.texture-cache/
```

Recommended `resource_packs/README.md` wording:

```md
# Resource Packs

Place user-supplied Minecraft Java-compatible resource pack ZIPs or folders here.

Examples:
- Faithful-32x-1.21.11.zip
- MyPack/

These packs are local user assets and must not be committed unless their license explicitly allows redistribution.

Veilstone does not ship Minecraft assets or third-party resource packs.
```

---

## Current project state

The current renderer is already close to supporting texture packs.

Existing facts from the current codebase:

- Blocks define `texture_top`, `texture_side`, and `texture_bottom` in `data/blocks.toml`.
- `BlockDef` already stores per-face texture keys.
- Mesh builders already consume `texture_uvs: dict[str, tuple[float, float, float, float]]`.
- The shader samples a single atlas using per-vertex atlas rectangles.
- `create_block_atlas()` currently generates a procedural atlas in Python.
- `DemoWorldRenderer` currently creates the texture once at startup and passes `atlas.uvs` into mesh workers.

This means the main migration is to replace:

```python
atlas = create_block_atlas()
```

with an active texture-pack atlas provider.

The mesh format and shader do not need a large rewrite for the MVP.

---

## Desired user experience

### Main Menu / Settings flow

The player should be able to:

1. Open `Settings`.
2. Open `Texture Packs`.
3. See available packs:
   - `Default`
   - local ZIPs/folders from `resource_packs/`
   - local user-data packs from the configured user data directory
4. Select a pack.
5. Press `Apply`.
6. The game imports/builds the atlas if needed.
7. The selected pack becomes active.
8. If a world is already open, visible chunks are remeshed and the new pack appears without restarting.

### In-world flow

While playing:

1. Press `Escape`.
2. Open `Settings`.
3. Open `Texture Packs`.
4. Select `Faithful-32x-1.21.11.zip`.
5. Press `Apply`.
6. Show a short loading state:
   - `Importing texture pack...`
   - `Building atlas...`
   - `Remeshing visible chunks...`
7. Return to the world with the new textures applied.

### Error handling

If a pack is invalid:

- show `Invalid resource pack`;
- keep current active pack;
- write/import a detailed report.

If some textures are missing:

- apply the pack anyway;
- use default/generated fallback textures;
- show `Applied with missing textures: N`;
- expose the import report in logs or debug UI.

---

## Target folder layout

Repository:

```text
resource_packs/
  README.md

data/
  resource_pack_mappings/
    minecraft_java.toml

src/voxel_sandbox/render/texture_packs/
  __init__.py
  atlas.py
  cache.py
  importer.py
  minecraft_java.py
  models.py
  registry.py

tests/unit/render/test_texture_pack_importer.py
tests/unit/render/test_texture_atlas_builder.py
tests/unit/render/test_texture_pack_registry.py
tests/fixtures/resource_packs/fake_minecraft_pack/
  pack.mcmeta
  assets/minecraft/textures/block/stone.png
  assets/minecraft/textures/block/dirt.png
  assets/minecraft/textures/block/grass_block_top.png
```

Local/user cache:

```text
saves/texture_cache/
  default/
  faithful-32x-1-21-11-<hash>/
    blocks_atlas.png
    blocks_atlas.json
    import_report.json
```

The exact cache root can be adjusted later to platform user-data paths. For MVP, `saves/texture_cache/` is fine if it is ignored by git.

---

## Texture key model

Veilstone should keep its own texture keys.

Example from `data/blocks.toml`:

```toml
[[block]]
key = "grass"
texture_top = "grass_top"
texture_side = "grass_side"
texture_bottom = "dirt"
```

The texture pack system maps external pack resources to these Veilstone keys.

Do not rename all Veilstone texture keys to Minecraft names. Keep the game independent.

---

## Minecraft Java mapping file

Add:

```text
data/resource_pack_mappings/minecraft_java.toml
```

Suggested MVP content:

```toml
[metadata]
format = "minecraft_java"
default_namespace = "minecraft"

[textures]
stone = "minecraft:block/stone"
dirt = "minecraft:block/dirt"
grass_top = "minecraft:block/grass_block_top"
grass_side = "minecraft:block/grass_block_side"

# Veilstone-specific blocks use close Minecraft substitutes for imported packs.
veilwood_cut = "minecraft:block/oak_log_top"
veilwood_bark = "minecraft:block/oak_log"
veilwood_leaves = "minecraft:block/oak_leaves"
veilwood_planks = "minecraft:block/oak_planks"

dusk_crystal_ore = "minecraft:block/diamond_ore"
gloam_lantern = "minecraft:block/lantern"
water = "minecraft:block/water_still"

runecraft_top = "minecraft:block/crafting_table_top"
runecraft_side = "minecraft:block/crafting_table_side"

glowing_mushroom = "minecraft:block/red_mushroom"
fireflies = "minecraft:block/glow_lichen"
```

External texture reference format:

```text
namespace:kind/name
```

Examples:

```text
minecraft:block/stone
minecraft:item/stick
```

For MVP, only `block` kind is required.

Resolver behavior:

```text
minecraft:block/stone
→ assets/minecraft/textures/block/stone.png
```

---

## Faithful-32x example handling

Faithful-32x is a 32x pack, so the atlas tile size should become 32.

Expected simple mappings:

```text
stone              → assets/minecraft/textures/block/stone.png
dirt               → assets/minecraft/textures/block/dirt.png
grass_top          → assets/minecraft/textures/block/grass_block_top.png
grass_side         → assets/minecraft/textures/block/grass_block_side.png
veilwood_cut       → assets/minecraft/textures/block/oak_log_top.png
veilwood_bark      → assets/minecraft/textures/block/oak_log.png
veilwood_leaves    → assets/minecraft/textures/block/oak_leaves.png
veilwood_planks    → assets/minecraft/textures/block/oak_planks.png
water              → assets/minecraft/textures/block/water_still.png
runecraft_top      → assets/minecraft/textures/block/crafting_table_top.png
runecraft_side     → assets/minecraft/textures/block/crafting_table_side.png
dusk_crystal_ore   → assets/minecraft/textures/block/diamond_ore.png
gloam_lantern      → assets/minecraft/textures/block/lantern.png
glowing_mushroom   → assets/minecraft/textures/block/red_mushroom.png
fireflies          → assets/minecraft/textures/block/glow_lichen.png
```

Important: some Minecraft textures are animated vertical strips.

Example:

```text
water_still.png may be 32x1024
```

MVP behavior:

- detect `height > width` and `height % width == 0`;
- treat it as animation strip;
- use the first `width x width` frame;
- record `animation_ignored = true` in import report.

Later behavior:

- parse `.png.mcmeta`;
- upload texture array or animation atlas frames;
- animate water/lava/fire in shader or texture update pass.

---

## Core data models

Suggested models:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class TexturePackInfo:
    id: str
    name: str
    source_path: Path
    source_kind: str  # "zip" | "folder" | "default"
    format: str       # "minecraft_java" | "veilstone_native"
    tile_size: int | None

@dataclass(frozen=True, slots=True)
class AtlasImage:
    width: int
    height: int
    pixels: bytes
    uvs: dict[str, tuple[float, float, float, float]]

@dataclass(frozen=True, slots=True)
class ImportReport:
    pack_id: str
    imported: list[str]
    missing: list[str]
    fallback: list[str]
    ignored_animations: list[str]
    warnings: list[str]
```

The existing `GeneratedAtlas` can either be kept and reused or replaced by a more general `AtlasImage`.

Compatibility goal:

```python
atlas.width
atlas.height
atlas.pixels
atlas.uvs
```

should remain available so `world_scene.py` and mesh builders require minimal change.

---

## Atlas builder

Add:

```text
src/voxel_sandbox/render/texture_packs/atlas.py
```

Responsibilities:

1. Accept `dict[str, PIL.Image.Image]`.
2. Normalize every image to RGBA.
3. Determine tile size.
4. Resize if needed.
5. Build a grid atlas.
6. Compute UV rects with half-pixel inset.
7. Flip pixels if needed to match existing OpenGL upload path.

Current `create_block_atlas()` flips vertically before `tobytes()`. Preserve the existing convention unless the shader/upload path changes.

Pseudo-code:

```python
def build_texture_atlas(
    tiles: dict[str, Image.Image],
    *,
    tile_size: int,
) -> AtlasImage:
    names = sorted(tiles)
    columns = ceil(sqrt(len(names)))
    rows = ceil(len(names) / columns)
    image = Image.new("RGBA", (columns * tile_size, rows * tile_size))

    uvs = {}
    for index, name in enumerate(names):
        tile_x = index % columns
        tile_y = index // columns
        tile = normalize_tile(tiles[name], tile_size)
        image.paste(tile, (tile_x * tile_size, tile_y * tile_size))
        uvs[name] = compute_uv_rect(tile_x, tile_y, columns, rows, tile_size)

    pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    return AtlasImage(image.width, image.height, pixels, uvs)
```

---

## Minecraft Java importer

Add:

```text
src/voxel_sandbox/render/texture_packs/minecraft_java.py
```

Responsibilities:

1. Accept ZIP or folder path.
2. Load `pack.mcmeta` if present.
3. Resolve texture references from mapping file.
4. Load only required textures, not the whole pack.
5. Convert images to RGBA.
6. Extract first frame from vertical animated strips.
7. Return imported tiles + report.

Required functions:

```python
def is_minecraft_java_pack(path: Path) -> bool:
    ...

def load_minecraft_pack_info(path: Path) -> TexturePackInfo:
    ...

def import_mapped_block_textures(
    source: Path,
    mapping: Mapping[str, str],
    fallback_tiles: Mapping[str, Image.Image],
) -> tuple[dict[str, Image.Image], ImportReport]:
    ...
```

ZIP resolver:

```python
assets/{namespace}/textures/{kind}/{name}.png
```

Folder resolver:

```python
path / "assets" / namespace / "textures" / kind / f"{name}.png"
```

---

## Fallback default texture provider

Keep the current generated textures as fallback.

Current generated keys include:

```text
stone
dirt
grass_top
grass_side
veilwood_cut
veilwood_bark
veilwood_leaves
dusk_crystal_ore
gloam_lantern
water
veilwood_planks
runecraft_top
runecraft_side
glowing_mushroom
fireflies
```

Refactor current `create_block_atlas()` into two layers:

```python
def create_default_block_tiles(tile_size: int = 32) -> dict[str, Image.Image]:
    ...

def create_block_atlas(tile_size: int = 32) -> AtlasImage:
    return build_texture_atlas(create_default_block_tiles(tile_size), tile_size=tile_size)
```

Then imported packs can use:

```text
default tiles
+ imported replacements
→ final atlas
```

Behavior:

```text
if pack has stone:
  use pack stone
else:
  use generated stone
```

---

## Texture pack registry

Add:

```text
src/voxel_sandbox/render/texture_packs/registry.py
```

Responsibilities:

- scan project `resource_packs/`;
- scan user-data resource pack directory later;
- detect ZIP/folder packs;
- include built-in `Default`;
- return list for UI.

Suggested API:

```python
def list_available_texture_packs(project_root: Path, user_data_root: Path | None = None) -> list[TexturePackInfo]:
    ...

def get_texture_pack_by_id(pack_id: str) -> TexturePackInfo:
    ...
```

Pack ID generation:

```text
Default → default
Faithful-32x-1.21.11.zip → faithful-32x-1-21-11
```

If duplicates exist, append a short hash.

---

## Cache

MVP can work without cache, but applying a pack in an open world is smoother with cache.

Cache key should include:

- pack path;
- pack file modified time;
- pack file size;
- mapping file hash;
- tile size;
- Veilstone version or atlas schema version.

Cache files:

```text
saves/texture_cache/<pack_id>-<hash>/
  blocks_atlas.png
  blocks_atlas.json
  import_report.json
```

For MVP, cache is optional.

Recommended sequence:

1. Implement runtime import first.
2. Add cache after UI flow works.

---

## Runtime renderer changes

Current path:

```python
atlas = create_block_atlas()
self.texture = context.texture((atlas.width, atlas.height), 4, atlas.pixels)
self.atlas_uvs = atlas.uvs
self.mesh_worker = SectionMeshWorker(self.registry, self.atlas_uvs, ...)
```

Target path:

```python
atlas = load_active_block_atlas(settings.graphics.texture_pack_id_or_path)
self._apply_block_atlas(atlas)
```

Add method on world renderer:

```python
def apply_texture_pack(self, atlas: AtlasImage) -> None:
    old_texture = self.texture
    self.texture = self.context.texture((atlas.width, atlas.height), 4, atlas.pixels)
    self.texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    self.texture.build_mipmaps()
    old_texture.release()

    self.atlas_uvs = atlas.uvs
    self.mesh_worker.update_texture_uvs(atlas.uvs)
    self.mesh_cache.clear()
    self.water_mesh_cache.clear()
    self.request_visible_remesh()
```

If `SectionMeshWorker` cannot update texture UVs, create a new worker and shut down the old one cleanly.

Need to verify current worker API before implementation.

---

## Applying in an open world

When the user applies a new pack while the world is open:

1. Pause or show loading overlay.
2. Import/build atlas.
3. Upload new OpenGL texture.
4. Update `atlas_uvs`.
5. Clear section mesh caches.
6. Rebuild visible section meshes using the same chunks and new UV rects.
7. Resume world.

World data does not change. Only mesh UVs and GPU texture change.

If import fails:

- keep old texture;
- keep old mesh cache;
- show error.

---

## UI changes

### Settings menu

Add a `Texture Packs` entry under Settings.

Flow:

```text
Settings
  Graphics
  Audio
  Controls
  Texture Packs
```

### Texture Packs screen

Show:

```text
Texture Packs

> Default
  Faithful-32x-1.21.11
  MyPack

[Apply] [Open Folder] [Back]
```

Useful metadata:

```text
Name: Faithful 32x
Source: resource_packs/Faithful-32x-1.21.11.zip
Format: Minecraft Java
Status: Not imported / Ready / Applied with warnings
```

### Controls

Minimum:

- Up/Down select pack.
- Enter apply selected pack.
- Escape back.
- Optional: button to open resource pack folder later.

### In-world apply

If the world is open, applying should not require restart.

Show overlay:

```text
Applying texture pack...
```

Then after success:

```text
Texture pack applied: Faithful-32x-1.21.11
Missing textures: 2, using fallback
```

---

## Settings persistence

Add to `config/settings.toml`:

```toml
[graphics]
texture_pack = "default"
```

Alternative MVP:

```toml
[graphics]
resource_pack_path = ""
```

Preferred long-term setting:

```toml
[graphics]
texture_pack_id = "default"
```

The registry resolves `texture_pack_id` to a local pack path.

For first implementation, `resource_pack_path` may be faster. For UI selection, `texture_pack_id` is cleaner.

Recommended path:

1. MVP with `graphics.resource_pack_path`.
2. UI phase migrates to `graphics.texture_pack_id`.

---

## Tests

Do not use real Faithful or Minecraft assets in tests.

Create tiny fake fixtures:

```text
tests/fixtures/resource_packs/fake_minecraft_pack/
  pack.mcmeta
  assets/minecraft/textures/block/stone.png
  assets/minecraft/textures/block/dirt.png
  assets/minecraft/textures/block/grass_block_top.png
  assets/minecraft/textures/block/water_still.png
```

Generate PNG fixtures during tests if possible to avoid binary fixtures.

Test cases:

### Importer tests

- detects folder pack with `pack.mcmeta`;
- detects zip pack with `pack.mcmeta`;
- resolves `minecraft:block/stone`;
- missing texture produces fallback and report entry;
- PNG converts to RGBA;
- vertical strip animation uses first frame and reports ignored animation.

### Atlas builder tests

- atlas contains all expected texture keys;
- UV rects are inside `[0, 1]`;
- missing keys are absent only if not requested;
- half-pixel inset is applied;
- tile size is consistent.

### Runtime tests

- default atlas still works;
- imported atlas overrides mapped textures;
- fallback tiles are used for missing pack textures;
- mesh builders accept imported atlas UVs.

### UI/controller tests

- texture pack list includes `Default`;
- texture pack list includes local zip/folder packs;
- selecting a pack updates settings;
- applying a pack calls renderer texture reload;
- failed import preserves previous active pack.

---

## Implementation phases

## Phase 1 — Data and local pack folder

Add:

```text
resource_packs/README.md
data/resource_pack_mappings/minecraft_java.toml
.gitignore rules for resource_packs and texture_cache
```

Acceptance:

- project has a documented place for user packs;
- third-party packs are ignored by git;
- mapping covers all current `data/blocks.toml` texture keys.

Checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

---

## Phase 2 — Atlas builder refactor

Refactor current procedural atlas:

```text
render/texture_atlas/generated.py
```

Into:

```text
create_default_block_tiles()
build_texture_atlas()
create_block_atlas()
```

Acceptance:

- default game visuals still work;
- existing `create_block_atlas()` API remains compatible;
- tests cover atlas UV creation.

Checks:

```bash
uv run pytest -m unit
uv run ruff check .
```

---

## Phase 3 — Minecraft Java pack importer

Add:

```text
render/texture_packs/minecraft_java.py
render/texture_packs/models.py
```

Acceptance:

- can import fake Minecraft pack folder;
- can import fake Minecraft pack zip;
- can import mapped textures from Faithful-like structure;
- missing textures use fallback;
- animated strips use first frame.

Checks:

```bash
uv run pytest -m unit
uv run ruff check .
uv run pyright
```

---

## Phase 4 — Active atlas loader

Add:

```text
render/texture_packs/importer.py
```

Suggested API:

```python
def load_active_block_atlas(
    resource_pack_path: Path | None,
    *,
    mapping_path: Path,
    fallback_tile_size: int = 32,
) -> AtlasImage:
    ...
```

Acceptance:

- `None` returns default generated atlas;
- Faithful zip path returns imported atlas with fallback for Veilstone-specific missing textures;
- does not read all textures from ZIP, only mapped ones.

Checks:

```bash
uv run pytest -m unit
uv run ruff check .
```

---

## Phase 5 — Renderer integration

Change `DemoWorldRenderer` startup:

```python
atlas = create_block_atlas()
```

to active atlas loading.

Acceptance:

- game starts with default textures;
- game starts with configured resource pack path;
- chunk meshes render using imported atlas;
- missing textures do not crash startup.

Checks:

```bash
uv run pytest -m unit
uv run pytest -m smoke
uv run ruff check .
```

---

## Phase 6 — Runtime apply in open world

Add renderer method:

```python
apply_texture_pack(...)
```

Acceptance:

- selecting a new pack while world is open uploads a new atlas;
- old texture is released;
- mesh caches are cleared;
- visible chunks are remeshed;
- player remains in the same world/session;
- failed import keeps previous texture.

Checks:

```bash
uv run pytest -m unit
uv run pytest -m integration
uv run ruff check .
```

Manual test:

```text
1. Start game.
2. Create/load world.
3. Open Settings → Texture Packs.
4. Select Faithful-32x-1.21.11.zip.
5. Apply.
6. Verify stone/dirt/grass/log/planks/water visuals change without restart.
7. Move around and verify new chunks use the selected pack.
```

---

## Phase 7 — UI picker

Add Settings → Texture Packs screen.

Acceptance:

- lists `Default`;
- lists local ZIP/folder packs from `resource_packs/`;
- can select a pack;
- can apply pack from menu and in-world pause settings;
- shows import warnings/missing count;
- persists selected pack.

Checks:

```bash
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m smoke
uv run ruff check .
```

---

## Phase 8 — Optional cache

Add cache to avoid rebuilding large packs repeatedly.

Acceptance:

- first import builds cache;
- second apply loads cache if pack/mapping unchanged;
- cache invalidates when pack file changes;
- cache invalidates when mapping file changes;
- cache is ignored by git.

---

## Phase 9 — Later improvements

Add only after MVP works:

- animated texture playback for water/lava/fire;
- item texture pack support;
- entity texture pack support;
- pack preview icons from `pack.png`;
- pack description from `pack.mcmeta`;
- open resource pack folder button;
- drag-and-drop pack install;
- support multiple namespaces;
- support custom Veilstone native packs;
- support `assets/veilstone/textures/block/*.png`;
- pack priority stack;
- live reload when ZIP/folder changes.

---

## Suggested Claude task prompt

Use this when asking Claude Code to implement the feature:

```text
Implement MVP user-supplied Minecraft Java-compatible texture pack support.

Goal:
Users can place a Minecraft-like resource pack ZIP/folder into resource_packs/, select it in the game UI, and apply it while a world is open. The game must not ship or commit third-party assets.

Use Faithful-32x-1.21.11.zip as a local manual test example only. Do not commit the ZIP or extracted assets.

Important current architecture:
- data/blocks.toml already has texture_top/texture_side/texture_bottom keys.
- Mesh builders already use texture_uvs.
- The shader already samples an atlas rect.
- create_block_atlas() currently generates a procedural atlas and should become fallback/default provider.

Implement in phases:
1. resource_packs/README.md + gitignore + minecraft_java mapping TOML.
2. Refactor generated atlas into default tile provider + generic atlas builder.
3. Add Minecraft Java ZIP/folder importer for mapped block textures.
4. Add active atlas loader with fallback for missing textures.
5. Integrate active atlas into DemoWorldRenderer startup.
6. Add runtime apply_texture_pack to upload new atlas and remesh visible chunks.
7. Add Settings → Texture Packs UI and persist selected pack.

MVP limitations:
- block textures only;
- no item/entity/model/blockstate support yet;
- animated PNG strips use first frame;
- missing textures use generated fallback;
- tests use fake fixture packs, not real Minecraft/Faithful assets.

Quality gates:
uv run ruff check .
uv run ruff format --check .
uv run pytest -m unit
uv run pytest -m integration
uv run pyright for cross-module/signature changes.
```

---

## Risk list

### Risk: UV/cache mismatch

If atlas UVs change, old meshes still point to old UV rects.

Mitigation:

- clear mesh caches after applying a new pack;
- remesh visible chunks.

### Risk: old OpenGL texture leak

If replacing atlas texture, old `moderngl.Texture` may remain allocated.

Mitigation:

- call `old_texture.release()` after new texture is created successfully.

### Risk: missing texture makes invisible blocks

If `texture_uvs` lacks a key, current lookup may remain zeros.

Mitigation:

- ensure final atlas always contains all texture keys used by `data/blocks.toml`;
- add explicit `missing` fallback tile.

### Risk: water animated strip appears wrong

MVP first-frame extraction is acceptable.

Mitigation:

- detect and crop first frame;
- record ignored animation in import report.

### Risk: Faithful or other packs use different names

Mitigation:

- use mapping file;
- allow user/project to edit mapping later;
- fallback on missing textures.

### Risk: UI apply during active meshing worker

Changing UVs while workers are building old meshes may race.

Mitigation:

- pause mesh submissions while applying;
- replace worker or update it safely;
- clear pending mesh queue if needed;
- remesh visible sections after apply.

---

## Definition of done for MVP

The feature is MVP-complete when:

- `resource_packs/` exists and is documented;
- third-party packs are ignored by git;
- Faithful-like ZIP/folder can be selected by path or UI;
- block textures are imported through mapping;
- atlas builds with fallback textures;
- game can start with default texture pack;
- game can start with selected user pack;
- player can apply a selected pack from UI while a world is open;
- visible chunks remesh and show the new atlas without restart;
- failed import preserves the previous active texture;
- tests use fake resource pack fixtures only;
- docs explain legal/asset-safety rules.
