from __future__ import annotations

import cProfile

import pytest

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.render.perf import RenderQueueSnapshot, StreamingStageSample, frame_bottleneck
from voxel_sandbox.render.render_quality import (
    RenderQualityProfile,
    build_custom_profile,
    resolve_render_quality_profile,
)
from voxel_sandbox.tools.benchmark_frame_streaming import (
    benchmark_player_position,
    benchmark_world_ready,
    format_bottleneck_distribution,
    format_quality_summary,
    format_streaming_stage_summary,
    format_veilstone_profile,
    fps_from_frame_ms,
    frame_pacing_delay,
    percentile_ms,
    run_benchmark,
    target_chunk_count,
    veilstone_profile_rows,
)


def test_format_bottleneck_distribution_uses_stable_complete_order() -> None:
    summary = format_bottleneck_distribution(
        (
            (7.0, 2.0),
            (1.0, 5.0),
            (4.0, 4.0),
            (0.0, 0.0),
            (9.0, 3.0),
        )
    )

    assert summary == "bottlenecks=update:2 render:1 balanced:1 idle:1"


def test_format_bottleneck_distribution_includes_zero_counts() -> None:
    assert (
        format_bottleneck_distribution(((2.0, 1.0),))
        == "bottlenecks=update:1 render:0 balanced:0 idle:0"
    )


def test_percentile_interpolates_sorted_samples() -> None:
    timings = [40.0, 10.0, 30.0, 20.0]

    assert percentile_ms(timings, 0) == 10.0
    assert percentile_ms(timings, 50) == 25.0
    assert percentile_ms(timings, 95) == 38.5
    assert percentile_ms([], 99) == 0.0


def test_frame_budget_helpers_report_fps_and_square_chunk_footprint() -> None:
    assert abs(fps_from_frame_ms(16.6666667) - 60.0) < 1e-6
    assert fps_from_frame_ms(0.0) == 0.0
    assert target_chunk_count(0) == 1
    assert target_chunk_count(2) == 25
    with pytest.raises(ValueError, match="negative"):
        target_chunk_count(-1)


def test_frame_pacing_uses_remaining_60hz_budget() -> None:
    assert abs(frame_pacing_delay(0.010) - (1.0 / 60.0 - 0.010)) < 1e-12
    assert frame_pacing_delay(0.020) == 0.0
    with pytest.raises(ValueError, match="positive"):
        frame_pacing_delay(0.010, 0.0)


def test_quality_summary_reports_low_60_effect_budget() -> None:
    custom = build_custom_profile(
        shadow_quality="medium",
        smooth_lighting=True,
        ambient_occlusion=True,
        fog=True,
        clouds=True,
        material_quality="color-only",
    )
    profile = resolve_render_quality_profile("low_60", custom=custom)

    assert format_quality_summary(profile) == (
        "quality=low_60 shadows=off smooth=off ao=off fog=on "
        "clouds=off wind=off water=off materials=color-only terrain_filter=nearest"
    )


def test_benchmark_world_ready_requires_loaded_visible_geometry() -> None:
    assert not benchmark_world_ready(RenderQueueSnapshot())
    assert not benchmark_world_ready(RenderQueueSnapshot(loaded_chunks=1))
    assert not benchmark_world_ready(RenderQueueSnapshot(visible_sections=1))
    assert benchmark_world_ready(RenderQueueSnapshot(loaded_chunks=1, visible_sections=1))


def test_full_radius_readiness_requires_target_chunks_and_idle_queues() -> None:
    ready = RenderQueueSnapshot(loaded_chunks=625, visible_sections=1)

    assert benchmark_world_ready(ready, target_chunks=625)
    assert not benchmark_world_ready(
        RenderQueueSnapshot(loaded_chunks=624, visible_sections=1),
        target_chunks=625,
    )
    assert not benchmark_world_ready(
        RenderQueueSnapshot(loaded_chunks=625, pending_stream_remeshes=1, visible_sections=1),
        target_chunks=625,
    )


def test_frame_streaming_benchmark_reports_unavailable_without_display(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "voxel_sandbox.tools.benchmark_frame_streaming.active_display_available",
        lambda: False,
    )

    assert run_benchmark(AppSettings(), frames=1, warmup_frames=0) == 2
    assert capsys.readouterr().out == (
        "frame streaming benchmark: unavailable (no active display)\n"
    )


def test_standalone_benchmark_dispatches_without_display_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    captured_quality: list[RenderQualityProfile] = []

    def fake_standalone(
        _settings: AppSettings,
        quality: RenderQualityProfile,
        **options: object,
    ) -> int:
        captured_quality.append(quality)
        captured.update(options)
        return 7

    monkeypatch.setattr(
        "voxel_sandbox.tools.benchmark_frame_streaming._run_standalone_benchmark",
        fake_standalone,
    )
    monkeypatch.setattr(
        "voxel_sandbox.tools.benchmark_frame_streaming.active_display_available",
        lambda: pytest.fail("standalone backend must not inspect Cocoa displays"),
    )

    result = run_benchmark(
        AppSettings(),
        frames=1,
        warmup_frames=0,
        quality_preset="low_60",
        render_distance=12,
        backend="standalone",
    )

    assert result == 7
    assert captured_quality[0].preset == "low_60"
    assert captured_quality[0].linear_texture_minification is False
    assert captured["frames"] == 1
    assert captured["render_distance"] == 12
    assert captured["screenshot_output"] is None


def test_walk_path_uses_realistic_linear_distance_without_z_teleports() -> None:
    assert benchmark_player_position(0, path="walk", movement_speed=5.0) == (8.5, 8.5)
    assert benchmark_player_position(120, path="walk", movement_speed=5.0) == (18.5, 8.5)


def test_stress_path_retains_legacy_streaming_motion() -> None:
    assert benchmark_player_position(24, path="stress", movement_speed=45.0) == (26.5, 16.5)


def test_veilstone_profile_is_filtered_sorted_and_bounded() -> None:
    profile = cProfile.Profile()
    profile.enable()
    for _ in range(10_000):
        frame_bottleneck(4.0, 2.0)
    profile.disable()

    rows = veilstone_profile_rows(profile, limit=1)
    output = format_veilstone_profile(profile, limit=1)

    assert len(rows) == 1
    assert "voxel_sandbox/render/perf.py:" in rows[0].function
    assert rows[0].function.endswith(":frame_bottleneck")
    assert output.startswith("update profile top=1 scope=voxel_sandbox sort=cumulative\n")
    assert "frame_bottleneck" in output


def test_veilstone_profile_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        veilstone_profile_rows(cProfile.Profile(), limit=0)


def test_streaming_stage_summary_reports_percentiles_and_worst_frame() -> None:
    summary = format_streaming_stage_summary(
        [
            StreamingStageSample(streamer_ms=1.0, relight_ms=2.0),
            StreamingStageSample(streamer_ms=3.0, integration_ms=4.0, remesh_ms=5.0),
        ]
    )

    assert "streamer_p95=2.900ms" in summary
    assert "worst_frame=1" in summary
    assert "worst_total=12.000ms" in summary
    assert format_streaming_stage_summary([]) == "streaming_stages=unavailable"
