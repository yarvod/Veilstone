from __future__ import annotations

import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path

from PIL import Image

from voxel_sandbox.render.material_metadata import material_sidecar_refs
from voxel_sandbox.render.texture_packs.models import ImportReport

_PLAINS_GRASS_TINT = (145, 189, 89)
_PLAINS_FOLIAGE_TINT = (89, 174, 48)

_BIOME_TINTS: dict[str, tuple[int, int, int]] = {
    "minecraft:block/grass_block_top": _PLAINS_GRASS_TINT,
    "minecraft:block/grass_block_side_overlay": _PLAINS_GRASS_TINT,
    "minecraft:block/short_grass": _PLAINS_GRASS_TINT,
    "minecraft:block/tall_grass_top": _PLAINS_GRASS_TINT,
    "minecraft:block/tall_grass_bottom": _PLAINS_GRASS_TINT,
    "minecraft:block/oak_leaves": _PLAINS_FOLIAGE_TINT,
}


def resource_location_to_texture_path(resource: str) -> str:
    """Convert a resource location to its path inside a resource pack.

    Examples:
        "minecraft:block/stone" -> "assets/minecraft/textures/block/stone.png"
        "veilstone:block/my_block" -> "assets/veilstone/textures/block/my_block.png"
    """
    if ":" not in resource:
        raise ValueError(
            f"Invalid resource location {resource!r}: "
            "missing namespace (expected 'namespace:kind/name')"
        )
    namespace, rest = resource.split(":", 1)
    if "/" not in rest:
        raise ValueError(
            f"Invalid resource location {resource!r}: "
            "missing kind separator (expected 'namespace:kind/name')"
        )
    return f"assets/{namespace}/textures/{rest}.png"


def is_minecraft_java_pack(path: Path) -> bool:
    """Return True if path is a Minecraft Java resource pack (folder or ZIP)."""
    if path.is_dir():
        return (path / "pack.mcmeta").exists()
    if path.is_file() and path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                return "pack.mcmeta" in zf.namelist()
        except zipfile.BadZipFile:
            return False
    return False


def _load_png_from_folder(folder: Path, asset_path: str) -> Image.Image | None:
    full = folder / asset_path
    if not full.exists():
        return None
    return Image.open(full).convert("RGBA")


def _load_png_from_zip(zf: zipfile.ZipFile, asset_path: str) -> Image.Image | None:
    try:
        with zf.open(asset_path) as f:
            return Image.open(f).convert("RGBA")
    except KeyError:
        return None


def _first_frame(image: Image.Image) -> tuple[Image.Image, bool]:
    """Crop the first frame if the image is a vertical animation strip."""
    w, h = image.size
    if h > w and h % w == 0:
        return image.crop((0, 0, w, w)), True
    return image, False


def load_block_textures(
    source: Path,
    resource_ids: Mapping[str, None],
    fallback_tiles: Mapping[str, Image.Image],
) -> tuple[dict[str, Image.Image], ImportReport]:
    """Load textures for the given resource IDs from a pack folder or ZIP.

    resource_ids: set of resource locations to import (e.g. {"minecraft:block/stone", ...})
    fallback_tiles: tiles to use when a texture is missing from the pack
    """
    report = ImportReport(pack_id=source.name)
    result: dict[str, Image.Image] = {}

    use_zip = source.is_file() and source.suffix.lower() == ".zip"
    zip_names: set[str] = set()
    if use_zip:
        with zipfile.ZipFile(source) as zf:
            zip_names = set(zf.namelist())

    def _load(asset_path: str) -> Image.Image | None:
        if use_zip:
            with zipfile.ZipFile(source) as zf:
                return _load_png_from_zip(zf, asset_path)
        return _load_png_from_folder(source, asset_path)

    def _exists(asset_path: str) -> bool:
        if use_zip:
            return asset_path in zip_names
        return (source / asset_path).exists()

    for resource_id in resource_ids:
        try:
            asset_path = resource_location_to_texture_path(resource_id)
        except ValueError:
            report.warnings.append(f"Skipped invalid resource ID: {resource_id!r}")
            continue

        report.unsupported_material_maps.extend(
            sidecar_path
            for sidecar_path in _material_sidecar_paths(asset_path)
            if _exists(sidecar_path)
        )
        image = _load(asset_path)

        if image is None:
            if resource_id in fallback_tiles:
                result[resource_id] = fallback_tiles[resource_id].copy()
                report.fallback.append(resource_id)
            else:
                report.missing.append(resource_id)
            continue

        image, animated = _first_frame(image)
        if animated:
            report.ignored_animations.append(resource_id)

        image = _apply_resource_overlays(resource_id, image, _load)
        result[resource_id] = _apply_resource_tint(resource_id, image)
        report.imported.append(resource_id)

    report.unsupported_material_maps.sort()
    return result, report


def _material_sidecar_paths(asset_path: str) -> tuple[str, ...]:
    return tuple(ref.asset_path for ref in material_sidecar_refs(asset_path))


def _apply_resource_overlays(
    resource_id: str,
    image: Image.Image,
    load: Callable[[str], Image.Image | None],
) -> Image.Image:
    if resource_id != "minecraft:block/grass_block_side":
        return image
    overlay_path = resource_location_to_texture_path("minecraft:block/grass_block_side_overlay")
    overlay = load(overlay_path)
    if overlay is None:
        return image
    overlay, _ = _first_frame(overlay)
    tinted_overlay = _apply_resource_tint("minecraft:block/grass_block_side_overlay", overlay)
    return Image.alpha_composite(image.convert("RGBA"), tinted_overlay.convert("RGBA"))


def _apply_resource_tint(resource_id: str, image: Image.Image) -> Image.Image:
    tint = _BIOME_TINTS.get(resource_id)
    if tint is None:
        return image
    red, green, blue, alpha = image.convert("RGBA").split()
    tint_r, tint_g, tint_b = tint
    return Image.merge(
        "RGBA",
        (
            red.point(_tint_lut(tint_r)),
            green.point(_tint_lut(tint_g)),
            blue.point(_tint_lut(tint_b)),
            alpha,
        ),
    )


def _tint_lut(multiplier: int) -> list[int]:
    return [value * multiplier // 255 for value in range(256)]
