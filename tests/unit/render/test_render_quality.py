from __future__ import annotations

import pytest

from voxel_sandbox.render.render_quality import (
    QUALITY_PRESETS,
    RenderQualityProfile,
    build_custom_profile,
    resolve_render_quality_profile,
)


def _custom_profile() -> RenderQualityProfile:
    return RenderQualityProfile(
        preset="custom",
        render_distance=None,
        shadow_quality="medium",
        smooth_lighting=True,
        ambient_occlusion=False,
        fog=False,
        clouds=True,
        vegetation_wind=True,
        water_detail=True,
        material_quality="color-only",
    )


def test_build_custom_profile_wraps_user_flags() -> None:
    profile = build_custom_profile(
        shadow_quality="off",
        smooth_lighting=False,
        ambient_occlusion=True,
        fog=True,
        clouds=False,
        material_quality="material-preview",
    )

    assert profile.preset == "custom"
    assert profile.render_distance is None
    assert profile.shadow_quality == "off"
    assert profile.smooth_lighting is False
    assert profile.ambient_occlusion is True
    assert profile.clouds is False
    assert profile.water_detail is True
    assert profile.material_quality == "material-preview"


def test_custom_preset_keeps_user_flags() -> None:
    custom = _custom_profile()

    resolved = resolve_render_quality_profile("custom", custom=custom)

    assert resolved == custom


def test_unknown_preset_falls_back_to_custom() -> None:
    custom = _custom_profile()

    resolved = resolve_render_quality_profile("ultra-mega", custom=custom)

    assert resolved.preset == "custom"
    assert resolved.ambient_occlusion is False


def test_low_60_preset_disables_expensive_effects() -> None:
    resolved = resolve_render_quality_profile("low_60", custom=_custom_profile())

    assert resolved.preset == "low_60"
    assert resolved.render_distance == 2
    assert resolved.shadow_quality == "off"
    assert resolved.smooth_lighting is False
    assert resolved.ambient_occlusion is False
    assert resolved.clouds is False
    assert resolved.vegetation_wind is False
    assert resolved.water_detail is False
    assert resolved.material_quality == "color-only"


def test_high_preset_enables_material_preview() -> None:
    resolved = resolve_render_quality_profile("high", custom=_custom_profile())

    assert resolved.material_quality == "material-preview"
    assert resolved.shadow_quality == "medium"
    assert resolved.render_distance is None


@pytest.mark.parametrize("preset", QUALITY_PRESETS)
def test_all_named_presets_resolve(preset: str) -> None:
    resolved = resolve_render_quality_profile(preset, custom=_custom_profile())

    assert resolved.preset in QUALITY_PRESETS
    assert resolved.material_quality in {"color-only", "material-preview"}
