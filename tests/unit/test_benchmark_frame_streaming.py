from __future__ import annotations

from voxel_sandbox.tools.benchmark_frame_streaming import format_bottleneck_distribution


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
