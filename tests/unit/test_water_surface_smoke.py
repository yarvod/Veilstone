from __future__ import annotations

import pytest

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.render.render_quality import build_custom_profile, resolve_render_quality_profile
from voxel_sandbox.tools.water_surface_smoke import (
    WATER_SMOKE_VARIANTS,
    apply_water_smoke_scene,
    build_water_smoke_scene,
    choose_water_scene_base_y,
    summarize_item_stability,
    water_capture_settings,
)


def test_water_smoke_variants_cover_low_and_detailed_profiles() -> None:
    assert [variant.name for variant in WATER_SMOKE_VARIANTS] == ["low_60", "detailed"]

    water_detail: list[bool] = []
    for variant in WATER_SMOKE_VARIANTS:
        settings = water_capture_settings(AppSettings(), variant, render_distance=2)
        profile = resolve_render_quality_profile(
            settings.graphics.quality_preset,
            custom=build_custom_profile(
                shadow_quality=settings.graphics.shadow_quality,
                smooth_lighting=settings.graphics.smooth_lighting,
                ambient_occlusion=settings.graphics.ambient_occlusion,
                fog=settings.graphics.fog,
                clouds=settings.graphics.clouds,
                material_quality=settings.graphics.material_quality,
            ),
        )
        water_detail.append(profile.water_detail)
        assert settings.world.seed == "veilstone-water-smoke"
        assert settings.world.generation_backend == "thread"
        assert settings.world.meshing_backend == "thread"
        assert settings.graphics.day_cycle_seconds == 0.0
        assert profile.shadow_quality == "off"
        assert profile.material_quality == "color-only"
        assert profile.clouds is False

    assert water_detail == [False, True]


def test_water_smoke_scene_builds_closed_pool_with_item_over_water() -> None:
    registry = create_core_block_registry()
    placed: dict[tuple[int, int, int], int] = {}
    scene = apply_water_smoke_scene(
        placed.__setitem__,
        registry,
        base_y=96,
    )

    assert scene == build_water_smoke_scene(base_y=96)
    assert scene.water_surface_y == 98.0
    assert scene.item_position == (8.5, 98.05, 10.5)
    assert placed[(8, 97, 10)] == registry.by_key("water").id
    assert placed[(3, 97, 10)] == registry.by_key("stone").id
    assert placed[(13, 97, 10)] == registry.by_key("stone").id
    assert placed[(8, 97, 5)] == registry.by_key("stone").id
    assert placed[(8, 97, 15)] == registry.by_key("stone").id


def test_water_scene_height_stays_above_terrain() -> None:
    assert choose_water_scene_base_y(lambda _x, _z: 72) == 96
    assert choose_water_scene_base_y(lambda _x, _z: 101) == 111


def test_item_stability_uses_tail_jitter() -> None:
    stability = summarize_item_stability(
        [95.0, 97.0, 97.858, 97.861, 97.859],
        item_y=97.8594,
        item_vy=-0.00008,
        tail_size=3,
    )

    assert stability.item_y == 97.8594
    assert stability.item_vy == -0.0001
    assert stability.last_jitter == 0.003


def test_item_stability_rejects_empty_samples() -> None:
    with pytest.raises(ValueError, match="at least one sample"):
        summarize_item_stability([], item_y=0.0, item_vy=0.0)
