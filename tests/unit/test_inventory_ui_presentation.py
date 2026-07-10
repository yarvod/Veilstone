"""Tests for inventory UI presentation helpers."""
# pyright: reportAttributeAccessIssue=false, reportPrivateUsage=false

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from voxel_sandbox.domain.crafting import CraftingGrid
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.render.inventory_ui import InventoryController
from voxel_sandbox.render.texture_atlas import GeneratedAtlas


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


def test_resource_pack_refresh_reuses_sprites_and_inventory_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_stone = object()
    old_dirt = object()
    next_stone = object()
    next_dirt = object()
    inventory_state = [ItemStack(1, 1), ItemStack(2, 1)]
    controller = cast(Any, InventoryController.__new__(InventoryController))
    controller.win = SimpleNamespace(
        item_registry=object(),
        inventory=inventory_state,
        crafting_grid=[ItemStack(1, 1)],
        cursor_stack=ItemStack(2, 1),
        selected_hotbar_index=lambda: 1,
        world_runtime=SimpleNamespace(block_registry=object()),
    )
    controller.item_icon_images = {1: old_stone, 2: old_dirt}
    controller.hotbar_icons = [SimpleNamespace(image=old_stone)]
    controller.inventory_icons = [
        SimpleNamespace(image=old_stone),
        SimpleNamespace(image=old_dirt),
    ]
    controller.crafting_icons = [SimpleNamespace(image=old_stone)]
    controller.crafting_result_icon = SimpleNamespace(image=old_dirt)
    controller.cursor_item_icon = SimpleNamespace(image=old_stone)
    controller.held_item_icon = SimpleNamespace(image=old_dirt)
    controller.crafting_result_stack = lambda: ItemStack(2, 1)

    def fake_create_item_icons(*_args: Any) -> dict[int, Any]:
        return {1: next_stone, 2: next_dirt}

    monkeypatch.setattr(
        "voxel_sandbox.render.inventory_ui.create_item_icons",
        fake_create_item_icons,
    )
    atlas = GeneratedAtlas(1, 1, b"\x00\x00\x00\xff", {})

    controller.refresh_item_icons(atlas)

    assert controller.item_icon_images == {1: next_stone, 2: next_dirt}
    assert controller.hotbar_icons[0].image is next_stone
    assert controller.inventory_icons[0].image is next_stone
    assert controller.inventory_icons[1].image is next_dirt
    assert controller.crafting_icons[0].image is next_stone
    assert controller.crafting_result_icon.image is next_dirt
    assert controller.cursor_item_icon.image is next_dirt
    assert controller.held_item_icon.image is next_dirt
    assert controller.win.inventory is inventory_state
