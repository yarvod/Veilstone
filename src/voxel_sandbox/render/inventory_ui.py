"""Inventory and crafting controller extracted from GameWindow."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

import pyglet

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.crafting import CraftingGrid, RecipeBook
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemRegistry, ItemStack
from voxel_sandbox.render.input_state import mouse
from voxel_sandbox.render.ui.item_icons import (
    HEART_SIZE,
    ICON_SIZE,
    create_hand_image,
    create_heart_icons,
    create_item_icons,
)
from voxel_sandbox.render.ui.menu import platform_font_name

if TYPE_CHECKING:
    from voxel_sandbox.render.window import GameWindow


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
                    self.s.crafting_grid.set_index(index, current.with_count(current.count + moved))
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
        self.s.cursor_stack = self.s.cursor_stack.with_count(remaining) if remaining else None

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

    def handle_inventory_click(self, index: int, button: int, *, quick_move: bool) -> None:
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
            self.s.cursor_stack = self.s.cursor_stack.with_count(remaining) if remaining else None

    def _return_or_drop(self, stack: ItemStack, drop_callback: Callable[[ItemStack], None]) -> None:
        remainder = self.s.inventory.add(stack, self.s.item_registry)
        if remainder is not None:
            drop_callback(remainder)


_FONT = platform_font_name(sys.platform)


class InventoryController:
    """Owns all inventory sprites and rendering; delegates logic to InventoryLogic."""

    def __init__(self, win: GameWindow) -> None:
        self.win = win

        block_registry = cast(BlockRegistry, win.world_runtime.block_registry)
        self.item_icon_images = create_item_icons(win.item_registry, block_registry)
        self.heart_images = create_heart_icons()
        self.heart_sprites = [
            pyglet.sprite.Sprite(self.heart_images[0], batch=win.hud_batch, group=win.hud_fg_group)
            for _ in range(10)
        ]

        default_icon = self.item_icon_images[1]

        self.hotbar_slots = [
            pyglet.shapes.BorderedRectangle(
                0, 0, 52, 52, 3, batch=win.hud_batch, group=win.hud_bg_group
            )
            for _ in range(9)
        ]
        self.hotbar_icons = [
            pyglet.sprite.Sprite(default_icon, batch=win.hud_batch, group=win.hud_fg_group)
            for _ in range(9)
        ]
        self.hotbar_count_labels = [
            pyglet.text.Label(
                "",
                anchor_x="right",
                anchor_y="bottom",
                font_name=_FONT,
                font_size=12,
                color=(255, 255, 255, 255),
                batch=win.hud_batch,
                group=win.hud_text_group,
            )
            for _ in range(9)
        ]
        self.hotbar_key_labels = [
            pyglet.text.Label(
                str(index + 1),
                anchor_x="left",
                anchor_y="top",
                font_name=_FONT,
                font_size=8,
                color=(190, 200, 215, 255),
                batch=win.hud_batch,
                group=win.hud_text_group,
            )
            for index in range(9)
        ]

        self.inventory_title = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            font_name=_FONT,
            font_size=22,
            color=(245, 220, 140, 255),
        )
        self.inventory_panel = pyglet.shapes.BorderedRectangle(
            0, 0, 540, 500, 4, color=(34, 38, 48), border_color=(132, 142, 158)
        )
        self.inventory_slots = [
            pyglet.shapes.BorderedRectangle(0, 0, 48, 48, 2) for _ in range(len(win.inventory))
        ]
        self.inventory_icons = [
            pyglet.sprite.Sprite(default_icon) for _ in range(len(win.inventory))
        ]
        self.inventory_count_labels = [
            pyglet.text.Label(
                "",
                anchor_x="right",
                anchor_y="bottom",
                font_name=_FONT,
                font_size=12,
                color=(255, 255, 255, 255),
            )
            for _ in range(len(win.inventory))
        ]
        self.crafting_slots = [pyglet.shapes.BorderedRectangle(0, 0, 48, 48, 2) for _ in range(9)]
        self.crafting_icons = [pyglet.sprite.Sprite(default_icon) for _ in range(9)]
        self.crafting_count_labels = [
            pyglet.text.Label(
                "",
                anchor_x="right",
                anchor_y="bottom",
                font_name=_FONT,
                font_size=12,
                color=(255, 255, 255, 255),
            )
            for _ in range(9)
        ]
        self.crafting_result_slot = pyglet.shapes.BorderedRectangle(0, 0, 56, 56, 3)
        self.crafting_result_icon = pyglet.sprite.Sprite(default_icon)
        self.crafting_result_count = pyglet.text.Label(
            "",
            anchor_x="right",
            anchor_y="bottom",
            font_name=_FONT,
            font_size=12,
        )
        self.crafting_label = pyglet.text.Label(
            "CRAFTING",
            anchor_x="left",
            anchor_y="bottom",
            font_name=_FONT,
            font_size=13,
            color=(205, 215, 230, 255),
        )
        self.crafting_arrow = pyglet.text.Label(
            ">",
            anchor_x="center",
            anchor_y="center",
            font_name=_FONT,
            font_size=26,
        )
        self.cursor_item_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="bottom",
            font_name=_FONT,
            font_size=13,
            color=(245, 220, 140, 255),
        )
        self.cursor_item_icon = pyglet.sprite.Sprite(default_icon)
        self.held_item_icon = pyglet.sprite.Sprite(
            default_icon, batch=win.hud_batch, group=win.hud_fg_group
        )
        self.held_hand_sprite = pyglet.sprite.Sprite(
            create_hand_image(), batch=win.hud_batch, group=win.hud_fg_group
        )
        self.hud_status_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="bottom",
            font_name=_FONT,
            font_size=13,
            color=(245, 235, 210, 255),
            batch=win.hud_batch,
            group=win.hud_text_group,
        )
        self._inv_status_label = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            font_name=_FONT,
            font_size=13,
            color=(160, 180, 215, 255),
        )

        # ── rendering ───────────────────────────────────────────────────────────

        self.hover_tooltip_bg = pyglet.shapes.BorderedRectangle(
            0,
            0,
            96,
            28,
            2,
            color=(18, 20, 28),
            border_color=(122, 126, 158),
        )
        self.hover_tooltip_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="center",
            font_name=_FONT,
            font_size=13,
            color=(245, 245, 245, 255),
        )

    def draw_hotbar(self) -> None:
        win = self.win
        if win.inventory_open:
            for s in self.hotbar_slots:
                s.visible = False
            for s in self.hotbar_icons:
                s.visible = False
            for s in self.hotbar_count_labels:
                s.visible = False
            for s in self.hotbar_key_labels:
                s.visible = False
            return
        for s in self.hotbar_slots:
            s.visible = True
        for s in self.hotbar_icons:
            s.visible = True
        for s in self.hotbar_count_labels:
            s.visible = True
        for s in self.hotbar_key_labels:
            s.visible = True

        slot_size = 52
        start_x = win.width // 2 - (slot_size * 9) // 2
        hovered_index = self.hotbar_slot_at(win.mouse_x, win.mouse_y)
        for index, shape in enumerate(self.hotbar_slots):
            stack = win.inventory[index]
            x = start_x + index * slot_size
            self._draw_item_slot(
                shape,
                self.hotbar_icons[index],
                self.hotbar_count_labels[index],
                stack,
                x,
                16,
                slot_size,
                selected=index == win.hotbar.selected_index,
                hovered=index == hovered_index,
            )
            key_label = self.hotbar_key_labels[index]
            key_label.x = x + 4
            key_label.y = 64
            if getattr(key_label, "batch", None) is None:
                key_label.draw()

    def draw_health(self) -> None:
        win = self.win
        if win.inventory_open:
            for s in self.heart_sprites:
                s.visible = False
            return
        for s in self.heart_sprites:
            s.visible = True
        start_x = win.width // 2 - (52 * 9) // 2
        for index, sprite in enumerate(self.heart_sprites):
            remaining = win.player_health - index * 2.0
            state = 2 if remaining >= 2.0 else 1 if remaining > 0.0 else 0
            sprite.image = self.heart_images[state]
            sprite.x = start_x + index * (HEART_SIZE + 2)
            sprite.y = 74
            if getattr(sprite, "batch", None) is None:
                sprite.draw()

    def draw_held_item(self) -> None:
        self.held_hand_sprite.visible = False
        self.held_item_icon.visible = False

    def update_hud_status(self) -> None:
        win = self.win
        if win.inventory_status and not win.inventory_open:
            self.hud_status_label.visible = True
            self.hud_status_label.text = win.inventory_status
            self.hud_status_label.x = 20
            self.hud_status_label.y = 112 if win.text_input is not None else 82
        else:
            self.hud_status_label.visible = False

    def draw_inventory(self) -> None:
        win = self.win
        center_x = win.width // 2
        center_y = win.height // 2
        self.inventory_panel.x = center_x - 270
        self.inventory_panel.y = center_y - 270
        self.inventory_panel.height = 540
        self.inventory_panel.draw()
        self.inventory_title.text = "INVENTORY"
        self.inventory_title.x = center_x
        self.inventory_title.y = center_y + 218
        self.inventory_title.draw()
        hovered_inventory_index = self.slot_at(win.mouse_x, win.mouse_y)
        hovered_crafting_index = self.crafting_slot_at(win.mouse_x, win.mouse_y)
        hovered_result = self.crafting_result_at(win.mouse_x, win.mouse_y)
        display_indices = (*range(9, len(win.inventory)), *range(9))
        for display_index, index in enumerate(display_indices):
            x, y = self._inventory_slot_position(display_index)
            self._draw_item_slot(
                self.inventory_slots[index],
                self.inventory_icons[index],
                self.inventory_count_labels[index],
                win.inventory[index],
                x,
                y,
                48,
                selected=index == win.hotbar.selected_index,
                hovered=index == hovered_inventory_index,
            )
        craft_origin_x, craft_origin_y = self._crafting_origin()
        self.crafting_label.text = f"CRAFTING {win.crafting_grid_size}x{win.crafting_grid_size}"
        self.crafting_label.x = craft_origin_x
        self.crafting_label.y = craft_origin_y + 58
        self.crafting_label.draw()
        for index in range(9):
            visible = index < len(win.crafting_grid)
            self.crafting_icons[index].visible = False
            self.crafting_count_labels[index].text = ""
            if not visible:
                continue
            x, y = self._crafting_slot_position(index)
            self._draw_item_slot(
                self.crafting_slots[index],
                self.crafting_icons[index],
                self.crafting_count_labels[index],
                win.crafting_grid[index],
                x,
                y,
                48,
                hovered=index == hovered_crafting_index,
            )
        result_x, result_y = self._crafting_result_position()
        result_stack = self.crafting_result_stack()
        self._draw_item_slot(
            self.crafting_result_slot,
            self.crafting_result_icon,
            self.crafting_result_count,
            result_stack,
            result_x,
            result_y,
            56,
            selected=result_stack is not None,
            hovered=hovered_result,
        )
        self.crafting_arrow.x = result_x - 50
        self.crafting_arrow.y = result_y + 28
        self.crafting_arrow.draw()
        self._inv_status_label.text = win.inventory_status
        self._inv_status_label.x = center_x
        self._inv_status_label.y = center_y - 270
        self._inv_status_label.draw()
        if win.cursor_stack is not None:
            definition = win.item_registry.by_id(win.cursor_stack.item_id)
            self.cursor_item_icon.image = self.item_icon_images[win.cursor_stack.item_id]
            self.cursor_item_icon.scale = 38 / ICON_SIZE
            self.cursor_item_icon.x = win.mouse_x + 8
            self.cursor_item_icon.y = win.mouse_y + 8
            self.cursor_item_icon.draw()
            self.cursor_item_label.text = (
                f"{definition.name} {win.cursor_stack.count}"
                if win.cursor_stack.count > 1
                else definition.name
            )
            self.cursor_item_label.x = win.mouse_x + 48
            self.cursor_item_label.y = win.mouse_y + 10
            self.cursor_item_label.draw()
        else:
            self._draw_hover_tooltip()

    def _draw_item_slot(
        self,
        shape: pyglet.shapes.BorderedRectangle,
        icon: pyglet.sprite.Sprite,
        count_label: pyglet.text.Label,
        stack: ItemStack | None,
        x: int,
        y: int,
        size: int,
        *,
        selected: bool = False,
        hovered: bool = False,
    ) -> None:
        shape.x = x
        shape.y = y
        shape.width = size
        shape.height = size
        if selected:
            shape.color = (84, 90, 108, 255)
            shape.border_color = (255, 245, 135, 255)
        elif hovered:
            shape.color = (76, 82, 98, 255)
            shape.border_color = (205, 215, 235, 255)
        else:
            shape.color = (58, 63, 76, 255)
            shape.border_color = (125, 136, 154, 255)
        if getattr(shape, "batch", None) is None:
            shape.draw()
        if stack is None:
            icon.visible = False
            count_label.text = ""
            return
        icon.visible = True
        icon.image = self.item_icon_images[stack.item_id]
        icon.scale = (size - 12) / ICON_SIZE
        icon.x = x + 6
        icon.y = y + 6
        if getattr(icon, "batch", None) is None:
            icon.draw()
        count_label.text = str(stack.count) if stack.count > 1 else ""
        count_label.x = x + size - 4
        count_label.y = y + 2
        if getattr(count_label, "batch", None) is None:
            count_label.draw()

    # ── hit testing ─────────────────────────────────────────────────────────

    def hotbar_slot_at(self, x: int, y: int) -> int | None:
        slot_size = 52
        start_x = self.win.width // 2 - (slot_size * 9) // 2
        if not (16 <= y <= 16 + slot_size):
            return None
        index = (x - start_x) // slot_size
        if 0 <= index < 9 and start_x + index * slot_size <= x <= start_x + (index + 1) * slot_size:
            return int(index)
        return None

    def hovered_stack_at(self, x: int, y: int) -> ItemStack | None:
        if self.win.inventory_open:
            inventory_index = self.slot_at(x, y)
            if inventory_index is not None:
                return self.win.inventory[inventory_index]
            crafting_index = self.crafting_slot_at(x, y)
            if crafting_index is not None:
                return self.win.crafting_grid[crafting_index]
            if self.crafting_result_at(x, y):
                return self.crafting_result_stack()
            return None
        hotbar_index = self.hotbar_slot_at(x, y)
        if hotbar_index is None:
            return None
        return self.win.inventory[hotbar_index]

    def _draw_hover_tooltip(self) -> None:
        stack = self.hovered_stack_at(self.win.mouse_x, self.win.mouse_y)
        if stack is None:
            return
        definition = self.win.item_registry.by_id(stack.item_id)
        text = definition.name if stack.count == 1 else f"{definition.name} x{stack.count}"
        width = max(96, len(text) * 8 + 18)
        x = min(self.win.mouse_x + 14, self.win.width - width - 8)
        y = min(self.win.mouse_y + 24, self.win.height - 34)
        x = max(8, x)
        y = max(8, y)
        self.hover_tooltip_bg.x = x
        self.hover_tooltip_bg.y = y
        self.hover_tooltip_bg.width = width
        self.hover_tooltip_bg.height = 28
        self.hover_tooltip_bg.draw()
        self.hover_tooltip_label.text = text
        self.hover_tooltip_label.x = x + 9
        self.hover_tooltip_label.y = y + 14
        self.hover_tooltip_label.draw()

    def slot_at(self, x: int, y: int) -> int | None:
        display_indices = (*range(9, len(self.win.inventory)), *range(9))
        for display_index, index in enumerate(display_indices):
            slot_x, slot_y = self._inventory_slot_position(display_index)
            if slot_x <= x <= slot_x + 48 and slot_y <= y <= slot_y + 48:
                return index
        return None

    def crafting_slot_at(self, x: int, y: int) -> int | None:
        for index in range(len(self.win.crafting_grid)):
            slot_x, slot_y = self._crafting_slot_position(index)
            if slot_x <= x <= slot_x + 48 and slot_y <= y <= slot_y + 48:
                return index
        return None

    def crafting_result_at(self, x: int, y: int) -> bool:
        slot_x, slot_y = self._crafting_result_position()
        return slot_x <= x <= slot_x + 56 and slot_y <= y <= slot_y + 56

    def crafting_result_stack(self) -> ItemStack | None:
        self._sync_to_inv()
        return self.win._inv.crafting_result()

    # ── position helpers ─────────────────────────────────────────────────────

    def _inventory_slot_position(self, display_index: int) -> tuple[int, int]:
        win = self.win
        row, column = divmod(display_index, win.inventory.width)
        start_x = win.width // 2 - 232
        start_y = win.height // 2 - (15 if win.crafting_grid_size == 2 else 70)
        y = start_y - row * 52
        if row == 3:
            y -= 10
        return start_x + column * 52, y

    def _crafting_origin(self) -> tuple[int, int]:
        return self.win.width // 2 - 220, self.win.height // 2 + 90

    def _crafting_slot_position(self, index: int) -> tuple[int, int]:
        win = self.win
        row, column = divmod(index, win.crafting_grid_size)
        origin_x, origin_y = self._crafting_origin()
        return origin_x + column * 52, origin_y - row * 52

    def _crafting_result_position(self) -> tuple[int, int]:
        _origin_x, origin_y = self._crafting_origin()
        return self.win.width // 2 + 135, origin_y - (self.win.crafting_grid_size - 1) * 26

    # ── actions ─────────────────────────────────────────────────────────────

    def open(self, grid_size: int) -> None:
        self._sync_to_inv()
        self.win._inv.open(grid_size)
        self._sync_from_inv()

    def close(self) -> None:
        self._sync_to_inv()
        self.win._inv.close(self._return_or_drop_stack)
        self._sync_from_inv()

    def handle_crafting_click(self, index: int, button: int) -> None:
        self._sync_to_inv()
        self.win._inv.handle_crafting_click(index, button)
        self._sync_from_inv()

    def take_crafting_result(self) -> None:
        self._sync_to_inv()
        self.win._inv.take_crafting_result()
        self._sync_from_inv()

    def handle_inventory_click(self, index: int, button: int, *, quick_move: bool) -> None:
        self._sync_to_inv()
        self.win._inv.handle_inventory_click(index, button, quick_move=quick_move)
        self._sync_from_inv()

    def drop_selected_item(self) -> None:
        win = self.win
        stack = win.inventory.take_from_slot(win.hotbar.selected_index)
        if stack is None:
            return
        direction = win.camera.direction
        position = (
            win.camera.position[0] + direction[0] * 1.5,
            win.camera.position[1] + direction[1] * 1.5,
            win.camera.position[2] + direction[2] * 1.5,
        )
        win.entities.spawn_item(position, stack)
        win.inventory_status = f"Dropped {win.item_registry.by_id(stack.item_id).name}"

    def _return_or_drop_stack(self, stack: ItemStack) -> None:
        win = self.win
        remainder = win.inventory.add(stack, win.item_registry)
        if remainder is not None:
            win.entities.spawn_item(
                (win.player.x, win.player.y + 0.5, win.player.z),
                remainder,
            )

    # ── sync helpers ─────────────────────────────────────────────────────────

    def _sync_to_inv(self) -> None:
        win = self.win
        win._inv_state.crafting_grid = win.crafting_grid
        win._inv_state.crafting_grid_size = win.crafting_grid_size
        win._inv_state.cursor_stack = win.cursor_stack
        win._inv_state.inventory_open = win.inventory_open
        win._inv_state.status = win.inventory_status

    def _sync_from_inv(self) -> None:
        win = self.win
        win.crafting_grid = win._inv_state.crafting_grid
        win.crafting_grid_size = win._inv_state.crafting_grid_size
        win.cursor_stack = win._inv_state.cursor_stack
        win.inventory_open = win._inv_state.inventory_open
        win.inventory_status = win._inv_state.status
