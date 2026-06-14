from __future__ import annotations

from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.engine.ecs import EntitySimulation, MobKind, MobState


def flat_ground(x: int, z: int) -> int:
    del x, z
    return 10


def no_hazard(x: int, y: int, z: int) -> bool:
    del x, y, z
    return False


def test_passive_mob_wanders_and_hostile_transitions_to_chase_and_attack() -> None:
    simulation = EntitySimulation(seed=42)
    passive = simulation.spawn_mob(MobKind.PASSIVE, (0.0, 10.0, 0.0))
    hostile = simulation.spawn_mob(MobKind.HOSTILE, (8.0, 10.0, 0.0))

    simulation.update(0.5, (0.0, 10.0, 0.0), flat_ground, no_hazard)

    assert simulation.world.mob_ai[passive].state is MobState.WANDER
    assert simulation.world.mob_ai[hostile].state is MobState.CHASE
    assert simulation.world.transforms[hostile].x < 8.0

    simulation.world.transforms[hostile].x = 1.0
    damage = simulation.update(0.1, (0.0, 10.0, 0.0), flat_ground, no_hazard)

    assert simulation.world.mob_ai[hostile].state is MobState.ATTACK
    assert damage == 2.0


def test_mob_death_spawns_item_entity_that_can_be_picked_up() -> None:
    simulation = EntitySimulation(seed=1)
    registry = create_core_item_registry()
    inventory = Inventory()
    mob = simulation.spawn_mob(MobKind.PASSIVE, (2.0, 10.0, 2.0))

    assert simulation.damage(mob, 100.0) == (ItemStack(4, 1),)
    assert simulation.world.mob_ai[mob].state is MobState.DEATH
    assert len(simulation.world.items) == 1

    simulation.update(0.7, (2.0, 10.0, 2.0), flat_ground, no_hazard)
    assert mob not in simulation.world.alive

    picked = simulation.pickup_items((2.0, 10.0, 2.0), 1.0, inventory, registry)
    assert picked == (ItemStack(4, 1),)
    assert len(simulation.world.items) == 0


def test_far_mob_despawns() -> None:
    simulation = EntitySimulation()
    mob = simulation.spawn_mob(MobKind.PASSIVE, (60.0, 10.0, 0.0))

    simulation.update(0.1, (0.0, 10.0, 0.0), flat_ground, no_hazard)

    assert mob not in simulation.world.alive


def test_population_rules_spawn_requested_mob_counts() -> None:
    simulation = EntitySimulation(seed=9)

    simulation.maintain_population(
        (0.0, 10.0, 0.0),
        flat_ground,
        no_hazard,
        passive_count=3,
        hostile_count=2,
    )

    kinds = [ai.kind for _entity, ai in simulation.world.mob_ai.items()]
    assert kinds.count(MobKind.PASSIVE) == 3
    assert kinds.count(MobKind.HOSTILE) == 2
