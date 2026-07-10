from __future__ import annotations

from voxel_sandbox.application.inventory_presentation import (
    build_crafting_result_snapshot,
    build_item_icon_snapshot,
    resolve_inventory_status_text,
)
from voxel_sandbox.domain.crafting import CraftingGrid
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry


def test_item_icon_snapshot_contains_render_facing_text() -> None:
    snapshot = build_item_icon_snapshot(ItemStack(1, 32), create_core_item_registry())

    assert snapshot.item_id == 1
    assert snapshot.name == "Stone"
    assert snapshot.model_key == "stone"
    assert snapshot.count_text == "32"
    assert snapshot.tooltip == "Stone x32"


def test_item_icon_snapshot_omits_single_count_text() -> None:
    snapshot = build_item_icon_snapshot(ItemStack(1, 1), create_core_item_registry())

    assert snapshot.count_text == ""
    assert snapshot.tooltip == "Stone"


def test_crafting_result_snapshot_reports_missing_recipe_for_filled_grid() -> None:
    registry = create_core_item_registry()
    grid = CraftingGrid(2, 2)
    grid.set_index(0, ItemStack(1, 1))

    snapshot = build_crafting_result_snapshot(None, grid, registry)

    assert snapshot.result is None
    assert snapshot.has_inputs
    assert not snapshot.available
    assert snapshot.status_text == "No matching recipe"


def test_crafting_result_snapshot_wraps_available_result() -> None:
    registry = create_core_item_registry()
    grid = CraftingGrid(2, 2)
    grid.set_index(0, ItemStack(1, 1))

    snapshot = build_crafting_result_snapshot(ItemStack(4, 2), grid, registry)

    assert snapshot.result is not None
    assert snapshot.result.name == "Oak Log"
    assert snapshot.result.count_text == "2"
    assert snapshot.available
    assert snapshot.status_text == ""


def test_inventory_status_prefers_fresh_action_over_recipe_error() -> None:
    registry = create_core_item_registry()
    grid = CraftingGrid(2, 2)
    grid.set_index(0, ItemStack(1, 1))
    snapshot = build_crafting_result_snapshot(None, grid, registry)

    assert (
        resolve_inventory_status_text("Distributed Stone x7 across 3 slots.", snapshot)
        == "Distributed Stone x7 across 3 slots."
    )


def test_inventory_status_uses_recipe_error_without_action() -> None:
    registry = create_core_item_registry()
    grid = CraftingGrid(2, 2)
    grid.set_index(0, ItemStack(1, 1))
    snapshot = build_crafting_result_snapshot(None, grid, registry)

    assert resolve_inventory_status_text("", snapshot) == "No matching recipe"


def test_inventory_status_keeps_default_instruction_without_recipe_feedback() -> None:
    snapshot = build_crafting_result_snapshot(
        None,
        CraftingGrid(2, 2),
        create_core_item_registry(),
    )

    assert (
        resolve_inventory_status_text(
            "Place ingredients in the grid; click the result to craft.",
            snapshot,
        )
        == "Place ingredients in the grid; click the result to craft."
    )


def test_inventory_status_is_empty_for_available_result_without_action() -> None:
    registry = create_core_item_registry()
    grid = CraftingGrid(2, 2)
    grid.set_index(0, ItemStack(1, 1))
    snapshot = build_crafting_result_snapshot(ItemStack(4, 2), grid, registry)

    assert resolve_inventory_status_text("", snapshot) == ""
