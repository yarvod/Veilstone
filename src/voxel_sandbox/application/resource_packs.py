from __future__ import annotations

import zipfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol

from PIL import UnidentifiedImageError

from voxel_sandbox.app.settings import AppSettings


class SettingsStorePort(Protocol):
    def save(self, settings: AppSettings) -> None: ...


class WorldRenderPort(Protocol):
    registry: Any

    def apply_texture_pack(self, atlas: Any) -> None: ...


@dataclass(frozen=True, slots=True)
class ApplyResourcePackResult:
    applied: bool
    settings: AppSettings
    status: str


AtlasLoader = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class ApplyResourcePackUseCase:
    atlas_loader: AtlasLoader
    settings_store: SettingsStorePort

    def execute(
        self,
        *,
        path: str | None,
        settings: AppSettings,
        renderer: WorldRenderPort,
        cache_root: Path,
    ) -> ApplyResourcePackResult:
        pack_path = Path(path) if path is not None else None
        if pack_path is not None and not pack_path.exists():
            return ApplyResourcePackResult(
                applied=False,
                settings=settings,
                status=f"Resource pack not found: {pack_path}",
            )

        try:
            atlas = self.atlas_loader(
                pack_path,
                registry=renderer.registry,
                cache_root=cache_root,
            )
        except (OSError, ValueError, zipfile.BadZipFile, UnidentifiedImageError) as error:
            return ApplyResourcePackResult(
                applied=False,
                settings=settings,
                status=f"Resource pack failed: {error}",
            )

        renderer.apply_texture_pack(atlas)
        next_settings = replace(
            settings,
            graphics=replace(
                settings.graphics,
                resource_pack_path="" if path is None else str(pack_path),
            ),
        )
        self.settings_store.save(next_settings)
        return ApplyResourcePackResult(
            applied=True,
            settings=next_settings,
            status=(
                "Resource pack reset to default."
                if path is None
                else f"Resource pack applied: {pack_path}"
            ),
        )
