from __future__ import annotations

from voxel_sandbox.domain.blocks.entities import BlockEntityRegistry, GenericBlockEntity
from voxel_sandbox.domain.blocks.structures import StructureWorld


def test_gate_altar_and_bridge_advance_without_rebuilding_definitions() -> None:
    world = StructureWorld()
    gate = world.spawn("gate", (0, 10, 0))
    altar = world.spawn("altar", (10, 10, 0))
    bridge = world.spawn("bridge", (20, 10, 0))
    definition_ids = {key: id(value) for key, value in world.definitions.items()}

    world.toggle(gate.entity_id)
    world.toggle(altar.entity_id)
    world.toggle(bridge.entity_id)
    assert world.update(0.5)

    assert 0.0 < gate.progress < 1.0
    assert 0.0 < altar.progress < 1.0
    assert 0.0 < bridge.progress < 1.0
    assert definition_ids == {key: id(value) for key, value in world.definitions.items()}


def test_structure_collision_follows_moving_parts() -> None:
    world = StructureWorld()
    gate = world.spawn("gate", (0, 10, 0))

    assert world.is_solid_cell(0, 10, 0)
    world.toggle(gate.entity_id)
    world.update(10.0)

    assert not world.is_solid_cell(0, 10, 0)
    assert world.is_solid_cell(0, 13, 0)


def test_structure_snapshots_replace_runtime_state() -> None:
    original = StructureWorld()
    entity = original.spawn("bridge", (3, 12, -4))
    original.toggle(entity.entity_id)
    original.update(0.75)

    restored = StructureWorld()
    restored.replace_from_snapshots(original.snapshots())

    assert restored.snapshots() == original.snapshots()
    assert restored.next_entity_id == entity.entity_id + 1


def test_structure_raycast_selects_nearest_runtime_entity() -> None:
    world = StructureWorld()
    nearest = world.spawn("gate", (0, 10, 0))
    world.spawn("gate", (0, 10, 4))

    hit = world.raycast_entity((0.5, 10.5, -3.0), (0.0, 0.0, 1.0), 10.0)

    assert hit is not None
    assert hit[0] == nearest.entity_id
    assert hit[1] == 3.0


def test_block_entity_registry_rejects_unknown_and_duplicate_types() -> None:
    registry = BlockEntityRegistry()
    registry.register("altar_controller", GenericBlockEntity)

    entity = registry.create("altar_controller", {"charge": 3})
    assert entity.snapshot() == {
        "kind": "altar_controller",
        "data": {"charge": 3},
    }

    try:
        registry.register("altar_controller", GenericBlockEntity)
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate block entity type was accepted")
