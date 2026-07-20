from __future__ import annotations

from typing import cast

import pytest
from PIL import Image

from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.texture_atlas import (
    GeneratedAtlas,
    build_material_atlas_bundle,
    build_parallel_material_atlas,
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


def test_build_texture_atlas_records_sampling_metadata() -> None:
    atlas = build_texture_atlas(create_default_block_tiles(tile_size=16), tile_size=16)

    assert atlas.tile_size == 16
    assert atlas.edge_inset_pixels == 0.5
    assert atlas.gutter_pixels == 1


def test_build_texture_atlas_extrudes_tile_edges_into_gutter() -> None:
    tile = Image.new("RGBA", (2, 2))
    tile.putpixel((0, 0), (255, 0, 0, 255))
    tile.putpixel((1, 0), (0, 255, 0, 255))
    tile.putpixel((0, 1), (0, 0, 255, 255))
    tile.putpixel((1, 1), (255, 255, 0, 255))

    atlas = build_texture_atlas({"test:block": tile}, tile_size=2)
    image = Image.frombytes("RGBA", (atlas.width, atlas.height), atlas.pixels).transpose(
        Image.Transpose.FLIP_TOP_BOTTOM
    )

    assert image.size == (4, 4)
    assert image.getpixel((0, 0)) == (255, 0, 0, 255)
    assert image.getpixel((3, 0)) == (0, 255, 0, 255)
    assert image.getpixel((0, 3)) == (0, 0, 255, 255)
    assert image.getpixel((3, 3)) == (255, 255, 0, 255)
    assert image.getpixel((0, 1)) == image.getpixel((1, 1))
    assert image.getpixel((3, 2)) == image.getpixel((2, 2))


def test_parallel_material_atlas_reuses_color_dimensions_and_uvs() -> None:
    color_atlas = build_texture_atlas(
        {
            "minecraft:block/dirt": Image.new("RGBA", (4, 4), (10, 20, 30, 255)),
            "minecraft:block/stone": Image.new("RGBA", (4, 4), (40, 50, 60, 255)),
        },
        tile_size=4,
    )

    material_atlas = build_parallel_material_atlas(
        color_atlas,
        role=MaterialMapRole.NORMAL,
        tiles={"minecraft:block/stone": Image.new("RGBA", (4, 4), (128, 128, 255, 255))},
        default_color=(128, 128, 128, 255),
    )

    assert material_atlas.role is MaterialMapRole.NORMAL
    assert material_atlas.width == color_atlas.width
    assert material_atlas.height == color_atlas.height
    assert material_atlas.uvs == color_atlas.uvs
    assert material_atlas.tile_size == color_atlas.tile_size
    assert material_atlas.edge_inset_pixels == color_atlas.edge_inset_pixels
    assert material_atlas.gutter_pixels == color_atlas.gutter_pixels


def test_parallel_material_atlas_places_tiles_in_matching_color_slots() -> None:
    color_atlas = build_texture_atlas(
        {
            "minecraft:block/dirt": Image.new("RGBA", (4, 4), (10, 20, 30, 255)),
            "minecraft:block/stone": Image.new("RGBA", (4, 4), (40, 50, 60, 255)),
        },
        tile_size=4,
    )

    material_atlas = build_parallel_material_atlas(
        color_atlas,
        role=MaterialMapRole.MER,
        tiles={"minecraft:block/stone": Image.new("RGBA", (4, 4), (20, 40, 80, 255))},
        default_color=(1, 2, 3, 255),
    )
    image = Image.frombytes(
        "RGBA", (material_atlas.width, material_atlas.height), material_atlas.pixels
    ).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    def sample(resource_id: str) -> tuple[int, int, int, int]:
        uv = material_atlas.uvs[resource_id]
        x = round((uv[0] - material_atlas.edge_inset_pixels / material_atlas.width) * image.width)
        y = round(
            (1.0 - uv[3] - material_atlas.edge_inset_pixels / material_atlas.height) * image.height
        )
        pixel = cast(tuple[int, int, int, int], image.getpixel((x, y)))
        return (int(pixel[0]), int(pixel[1]), int(pixel[2]), int(pixel[3]))

    assert sample("minecraft:block/stone") == (20, 40, 80, 255)
    assert sample("minecraft:block/dirt") == (1, 2, 3, 255)


def test_material_atlas_bundle_omits_missing_roles() -> None:
    color_atlas = build_texture_atlas(
        {
            "minecraft:block/dirt": Image.new("RGBA", (4, 4), (10, 20, 30, 255)),
            "minecraft:block/stone": Image.new("RGBA", (4, 4), (40, 50, 60, 255)),
        },
        tile_size=4,
    )

    bundle = build_material_atlas_bundle(
        color_atlas,
        material_tiles={
            MaterialMapRole.NORMAL: {
                "minecraft:block/stone": Image.new("RGBA", (4, 4), (128, 128, 255, 255))
            },
            MaterialMapRole.MER: {},
        },
        defaults={
            MaterialMapRole.NORMAL: (128, 128, 128, 255),
            MaterialMapRole.MER: (0, 0, 0, 255),
        },
    )

    assert bundle.color is color_atlas
    assert set(bundle.materials) == {MaterialMapRole.NORMAL}


def test_material_atlas_bundle_keeps_present_roles_aligned_with_color() -> None:
    color_atlas = build_texture_atlas(
        {
            "minecraft:block/dirt": Image.new("RGBA", (4, 4), (10, 20, 30, 255)),
            "minecraft:block/stone": Image.new("RGBA", (4, 4), (40, 50, 60, 255)),
        },
        tile_size=4,
    )

    bundle = build_material_atlas_bundle(
        color_atlas,
        material_tiles={
            MaterialMapRole.NORMAL: {
                "minecraft:block/stone": Image.new("RGBA", (4, 4), (128, 128, 255, 255))
            },
            MaterialMapRole.MER: {
                "minecraft:block/stone": Image.new("RGBA", (4, 4), (10, 20, 30, 255))
            },
        },
        defaults={
            MaterialMapRole.NORMAL: (128, 128, 128, 255),
            MaterialMapRole.MER: (0, 0, 0, 255),
        },
    )

    for atlas in bundle.materials.values():
        assert atlas.width == color_atlas.width
        assert atlas.height == color_atlas.height
        assert atlas.uvs == color_atlas.uvs
        assert atlas.tile_size == color_atlas.tile_size
        assert atlas.edge_inset_pixels == color_atlas.edge_inset_pixels
        assert atlas.gutter_pixels == color_atlas.gutter_pixels


def test_grass_terrain_uvs_preserve_half_pixel_sampling_gutter() -> None:
    tile_size = 16
    atlas = build_texture_atlas(
        create_default_block_tiles(tile_size=tile_size), tile_size=tile_size
    )
    expected_u_span = (tile_size - atlas.edge_inset_pixels * 2.0) / atlas.width
    expected_v_span = (tile_size - atlas.edge_inset_pixels * 2.0) / atlas.height

    for texture in (
        "minecraft:block/grass_block_top",
        "minecraft:block/grass_block_side",
        "minecraft:block/dirt",
    ):
        u0, v0, u1, v1 = atlas.uvs[texture]
        assert u1 - u0 == pytest.approx(expected_u_span)
        assert v1 - v0 == pytest.approx(expected_v_span)


def test_build_texture_atlas_dimensions_are_multiples_of_tile_size() -> None:
    tiles = create_default_block_tiles(tile_size=8)
    atlas = build_texture_atlas(tiles, tile_size=8)
    cell_size = atlas.tile_size + atlas.gutter_pixels * 2
    assert atlas.width % cell_size == 0
    assert atlas.height % cell_size == 0
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
    assert atlas.width == 18
    assert atlas.height == 18


def test_create_block_atlas_backward_compatible() -> None:
    atlas = create_block_atlas(tile_size=16)
    assert isinstance(atlas, GeneratedAtlas)
    assert set(atlas.uvs) == _EXPECTED_KEYS
    assert all(0.0 <= c <= 1.0 for uv in atlas.uvs.values() for c in uv)
    assert len(atlas.pixels) == atlas.width * atlas.height * 4
