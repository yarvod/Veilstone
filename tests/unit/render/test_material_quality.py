from __future__ import annotations

from voxel_sandbox.render.material_quality import (
    MaterialQualityProfile,
    resolve_material_pipeline,
    resolve_material_pipeline_from_graphics,
)


def test_default_material_pipeline_keeps_material_bundle_disabled() -> None:
    decision = resolve_material_pipeline()

    assert decision.profile is MaterialQualityProfile.COLOR_ONLY
    assert decision.shader_profile == "color"
    assert decision.build_material_bundle is False


def test_low_material_pipeline_keeps_material_bundle_disabled() -> None:
    decision = resolve_material_pipeline("low")

    assert decision.profile is MaterialQualityProfile.LOW
    assert decision.shader_profile == "color"
    assert decision.build_material_bundle is False


def test_material_preview_names_future_opt_in_bundle_path() -> None:
    decision = resolve_material_pipeline("pbr-preview")

    assert decision.profile is MaterialQualityProfile.MATERIAL_PREVIEW
    assert decision.shader_profile == "pbr-preview"
    assert decision.build_material_bundle is True


def test_graphics_material_quality_routes_through_pipeline_decision() -> None:
    decision = resolve_material_pipeline_from_graphics("color-only")

    assert decision.profile is MaterialQualityProfile.COLOR_ONLY
    assert decision.build_material_bundle is False
