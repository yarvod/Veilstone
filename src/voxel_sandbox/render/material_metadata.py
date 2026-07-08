from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MaterialMapRole(StrEnum):
    NORMAL = "normal"
    SPECULAR = "specular"
    EMISSIVE = "emissive"
    MER = "mer"


MATERIAL_SIDECAR_SUFFIXES: dict[MaterialMapRole, str] = {
    MaterialMapRole.NORMAL: "_n",
    MaterialMapRole.SPECULAR: "_s",
    MaterialMapRole.EMISSIVE: "_e",
    MaterialMapRole.MER: "_mer",
}


@dataclass(frozen=True, slots=True, order=True)
class MaterialTextureRef:
    role: MaterialMapRole
    asset_path: str


@dataclass(frozen=True, slots=True)
class MaterialCacheKey:
    resource_id: str
    color_asset_path: str
    shader_profile: str
    maps: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class RenderMaterialMetadata:
    resource_id: str
    color_asset_path: str
    maps: tuple[MaterialTextureRef, ...] = ()
    shader_profile: str = "color"

    def cache_key(self) -> MaterialCacheKey:
        return MaterialCacheKey(
            resource_id=self.resource_id,
            color_asset_path=self.color_asset_path,
            shader_profile=self.shader_profile,
            maps=tuple((ref.role.value, ref.asset_path) for ref in sorted(self.maps)),
        )


def material_sidecar_refs(color_asset_path: str) -> tuple[MaterialTextureRef, ...]:
    if not color_asset_path.endswith(".png"):
        return ()
    stem = color_asset_path[:-4]
    return tuple(
        MaterialTextureRef(role, f"{stem}{suffix}.png")
        for role, suffix in MATERIAL_SIDECAR_SUFFIXES.items()
    )
