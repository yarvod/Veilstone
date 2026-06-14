from __future__ import annotations

import pyglet
from PIL import Image, ImageDraw

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.items import ItemDef, ItemRegistry, ItemType
from voxel_sandbox.render.texture_atlas import create_block_atlas

ICON_SIZE = 32


def create_item_icons(
    items: ItemRegistry,
    blocks: BlockRegistry,
) -> dict[int, pyglet.image.AbstractImage]:
    atlas = create_block_atlas()
    atlas_image = Image.frombytes("RGBA", (atlas.width, atlas.height), atlas.pixels).transpose(
        Image.Transpose.FLIP_TOP_BOTTOM
    )
    icons: dict[int, pyglet.image.AbstractImage] = {}
    for item in items:
        if item.block_id is not None:
            texture = blocks.by_id(item.block_id).texture_top
            image = _crop_atlas_tile(atlas_image, atlas.uvs[texture])
        else:
            image = _draw_non_block_icon(item)
        icons[item.id] = pyglet.image.ImageData(
            ICON_SIZE,
            ICON_SIZE,
            "RGBA",
            image.tobytes(),
            pitch=-ICON_SIZE * 4,
        )
    return icons


def _crop_atlas_tile(
    atlas: Image.Image,
    uv: tuple[float, float, float, float],
) -> Image.Image:
    left = round(uv[0] * atlas.width)
    right = round(uv[2] * atlas.width)
    top = round((1.0 - uv[3]) * atlas.height)
    bottom = round((1.0 - uv[1]) * atlas.height)
    return atlas.crop((left, top, right, bottom)).resize(
        (ICON_SIZE, ICON_SIZE), Image.Resampling.NEAREST
    )


def _draw_non_block_icon(item: ItemDef) -> Image.Image:
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE))
    draw = ImageDraw.Draw(image)
    if item.item_type is ItemType.RESOURCE:
        draw.polygon(((16, 2), (27, 14), (18, 29), (5, 19)), fill=(145, 92, 205, 255))
        draw.polygon(((16, 5), (22, 15), (16, 24), (9, 18)), fill=(222, 177, 255, 255))
        draw.line(((16, 5), (16, 24)), fill=(88, 48, 132, 255), width=2)
    elif item.item_type is ItemType.FLUID_CONTAINER:
        draw.rectangle((10, 7, 23, 27), fill=(92, 72, 61, 255), outline=(36, 30, 30, 255), width=2)
        draw.rectangle((12, 11, 21, 24), fill=(48, 132, 188, 255))
        draw.rectangle((13, 4, 20, 9), fill=(154, 142, 122, 255))
    else:
        draw.rectangle((7, 7, 25, 25), fill=(190, 180, 150, 255))
    return image
