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
    image = Image.new("RGBA", (tile_size * 2, tile_size * 2))
    draw = ImageDraw.Draw(image)
    colors = {
        "stone": (92, 100, 112, 255),
        "dirt": (102, 68, 45, 255),
        "grass_top": (75, 128, 76, 255),
        "grass_side": (83, 104, 60, 255),
    }
    positions = {
        "stone": (0, 0),
        "dirt": (1, 0),
        "grass_top": (0, 1),
        "grass_side": (1, 1),
    }
    uvs: dict[str, tuple[float, float, float, float]] = {}
    for name, (tile_x, tile_y) in positions.items():
        x0, y0 = tile_x * tile_size, tile_y * tile_size
        draw.rectangle((x0, y0, x0 + tile_size - 1, y0 + tile_size - 1), fill=colors[name])
        for offset in range(3, tile_size, 7):
            shade = (*tuple(max(0, channel - 12) for channel in colors[name][:3]), 255)
            draw.point((x0 + offset, y0 + (offset * 5) % tile_size), fill=shade)
        u0, v0 = tile_x / 2.0, 1.0 - (tile_y + 1) / 2.0
        u1, v1 = (tile_x + 1) / 2.0, 1.0 - tile_y / 2.0
        inset = 0.5 / (tile_size * 2)
        uvs[name] = (u0 + inset, v0 + inset, u1 - inset, v1 - inset)

    pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    return GeneratedAtlas(image.width, image.height, pixels, uvs)
