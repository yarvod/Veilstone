from __future__ import annotations

from pathlib import Path

from voxel_sandbox.domain.crafting import RecipeBook
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import create_core_item_registry
from voxel_sandbox.engine.item_drops import ItemDropStore

RECIPES = Path(__file__).parents[2] / "config" / "recipes.toml"


def test_collected_log_can_be_crafted_into_placeable_workbench() -> None:
    registry = create_core_item_registry()
    inventory = Inventory()
    drops = ItemDropStore()
    log_drop = registry.drop_for_block(4)
    assert log_drop is not None
    for index in range(4):
        drops.spawn((float(index), 0.0, 0.0), log_drop)

    picked_up = drops.pickup_near((1.5, 0.0, 0.0), 3.0, inventory, registry)
    assert sum(stack.count for stack in picked_up) == 4

    recipes = RecipeBook.from_toml(RECIPES, registry)
    assert recipes.craft_from_inventory("veilwood_planks", inventory, registry, grid_size=2)
    assert recipes.craft_from_inventory("workbench", inventory, registry, grid_size=2)

    workbench = registry.by_key("workbench")
    assert inventory.count(workbench.id) == 1
    assert workbench.block_id == 10
