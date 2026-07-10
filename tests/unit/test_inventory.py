from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from voxel_sandbox.domain.inventory import Hotbar, Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry


def test_inventory_merges_splits_moves_and_removes_stacks() -> None:
    registry = create_core_item_registry()
    inventory = Inventory(9, 2)

    assert inventory.add(ItemStack(3, 70), registry) is None
    assert inventory[0] == ItemStack(3, 64)
    assert inventory[1] == ItemStack(3, 6)
    assert inventory.split(0) == ItemStack(3, 32)
    assert inventory[0] == ItemStack(3, 32)

    inventory.move(1, 0, registry)
    assert inventory[0] == ItemStack(3, 38)
    assert inventory[1] is None
    assert inventory.remove(3, 8)
    assert inventory.count(3) == 30
    assert not inventory.remove(3, 31)


def test_inventory_split_takes_larger_half_from_odd_stack() -> None:
    inventory = Inventory()
    registry = create_core_item_registry()
    inventory.set(0, ItemStack(3, 5), registry)

    assert inventory.split(0) == ItemStack(3, 3)
    assert inventory[0] == ItemStack(3, 2)


def test_inventory_split_keeps_even_and_single_stack_behavior() -> None:
    inventory = Inventory()
    registry = create_core_item_registry()
    inventory.set(0, ItemStack(3, 6), registry)
    inventory.set(1, ItemStack(3, 1), registry)

    assert inventory.split(0) == ItemStack(3, 3)
    assert inventory[0] == ItemStack(3, 3)
    assert inventory.split(1) is None
    assert inventory[1] == ItemStack(3, 1)


def test_inventory_returns_remainder_and_honors_unstackable_items() -> None:
    registry = create_core_item_registry()
    inventory = Inventory(9, 1)
    for index in range(9):
        inventory.set(index, ItemStack(8, 1), registry)

    assert inventory.add(ItemStack(3, 2), registry) == ItemStack(3, 2)


def test_hotbar_selects_and_cycles_nine_inventory_slots() -> None:
    inventory = Inventory()
    hotbar = Hotbar(inventory)

    hotbar.select(8)
    hotbar.cycle(1)
    assert hotbar.selected_index == 0
    hotbar.cycle(-1)
    assert hotbar.selected_index == 8


@given(st.integers(min_value=1, max_value=1000))
def test_add_preserves_total_count_between_inventory_and_remainder(count: int) -> None:
    registry = create_core_item_registry()
    inventory = Inventory(9, 1)

    remainder = inventory.add(ItemStack(3, count), registry)

    stored = inventory.count(3)
    remaining = remainder.count if remainder is not None else 0
    assert stored + remaining == count
    assert all(stack is None or stack.count <= 64 for stack in inventory)
