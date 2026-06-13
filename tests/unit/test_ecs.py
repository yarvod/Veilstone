from __future__ import annotations

from voxel_sandbox.engine.ecs import EntityWorld, Health, Transform, Velocity


def test_entity_world_creates_queries_and_destroys_components() -> None:
    world = EntityWorld()
    first = world.create()
    second = world.create()
    world.transforms.set(first, Transform(1.0, 2.0, 3.0))
    world.velocities.set(first, Velocity(1.0, 0.0, 0.0))
    world.transforms.set(second, Transform(4.0, 5.0, 6.0))

    assert world.query(world.transforms, world.velocities) == (first,)
    assert world.query(world.transforms) == (first, second)

    world.destroy(first)

    assert first not in world.alive
    assert world.transforms.get(first) is None
    assert world.velocities.get(first) is None


def test_health_reports_death_and_clamps_at_zero() -> None:
    health = Health(5.0, 5.0)

    assert not health.damage(2.0)
    assert health.current == 3.0
    assert health.damage(10.0)
    assert health.current == 0.0
