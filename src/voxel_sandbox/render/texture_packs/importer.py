from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.render.texture_atlas.generated import (
    GeneratedAtlas,
    build_texture_atlas,
    create_default_block_tiles,
)
from voxel_sandbox.render.texture_packs.cache import load_cached_atlas, save_cached_atlas
from voxel_sandbox.render.texture_packs.minecraft_java import load_block_textures
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
    """Build the active block atlas for the given registry.

    If resource_pack_path is None, returns the default procedural atlas.
    Otherwise imports textures from the pack, uses fallback tiles for missing ones.
    """
    fallback_tiles = create_default_block_tiles(fallback_tile_size)

    if resource_pack_path is None:
        return build_texture_atlas(fallback_tiles, tile_size=fallback_tile_size)

    if cache_root is not None:
        try:
            cached = load_cached_atlas(cache_root, resource_pack_path)
        except OSError:
            cached = None
        if cached is not None:
            LOGGER.info("Texture pack %s: loaded atlas from cache", resource_pack_path.name)
            return cached

    texture_ids = _collect_texture_ids(registry)
    imported_tiles, report = load_block_textures(resource_pack_path, texture_ids, fallback_tiles)

    _log_report(report, resource_pack_path)
    if report_callback is not None:
        report_callback(report)

    merged = {**fallback_tiles, **imported_tiles}
    tile_size = _detect_tile_size(imported_tiles, fallback_tile_size)
    atlas = build_texture_atlas(merged, tile_size=tile_size)
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


def _detect_tile_size(imported_tiles: dict, fallback: int) -> int:
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
