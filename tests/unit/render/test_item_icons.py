from __future__ import annotations

import pyglet
from PIL import Image

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.domain.items import create_core_item_registry
from voxel_sandbox.render.texture_atlas import (
    GeneratedAtlas,
    build_texture_atlas,
    create_default_block_tiles,
)
from voxel_sandbox.render.ui.item_icons import (
    ICON_SIZE,
    create_item_icons,
    generated_atlas_image,
)


def _fake_atlas(
    *,
    top: tuple[int, int, int, int],
    side: tuple[int, int, int, int],
) -> GeneratedAtlas:
    tiles = create_default_block_tiles(tile_size=4)
    for texture_name in tiles:
        tiles[texture_name] = Image.new("RGBA", (4, 4), (90, 90, 90, 255))
    tiles["minecraft:block/grass_block_top"] = Image.new("RGBA", (4, 4), top)
    tiles["minecraft:block/grass_block_side"] = Image.new("RGBA", (4, 4), side)
    return build_texture_atlas(tiles, tile_size=4)


def _rgba_bytes(image: pyglet.image.AbstractImage) -> bytes:
    return image.get_image_data().get_data("RGBA", ICON_SIZE * 4)


def test_item_icons_follow_fake_active_atlas_and_keep_non_block_fallbacks() -> None:
    items = create_core_item_registry()
    blocks = create_core_block_registry()
    first_atlas = _fake_atlas(top=(240, 40, 30, 255), side=(20, 220, 70, 255))
    second_atlas = _fake_atlas(top=(30, 70, 240, 255), side=(230, 210, 30, 255))

    first_icons = create_item_icons(
        items,
        blocks,
        generated_atlas_image(first_atlas),
        first_atlas.uvs,
    )
    second_icons = create_item_icons(
        items,
        blocks,
        generated_atlas_image(second_atlas),
        second_atlas.uvs,
    )

    grass_id = items.by_key("grass_block").id
    resource_id = items.by_key("dusk_crystal").id
    first_grass = _rgba_bytes(first_icons[grass_id])
    second_grass = _rgba_bytes(second_icons[grass_id])

    assert bytes((240, 40, 30, 255)) in first_grass
    assert bytes((30, 70, 240, 255)) in second_grass
    assert first_grass != second_grass
    assert _rgba_bytes(first_icons[resource_id]) == _rgba_bytes(second_icons[resource_id])
