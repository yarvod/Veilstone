from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.domain.items import create_core_item_registry
from voxel_sandbox.render.model_snapshots import (
    build_block_model_snapshot,
    build_item_model_snapshot,
    item_block_atlas_rect,
    item_block_texture_name,
    item_block_texture_slots,
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


def test_block_model_snapshot_marks_visual_only_wind_motion() -> None:
    blocks = create_core_block_registry()

    grass_block = build_block_model_snapshot(blocks.by_key("grass_block").id, blocks)
    short_grass = build_block_model_snapshot(blocks.by_key("short_grass").id, blocks)
    wildflower = build_block_model_snapshot(blocks.by_key("wildflower").id, blocks)
    leaves = build_block_model_snapshot(blocks.by_key("oak_leaves").id, blocks)
    lantern = build_block_model_snapshot(blocks.by_key("lantern").id, blocks)

    assert grass_block.wind_motion == "none"
    assert short_grass.wind_motion == "cross_plant"
    assert wildflower.wind_motion == "cross_plant"
    assert leaves.wind_motion == "foliage"
    assert lantern.wind_motion == "none"


def test_grass_terrain_material_faces_keep_distinct_texture_roles() -> None:
    blocks = create_core_block_registry()
    grass = build_block_model_snapshot(blocks.by_key("grass_block").id, blocks)

    assert tuple((face.face, face.texture, face.tint) for face in grass.face_materials()) == (
        ("top", "minecraft:block/grass_block_top", "grass"),
        ("side", "minecraft:block/grass_block_side", None),
        ("bottom", "minecraft:block/dirt", None),
    )


def test_block_model_snapshot_builds_material_visual_snapshots() -> None:
    blocks = create_core_block_registry()
    grass = build_block_model_snapshot(blocks.by_key("grass_block").id, blocks)
    color_uvs = {
        "minecraft:block/grass_block_top": (0.0, 0.0, 0.25, 0.25),
        "minecraft:block/grass_block_side": (0.25, 0.0, 0.25, 0.25),
        "minecraft:block/dirt": (0.5, 0.0, 0.25, 0.25),
    }
    material_uvs = {
        "normal": {
            "minecraft:block/grass_block_top": (0.0, 0.25, 0.25, 0.25),
            "minecraft:block/grass_block_side": (0.25, 0.25, 0.25, 0.25),
        },
        "specular": {
            "minecraft:block/grass_block_top": (0.0, 0.5, 0.25, 0.25),
        },
    }

    visuals = grass.material_visuals(color_uvs, material_uvs)

    assert tuple(visual.face for visual in visuals) == ("top", "side", "bottom")
    assert visuals[0].texture == "minecraft:block/grass_block_top"
    assert visuals[0].color_rect == (0.0, 0.0, 0.25, 0.25)
    assert visuals[0].tint == "grass"
    assert visuals[0].material_rects == {
        "normal": (0.0, 0.25, 0.25, 0.25),
        "specular": (0.0, 0.5, 0.25, 0.25),
    }
    assert visuals[1].material_rects == {"normal": (0.25, 0.25, 0.25, 0.25)}
    assert visuals[2].material_rects == {}


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


def test_grass_block_item_texture_defaults_to_top_without_collapsing_terrain_faces() -> None:
    blocks = create_core_block_registry()
    items = create_core_item_registry()
    item = items.by_key("grass_block")
    slots = item_block_texture_slots(item.id, items, blocks)

    assert item_block_texture_name(item.id, items, blocks) == "minecraft:block/grass_block_top"
    assert item_block_texture_name(item.id, items, blocks, face="side") == (
        "minecraft:block/grass_block_side"
    )
    assert item_block_texture_name(item.id, items, blocks, face="bottom") == "minecraft:block/dirt"
    assert slots is not None
    assert slots.default == "minecraft:block/grass_block_top"
    assert slots.texture_for_face("side") == "minecraft:block/grass_block_side"
    assert slots.texture_for_face("bottom") == "minecraft:block/dirt"
