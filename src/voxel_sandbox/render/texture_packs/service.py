from __future__ import annotations

from pathlib import Path
from typing import Any

from voxel_sandbox.render.texture_packs.discovery import discover_texture_packs
from voxel_sandbox.render.texture_packs.importer import load_active_block_atlas


class RenderTexturePackService:
    """Render-adapter implementation of the texture pack application port."""

    def discover(self, root: Path) -> list[tuple[str, Path | None]]:
        return discover_texture_packs(root)

    def load_block_atlas(
        self,
        path: Path | None,
        *,
        registry: Any,
        cache_root: Path,
        report_callback: Any | None = None,
    ) -> Any:
        return load_active_block_atlas(
            path,
            registry=registry,
            report_callback=report_callback,
            cache_root=cache_root,
        )
