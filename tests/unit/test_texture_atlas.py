from __future__ import annotations

from PIL import Image

from voxel_sandbox.render.texture_atlas import (
    GeneratedAtlas,
    build_texture_atlas,
    create_block_atlas,
    create_default_block_tiles,
)

_EXPECTED_KEYS = {
    "minecraft:block/stone",
    "minecraft:block/dirt",
    "minecraft:block/grass_block_top",
    "minecraft:block/grass_block_side",
    "minecraft:block/oak_log_top",
    "minecraft:block/oak_log",
    "minecraft:block/oak_leaves",
    "minecraft:block/oak_planks",
    "minecraft:block/diamond_ore",
    "minecraft:block/lantern",
    "minecraft:block/water_still",
    "minecraft:block/crafting_table_top",
    "minecraft:block/crafting_table_side",
    "minecraft:block/red_mushroom",
    "minecraft:block/glow_lichen",
    "minecraft:block/short_grass",
    "minecraft:block/dandelion",
}


def test_default_tiles_returns_all_texture_keys() -> None:
    tiles = create_default_block_tiles(tile_size=8)
    assert set(tiles) == _EXPECTED_KEYS
    for name, img in tiles.items():
        assert img.size == (8, 8), f"{name}: expected 8x8, got {img.size}"
        assert img.mode == "RGBA"


def test_default_leaf_tile_contains_cutout_alpha() -> None:
    leaves = create_default_block_tiles(tile_size=16)["minecraft:block/oak_leaves"]
    alphas = [pixel[3] for pixel in leaves.getdata()]

    assert min(alphas) == 0
    assert max(alphas) == 255


def test_default_ground_cover_tiles_contain_cutout_alpha() -> None:
    tiles = create_default_block_tiles(tile_size=16)
    for name in ("minecraft:block/short_grass", "minecraft:block/dandelion"):
        alphas = [pixel[3] for pixel in tiles[name].getdata()]
        assert min(alphas) == 0
        assert max(alphas) == 255


def test_default_short_grass_is_sparse_upright_cutout() -> None:
    grass = create_default_block_tiles(tile_size=16)["minecraft:block/short_grass"]
    opaque_pixels = [
        (x, y) for y in range(16) for x in range(16) if grass.getpixel((x, y))[3] >= 128
    ]

    assert 20 <= len(opaque_pixels) <= 85
    assert all(y > 3 for _, y in opaque_pixels)
    assert sum(1 for _, y in opaque_pixels if y >= 12) > sum(1 for _, y in opaque_pixels if y <= 7)

    top_or_side_frame = [
        grass.getpixel((x, y))[3]
        for y in range(16)
        for x in range(16)
        if y == 0 or x == 0 or x == 15
    ]
    assert max(top_or_side_frame) == 0

    opaque_colors = [grass.getpixel((x, y))[:3] for x, y in opaque_pixels]
    assert min(sum(color) for color in opaque_colors) > 180
    assert all(green >= red and green >= blue for red, green, blue in opaque_colors)


def test_build_texture_atlas_contains_all_keys() -> None:
    tiles = create_default_block_tiles(tile_size=8)
    atlas = build_texture_atlas(tiles, tile_size=8)
    assert set(atlas.uvs) == _EXPECTED_KEYS


def test_build_texture_atlas_uv_coords_in_range() -> None:
    tiles = create_default_block_tiles(tile_size=8)
    atlas = build_texture_atlas(tiles, tile_size=8)
    for name, (u0, v0, u1, v1) in atlas.uvs.items():
        assert 0.0 <= u0 < u1 <= 1.0, f"{name}: bad U range {u0} {u1}"
        assert 0.0 <= v0 < v1 <= 1.0, f"{name}: bad V range {v0} {v1}"


def test_build_texture_atlas_half_pixel_inset() -> None:
    """UV borders must be inset by 0.5/atlas_dimension to avoid bleeding."""
    tiles = create_default_block_tiles(tile_size=8)
    atlas = build_texture_atlas(tiles, tile_size=8)
    inset_u = 0.5 / atlas.width
    inset_v = 0.5 / atlas.height
    for u0, v0, u1, v1 in atlas.uvs.values():
        assert u0 > inset_u * 0.5
        assert v0 > inset_v * 0.5
        assert u1 < 1.0 - inset_u * 0.5
        assert v1 < 1.0 - inset_v * 0.5


def test_build_texture_atlas_dimensions_are_multiples_of_tile_size() -> None:
    tiles = create_default_block_tiles(tile_size=8)
    atlas = build_texture_atlas(tiles, tile_size=8)
    assert atlas.width % 8 == 0
    assert atlas.height % 8 == 0
    assert len(atlas.pixels) == atlas.width * atlas.height * 4


def test_build_texture_atlas_is_deterministic() -> None:
    tiles = create_default_block_tiles(tile_size=8)
    a = build_texture_atlas(tiles, tile_size=8)
    b = build_texture_atlas(tiles, tile_size=8)
    assert a.pixels == b.pixels
    assert a.uvs == b.uvs


def test_build_texture_atlas_accepts_external_tiles() -> None:
    """Custom tiles override the atlas; any resource location key is accepted."""
    custom = {"minecraft:block/cobblestone": Image.new("RGBA", (16, 16), (140, 130, 120, 255))}
    atlas = build_texture_atlas(custom, tile_size=16)
    assert "minecraft:block/cobblestone" in atlas.uvs
    assert atlas.width == 16
    assert atlas.height == 16


def test_create_block_atlas_backward_compatible() -> None:
    atlas = create_block_atlas(tile_size=16)
    assert isinstance(atlas, GeneratedAtlas)
    assert set(atlas.uvs) == _EXPECTED_KEYS
    assert all(0.0 <= c <= 1.0 for uv in atlas.uvs.values() for c in uv)
    assert len(atlas.pixels) == atlas.width * atlas.height * 4
