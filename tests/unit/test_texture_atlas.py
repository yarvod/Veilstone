from __future__ import annotations

from voxel_sandbox.render.texture_atlas import create_block_atlas


def test_generated_atlas_contains_core_textures() -> None:
    atlas = create_block_atlas(tile_size=16)

    assert (atlas.width, atlas.height) == (64, 32)
    assert len(atlas.pixels) == 64 * 32 * 4
    assert set(atlas.uvs) == {
        "stone",
        "dirt",
        "grass_top",
        "grass_side",
        "veilwood_cut",
        "veilwood_bark",
        "veilwood_leaves",
        "dusk_crystal_ore",
    }
    assert all(0.0 <= coordinate <= 1.0 for uv in atlas.uvs.values() for coordinate in uv)
