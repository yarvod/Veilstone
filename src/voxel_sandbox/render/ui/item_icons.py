from __future__ import annotations

import pyglet
from PIL import Image, ImageDraw

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.items import ItemDef, ItemRegistry, ItemType
from voxel_sandbox.render.model_snapshots import item_block_texture_name
from voxel_sandbox.render.texture_atlas import create_block_atlas

ICON_SIZE = 32
HEART_SIZE = 18
HAND_SIZE = 128


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
        texture = item_block_texture_name(item.id, items, blocks)
        if texture is not None:
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


def create_heart_icons() -> tuple[pyglet.image.AbstractImage, ...]:
    return tuple(_heart_image(fill) for fill in (0.0, 0.5, 1.0))


def create_hand_image() -> pyglet.image.AbstractImage:
    image = Image.new("RGBA", (HAND_SIZE, HAND_SIZE))
    draw = ImageDraw.Draw(image)
    draw.polygon(
        ((54, 128), (45, 91), (56, 55), (86, 42), (110, 55), (104, 88), (91, 128)),
        fill=(167, 112, 82, 255),
    )
    draw.polygon(
        ((59, 91), (65, 58), (86, 49), (101, 58), (95, 77), (79, 86)),
        fill=(202, 145, 102, 255),
    )
    draw.polygon(((45, 91), (59, 91), (67, 128), (54, 128)), fill=(36, 96, 118, 255))
    return pyglet.image.ImageData(
        HAND_SIZE,
        HAND_SIZE,
        "RGBA",
        image.tobytes(),
        pitch=-HAND_SIZE * 4,
    )


def _heart_image(fill: float) -> pyglet.image.AbstractImage:
    image = Image.new("RGBA", (HEART_SIZE, HEART_SIZE))
    draw = ImageDraw.Draw(image)
    outline = (
        (4, 4),
        (7, 4),
        (9, 6),
        (11, 4),
        (14, 4),
        (16, 6),
        (16, 10),
        (9, 17),
        (2, 10),
        (2, 6),
    )
    draw.polygon(outline, fill=(62, 24, 30, 255))
    inner = ((4, 7), (7, 6), (9, 8), (11, 6), (14, 7), (14, 10), (9, 15), (4, 10))
    draw.polygon(inner, fill=(44, 38, 45, 255))
    if fill > 0.0:
        mask = Image.new("L", (HEART_SIZE, HEART_SIZE))
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.polygon(inner, fill=255)
        if fill < 1.0:
            mask_draw.rectangle((9, 0, HEART_SIZE, HEART_SIZE), fill=0)
        red = Image.new("RGBA", image.size, (210, 46, 58, 255))
        image.alpha_composite(Image.composite(red, Image.new("RGBA", image.size), mask))
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 7, 7, 9), fill=(255, 126, 132, 255))
    return pyglet.image.ImageData(
        HEART_SIZE,
        HEART_SIZE,
        "RGBA",
        image.tobytes(),
        pitch=-HEART_SIZE * 4,
    )


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
