from __future__ import annotations

import math
from collections.abc import Mapping
from typing import cast

from PIL import Image, ImageEnhance

from voxel_sandbox.render.model_snapshots import ItemModelSnapshot, TextureRect

type Point = tuple[float, float]
type RgbaPixel = tuple[int, int, int, int]


def compose_item_model_icon(
    model: ItemModelSnapshot,
    atlas: Image.Image,
    atlas_uvs: Mapping[str, TextureRect],
    *,
    size: int = 32,
) -> Image.Image | None:
    """Compose a pixel-art isometric block icon, or defer non-block items."""

    if model.block is None:
        return None
    top = crop_atlas_tile(atlas, atlas_uvs[model.block.texture_top], size=size)
    side = crop_atlas_tile(atlas, atlas_uvs[model.block.texture_side], size=size)
    return compose_isometric_block_icon(top, side, size=size)


def compose_isometric_block_icon(
    top: Image.Image,
    side: Image.Image,
    *,
    size: int = 32,
) -> Image.Image:
    if size < 16:
        raise ValueError("Isometric block icons require at least 16 pixels")

    scale = size / 32.0

    def point(x: float, y: float) -> Point:
        return x * scale, y * scale

    canvas = Image.new("RGBA", (size, size))
    left = _project_to_parallelogram(
        _shade_rgba(side, 0.82),
        size=size,
        origin=point(4, 8),
        u_axis=point(12, 6),
        v_axis=point(0, 15),
    )
    right = _project_to_parallelogram(
        _shade_rgba(side, 0.68),
        size=size,
        origin=point(16, 14),
        u_axis=point(12, -6),
        v_axis=point(0, 15),
    )
    top_face = _project_to_parallelogram(
        top.convert("RGBA"),
        size=size,
        origin=point(16, 2),
        u_axis=point(12, 6),
        v_axis=point(-12, 6),
    )
    canvas.alpha_composite(left)
    canvas.alpha_composite(right)
    canvas.alpha_composite(top_face)
    return canvas


def crop_atlas_tile(
    atlas: Image.Image,
    uv: TextureRect,
    *,
    size: int,
) -> Image.Image:
    left = round(uv[0] * atlas.width)
    right = round(uv[2] * atlas.width)
    top = round((1.0 - uv[3]) * atlas.height)
    bottom = round((1.0 - uv[1]) * atlas.height)
    return atlas.crop((left, top, right, bottom)).resize((size, size), Image.Resampling.NEAREST)


def _project_to_parallelogram(
    texture: Image.Image,
    *,
    size: int,
    origin: Point,
    u_axis: Point,
    v_axis: Point,
) -> Image.Image:
    determinant = u_axis[0] * v_axis[1] - u_axis[1] * v_axis[0]
    if abs(determinant) < 1e-8:
        raise ValueError("Projected face axes must not be collinear")

    source = texture.convert("RGBA")
    result = Image.new("RGBA", (size, size))
    corners = (
        origin,
        (origin[0] + u_axis[0], origin[1] + u_axis[1]),
        (origin[0] + v_axis[0], origin[1] + v_axis[1]),
        (
            origin[0] + u_axis[0] + v_axis[0],
            origin[1] + u_axis[1] + v_axis[1],
        ),
    )
    min_x = max(0, math.floor(min(point[0] for point in corners)))
    max_x = min(size - 1, math.ceil(max(point[0] for point in corners)))
    min_y = max(0, math.floor(min(point[1] for point in corners)))
    max_y = min(size - 1, math.ceil(max(point[1] for point in corners)))
    source_width, source_height = source.size

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            delta_x = x + 0.5 - origin[0]
            delta_y = y + 0.5 - origin[1]
            u = (delta_x * v_axis[1] - delta_y * v_axis[0]) / determinant
            v = (u_axis[0] * delta_y - u_axis[1] * delta_x) / determinant
            if not (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
                continue
            source_x = min(source_width - 1, int(u * source_width))
            source_y = min(source_height - 1, int(v * source_height))
            result.putpixel(
                (x, y),
                cast(
                    RgbaPixel,
                    source.getpixel((source_x, source_y)),
                ),
            )
    return result


def _shade_rgba(image: Image.Image, brightness: float) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    shaded = ImageEnhance.Brightness(rgba.convert("RGB")).enhance(brightness).convert("RGBA")
    shaded.putalpha(alpha)
    return shaded
