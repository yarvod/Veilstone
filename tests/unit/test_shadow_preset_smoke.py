from __future__ import annotations

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.tools.shadow_preset_smoke import (
    SHADOW_PRESET_VARIANTS,
    shadow_capture_settings,
)


def test_shadow_preset_smoke_variants_cover_shadow_profiles() -> None:
    assert [variant.name for variant in SHADOW_PRESET_VARIANTS] == [
        "off",
        "low",
        "medium",
        "high_material_preview",
    ]
    assert {variant.shadow_quality for variant in SHADOW_PRESET_VARIANTS} == {
        "off",
        "low",
        "medium",
    }


def test_shadow_capture_settings_uses_threaded_low_distance_world() -> None:
    settings = shadow_capture_settings(
        AppSettings(),
        SHADOW_PRESET_VARIANTS[-1],
        render_distance=2,
    )

    assert settings.graphics.quality_preset == "high"
    assert settings.graphics.shadow_quality == "medium"
    assert settings.graphics.material_quality == "material-preview"
    assert settings.world.render_distance == 2
    assert settings.world.generation_backend == "thread"
    assert settings.world.meshing_backend == "thread"
