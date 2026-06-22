"""Resource-pack alpha preservation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from voxel_sandbox.domain.blocks import load_block_registry_from_toml
from voxel_sandbox.render.texture_packs.importer import load_active_block_atlas


def _alpha_values_for_uv(
    atlas_image: Image.Image, uv: tuple[float, float, float, float]
) -> list[int]:
    u0, v0, u1, v1 = uv
    left = max(0, int(u0 * atlas_image.width))
    right = min(atlas_image.width, int(u1 * atlas_image.width) + 1)
    top = max(0, int(v0 * atlas_image.height))
    bottom = min(atlas_image.height, int(v1 * atlas_image.height) + 1)
    tile = atlas_image.crop((left, top, right, bottom))
    return [pixel[3] for pixel in tile.getdata()]


def test_faithful_oak_leaves_keep_cutout_alpha_in_block_atlas(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    pack = root / "resource_packs" / "Faithful-32x-1.21.11"
    if not pack.exists():
        pytest.skip("Faithful resource pack fixture is not available")
    registry = load_block_registry_from_toml(root / "data" / "blocks.toml")

    atlas = load_active_block_atlas(pack, registry=registry, cache_root=tmp_path)
    atlas_image = Image.frombytes("RGBA", (atlas.width, atlas.height), atlas.pixels)
    alphas = _alpha_values_for_uv(atlas_image, atlas.uvs["minecraft:block/oak_leaves"])

    assert min(alphas) == 0
    assert max(alphas) == 255
