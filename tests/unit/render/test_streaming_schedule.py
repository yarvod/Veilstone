from __future__ import annotations

from voxel_sandbox.engine.chunks import CHUNK_HEIGHT
from voxel_sandbox.render.streaming_schedule import (
    chunk_distance,
    chunk_visible,
    drain_fifo_keys,
    drain_priority_keys,
    frame_budget,
    section_visible,
    streaming_priority,
)


def test_frame_budget_clamps_negative_values() -> None:
    assert frame_budget(-4) == 0
    assert frame_budget(0) == 0
    assert frame_budget(3) == 3


def test_drain_fifo_keys_respects_budget_and_order() -> None:
    queue = {"a": None, "b": None, "c": None}

    drained = drain_fifo_keys(queue, 2)

    assert drained == ("a", "b")
    assert tuple(queue) == ("c",)


def test_drain_fifo_keys_with_zero_budget_does_not_mutate_queue() -> None:
    queue = {"a": None, "b": None}

    drained = drain_fifo_keys(queue, 0)

    assert drained == ()
    assert tuple(queue) == ("a", "b")


def test_drain_priority_keys_prefers_low_values_and_preserves_fifo_ties() -> None:
    queue = {"far-first": None, "near-first": None, "far-second": None, "near-second": None}
    priorities = {"far-first": 4, "near-first": 1, "far-second": 4, "near-second": 1}

    drained = drain_priority_keys(queue, 3, priorities.__getitem__)

    assert drained == ("near-first", "near-second", "far-first")
    assert tuple(queue) == ("far-second",)


def test_drain_priority_keys_with_zero_budget_does_not_rank_or_mutate() -> None:
    queue = {"a": None, "b": None}

    def unexpected_priority(_key: str) -> int:
        raise AssertionError("zero budget must not evaluate priority")

    assert drain_priority_keys(queue, 0, unexpected_priority) == ()
    assert tuple(queue) == ("a", "b")


def test_chunk_distance_handles_negative_coordinates_and_boundaries() -> None:
    assert chunk_distance((-3, -5), (-3, -5)) == 0
    assert chunk_distance((-3, -5), (-1, -8)) == 3
    assert chunk_distance((0, 0), (4, -4)) == 4


def test_streaming_priority_uses_visibility_only_after_distance() -> None:
    assert streaming_priority(2, True) < streaming_priority(2, False)
    assert streaming_priority(1, False) < streaming_priority(2, True)
    assert streaming_priority(2, None) == streaming_priority(2, True)


def test_streaming_priority_uses_collision_before_visibility_at_equal_distance() -> None:
    assert streaming_priority(2, False, True) < streaming_priority(2, True, False)
    assert streaming_priority(1, False, False) < streaming_priority(2, True, True)
    assert streaming_priority(2, True, None) == streaming_priority(2, True, False)


class _RecordingView:
    def __init__(self, *, visible: bool) -> None:
        self.visible = visible
        self.bounds: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []

    def intersects(
        self,
        minimum: tuple[float, float, float],
        maximum: tuple[float, float, float],
    ) -> bool:
        self.bounds.append((minimum, maximum))
        return self.visible


def test_chunk_and_section_visibility_use_world_aabbs() -> None:
    view = _RecordingView(visible=True)

    assert chunk_visible(view, (-2, 3)) is True
    assert section_visible(view, (-2, 4, 3)) is True
    assert view.bounds == [
        ((-32.0, 0.0, 48.0), (-16.0, float(CHUNK_HEIGHT), 64.0)),
        ((-32.0, 64.0, 48.0), (-16.0, 80.0, 64.0)),
    ]


def test_missing_visibility_snapshot_preserves_fallback_priority() -> None:
    assert chunk_visible(None, (4, 5)) is None
    assert section_visible(None, (4, 2, 5)) is None


def test_priority_drain_prefers_visible_work_at_equal_distance() -> None:
    queue = {"offscreen": None, "visible": None, "near-offscreen": None}
    priorities = {
        "offscreen": streaming_priority(2, False),
        "visible": streaming_priority(2, True),
        "near-offscreen": streaming_priority(1, False),
    }

    assert drain_priority_keys(queue, 2, priorities.__getitem__) == (
        "near-offscreen",
        "visible",
    )
    assert tuple(queue) == ("offscreen",)
