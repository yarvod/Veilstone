from __future__ import annotations

from voxel_sandbox.domain.items import ItemStack
from voxel_sandbox.engine.ecs import EntitySimulation


def flat_ground(_x: int, _z: int) -> int:
    return 1


def no_fluid(_x: int, _y: int, _z: int) -> bool:
    return False


def test_item_entity_falls_to_solid_floor() -> None:
    simulation = EntitySimulation(seed=1)
    item = simulation.spawn_item((0.5, 4.0, 0.5), ItemStack(1, 1))

    for _ in range(80):
        simulation.update(
            0.05,
            (0.0, 1.0, 0.0),
            flat_ground,
            no_fluid,
            is_solid=lambda _x, y, _z: y == 0,
        )

    transform = simulation.world.transforms[item]
    assert transform.y == 1.0
    assert simulation.world.velocities[item].y == 0.0


def test_item_entity_falls_after_supporting_block_is_removed() -> None:
    simulation = EntitySimulation(seed=1)
    item = simulation.spawn_item((0.5, 3.0, 0.5), ItemStack(1, 1))
    support_present = True

    def is_solid(_x: int, y: int, _z: int) -> bool:
        return y == 2 if support_present else y == 0

    simulation.update(0.05, (0.0, 1.0, 0.0), flat_ground, no_fluid, is_solid=is_solid)
    assert simulation.world.transforms[item].y == 3.0

    support_present = False
    for _ in range(80):
        simulation.update(0.05, (0.0, 1.0, 0.0), flat_ground, no_fluid, is_solid=is_solid)

    assert simulation.world.transforms[item].y == 1.0
