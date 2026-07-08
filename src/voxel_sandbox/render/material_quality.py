from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MaterialQualityProfile(StrEnum):
    COLOR_ONLY = "color-only"
    LOW = "low"
    MATERIAL_PREVIEW = "material-preview"


@dataclass(frozen=True, slots=True)
class MaterialPipelineDecision:
    profile: MaterialQualityProfile
    build_material_bundle: bool
    shader_profile: str


_PROFILE_ALIASES: dict[str, MaterialQualityProfile] = {
    "": MaterialQualityProfile.COLOR_ONLY,
    "default": MaterialQualityProfile.COLOR_ONLY,
    "color": MaterialQualityProfile.COLOR_ONLY,
    "color-only": MaterialQualityProfile.COLOR_ONLY,
    "low": MaterialQualityProfile.LOW,
    "material-preview": MaterialQualityProfile.MATERIAL_PREVIEW,
    "pbr-preview": MaterialQualityProfile.MATERIAL_PREVIEW,
}


def resolve_material_pipeline(profile: str | None = None) -> MaterialPipelineDecision:
    selected = _PROFILE_ALIASES.get((profile or "").strip().lower())
    if selected is None:
        selected = MaterialQualityProfile.COLOR_ONLY
    return MaterialPipelineDecision(
        profile=selected,
        build_material_bundle=selected is MaterialQualityProfile.MATERIAL_PREVIEW,
        shader_profile="pbr-preview"
        if selected is MaterialQualityProfile.MATERIAL_PREVIEW
        else "color",
    )


def resolve_material_pipeline_from_graphics(material_quality: str) -> MaterialPipelineDecision:
    return resolve_material_pipeline(material_quality)
