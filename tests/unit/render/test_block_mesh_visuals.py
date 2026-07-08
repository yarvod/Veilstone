from __future__ import annotations

import numpy as np

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.render.meshes.block_visuals import build_block_mesh_visual_lookups
from voxel_sandbox.render.vegetation_wind import WIND_CROSS_PLANT, WIND_FOLIAGE, WIND_STATIC


def test_block_mesh_visual_lookups_use_block_model_snapshots() -> None:
    blocks = create_core_block_registry()
    texture_uvs = {
        "minecraft:block/grass_block_top": (0.1, 0.2, 0.3, 0.4),
        "minecraft:block/grass_block_side": (0.2, 0.3, 0.4, 0.5),
        "minecraft:block/dirt": (0.3, 0.4, 0.5, 0.6),
        "minecraft:block/short_grass": (0.4, 0.5, 0.6, 0.7),
        "minecraft:block/oak_leaves": (0.5, 0.6, 0.7, 0.8),
        "minecraft:block/lantern": (0.6, 0.7, 0.8, 0.9),
    }

    lookups = build_block_mesh_visual_lookups(blocks, texture_uvs)

    grass = blocks.by_key("grass_block")
    short_grass = blocks.by_key("short_grass")
    leaves = blocks.by_key("oak_leaves")
    lantern = blocks.by_key("lantern")

    np.testing.assert_allclose(lookups.texture_rects["top"][grass.id], (0.1, 0.2, 0.3, 0.4))
    np.testing.assert_allclose(lookups.texture_rects["side"][grass.id], (0.2, 0.3, 0.4, 0.5))
    np.testing.assert_allclose(lookups.texture_rects["bottom"][grass.id], (0.3, 0.4, 0.5, 0.6))
    assert bool(lookups.cross_lookup[short_grass.id]) is True
    assert bool(lookups.cross_lookup[leaves.id]) is False
    assert lookups.wind_lookup[short_grass.id] == WIND_CROSS_PLANT
    assert lookups.wind_lookup[leaves.id] == WIND_FOLIAGE
    assert lookups.wind_lookup[lantern.id] == WIND_STATIC
    assert lookups.material_rects == {}


def test_block_mesh_visual_lookups_align_optional_material_rects() -> None:
    blocks = create_core_block_registry()
    texture_uvs = {
        "minecraft:block/grass_block_top": (0.1, 0.2, 0.3, 0.4),
        "minecraft:block/grass_block_side": (0.2, 0.3, 0.4, 0.5),
        "minecraft:block/dirt": (0.3, 0.4, 0.5, 0.6),
    }
    material_uvs = {
        "normal": {
            "minecraft:block/grass_block_top": (0.4, 0.5, 0.6, 0.7),
            "minecraft:block/grass_block_side": (0.5, 0.6, 0.7, 0.8),
        },
        "specular": {
            "minecraft:block/grass_block_top": (0.6, 0.7, 0.8, 0.9),
        },
    }

    lookups = build_block_mesh_visual_lookups(blocks, texture_uvs, material_uvs)

    grass = blocks.by_key("grass_block")
    np.testing.assert_allclose(
        lookups.material_rects["normal"]["top"][grass.id],
        (0.4, 0.5, 0.6, 0.7),
    )
    np.testing.assert_allclose(
        lookups.material_rects["normal"]["side"][grass.id],
        (0.5, 0.6, 0.7, 0.8),
    )
    np.testing.assert_allclose(
        lookups.material_rects["specular"]["top"][grass.id],
        (0.6, 0.7, 0.8, 0.9),
    )
    np.testing.assert_allclose(
        lookups.material_rects["specular"]["side"][grass.id],
        (0.0, 0.0, 0.0, 0.0),
    )
