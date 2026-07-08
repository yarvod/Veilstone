from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, sqrt

from PIL import Image, ImageDraw

from voxel_sandbox.render.material_metadata import MaterialAtlasManifest, MaterialMapRole


@dataclass(frozen=True, slots=True)
class GeneratedAtlas:
    width: int
    height: int
    pixels: bytes
    uvs: dict[str, tuple[float, float, float, float]]
    tile_size: int = 0
    edge_inset_pixels: float = 0.0
    material_manifest: MaterialAtlasManifest = field(default_factory=MaterialAtlasManifest)


@dataclass(frozen=True, slots=True)
class GeneratedMaterialAtlas:
    role: MaterialMapRole
    width: int
    height: int
    pixels: bytes
    uvs: dict[str, tuple[float, float, float, float]]
    tile_size: int
    edge_inset_pixels: float


# Default procedural tiles keyed by Minecraft-style resource locations.
# Colors are approximate; real textures come from user-supplied resource packs.
_DEFAULT_COLORS: dict[str, tuple[int, int, int, int]] = {
    "minecraft:block/stone": (92, 100, 112, 255),
    "minecraft:block/dirt": (102, 68, 45, 255),
    "minecraft:block/grass_block_top": (122, 176, 72, 255),
    "minecraft:block/grass_block_side": (108, 142, 70, 255),
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
        if name == "minecraft:block/short_grass":
            tiles[name] = _create_default_short_grass_tile(tile_size)
            continue
        if name == "minecraft:block/dandelion":
            tiles[name] = _create_default_dandelion_tile(tile_size)
            continue

        image = Image.new("RGBA", (tile_size, tile_size))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, tile_size - 1, tile_size - 1), fill=color)
        seed = sum((i + 1) * ord(c) for i, c in enumerate(name))
        for py in range(tile_size):
            for px in range(tile_size):
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


def _create_default_short_grass_tile(tile_size: int) -> Image.Image:
    image = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = max(1, round(tile_size / 18))
    blades = (
        ((2.5, 15.0), (3.8, 9.5), (74, 138, 48, 255)),
        ((4.5, 15.0), (5.5, 6.5), (103, 166, 62, 255)),
        ((6.5, 15.0), (7.0, 5.5), (136, 190, 76, 255)),
        ((8.0, 15.0), (8.0, 7.0), (95, 156, 56, 255)),
        ((9.5, 15.0), (11.0, 8.0), (120, 180, 68, 255)),
        ((11.5, 15.0), (13.6, 10.0), (86, 146, 54, 255)),
        ((5.7, 15.0), (3.8, 11.0), (112, 174, 62, 255)),
        ((10.2, 15.0), (12.6, 9.2), (142, 198, 82, 255)),
    )
    for start, end, color in blades:
        draw.line(
            (*_tile_point(start[0], start[1], tile_size), *_tile_point(end[0], end[1], tile_size)),
            fill=color,
            width=width,
        )
    return image


def _create_default_dandelion_tile(tile_size: int) -> Image.Image:
    image = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = max(1, round(tile_size / 18))
    draw.line(
        (*_tile_point(8.0, 15.0, tile_size), *_tile_point(8.0, 6.2, tile_size)),
        fill=(74, 136, 48, 255),
        width=width,
    )
    flower = _tile_point(8.0, 5.0, tile_size)
    radius = max(1, round(tile_size / 8))
    draw.ellipse(
        (flower[0] - radius, flower[1] - radius, flower[0] + radius, flower[1] + radius),
        fill=(238, 213, 63, 255),
    )
    center = max(1, radius // 2)
    draw.ellipse(
        (flower[0] - center, flower[1] - center, flower[0] + center, flower[1] + center),
        fill=(190, 144, 36, 255),
    )
    return image


def _tile_point(x: float, y: float, tile_size: int) -> tuple[int, int]:
    scale = (tile_size - 1) / 15.0
    return round(x * scale), round(y * scale)


def _procedural_alpha(
    name: str,
    px: int,
    py: int,
    tile_size: int,
    default_alpha: int,
) -> int:
    if name == "minecraft:block/oak_leaves" and ((px + py) % 5 == 0 or (px * 3 + py) % 11 == 0):
        return 0
    return default_alpha


def build_texture_atlas(
    tiles: dict[str, Image.Image],
    *,
    tile_size: int,
    material_manifest: MaterialAtlasManifest | None = None,
) -> GeneratedAtlas:
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
        tile = tiles[name].convert("RGBA").resize((tile_size, tile_size), Image.Resampling.NEAREST)
        image.paste(tile, (tile_x * tile_size, tile_y * tile_size))
        u0 = tile_x / columns
        v0 = 1.0 - (tile_y + 1) / rows
        u1 = (tile_x + 1) / columns
        v1 = 1.0 - tile_y / rows
        inset_u = 0.5 / atlas_w
        inset_v = 0.5 / atlas_h
        uvs[name] = (u0 + inset_u, v0 + inset_v, u1 - inset_u, v1 - inset_v)

    pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    return GeneratedAtlas(
        image.width,
        image.height,
        pixels,
        uvs,
        tile_size=tile_size,
        edge_inset_pixels=0.5,
        material_manifest=material_manifest or MaterialAtlasManifest(),
    )


def build_parallel_material_atlas(
    color_atlas: GeneratedAtlas,
    *,
    role: MaterialMapRole,
    tiles: dict[str, Image.Image],
    default_color: tuple[int, int, int, int],
) -> GeneratedMaterialAtlas:
    """Build a CPU-side material atlas aligned to an existing color atlas."""
    if color_atlas.tile_size <= 0:
        raise ValueError("Color atlas must include tile_size metadata")
    tile_size = color_atlas.tile_size
    image = Image.new("RGBA", (color_atlas.width, color_atlas.height))
    fallback = Image.new("RGBA", (tile_size, tile_size), default_color)
    inset_u = color_atlas.edge_inset_pixels / color_atlas.width
    inset_v = color_atlas.edge_inset_pixels / color_atlas.height

    for resource_id, uv in color_atlas.uvs.items():
        tile = (
            tiles.get(resource_id, fallback)
            .convert("RGBA")
            .resize((tile_size, tile_size), Image.Resampling.NEAREST)
        )
        x = round((uv[0] - inset_u) * color_atlas.width)
        y = round((1.0 - uv[3] - inset_v) * color_atlas.height)
        image.paste(tile, (x, y))

    return GeneratedMaterialAtlas(
        role=role,
        width=color_atlas.width,
        height=color_atlas.height,
        pixels=image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes(),
        uvs=dict(color_atlas.uvs),
        tile_size=tile_size,
        edge_inset_pixels=color_atlas.edge_inset_pixels,
    )


def create_block_atlas(tile_size: int = 32) -> GeneratedAtlas:
    """Build the default procedural block atlas (keyed by resource locations)."""
    return build_texture_atlas(create_default_block_tiles(tile_size), tile_size=tile_size)
