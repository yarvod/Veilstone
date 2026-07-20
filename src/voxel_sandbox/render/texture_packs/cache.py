from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

from PIL import Image

from voxel_sandbox.render.material_metadata import (
    MaterialAtlasManifest,
    MaterialMapRole,
    MaterialTextureRef,
    RenderMaterialMetadata,
    build_material_manifest,
)
from voxel_sandbox.render.texture_atlas.generated import GeneratedAtlas

CACHE_VERSION = 6


def load_cached_atlas(cache_root: Path, pack_path: Path) -> GeneratedAtlas | None:
    cache_dir = _cache_dir(cache_root, pack_path)
    atlas_path = cache_dir / "atlas.png"
    metadata_path = cache_dir / "atlas.json"
    if not atlas_path.exists() or not metadata_path.exists():
        return None

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        image = Image.open(atlas_path).convert("RGBA")
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if metadata.get("cache_version") != CACHE_VERSION:
        return None

    width = int(metadata["width"])
    height = int(metadata["height"])
    if image.size != (width, height):
        return None

    uvs = {str(key): _uv_rect(rect) for key, rect in metadata["uvs"].items()}
    try:
        material_manifest = _material_manifest_from_json(metadata.get("materials", []))
    except ValueError:
        return None
    pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    return GeneratedAtlas(
        width,
        height,
        pixels,
        uvs,
        tile_size=int(metadata.get("tile_size", 0)),
        edge_inset_pixels=float(metadata.get("edge_inset_pixels", 0.0)),
        gutter_pixels=int(metadata.get("gutter_pixels", 0)),
        material_manifest=material_manifest,
    )


def _uv_rect(value: object) -> tuple[float, float, float, float]:
    if not isinstance(value, list | tuple):
        raise ValueError("Cached texture atlas UV rect must contain four values")
    values = cast("list[object] | tuple[object, ...]", value)
    if len(values) != 4:
        raise ValueError("Cached texture atlas UV rect must contain four values")
    numbers: list[float] = []
    for item in values:
        if not isinstance(item, int | float):
            raise ValueError("Cached texture atlas UV rect values must be numeric")
        numbers.append(float(item))
    return (numbers[0], numbers[1], numbers[2], numbers[3])


def save_cached_atlas(cache_root: Path, pack_path: Path, atlas: GeneratedAtlas) -> None:
    cache_dir = _cache_dir(cache_root, pack_path)
    cache_dir.mkdir(parents=True, exist_ok=True)
    image = Image.frombytes("RGBA", (atlas.width, atlas.height), atlas.pixels)
    image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    image.save(cache_dir / "atlas.png")
    metadata: dict[str, Any] = {
        "cache_version": CACHE_VERSION,
        "width": atlas.width,
        "height": atlas.height,
        "tile_size": atlas.tile_size,
        "edge_inset_pixels": atlas.edge_inset_pixels,
        "gutter_pixels": atlas.gutter_pixels,
        "materials": _material_manifest_to_json(atlas.material_manifest),
        "uvs": atlas.uvs,
    }
    (cache_dir / "atlas.json").write_text(
        json.dumps(metadata, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _cache_dir(cache_root: Path, pack_path: Path) -> Path:
    pack_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", pack_path.name).strip("-") or "pack"
    return cache_root / f"{pack_id}-{_pack_hash(pack_path)}"


def _pack_hash(pack_path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(pack_path.name.encode("utf-8"))
    if pack_path.is_file():
        _hash_stat(hasher, pack_path, pack_path.name)
    else:
        for child in sorted(path for path in pack_path.rglob("*") if path.is_file()):
            _hash_stat(hasher, child, child.relative_to(pack_path).as_posix())
    return hasher.hexdigest()[:16]


def _hash_stat(hasher: Any, path: Path, relative_name: str) -> None:
    stat = path.stat()
    hasher.update(relative_name.encode("utf-8"))
    hasher.update(str(stat.st_size).encode("ascii"))
    hasher.update(str(stat.st_mtime_ns).encode("ascii"))


def _material_manifest_to_json(manifest: MaterialAtlasManifest) -> list[dict[str, object]]:
    return [
        {
            "resource_id": entry.resource_id,
            "color_asset_path": entry.color_asset_path,
            "shader_profile": entry.shader_profile,
            "maps": [
                {"role": ref.role.value, "asset_path": ref.asset_path} for ref in sorted(entry.maps)
            ],
        }
        for entry in manifest.entries
    ]


def _material_manifest_from_json(value: object) -> MaterialAtlasManifest:
    if not isinstance(value, list):
        raise ValueError("Cached material manifest must be a list")
    entries: list[RenderMaterialMetadata] = []
    for raw_entry in cast("list[object]", value):
        if not isinstance(raw_entry, dict):
            raise ValueError("Cached material manifest entry must be an object")
        entry = cast("dict[str, object]", raw_entry)
        maps = entry.get("maps", [])
        if not isinstance(maps, list):
            raise ValueError("Cached material manifest maps must be a list")
        refs: list[MaterialTextureRef] = []
        for raw_ref in cast("list[object]", maps):
            if not isinstance(raw_ref, dict):
                raise ValueError("Cached material map entry must be an object")
            ref = cast("dict[str, object]", raw_ref)
            role = ref.get("role")
            asset_path = ref.get("asset_path")
            if not isinstance(role, str) or not isinstance(asset_path, str):
                raise ValueError("Cached material map entry has invalid fields")
            refs.append(MaterialTextureRef(MaterialMapRole(role), asset_path))
        resource_id = entry.get("resource_id")
        color_asset_path = entry.get("color_asset_path")
        shader_profile = entry.get("shader_profile", "color")
        if (
            not isinstance(resource_id, str)
            or not isinstance(color_asset_path, str)
            or not isinstance(shader_profile, str)
        ):
            raise ValueError("Cached material manifest entry has invalid fields")
        entries.append(
            RenderMaterialMetadata(
                resource_id=resource_id,
                color_asset_path=color_asset_path,
                maps=tuple(refs),
                shader_profile=shader_profile,
            )
        )
    return build_material_manifest(entries)
