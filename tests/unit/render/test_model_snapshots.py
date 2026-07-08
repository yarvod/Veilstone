from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.domain.items import create_core_item_registry
from voxel_sandbox.render.model_snapshots import (
    build_block_model_snapshot,
    build_item_model_snapshot,
    item_block_atlas_rect,
    item_block_texture_name,
)


def test_block_model_snapshot_keeps_minecraft_texture_locations() -> None:
    blocks = create_core_block_registry()

    model = build_block_model_snapshot(blocks.by_key("grass_block").id, blocks)

    assert model.key == "grass_block"
    assert model.texture_top == "minecraft:block/grass_block_top"
    assert model.texture_side == "minecraft:block/grass_block_side"
    assert model.texture_bottom == "minecraft:block/dirt"
    assert model.texture_for_face("top") == "minecraft:block/grass_block_top"
    assert model.texture_for_face("side") == "minecraft:block/grass_block_side"
    assert model.texture_for_face("bottom") == "minecraft:block/dirt"
    assert model.tint_for_face("top") == "grass"
    assert model.tint_for_face("side") is None
    assert model.tint_for_face("bottom") is None


def test_block_model_snapshot_marks_tinted_vegetation_textures() -> None:
    blocks = create_core_block_registry()

    short_grass = build_block_model_snapshot(blocks.by_key("short_grass").id, blocks)
    leaves = build_block_model_snapshot(blocks.by_key("oak_leaves").id, blocks)

    assert short_grass.tint_for_face("side") == "grass"
    assert short_grass.render_shape == "cross"
    assert leaves.tint_for_face("top") == "foliage"


def test_grass_terrain_material_faces_keep_distinct_texture_roles() -> None:
    blocks = create_core_block_registry()
    grass = build_block_model_snapshot(blocks.by_key("grass_block").id, blocks)

    assert tuple((face.face, face.texture, face.tint) for face in grass.face_materials()) == (
        ("top", "minecraft:block/grass_block_top", "grass"),
        ("side", "minecraft:block/grass_block_side", None),
        ("bottom", "minecraft:block/dirt", None),
    )


def test_item_model_snapshot_resolves_block_item_model() -> None:
    blocks = create_core_block_registry()
    items = create_core_item_registry()
    item = items.by_key("crafting_table")

    model = build_item_model_snapshot(item.id, items, blocks)

    assert model.key == "crafting_table"
    assert model.is_block
    assert model.block is not None
    assert model.block.texture_top == "minecraft:block/crafting_table_top"
    assert item_block_texture_name(item.id, items, blocks) == ("minecraft:block/crafting_table_top")
    assert item_block_texture_name(item.id, items, blocks, face="side") == (
        "minecraft:block/crafting_table_side"
    )


def test_item_model_snapshot_keeps_non_block_items_textureless() -> None:
    blocks = create_core_block_registry()
    items = create_core_item_registry()
    item = items.by_key("dusk_crystal")

    model = build_item_model_snapshot(item.id, items, blocks)

    assert not model.is_block
    assert model.block is None
    assert item_block_texture_name(item.id, items, blocks) is None


def test_item_block_atlas_rect_uses_resolved_texture_key() -> None:
    blocks = create_core_block_registry()
    items = create_core_item_registry()
    item = items.by_key("oak_planks")
    atlas_uvs = {"minecraft:block/oak_planks": (0.1, 0.2, 0.3, 0.4)}

    assert item_block_atlas_rect(item.id, items, blocks, atlas_uvs) == (
        0.1,
        0.2,
        0.3,
        0.4,
    )
