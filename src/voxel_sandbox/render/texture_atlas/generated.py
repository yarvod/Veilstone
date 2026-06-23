from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt

from PIL import Image, ImageDraw


@dataclass(frozen=True, slots=True)
class GeneratedAtlas:
    width: int
    height: int
    pixels: bytes
    uvs: dict[str, tuple[float, float, float, float]]


# Default procedural tiles keyed by Minecraft-style resource locations.
# Colors are approximate; real textures come from user-supplied resource packs.
_DEFAULT_COLORS: dict[str, tuple[int, int, int, int]] = {
    "minecraft:block/stone": (92, 100, 112, 255),
    "minecraft:block/dirt": (102, 68, 45, 255),
    "minecraft:block/grass_block_top": (95, 159, 53, 255),
    "minecraft:block/grass_block_side": (90, 125, 55, 255),
    "minecraft:block/oak_log_top": (126, 104, 83, 255),
    "minecraft:block/oak_log": (64, 55, 72, 255),
    "minecraft:block/oak_leaves": (72, 128, 47, 255),
    "minecraft:block/oak_planks": (112, 87, 72, 255),
    "minecraft:block/diamond_ore": (90, 72, 122, 255),
    "minecraft:block/lantern": (226, 154, 72, 255),
    "minecraft:block/water_still": (46, 105, 157, 180),
    "minecraft:block/crafting_table_top": (87, 70, 98, 255),
    "minecraft:block/crafting_table_side": (72, 58, 82, 255),
    "minecraft:block/red_mushroom": (60, 200, 180, 255),
    "minecraft:block/glow_lichen": (200, 255, 100, 150),
    "minecraft:block/short_grass": (95, 140, 75, 255),
    "minecraft:block/dandelion": (230, 205, 70, 255),
}


def create_default_block_tiles(tile_size: int = 32) -> dict[str, Image.Image]:
    """Return procedurally generated PIL images keyed by resource location."""
    tiles: dict[str, Image.Image] = {}
    for name, color in _DEFAULT_COLORS.items():
        image = Image.new("RGBA", (tile_size, tile_size))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, tile_size - 1, tile_size - 1), fill=color)
        seed = sum((i + 1) * ord(c) for i, c in enumerate(name))
        for py in range(1, tile_size - 1):
            for px in range(1, tile_size - 1):
                seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
                offset = int(seed >> 29) - 3
                alpha = _procedural_alpha(name, px, py, tile_size, color[3])
                shade = (
                    *tuple(min(255, max(0, ch + offset)) for ch in color[:3]),
                    alpha,
                )
                draw.point((px, py), fill=shade)
        tiles[name] = image
    return tiles


def _procedural_alpha(
    name: str,
    px: int,
    py: int,
    tile_size: int,
    default_alpha: int,
) -> int:
    if name == "minecraft:block/oak_leaves" and ((px + py) % 5 == 0 or (px * 3 + py) % 11 == 0):
        return 0
    if name == "minecraft:block/short_grass":
        mid = tile_size // 2
        blade = mid - 1 <= px <= mid + 1 or abs(px - py) <= 1 or abs(px + py - tile_size) <= 1
        return default_alpha if blade else 0
    if name == "minecraft:block/dandelion":
        mid = tile_size // 2
        flower_y = tile_size // 3
        stem = abs(px - mid) <= 1
        flower = abs(px - mid) <= 4 and abs(py - flower_y) <= 4
        return default_alpha if stem or flower else 0
    return default_alpha


def build_texture_atlas(tiles: dict[str, Image.Image], *, tile_size: int) -> GeneratedAtlas:
    """Pack PIL images into a square-ish atlas and return UV coordinates."""
    names = sorted(tiles)
    count = len(names)
    columns = max(1, ceil(sqrt(count)))
    rows = max(1, ceil(count / columns))
    atlas_w = columns * tile_size
    atlas_h = rows * tile_size
    image = Image.new("RGBA", (atlas_w, atlas_h))

    uvs: dict[str, tuple[float, float, float, float]] = {}
    for index, name in enumerate(names):
        tile_x = index % columns
        tile_y = index // columns
        tile = tiles[name].convert("RGBA").resize((tile_size, tile_size), Image.NEAREST)
        image.paste(tile, (tile_x * tile_size, tile_y * tile_size))
        u0 = tile_x / columns
        v0 = 1.0 - (tile_y + 1) / rows
        u1 = (tile_x + 1) / columns
        v1 = 1.0 - tile_y / rows
        inset_u = 0.5 / atlas_w
        inset_v = 0.5 / atlas_h
        uvs[name] = (u0 + inset_u, v0 + inset_v, u1 - inset_u, v1 - inset_v)

    pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    return GeneratedAtlas(image.width, image.height, pixels, uvs)


def create_block_atlas(tile_size: int = 32) -> GeneratedAtlas:
    """Build the default procedural block atlas (keyed by resource locations)."""
    return build_texture_atlas(create_default_block_tiles(tile_size), tile_size=tile_size)
