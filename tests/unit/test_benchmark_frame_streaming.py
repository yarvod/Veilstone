from __future__ import annotations

import cProfile

import pytest

from voxel_sandbox.render.perf import frame_bottleneck
from voxel_sandbox.tools.benchmark_frame_streaming import (
    format_bottleneck_distribution,
    format_veilstone_profile,
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
