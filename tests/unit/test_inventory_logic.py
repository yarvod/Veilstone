"""Tests for InventoryLogic — extracted inventory/crafting controller."""

from __future__ import annotations

from pyglet.window import mouse

from voxel_sandbox.domain.crafting import CraftingGrid, RecipeBook
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.render.inventory_ui import InventoryLogic, InventoryState


def _make_logic() -> InventoryLogic:
    registry = create_core_item_registry()
    recipes_path = None
    state = InventoryState(
        inventory=Inventory(),
        item_registry=registry,
        recipe_book=RecipeBook(()),
    )
    return InventoryLogic(state)


class TestInventoryOpen:
    def test_open_sets_state(self):
        logic = _make_logic()
        logic.open(3)
        assert logic.s.inventory_open
        assert logic.s.crafting_grid_size == 3

    def test_close_returns_crafting_items(self):
        logic = _make_logic()
        logic.open(2)
        logic.s.crafting_grid.set_index(0, ItemStack(1, 5))
        dropped: list[ItemStack] = []
        logic.close(dropped.append)
        assert not logic.s.inventory_open
        assert logic.s.inventory[0] is not None or len(dropped) > 0

    def test_close_returns_cursor_stack(self):
        logic = _make_logic()
        logic.open(2)
        logic.s.cursor_stack = ItemStack(1, 3)
        dropped: list[ItemStack] = []
        logic.close(dropped.append)
        assert logic.s.cursor_stack is None


class TestCraftingClick:
    def test_pick_up_item_from_grid(self):
        logic = _make_logic()
        logic.open(2)
        logic.s.crafting_grid.set_index(0, ItemStack(1, 5))
        logic.handle_crafting_click(0, mouse.LEFT)
        assert logic.s.cursor_stack is not None
        assert logic.s.cursor_stack.count == 5
        assert logic.s.crafting_grid[0] is None

    def test_place_item_into_grid(self):
        logic = _make_logic()
        logic.open(2)
        logic.s.cursor_stack = ItemStack(1, 3)
        logic.handle_crafting_click(0, mouse.LEFT)
        assert logic.s.cursor_stack is None
        assert logic.s.crafting_grid[0] is not None
        assert logic.s.crafting_grid[0].count == 3

    def test_right_click_places_one(self):
        logic = _make_logic()
        logic.open(2)
        logic.s.cursor_stack = ItemStack(1, 5)
        logic.handle_crafting_click(0, mouse.RIGHT)
        assert logic.s.cursor_stack.count == 4
        assert logic.s.crafting_grid[0].count == 1


class TestInventoryClick:
    def test_pick_up_item(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 10), reg)
        logic.handle_inventory_click(0, mouse.LEFT, quick_move=False)
        assert logic.s.cursor_stack is not None
        assert logic.s.cursor_stack.count == 10
        assert logic.s.inventory[0] is None

    def test_place_item(self):
        logic = _make_logic()
        logic.s.cursor_stack = ItemStack(1, 5)
        logic.handle_inventory_click(0, mouse.LEFT, quick_move=False)
        assert logic.s.cursor_stack is None
        assert logic.s.inventory[0] is not None

    def test_quick_move(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 10), reg)
        logic.handle_inventory_click(0, mouse.LEFT, quick_move=True)
        assert logic.s.inventory[0] is None
        assert any(logic.s.inventory[i] is not None for i in range(9, 27))

    def test_split_with_right_click(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 10), reg)
        logic.handle_inventory_click(0, mouse.RIGHT, quick_move=False)
        assert logic.s.cursor_stack is not None
        assert logic.s.cursor_stack.count == 5
        assert logic.s.inventory[0].count == 5
