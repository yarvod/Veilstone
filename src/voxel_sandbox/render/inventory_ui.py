"""Inventory and crafting controller extracted from GameWindow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pyglet
from pyglet.window import mouse

from voxel_sandbox.domain.crafting import CraftingGrid, RecipeBook
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemRegistry, ItemStack


@dataclass
class InventoryState:
    inventory: Inventory
    item_registry: ItemRegistry
    recipe_book: RecipeBook
    crafting_grid: CraftingGrid = field(default_factory=lambda: CraftingGrid(2, 2))
    crafting_grid_size: int = 2
    cursor_stack: ItemStack | None = None
    inventory_open: bool = False
    status: str = ""


class InventoryLogic:
    """Pure logic for inventory and crafting operations — no rendering."""

    def __init__(self, state: InventoryState) -> None:
        self.s = state

    def open(self, grid_size: int) -> None:
        self.s.inventory_open = True
        self.s.crafting_grid_size = grid_size
        self.s.crafting_grid = CraftingGrid(grid_size, grid_size)
        self.s.status = "Place ingredients in the grid; click the result to craft."

    def close(self, drop_callback: Callable[[ItemStack], None]) -> None:
        for index in range(len(self.s.crafting_grid)):
            stack = self.s.crafting_grid.take(index)
            if stack is not None:
                self._return_or_drop(stack, drop_callback)
        if self.s.cursor_stack is not None:
            self._return_or_drop(self.s.cursor_stack, drop_callback)
            self.s.cursor_stack = None
        self.s.inventory_open = False
        self.s.status = ""

    def crafting_result(self) -> ItemStack | None:
        recipe = self.s.recipe_book.match(self.s.crafting_grid)
        return recipe.result if recipe is not None else None

    def handle_crafting_click(self, index: int, button: int) -> None:
        current = self.s.crafting_grid[index]
        if button == mouse.LEFT:
            if self.s.cursor_stack is None:
                self.s.cursor_stack = self.s.crafting_grid.take(index)
            elif current is None:
                self.s.crafting_grid.set_index(index, self.s.cursor_stack)
                self.s.cursor_stack = None
            elif current.item_id == self.s.cursor_stack.item_id:
                maximum = self.s.item_registry.by_id(current.item_id).max_stack
                moved = min(maximum - current.count, self.s.cursor_stack.count)
                if moved > 0:
                    self.s.crafting_grid.set_index(
                        index, current.with_count(current.count + moved)
                    )
                    remaining = self.s.cursor_stack.count - moved
                    self.s.cursor_stack = (
                        self.s.cursor_stack.with_count(remaining) if remaining else None
                    )
            else:
                self.s.crafting_grid.set_index(index, self.s.cursor_stack)
                self.s.cursor_stack = current
            return
        if button != mouse.RIGHT:
            return
        if self.s.cursor_stack is None:
            if current is None:
                return
            take_count = (current.count + 1) // 2
            remaining = current.count - take_count
            self.s.cursor_stack = current.with_count(take_count)
            self.s.crafting_grid.set_index(
                index, current.with_count(remaining) if remaining else None
            )
            return
        maximum = self.s.item_registry.by_id(self.s.cursor_stack.item_id).max_stack
        if current is None:
            self.s.crafting_grid.set_index(index, self.s.cursor_stack.with_count(1))
        elif current.item_id == self.s.cursor_stack.item_id and current.count < maximum:
            self.s.crafting_grid.set_index(index, current.with_count(current.count + 1))
        else:
            return
        remaining = self.s.cursor_stack.count - 1
        self.s.cursor_stack = (
            self.s.cursor_stack.with_count(remaining) if remaining else None
        )

    def take_crafting_result(self) -> None:
        result = self.crafting_result()
        if result is None:
            self.s.status = "The current pattern has no recipe."
            return
        maximum = self.s.item_registry.by_id(result.item_id).max_stack
        if self.s.cursor_stack is not None and (
            self.s.cursor_stack.item_id != result.item_id
            or self.s.cursor_stack.count + result.count > maximum
        ):
            self.s.status = "Clear the cursor before taking this result."
            return
        crafted = self.s.recipe_book.craft(self.s.crafting_grid)
        if crafted is None:
            return
        self.s.cursor_stack = (
            crafted
            if self.s.cursor_stack is None
            else self.s.cursor_stack.with_count(self.s.cursor_stack.count + crafted.count)
        )
        definition = self.s.item_registry.by_id(crafted.item_id)
        self.s.status = f"Crafted {definition.name} x{crafted.count}."

    def handle_inventory_click(
        self, index: int, button: int, *, quick_move: bool
    ) -> None:
        inv = self.s.inventory
        reg = self.s.item_registry
        if quick_move and button == mouse.LEFT and self.s.cursor_stack is None:
            target_range = range(9, len(inv)) if index < 9 else range(9)
            for target in target_range:
                inv.move(index, target, reg)
                if inv[index] is None:
                    break
            return
        current = inv[index]
        if button == mouse.LEFT:
            if self.s.cursor_stack is None:
                if current is not None:
                    self.s.cursor_stack = inv.take_from_slot(index, current.count)
                return
            if current is None:
                inv.set(index, self.s.cursor_stack, reg)
                self.s.cursor_stack = None
                return
            if current.item_id != self.s.cursor_stack.item_id:
                inv.set(index, self.s.cursor_stack, reg)
                self.s.cursor_stack = current
                return
            maximum = reg.by_id(current.item_id).max_stack
            moved = min(maximum - current.count, self.s.cursor_stack.count)
            if moved:
                inv.set(index, current.with_count(current.count + moved), reg)
                remaining = self.s.cursor_stack.count - moved
                self.s.cursor_stack = (
                    self.s.cursor_stack.with_count(remaining) if remaining else None
                )
        elif button == mouse.RIGHT:
            if self.s.cursor_stack is None:
                self.s.cursor_stack = inv.split(index)
                return
            if current is None:
                inv.set(index, self.s.cursor_stack.with_count(1), reg)
            elif (
                current.item_id == self.s.cursor_stack.item_id
                and current.count < reg.by_id(current.item_id).max_stack
            ):
                inv.set(index, current.with_count(current.count + 1), reg)
            else:
                return
            remaining = self.s.cursor_stack.count - 1
            self.s.cursor_stack = (
                self.s.cursor_stack.with_count(remaining) if remaining else None
            )

    def _return_or_drop(
        self, stack: ItemStack, drop_callback: Callable[[ItemStack], None]
    ) -> None:
        remainder = self.s.inventory.add(stack, self.s.item_registry)
        if remainder is not None:
            drop_callback(remainder)
