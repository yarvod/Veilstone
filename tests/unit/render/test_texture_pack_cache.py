from __future__ import annotations

import json
import time
from pathlib import Path

from voxel_sandbox.render.material_metadata import (
    MaterialAtlasManifest,
    MaterialMapRole,
    MaterialTextureRef,
    RenderMaterialMetadata,
)
from voxel_sandbox.render.texture_atlas import GeneratedAtlas
from voxel_sandbox.render.texture_packs.cache import load_cached_atlas, save_cached_atlas


def test_texture_pack_cache_roundtrip(tmp_path: Path) -> None:
    pack = tmp_path / "Pack.zip"
    pack.write_bytes(b"pack")
    cache_root = tmp_path / "cache"
    atlas = GeneratedAtlas(
        1,
        1,
        b"\x10\x20\x30\xff",
        {"minecraft:block/stone": (0.1, 0.2, 0.3, 0.4)},
        tile_size=16,
        edge_inset_pixels=0.5,
        material_manifest=MaterialAtlasManifest(
            (
                RenderMaterialMetadata(
                    resource_id="minecraft:block/stone",
                    color_asset_path="assets/minecraft/textures/block/stone.png",
                    maps=(
                        MaterialTextureRef(
                            MaterialMapRole.NORMAL,
                            "assets/minecraft/textures/block/stone_n.png",
                        ),
                    ),
                    shader_profile="pbr",
                ),
            )
        ),
    )

    save_cached_atlas(cache_root, pack, atlas)

    cached = load_cached_atlas(cache_root, pack)
    assert cached == atlas


def test_texture_pack_cache_invalidates_when_pack_changes(tmp_path: Path) -> None:
    pack = tmp_path / "Pack.zip"
    pack.write_bytes(b"pack")
    cache_root = tmp_path / "cache"
    atlas = GeneratedAtlas(1, 1, b"\x10\x20\x30\xff", {})

    save_cached_atlas(cache_root, pack, atlas)
    assert load_cached_atlas(cache_root, pack) == atlas

    time.sleep(0.001)
    pack.write_bytes(b"changed")
    assert load_cached_atlas(cache_root, pack) is None


def test_texture_pack_cache_invalidates_old_schema(tmp_path: Path) -> None:
    pack = tmp_path / "Pack.zip"
    pack.write_bytes(b"pack")
    cache_root = tmp_path / "cache"
    atlas = GeneratedAtlas(1, 1, b"\x10\x20\x30\xff", {})

    save_cached_atlas(cache_root, pack, atlas)
    metadata_path = next(cache_root.rglob("atlas.json"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.pop("cache_version")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    assert load_cached_atlas(cache_root, pack) is None


def test_texture_pack_cache_invalidates_v4_materialless_schema(tmp_path: Path) -> None:
    pack = tmp_path / "Pack.zip"
    pack.write_bytes(b"pack")
    cache_root = tmp_path / "cache"
    atlas = GeneratedAtlas(1, 1, b"\x10\x20\x30\xff", {})

    save_cached_atlas(cache_root, pack, atlas)
    metadata_path = next(cache_root.rglob("atlas.json"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["cache_version"] = 4
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    assert load_cached_atlas(cache_root, pack) is None
