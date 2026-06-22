"""Tests for inventory UI presentation helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from voxel_sandbox.domain.crafting import CraftingGrid
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.render.inventory_ui import InventoryController


def _controller() -> InventoryController:
    inventory = Inventory()
    registry = create_core_item_registry()
    controller = InventoryController.__new__(InventoryController)
    controller.win = SimpleNamespace(
        width=1280,
        height=720,
        inventory=inventory,
        item_registry=registry,
        inventory_open=False,
        crafting_grid=CraftingGrid(2, 2),
        crafting_grid_size=2,
    )
    return controller


def test_hotbar_slot_hit_testing_matches_rendered_slots() -> None:
    controller = _controller()
    start_x = controller.win.width // 2 - (52 * 9) // 2

    assert controller.hotbar_slot_at(start_x + 26, 42) == 0
    assert controller.hotbar_slot_at(start_x + 52 * 8 + 26, 42) == 8
    assert controller.hotbar_slot_at(start_x - 1, 42) is None
    assert controller.hotbar_slot_at(start_x + 26, 90) is None


def test_hovered_stack_reads_hotbar_when_inventory_is_closed() -> None:
    controller = _controller()
    registry = controller.win.item_registry
    controller.win.inventory.set(0, ItemStack(3, 2), registry)
    start_x = controller.win.width // 2 - (52 * 9) // 2

    assert controller.hovered_stack_at(start_x + 26, 42) == ItemStack(3, 2)


def test_hovered_stack_reads_inventory_when_open() -> None:
    controller = _controller()
    registry = controller.win.item_registry
    controller.win.inventory_open = True
    controller.win.inventory.set(9, ItemStack(4, 5), registry)
    x, y = controller._inventory_slot_position(0)

    assert controller.hovered_stack_at(x + 24, y + 24) == ItemStack(4, 5)


def test_drag_target_slot_uses_distinct_highlight() -> None:
    controller = _controller()
    controller.win.cursor_stack = ItemStack(3, 2)
    shape = SimpleNamespace(draw=lambda: None)
    icon = SimpleNamespace(visible=True)
    count_label = SimpleNamespace(text="")

    controller._draw_item_slot(
        cast(Any, shape),
        cast(Any, icon),
        cast(Any, count_label),
        None,
        10,
        10,
        48,
        hovered=True,
    )

    assert shape.border_color == (120, 255, 185, 255)
