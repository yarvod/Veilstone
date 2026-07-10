"""Tests for InventoryLogic — extracted inventory/crafting controller."""

from __future__ import annotations

from types import SimpleNamespace

from voxel_sandbox.domain.crafting import Recipe, RecipeBook
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


def _make_plank_crafting_logic(*, inventory: Inventory | None = None) -> InventoryLogic:
    registry = create_core_item_registry()
    recipe = Recipe(
        "planks",
        ((registry.by_key("oak_log").id,),),
        ItemStack(registry.by_key("oak_planks").id, 4),
        shaped=False,
    )
    state = InventoryState(
        inventory=inventory or Inventory(),
        item_registry=registry,
        recipe_book=RecipeBook((recipe,)),
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
    def test_ordinary_crafting_click_clears_stale_action_feedback(self):
        logic = _make_logic()
        logic.s.status = "Distributed Stone x4 across 2 slots."
        logic.s.crafting_grid.set_index(0, ItemStack(1, 1))

        logic.handle_crafting_click(0, mouse.LEFT)

        assert logic.s.status == ""

    def test_shift_click_moves_full_stack_to_inventory_without_cursor(self):
        logic = _make_logic()
        logic.s.crafting_grid.set_index(0, ItemStack(4, 5))
        logic.s.cursor_stack = ItemStack(2, 3)

        logic.handle_crafting_click(0, mouse.LEFT, quick_move=True)

        assert logic.s.crafting_grid[0] is None
        assert logic.s.inventory.count(4) == 5
        assert logic.s.cursor_stack == ItemStack(2, 3)
        assert logic.s.status == "Moved Oak Log x5 to inventory."

    def test_shift_click_preserves_remainder_when_inventory_only_partly_fits(self):
        inventory = Inventory(1, 1)
        logic = _make_logic()
        logic.s.inventory = inventory
        inventory.set(0, ItemStack(4, 62), logic.s.item_registry)
        logic.s.crafting_grid.set_index(0, ItemStack(4, 5))

        logic.handle_crafting_click(0, mouse.LEFT, quick_move=True)

        assert inventory[0] == ItemStack(4, 64)
        assert logic.s.crafting_grid[0] == ItemStack(4, 3)
        assert logic.s.cursor_stack is None
        assert logic.s.status == "Moved Oak Log x2 to inventory."

    def test_shift_click_full_inventory_keeps_crafting_stack_and_cursor(self):
        inventory = Inventory(1, 1)
        logic = _make_logic()
        logic.s.inventory = inventory
        inventory.set(0, ItemStack(1, 64), logic.s.item_registry)
        logic.s.crafting_grid.set_index(0, ItemStack(4, 5))
        logic.s.cursor_stack = ItemStack(2, 3)

        logic.handle_crafting_click(0, mouse.LEFT, quick_move=True)

        assert inventory[0] == ItemStack(1, 64)
        assert logic.s.crafting_grid[0] == ItemStack(4, 5)
        assert logic.s.cursor_stack == ItemStack(2, 3)
        assert logic.s.status == "Inventory has no room for Oak Log."

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


class TestCraftingResult:
    def test_quick_move_without_recipe_keeps_existing_feedback(self):
        logic = _make_plank_crafting_logic()

        logic.take_crafting_result(quick_move=True)

        assert logic.s.status == "The current pattern has no recipe."

    def test_ordinary_click_still_moves_one_result_to_cursor(self):
        logic = _make_plank_crafting_logic()
        logic.s.crafting_grid.set_index(0, ItemStack(4, 2))

        logic.take_crafting_result()

        assert logic.s.cursor_stack == ItemStack(9, 4)
        assert logic.s.crafting_grid[0] == ItemStack(4, 1)
        assert logic.s.inventory.count(9) == 0

    def test_quick_move_repeats_recipe_into_inventory(self):
        logic = _make_plank_crafting_logic()
        logic.s.crafting_grid.set_index(0, ItemStack(4, 3))

        logic.take_crafting_result(quick_move=True)

        assert logic.s.cursor_stack is None
        assert logic.s.crafting_grid[0] is None
        assert logic.s.inventory.count(9) == 12
        assert logic.s.status == "Crafted Oak Planks x12 into inventory."

    def test_quick_move_does_not_consume_inputs_when_inventory_is_full(self):
        inventory = Inventory(1, 1)
        logic = _make_plank_crafting_logic(inventory=inventory)
        logic.s.inventory.set(0, ItemStack(1, 64), logic.s.item_registry)
        logic.s.crafting_grid.set_index(0, ItemStack(4, 2))

        logic.take_crafting_result(quick_move=True)

        assert logic.s.inventory[0] == ItemStack(1, 64)
        assert logic.s.crafting_grid[0] == ItemStack(4, 2)
        assert logic.s.status == "Inventory has no room for the crafting result."

    def test_quick_move_stops_at_stack_limit_without_losing_inputs(self):
        inventory = Inventory(1, 1)
        logic = _make_plank_crafting_logic(inventory=inventory)
        logic.s.inventory.set(0, ItemStack(9, 60), logic.s.item_registry)
        logic.s.crafting_grid.set_index(0, ItemStack(4, 2))

        logic.take_crafting_result(quick_move=True)

        assert logic.s.inventory[0] == ItemStack(9, 64)
        assert logic.s.crafting_grid[0] == ItemStack(4, 1)
        assert logic.s.status == "Crafted Oak Planks x4 into inventory."


class TestInventoryClick:
    def test_ordinary_inventory_click_clears_stale_action_feedback(self):
        logic = _make_logic()
        logic.s.status = "Moved Stone x2 to inventory."

        logic.handle_inventory_click(0, mouse.LEFT, quick_move=False)

        assert logic.s.status == ""

    def test_left_drag_distribution_splits_even_share_and_keeps_remainder(self):
        logic = _make_logic()
        logic.s.cursor_stack = ItemStack(1, 10)

        logic.distribute_cursor_stack((("inventory", 0), ("inventory", 1), ("crafting", 0)))

        assert logic.s.inventory[0] == ItemStack(1, 3)
        assert logic.s.inventory[1] == ItemStack(1, 3)
        assert logic.s.crafting_grid[0] == ItemStack(1, 3)
        assert logic.s.cursor_stack == ItemStack(1, 1)
        assert logic.s.status == "Distributed Stone x9 across 3 slots."

    def test_left_drag_distribution_skips_invalid_targets_and_respects_capacity(self):
        logic = _make_logic()
        logic.s.inventory.set(0, ItemStack(2, 3), logic.s.item_registry)
        logic.s.inventory.set(1, ItemStack(1, 63), logic.s.item_registry)
        logic.s.cursor_stack = ItemStack(1, 8)

        logic.distribute_cursor_stack(
            (
                ("inventory", 0),
                ("inventory", 1),
                ("crafting", 0),
                ("crafting", 0),
            )
        )

        assert logic.s.inventory[0] == ItemStack(2, 3)
        assert logic.s.inventory[1] == ItemStack(1, 64)
        assert logic.s.crafting_grid[0] == ItemStack(1, 4)
        assert logic.s.cursor_stack == ItemStack(1, 3)
        assert logic.s.status == "Distributed Stone x5 across 2 slots."

    def test_left_drag_distribution_keeps_cursor_when_share_is_zero(self):
        logic = _make_logic()
        logic.s.cursor_stack = ItemStack(1, 2)

        logic.distribute_cursor_stack((("inventory", 0), ("inventory", 1), ("crafting", 0)))

        assert logic.s.cursor_stack == ItemStack(1, 2)
        assert all(logic.s.inventory[index] is None for index in (0, 1))
        assert logic.s.crafting_grid[0] is None

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

    def test_quick_move_skips_incompatible_target_before_empty_slot(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 10), reg)
        logic.s.inventory.set(9, ItemStack(2, 5), reg)

        logic.handle_inventory_click(0, mouse.LEFT, quick_move=True)

        assert logic.s.inventory[0] is None
        assert logic.s.inventory[9] == ItemStack(2, 5)
        assert logic.s.inventory[10] == ItemStack(1, 10)
        assert logic.s.status == "Moved Stone x10."

    def test_quick_move_preserves_source_remainder_when_main_inventory_is_full(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 10), reg)
        logic.s.inventory.set(9, ItemStack(1, 60), reg)
        for index in range(10, len(logic.s.inventory)):
            logic.s.inventory.set(index, ItemStack(2, 64), reg)

        logic.handle_inventory_click(0, mouse.LEFT, quick_move=True)

        assert logic.s.inventory[0] == ItemStack(1, 6)
        assert logic.s.inventory[9] == ItemStack(1, 64)
        assert all(logic.s.inventory[index] == ItemStack(2, 64) for index in range(10, 36))
        assert logic.s.status == "Moved Stone x4."

    def test_quick_move_from_main_merges_then_uses_empty_hotbar_slot(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(9, ItemStack(1, 10), reg)
        logic.s.inventory.set(0, ItemStack(2, 5), reg)
        logic.s.inventory.set(1, ItemStack(1, 60), reg)

        logic.handle_inventory_click(9, mouse.LEFT, quick_move=True)

        assert logic.s.inventory[9] is None
        assert logic.s.inventory[0] == ItemStack(2, 5)
        assert logic.s.inventory[1] == ItemStack(1, 64)
        assert logic.s.inventory[2] == ItemStack(1, 6)
        assert logic.s.status == "Moved Stone x10."

    def test_split_with_right_click(self):
        logic = _make_logic()
        reg = logic.s.item_registry
        logic.s.inventory.set(0, ItemStack(1, 10), reg)
        logic.handle_inventory_click(0, mouse.RIGHT, quick_move=False)
        assert logic.s.cursor_stack is not None
        assert logic.s.cursor_stack.count == 5
        assert logic.s.inventory[0].count == 5

    def test_odd_stack_right_click_matches_crafting_grid_ceil_half_split(self):
        inventory_logic = _make_logic()
        inventory_logic.s.inventory.set(
            0,
            ItemStack(1, 5),
            inventory_logic.s.item_registry,
        )
        crafting_logic = _make_logic()
        crafting_logic.s.crafting_grid.set_index(0, ItemStack(1, 5))

        inventory_logic.handle_inventory_click(0, mouse.RIGHT, quick_move=False)
        crafting_logic.handle_crafting_click(0, mouse.RIGHT)

        assert inventory_logic.s.cursor_stack == ItemStack(1, 3)
        assert inventory_logic.s.inventory[0] == ItemStack(1, 2)
        assert crafting_logic.s.cursor_stack == ItemStack(1, 3)
        assert crafting_logic.s.crafting_grid[0] == ItemStack(1, 2)

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

    def test_right_click_skips_incompatible_slot_without_changing_cursor(self):
        logic = _make_logic()
        logic.s.inventory.set(0, ItemStack(2, 3), logic.s.item_registry)
        logic.s.cursor_stack = ItemStack(1, 5)

        logic.handle_inventory_click(0, mouse.RIGHT, quick_move=False)

        assert logic.s.cursor_stack == ItemStack(1, 5)
        assert logic.s.inventory[0] == ItemStack(2, 3)

    def test_right_click_skips_full_compatible_slot_without_changing_cursor(self):
        logic = _make_logic()
        logic.s.inventory.set(0, ItemStack(1, 64), logic.s.item_registry)
        logic.s.cursor_stack = ItemStack(1, 5)

        logic.handle_inventory_click(0, mouse.RIGHT, quick_move=False)

        assert logic.s.cursor_stack == ItemStack(1, 5)
        assert logic.s.inventory[0] == ItemStack(1, 64)
