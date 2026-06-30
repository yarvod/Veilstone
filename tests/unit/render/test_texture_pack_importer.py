"""Tests for Minecraft Java resource pack importer.

All PNG fixtures are generated in-memory — no third-party assets are committed.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import cast

import pytest
from PIL import Image

from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.render.texture_atlas import GeneratedAtlas
from voxel_sandbox.render.texture_packs.importer import load_active_block_atlas
from voxel_sandbox.render.texture_packs.minecraft_java import (
    is_minecraft_java_pack,
    load_block_textures,
    resource_location_to_texture_path,
)

# ---------------------------------------------------------------------------
# Helpers to build fake pack fixtures
# ---------------------------------------------------------------------------


def _png_bytes(
    width: int,
    height: int,
    color: tuple[int, int, int, int] = (128, 128, 128, 255),
) -> bytes:
    img = Image.new("RGBA", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_folder_pack(tmp_path: Path, textures: dict[str, tuple[int, int]]) -> Path:
    """Create a fake Minecraft Java folder pack. textures: {block_name: (width, height)}"""
    pack_dir = tmp_path / "fake_pack"
    (pack_dir / "assets" / "minecraft" / "textures" / "block").mkdir(parents=True)
    (pack_dir / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 18, "description": "Fake pack"}}),
        encoding="utf-8",
    )
    for tex_name, (w, h) in textures.items():
        (pack_dir / "assets" / "minecraft" / "textures" / "block" / f"{tex_name}.png").write_bytes(
            _png_bytes(w, h)
        )
    return pack_dir


def _make_zip_pack(tmp_path: Path, textures: dict[str, tuple[int, int]]) -> Path:
    """Create a fake Minecraft Java ZIP pack. textures: {block_name: (width, height)}"""
    zip_path = tmp_path / "fake_pack.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "pack.mcmeta",
            json.dumps({"pack": {"pack_format": 18, "description": "Fake pack"}}),
        )
        for tex_name, (w, h) in textures.items():
            zf.writestr(
                f"assets/minecraft/textures/block/{tex_name}.png",
                _png_bytes(w, h),
            )
    return zip_path


_FALLBACK = {
    "minecraft:block/stone": Image.new("RGBA", (4, 4), (50, 50, 50, 255)),
    "minecraft:block/dirt": Image.new("RGBA", (4, 4), (100, 70, 40, 255)),
    "minecraft:block/water_still": Image.new("RGBA", (4, 4), (40, 100, 200, 180)),
}

_IDS = {k: None for k in _FALLBACK}


# ---------------------------------------------------------------------------
# resource_location_to_texture_path
# ---------------------------------------------------------------------------


def test_resolver_stone() -> None:
    assert (
        resource_location_to_texture_path("minecraft:block/stone")
        == "assets/minecraft/textures/block/stone.png"
    )


def test_resolver_custom_namespace() -> None:
    assert (
        resource_location_to_texture_path("veilstone:block/my_block")
        == "assets/veilstone/textures/block/my_block.png"
    )


def test_resolver_missing_namespace_raises() -> None:
    with pytest.raises(ValueError, match="namespace"):
        resource_location_to_texture_path("block/stone")


def test_resolver_missing_kind_raises() -> None:
    with pytest.raises(ValueError, match="kind"):
        resource_location_to_texture_path("minecraft:stone")


# ---------------------------------------------------------------------------
# is_minecraft_java_pack
# ---------------------------------------------------------------------------


def test_folder_pack_with_mcmeta_detected(tmp_path: Path) -> None:
    pack = _make_folder_pack(tmp_path, {})
    assert is_minecraft_java_pack(pack) is True


def test_folder_without_mcmeta_not_detected(tmp_path: Path) -> None:
    folder = tmp_path / "not_a_pack"
    folder.mkdir()
    assert is_minecraft_java_pack(folder) is False


def test_zip_pack_with_mcmeta_detected(tmp_path: Path) -> None:
    pack = _make_zip_pack(tmp_path, {})
    assert is_minecraft_java_pack(pack) is True


def test_zip_without_mcmeta_not_detected(tmp_path: Path) -> None:
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("assets/minecraft/textures/block/stone.png", b"data")
    assert is_minecraft_java_pack(zip_path) is False


def test_nonexistent_path_not_detected(tmp_path: Path) -> None:
    assert is_minecraft_java_pack(tmp_path / "no_such_path") is False


# ---------------------------------------------------------------------------
# load_block_textures — folder
# ---------------------------------------------------------------------------


def test_folder_import_resolves_stone(tmp_path: Path) -> None:
    pack = _make_folder_pack(
        tmp_path, {"stone": (16, 16), "dirt": (16, 16), "water_still": (16, 16)}
    )
    tiles, report = load_block_textures(pack, _IDS, _FALLBACK)
    assert "minecraft:block/stone" in tiles
    assert "minecraft:block/stone" in report.imported


def test_folder_import_applies_minecraft_grass_tint(tmp_path: Path) -> None:
    pack = _make_folder_pack(tmp_path, {"grass_block_top": (16, 16), "stone": (16, 16)})
    fallback = {
        "minecraft:block/grass_block_top": Image.new("RGBA", (4, 4), (128, 128, 128, 255)),
        "minecraft:block/stone": Image.new("RGBA", (4, 4), (50, 50, 50, 255)),
    }
    tiles, report = load_block_textures(pack, {key: None for key in fallback}, fallback)

    grass_pixel = cast(
        tuple[int, int, int, int], tiles["minecraft:block/grass_block_top"].getpixel((0, 0))
    )
    stone_pixel = cast(tuple[int, int, int, int], tiles["minecraft:block/stone"].getpixel((0, 0)))

    assert "minecraft:block/grass_block_top" in report.imported
    assert grass_pixel[1] > grass_pixel[0] > grass_pixel[2]
    assert stone_pixel == (128, 128, 128, 255)


def test_folder_import_composes_grass_side_overlay(tmp_path: Path) -> None:
    pack_dir = tmp_path / "fake_pack"
    block_dir = pack_dir / "assets" / "minecraft" / "textures" / "block"
    block_dir.mkdir(parents=True)
    (pack_dir / "pack.mcmeta").write_text(
        json.dumps({"pack": {"pack_format": 18, "description": "Fake pack"}}),
        encoding="utf-8",
    )
    side = Image.new("RGBA", (4, 4), (96, 64, 32, 255))
    overlay = Image.new("RGBA", (4, 4), (255, 255, 255, 0))
    overlay.putpixel((0, 0), (255, 255, 255, 255))
    side.save(block_dir / "grass_block_side.png")
    overlay.save(block_dir / "grass_block_side_overlay.png")
    fallback = {"minecraft:block/grass_block_side": Image.new("RGBA", (4, 4), (50, 50, 50, 255))}

    tiles, report = load_block_textures(pack_dir, {key: None for key in fallback}, fallback)

    overlay_pixel = cast(
        tuple[int, int, int, int], tiles["minecraft:block/grass_block_side"].getpixel((0, 0))
    )
    base_pixel = cast(
        tuple[int, int, int, int], tiles["minecraft:block/grass_block_side"].getpixel((1, 1))
    )
    assert "minecraft:block/grass_block_side" in report.imported
    assert overlay_pixel[:3] == (145, 189, 89)
    assert base_pixel == (96, 64, 32, 255)


def test_folder_import_missing_uses_fallback(tmp_path: Path) -> None:
    pack = _make_folder_pack(tmp_path, {"stone": (16, 16), "dirt": (16, 16)})
    _tiles, report = load_block_textures(pack, _IDS, _FALLBACK)
    assert "minecraft:block/water_still" in _tiles
    assert "minecraft:block/water_still" in report.fallback
    assert "minecraft:block/water_still" not in report.imported


def test_folder_import_all_present(tmp_path: Path) -> None:
    pack = _make_folder_pack(
        tmp_path, {"stone": (16, 16), "dirt": (16, 16), "water_still": (16, 16)}
    )
    _tiles, report = load_block_textures(pack, _IDS, _FALLBACK)
    _expected = {"minecraft:block/stone", "minecraft:block/dirt", "minecraft:block/water_still"}
    assert set(report.imported) == _expected
    assert report.fallback == []
    assert report.missing == []


# ---------------------------------------------------------------------------
# load_block_textures — ZIP
# ---------------------------------------------------------------------------


def test_zip_import_resolves_correctly(tmp_path: Path) -> None:
    pack = _make_zip_pack(tmp_path, {"stone": (16, 16), "dirt": (16, 16), "water_still": (16, 16)})
    _tiles, report = load_block_textures(pack, _IDS, _FALLBACK)
    _expected = {"minecraft:block/stone", "minecraft:block/dirt", "minecraft:block/water_still"}
    assert set(report.imported) == _expected


def test_zip_import_missing_uses_fallback(tmp_path: Path) -> None:
    pack = _make_zip_pack(tmp_path, {"stone": (16, 16)})
    _tiles, report = load_block_textures(pack, _IDS, _FALLBACK)
    assert "minecraft:block/water_still" in report.fallback
    assert "minecraft:block/dirt" in report.fallback


# ---------------------------------------------------------------------------
# Animated strip detection
# ---------------------------------------------------------------------------


def test_animated_strip_uses_first_frame(tmp_path: Path) -> None:
    pack = _make_folder_pack(tmp_path, {"water_still": (16, 64)})
    ids = {"minecraft:block/water_still": None}
    tiles, report = load_block_textures(pack, ids, _FALLBACK)
    assert "minecraft:block/water_still" in report.ignored_animations
    assert tiles["minecraft:block/water_still"].size == (16, 16)


def test_non_animated_texture_not_flagged(tmp_path: Path) -> None:
    pack = _make_folder_pack(tmp_path, {"stone": (16, 16)})
    ids = {"minecraft:block/stone": None}
    tiles, report = load_block_textures(pack, ids, _FALLBACK)
    assert report.ignored_animations == []
    assert tiles["minecraft:block/stone"].size == (16, 16)


# ---------------------------------------------------------------------------
# RGBA conversion
# ---------------------------------------------------------------------------


def test_rgb_png_converted_to_rgba(tmp_path: Path) -> None:
    img = Image.new("RGB", (8, 8), (200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    pack = tmp_path / "rgb_pack"
    (pack / "assets" / "minecraft" / "textures" / "block").mkdir(parents=True)
    (pack / "pack.mcmeta").write_text('{"pack":{}}', encoding="utf-8")
    (pack / "assets" / "minecraft" / "textures" / "block" / "stone.png").write_bytes(buf.getvalue())
    ids = {"minecraft:block/stone": None}
    tiles, _ = load_block_textures(pack, ids, {})
    assert tiles["minecraft:block/stone"].mode == "RGBA"


def test_default_atlas_loads_bundled_resource_pack() -> None:
    atlas = load_active_block_atlas(None, registry=create_core_block_registry())

    assert atlas.width % 16 == 0
    assert "minecraft:block/stone" in atlas.uvs
    assert "minecraft:block/grass_block_top" in atlas.uvs


def test_user_pack_missing_textures_fallback_to_bundled_default(tmp_path: Path) -> None:
    pack = _make_folder_pack(tmp_path, {"stone": (16, 16)})
    atlas = load_active_block_atlas(pack, registry=create_core_block_registry())
    expected = Image.open(
        resource_path("resource_packs/default/assets/minecraft/textures/block/dirt.png")
    ).convert("RGBA")
    expected_pixels = {
        cast(tuple[int, int, int, int], expected.getpixel((x, y)))
        for y in range(expected.height)
        for x in range(expected.width)
    }

    assert _sample_atlas_tile(atlas, "minecraft:block/dirt") in expected_pixels


def _sample_atlas_tile(atlas: GeneratedAtlas, resource_id: str) -> tuple[int, int, int, int]:
    image = Image.frombytes("RGBA", (atlas.width, atlas.height), atlas.pixels)
    u0, v0, u1, v1 = atlas.uvs[resource_id]
    x = int(((u0 + u1) / 2.0) * atlas.width)
    y = int(((v0 + v1) / 2.0) * atlas.height)
    return cast(tuple[int, int, int, int], image.getpixel((x, y)))
