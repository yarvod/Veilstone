from __future__ import annotations

from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.engine.item_drops import ItemDropStore


def test_world_drop_pickup_moves_stack_into_inventory_and_removes_drop() -> None:
    registry = create_core_item_registry()
    inventory = Inventory()
    drops = ItemDropStore()
    drops.spawn((2.0, 3.0, 4.0), ItemStack(4, 3))

    assert not drops.pickup_near((0.0, 0.0, 0.0), 1.5, inventory, registry)
    picked_up = drops.pickup_near((2.5, 3.0, 4.0), 1.5, inventory, registry)

    assert picked_up == (ItemStack(4, 3),)
    assert inventory.count(4) == 3
    assert len(drops) == 0


def test_pickup_keeps_remainder_when_inventory_is_full() -> None:
    registry = create_core_item_registry()
    inventory = Inventory(9, 1)
    for index in range(9):
        inventory.set(index, ItemStack(8, 1), registry)
    drops = ItemDropStore()
    drops.spawn((0.0, 0.0, 0.0), ItemStack(3, 2))

    assert not drops.pickup_near((0.0, 0.0, 0.0), 1.0, inventory, registry)
    assert drops.all()[0].stack == ItemStack(3, 2)
