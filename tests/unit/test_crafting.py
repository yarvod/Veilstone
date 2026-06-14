from __future__ import annotations

from pathlib import Path

from voxel_sandbox.domain.crafting import CraftingGrid, RecipeBook
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry

RECIPES = Path(__file__).parents[2] / "config" / "recipes.toml"


def test_shapeless_recipe_matches_any_2x2_position_and_consumes_one() -> None:
    registry = create_core_item_registry()
    book = RecipeBook.from_toml(RECIPES, registry)
    grid = CraftingGrid(2, 2)
    grid.set(1, 1, ItemStack(registry.by_key("veilwood_log").id, 2))

    assert book.match(grid).key == "veilwood_planks"  # type: ignore[union-attr]
    assert book.craft(grid) == ItemStack(registry.by_key("veilwood_planks").id, 4)
    assert grid[3] == ItemStack(registry.by_key("veilwood_log").id, 1)


def test_shaped_recipe_is_trimmed_but_preserves_layout() -> None:
    registry = create_core_item_registry()
    book = RecipeBook.from_toml(RECIPES, registry)
    grid = CraftingGrid(3, 3)
    planks = registry.by_key("veilwood_planks").id
    for x, y in ((1, 1), (2, 1), (1, 2), (2, 2)):
        grid.set(x, y, ItemStack(planks, 1))

    assert book.match(grid).key == "workbench"  # type: ignore[union-attr]
    assert book.craft(grid) == ItemStack(registry.by_key("workbench").id, 1)


def test_3x3_recipe_cannot_be_crafted_in_player_2x2_grid() -> None:
    registry = create_core_item_registry()
    book = RecipeBook.from_toml(RECIPES, registry)
    inventory = Inventory()
    inventory.add(ItemStack(registry.by_key("dusk_crystal").id, 1), registry)
    inventory.add(ItemStack(registry.by_key("veilwood_planks").id, 4), registry)

    assert not book.craft_from_inventory("gloam_lantern", inventory, registry, grid_size=2)
    assert book.craft_from_inventory("gloam_lantern", inventory, registry, grid_size=3)
    assert inventory.count(registry.by_key("gloam_lantern").id) == 1


def test_inventory_crafting_is_atomic_when_inputs_or_output_space_are_missing() -> None:
    registry = create_core_item_registry()
    book = RecipeBook.from_toml(RECIPES, registry)
    inventory = Inventory(9, 1)

    assert not book.craft_from_inventory("veilwood_planks", inventory, registry, grid_size=2)
    assert list(inventory) == [None] * 9


def test_crafting_grid_supports_cursor_style_index_take_and_replace() -> None:
    grid = CraftingGrid(2, 2)
    stack = ItemStack(4, 3)

    grid.set_index(2, stack)

    assert len(grid) == 4
    assert grid.take(2) == stack
    assert grid[2] is None
