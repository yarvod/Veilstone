"""Tests for InventoryLogic — extracted inventory/crafting controller."""

from __future__ import annotations

from types import SimpleNamespace

from voxel_sandbox.domain.crafting import RecipeBook
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.render.input_state import mouse
from voxel_sandbox.render.inventory_ui import InventoryController, InventoryLogic, InventoryState


def _make_logic() -> InventoryLogic:
    registry = create_core_item_registry()
    state = InventoryState(
        inventory=Inventory(),
        item_registry=registry,
        recipe_book=RecipeBook(()),
    )
    return InventoryLogic(state)


def test_inventory_controller_sync_refreshes_world_inventory_reference() -> None:
    registry = create_core_item_registry()
    old_inventory = Inventory()
    old_inventory.set(0, ItemStack(1, 64), registry)
    new_inventory = Inventory()
    state = InventoryState(
        inventory=old_inventory,
        item_registry=registry,
        recipe_book=RecipeBook(()),
    )
    controller = object.__new__(InventoryController)
    controller.win = SimpleNamespace(
        inventory=new_inventory,
        crafting_grid=state.crafting_grid,
        crafting_grid_size=state.crafting_grid_size,
        cursor_stack=None,
        inventory_open=False,
        inventory_status="",
        _inv_state=state,
    )

    controller._sync_to_inv()

    assert state.inventory is new_inventory
    assert state.inventory[0] is None


def test_drop_selected_item_uses_view_drop_port() -> None:
    registry = create_core_item_registry()
    inventory = Inventory()
    inventory.set(2, ItemStack(1, 3), registry)
    dropped: list[ItemStack] = []
    controller = object.__new__(InventoryController)
    controller.win = SimpleNamespace(
        inventory=inventory,
        item_registry=registry,
        inventory_status="",
        selected_hotbar_index=lambda: 2,
        spawn_drop_from_camera=dropped.append,
    )

    controller.drop_selected_item()

    assert dropped == [ItemStack(1, 1)]
    assert inventory[2] == ItemStack(1, 2)
    assert "Dropped" in controller.win.inventory_status


def test_return_or_drop_stack_uses_near_player_drop_port_when_inventory_full() -> None:
    registry = create_core_item_registry()
    inventory = Inventory(1, 1)
    inventory.set(0, ItemStack(8, 1), registry)
    dropped: list[ItemStack] = []
    controller = object.__new__(InventoryController)
    controller.win = SimpleNamespace(
        inventory=inventory,
        item_registry=registry,
        spawn_drop_near_player=dropped.append,
    )

    controller._return_or_drop_stack(ItemStack(1, 1))

    assert dropped == [ItemStack(1, 1)]


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

    def test_left_click_merges_cursor_stack_into_same_item(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 10), reg)
        logic.s.cursor_stack = ItemStack(1, 5)

        logic.handle_inventory_click(0, mouse.LEFT, quick_move=False)

        assert logic.s.cursor_stack is None
        assert logic.s.inventory[0] == ItemStack(1, 15)

    def test_left_click_partially_merges_up_to_stack_limit(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 63), reg)
        logic.s.cursor_stack = ItemStack(1, 4)

        logic.handle_inventory_click(0, mouse.LEFT, quick_move=False)

        assert logic.s.cursor_stack == ItemStack(1, 3)
        assert logic.s.inventory[0] == ItemStack(1, 64)

    def test_left_click_swaps_different_item_stack(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 10), reg)
        logic.s.cursor_stack = ItemStack(2, 3)

        logic.handle_inventory_click(0, mouse.LEFT, quick_move=False)

        assert logic.s.cursor_stack == ItemStack(1, 10)
        assert logic.s.inventory[0] == ItemStack(2, 3)

    def test_right_click_places_one_item_into_empty_slot(self):
        logic = _make_logic()
        logic.s.cursor_stack = ItemStack(1, 5)

        logic.handle_inventory_click(0, mouse.RIGHT, quick_move=False)

        assert logic.s.cursor_stack == ItemStack(1, 4)
        assert logic.s.inventory[0] == ItemStack(1, 1)
