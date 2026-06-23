from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

from PIL import Image

from voxel_sandbox.render.texture_atlas.generated import GeneratedAtlas

CACHE_VERSION = 2


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
    pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    return GeneratedAtlas(width, height, pixels, uvs)


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
