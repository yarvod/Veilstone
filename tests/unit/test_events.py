from __future__ import annotations

from voxel_sandbox.engine.events import BlockBroken, BlockPlaced, EntityDied, EventBus


def test_event_bus_dispatches_by_event_type() -> None:
    bus = EventBus()
    broken: list[BlockBroken] = []
    placed: list[BlockPlaced] = []

    bus.subscribe(BlockBroken, broken.append)
    bus.subscribe(BlockPlaced, placed.append)

    event = BlockBroken(1, (2, 3, 4))
    bus.publish(event)

    assert broken == [event]
    assert placed == []


def test_event_bus_calls_all_handlers() -> None:
    bus = EventBus()
    calls: list[str] = []

    bus.subscribe(EntityDied, lambda _event: calls.append("a"))
    bus.subscribe(EntityDied, lambda _event: calls.append("b"))

    bus.publish(EntityDied(7, "hostile", (1.0, 2.0, 3.0)))

    assert calls == ["a", "b"]
