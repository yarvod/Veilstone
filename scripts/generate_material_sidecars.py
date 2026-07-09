"""Generate deterministic normal-map sidecars for default resource-pack blocks.

Derives `<name>_n.png` height-based normal maps from the color textures so the
opt-in material-preview profile has real NORMAL atlas content. Regenerate with:

    uv run python scripts/generate_material_sidecars.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

BLOCK_DIR = Path("resource_packs/default/assets/minecraft/textures/block")

# Opaque terrain-like blocks; cutout foliage and animated fluids are skipped
# because the preview shader only consumes normals for solid chunk faces.
SIDECAR_SOURCES = (
    "stone",
    "dirt",
    "grass_block_top",
    "grass_block_side",
    "oak_planks",
    "oak_log",
    "oak_log_top",
    "diamond_ore",
    "crafting_table_top",
    "crafting_table_side",
)

NORMAL_STRENGTH = 2.0


def generate_normal_map(color_path: Path) -> Image.Image:
    height_map = Image.open(color_path).convert("L")
    width, height = height_map.size
    pixels = height_map.load()
    assert pixels is not None

    def sample(x: int, y: int) -> float:
        return pixels[x % width, y % height] / 255.0

    normal = Image.new("RGBA", (width, height))
    output = normal.load()
    assert output is not None
    for y in range(height):
        for x in range(width):
            dx = (sample(x - 1, y) - sample(x + 1, y)) * NORMAL_STRENGTH
            dy = (sample(x, y - 1) - sample(x, y + 1)) * NORMAL_STRENGTH
            length = (dx * dx + dy * dy + 1.0) ** 0.5
            output[x, y] = (
                round((dx / length * 0.5 + 0.5) * 255),
                round((dy / length * 0.5 + 0.5) * 255),
                round((1.0 / length * 0.5 + 0.5) * 255),
                255,
            )
    return normal


def main() -> None:
    for name in SIDECAR_SOURCES:
        color_path = BLOCK_DIR / f"{name}.png"
        target = BLOCK_DIR / f"{name}_n.png"
        generate_normal_map(color_path).save(target)
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
