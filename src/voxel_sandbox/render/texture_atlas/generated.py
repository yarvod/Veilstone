from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw


@dataclass(frozen=True, slots=True)
class GeneratedAtlas:
    width: int
    height: int
    pixels: bytes
    uvs: dict[str, tuple[float, float, float, float]]


def create_block_atlas(tile_size: int = 32) -> GeneratedAtlas:
    columns = 5
    rows = 2
    image = Image.new("RGBA", (tile_size * columns, tile_size * rows))
    draw = ImageDraw.Draw(image)
    colors = {
        "stone": (92, 100, 112, 255),
        "dirt": (102, 68, 45, 255),
        "grass_top": (75, 128, 76, 255),
        "grass_side": (83, 104, 60, 255),
        "veilwood_cut": (126, 104, 83, 255),
        "veilwood_bark": (64, 55, 72, 255),
        "veilwood_leaves": (48, 85, 76, 255),
        "dusk_crystal_ore": (90, 72, 122, 255),
        "gloam_lantern": (226, 154, 72, 255),
    }
    positions = {
        "stone": (0, 0),
        "dirt": (1, 0),
        "grass_top": (0, 1),
        "grass_side": (1, 1),
        "veilwood_cut": (2, 0),
        "veilwood_bark": (3, 0),
        "veilwood_leaves": (2, 1),
        "dusk_crystal_ore": (3, 1),
        "gloam_lantern": (4, 0),
    }
    uvs: dict[str, tuple[float, float, float, float]] = {}
    for name, (tile_x, tile_y) in positions.items():
        x0, y0 = tile_x * tile_size, tile_y * tile_size
        draw.rectangle((x0, y0, x0 + tile_size - 1, y0 + tile_size - 1), fill=colors[name])
        for offset in range(3, tile_size, 7):
            shade = (*tuple(max(0, channel - 12) for channel in colors[name][:3]), 255)
            draw.point((x0 + offset, y0 + (offset * 5) % tile_size), fill=shade)
        u0, v0 = tile_x / columns, 1.0 - (tile_y + 1) / rows
        u1, v1 = (tile_x + 1) / columns, 1.0 - tile_y / rows
        inset_u = 0.5 / (tile_size * columns)
        inset_v = 0.5 / (tile_size * rows)
        uvs[name] = (u0 + inset_u, v0 + inset_v, u1 - inset_u, v1 - inset_v)

    pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    return GeneratedAtlas(image.width, image.height, pixels, uvs)
