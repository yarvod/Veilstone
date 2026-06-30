from __future__ import annotations

from voxel_sandbox.render.streaming_schedule import drain_fifo_keys, frame_budget


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
