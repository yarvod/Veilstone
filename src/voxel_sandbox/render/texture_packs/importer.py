from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.render.texture_atlas.generated import (
    GeneratedAtlas,
    build_texture_atlas,
    create_default_block_tiles,
)
from voxel_sandbox.render.texture_packs.cache import load_cached_atlas, save_cached_atlas
from voxel_sandbox.render.texture_packs.minecraft_java import (
    discover_material_manifest,
    load_block_textures,
)
from voxel_sandbox.render.texture_packs.models import ImportReport

LOGGER = logging.getLogger(__name__)


def _collect_texture_ids(registry: BlockRegistry) -> dict[str, None]:
    """Return all unique resource location IDs used as textures in the registry."""
    ids: dict[str, None] = {}
    for block in registry:
        for tex_id in (block.texture_top, block.texture_side, block.texture_bottom):
            if tex_id and tex_id != "missing":
                ids[tex_id] = None
    return ids


def load_active_block_atlas(
    resource_pack_path: Path | None,
    *,
    registry: BlockRegistry,
    fallback_tile_size: int = 32,
    report_callback: Callable[[ImportReport], None] | None = None,
    cache_root: Path | None = None,
) -> GeneratedAtlas:
    """Build active block atlas from the registry.

    resource_pack_path None loads the bundled default pack. Generated tiles are
    only a fallback when bundled textures are unavailable.
    Otherwise imports a texture pack, using bundled default tiles for missing ones.
    """
    generated_tiles = create_default_block_tiles(fallback_tile_size)
    texture_ids = _collect_texture_ids(registry)
    fallback_tiles = _load_default_pack_tiles(texture_ids, generated_tiles)

    if resource_pack_path is None:
        tile_size = _detect_tile_size(fallback_tiles, fallback_tile_size)
        return build_texture_atlas(fallback_tiles, tile_size=tile_size)

    if cache_root is not None:
        try:
            cached = load_cached_atlas(cache_root, resource_pack_path)
        except OSError:
            cached = None
        if cached is not None:
            LOGGER.info("Texture pack %s: loaded atlas from cache", resource_pack_path.name)
            return cached

    imported_tiles, report = load_block_textures(resource_pack_path, texture_ids, fallback_tiles)
    material_manifest = discover_material_manifest(resource_pack_path, texture_ids)

    _log_report(report, resource_pack_path)
    if report_callback is not None:
        report_callback(report)

    merged = {**fallback_tiles, **imported_tiles}
    tile_size = _detect_tile_size(imported_tiles, fallback_tile_size)
    atlas = build_texture_atlas(
        merged,
        tile_size=tile_size,
        material_manifest=material_manifest,
    )
    if cache_root is not None:
        try:
            save_cached_atlas(cache_root, resource_pack_path, atlas)
        except OSError as error:
            LOGGER.warning(
                "Texture pack %s: failed to write atlas cache: %s",
                resource_pack_path.name,
                error,
            )
    return atlas


def _load_default_pack_tiles(
    texture_ids: dict[str, None],
    generated_tiles: dict[str, Image.Image],
) -> dict[str, Image.Image]:
    default_pack = resource_path("resource_packs/default")
    if not default_pack.exists():
        return generated_tiles
    tiles, report = load_block_textures(default_pack, texture_ids, generated_tiles)
    _log_report(report, default_pack)
    return {**generated_tiles, **tiles}


def _detect_tile_size(imported_tiles: dict[str, Image.Image], fallback: int) -> int:
    for img in imported_tiles.values():
        return img.width
    return fallback


def _log_report(report: ImportReport, source: Path) -> None:
    if report.imported:
        LOGGER.info("Texture pack %s: imported %d textures", source.name, len(report.imported))
    if report.fallback:
        LOGGER.info(
            "Texture pack %s: fallback for %d textures: %s",
            source.name,
            len(report.fallback),
            report.fallback,
        )
    if report.missing:
        LOGGER.warning(
            "Texture pack %s: %d textures missing (no fallback): %s",
            source.name,
            len(report.missing),
            report.missing,
        )
    if report.ignored_animations:
        LOGGER.info(
            "Texture pack %s: %d animated textures (first frame used): %s",
            source.name,
            len(report.ignored_animations),
            report.ignored_animations,
        )
