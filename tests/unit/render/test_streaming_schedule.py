from __future__ import annotations

from voxel_sandbox.render.streaming_schedule import (
    chunk_distance,
    drain_fifo_keys,
    drain_priority_keys,
    frame_budget,
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
