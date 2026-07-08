from __future__ import annotations

from voxel_sandbox.render.material_quality import (
    MaterialQualityProfile,
    resolve_material_pipeline,
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
