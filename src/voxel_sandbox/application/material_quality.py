from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.application.resource_packs import SettingsStorePort

VALID_MATERIAL_QUALITIES = ("color-only", "low", "material-preview")


class MaterialRenderPort(Protocol):
    def apply_material_quality(
        self, material_quality: str, resource_pack_path: str = ""
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ApplyMaterialQualityResult:
    applied: bool
    settings: AppSettings
    status: str


@dataclass(frozen=True, slots=True)
class ApplyMaterialQualityUseCase:
    settings_store: SettingsStorePort

    def execute(
        self,
        *,
        quality: str,
        settings: AppSettings,
        renderer: MaterialRenderPort,
    ) -> ApplyMaterialQualityResult:
        normalized = quality.strip().lower()
        if normalized not in VALID_MATERIAL_QUALITIES:
            return ApplyMaterialQualityResult(
                applied=False,
                settings=settings,
                status="Materials must be color-only, low or material-preview.",
            )

        renderer.apply_material_quality(
            normalized,
            settings.graphics.resource_pack_path,
        )
        next_settings = replace(
            settings,
            graphics=replace(settings.graphics, material_quality=normalized),
        )
        self.settings_store.save(next_settings)
        return ApplyMaterialQualityResult(
            applied=True,
            settings=next_settings,
            status=f"Material quality applied: {normalized}",
        )
