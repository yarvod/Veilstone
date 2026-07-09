from __future__ import annotations

from dataclasses import dataclass, replace

QUALITY_PRESETS = ("custom", "low_60", "balanced", "high", "cinematic")


@dataclass(frozen=True, slots=True)
class RenderQualityProfile:
    """Resolved render knobs for one quality preset.

    ``render_distance`` is ``None`` when the preset does not override the
    player's world render distance.
    """

    preset: str
    render_distance: int | None
    shadow_quality: str
    smooth_lighting: bool
    ambient_occlusion: bool
    fog: bool
    clouds: bool
    vegetation_wind: bool
    material_quality: str


_PRESET_PROFILES: dict[str, RenderQualityProfile] = {
    "low_60": RenderQualityProfile(
        preset="low_60",
        render_distance=2,
        shadow_quality="off",
        smooth_lighting=False,
        ambient_occlusion=False,
        fog=True,
        clouds=False,
        vegetation_wind=False,
        material_quality="color-only",
    ),
    "balanced": RenderQualityProfile(
        preset="balanced",
        render_distance=None,
        shadow_quality="medium",
        smooth_lighting=True,
        ambient_occlusion=True,
        fog=True,
        clouds=True,
        vegetation_wind=True,
        material_quality="color-only",
    ),
    "high": RenderQualityProfile(
        preset="high",
        render_distance=None,
        shadow_quality="medium",
        smooth_lighting=True,
        ambient_occlusion=True,
        fog=True,
        clouds=True,
        vegetation_wind=True,
        material_quality="material-preview",
    ),
    "cinematic": RenderQualityProfile(
        preset="cinematic",
        render_distance=None,
        shadow_quality="medium",
        smooth_lighting=True,
        ambient_occlusion=True,
        fog=True,
        clouds=True,
        vegetation_wind=True,
        material_quality="material-preview",
    ),
}


def build_custom_profile(
    *,
    shadow_quality: str,
    smooth_lighting: bool,
    ambient_occlusion: bool,
    fog: bool,
    clouds: bool,
    material_quality: str,
) -> RenderQualityProfile:
    """Wrap the user's individual graphics flags as the custom profile."""
    return RenderQualityProfile(
        preset="custom",
        render_distance=None,
        shadow_quality=shadow_quality,
        smooth_lighting=smooth_lighting,
        ambient_occlusion=ambient_occlusion,
        fog=fog,
        clouds=clouds,
        vegetation_wind=True,
        material_quality=material_quality,
    )


def resolve_render_quality_profile(
    preset: str,
    *,
    custom: RenderQualityProfile,
) -> RenderQualityProfile:
    """Resolve a preset name into a profile; unknown/custom keeps user flags."""
    normalized = preset.strip().lower()
    resolved = _PRESET_PROFILES.get(normalized)
    if resolved is None:
        return replace(custom, preset="custom")
    return resolved
