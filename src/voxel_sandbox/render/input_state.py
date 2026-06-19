from __future__ import annotations

import logging
import sys
from dataclasses import replace
from typing import TYPE_CHECKING

from pyglet.window import key, mouse

from voxel_sandbox.app.settings import save_user_settings
from voxel_sandbox.engine.events import BlockBroken, BlockPlaced, EntityDamaged, EntityDied
from voxel_sandbox.render.ui.menu import Screen
from voxel_sandbox.render.ui.text_input import TextPurpose

if TYPE_CHECKING:
    from voxel_sandbox.render.window import GameWindow

LOGGER = logging.getLogger(__name__)


def macos_game_key_bindings() -> dict[int, int]:
    return {
        0x0D: ord("w"),
        0x00: ord("a"),
        0x01: ord("s"),
        0x02: ord("d"),
    }


def configure_layout_independent_game_keys() -> None:
    """Bind macOS physical letter positions used by gameplay controls."""
    if sys.platform != "darwin":
        return

    from pyglet.libs.darwin import quartzkey

    quartzkey.keymap.update(macos_game_key_bindings())


class KeyState:
    def __init__(self) -> None:
        self._pressed: set[int] = set()

    def press(self, symbol: int) -> None:
        self._pressed.add(symbol)

    def release(self, symbol: int) -> None:
        self._pressed.discard(symbol)

    def clear(self) -> None:
        self._pressed.clear()

    def is_pressed(self, symbol: int) -> bool:
        return symbol in self._pressed


class InputHandler:
    """Contains all input event logic, keeping GameWindow a thin coordinator."""

    def __init__(self, win: GameWindow) -> None:
        self.win = win

    def on_key_press(self, symbol: int | None, modifiers: int) -> None:
        del modifiers
        win = self.win
        if symbol is None:
            LOGGER.debug("Ignored key event without a symbol")
            return
        if win.rebinding_action is not None:
            self.apply_rebind(symbol)
            return
        if win.text_input is not None:
            if symbol in {key.ENTER, key.RETURN}:
                win.menu_ui._submit_text_input()
            elif symbol == key.ESCAPE:
                win.text_input = None
            elif symbol == key.BACKSPACE:
                win.text_input.backspace()
            win._sync_mouse_capture()
            return
        if not win.menu.in_game:
            if symbol in {key.UP, key.W}:
                if win.menu.screen is Screen.SINGLEPLAYER and win.menu_ui.world_list_items:
                    win.menu_ui.world_list_index = max(0, win.menu_ui.world_list_index - 1)
                else:
                    win.menu.move_selection(-1)
                win.menu_ui._play_ui_sound()
            elif symbol in {key.DOWN, key.S}:
                if win.menu.screen is Screen.SINGLEPLAYER and win.menu_ui.world_list_items:
                    win.menu_ui.world_list_index = min(
                        len(win.menu_ui.world_list_items) - 1, win.menu_ui.world_list_index + 1
                    )
                else:
                    win.menu.move_selection(1)
                win.menu_ui._play_ui_sound()
            elif symbol in {key.ENTER, key.RETURN, key.SPACE}:
                win.menu_ui._play_ui_sound()
                if (
                    win.menu.screen is Screen.SINGLEPLAYER
                    and win.menu_ui.world_list_items
                    and 0 <= win.menu_ui.world_list_index < len(win.menu_ui.world_list_items)
                ):
                    name, _ = win.menu_ui.world_list_items[win.menu_ui.world_list_index]
                    win._worlds.load_world(name)
                else:
                    win.menu_ui._handle_menu_command(win.menu.activate())
            elif symbol == key.ESCAPE:
                win.menu_ui._play_ui_sound()
                win.menu.back()
                win._sync_game_state()
            win._sync_mouse_capture()
            return
        if symbol == key.E:
            if win.inventory_open:
                win._inv_ctrl.close()
            else:
                win._inv_ctrl.open(2)
            win.key_state.clear()
            win._sync_mouse_capture()
            return
        if win.inventory_open:
            if symbol == key.ESCAPE:
                win._inv_ctrl.close()
                win._sync_mouse_capture()
            elif symbol == key.C:
                win._inv_ctrl.take_crafting_result()
            elif ord("1") <= symbol <= ord("9"):
                win.hotbar.select(symbol - ord("1"))
            return
        if symbol == key.ESCAPE:
            win.menu.back()
            win._sync_game_state()
            win._sync_mouse_capture()
            return
        if symbol == key.F5:
            win.debug_shader.reload(force=True)
            return
        if symbol == key.F3:
            win.debug_overlay_visible = not win.debug_overlay_visible
            return
        if symbol == key.F6:
            win.world_renderer.toggle_smooth_lighting()
            return
        if symbol == key.F7:
            win.world_renderer.toggle_ambient_occlusion()
            return
        if symbol == key.F8:
            win.world_renderer.toggle_fog()
            return
        if symbol == key.F9:
            win.world_renderer.toggle_mesher()
            return
        if ord("1") <= symbol <= ord("9"):
            win.hotbar.select(symbol - ord("1"))
            return
        if symbol == key.Q:
            win._inv_ctrl.drop_selected_item()
            return
        if symbol == key.T:
            win.menu_ui._begin_text_input(TextPurpose.CHAT, "Chat message", maximum_length=256)
            return
        if symbol == key.SLASH:
            win.menu_ui._begin_text_input(
                TextPurpose.COMMAND,
                "Command (/help)",
                initial="/",
                maximum_length=256,
            )
            return
        win.key_state.press(symbol)

    def on_text(self, text: str) -> None:
        win = self.win
        if win.text_input is not None:
            if (
                win.text_input.purpose is TextPurpose.COMMAND
                and win.text_input.value == "/"
                and text == "/"
            ):
                return
            win.text_input.append(text)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        del modifiers
        self.win.key_state.release(symbol)

    def on_deactivate(self) -> None:
        win = self.win
        win.key_state.clear()
        if win.mouse_captured:
            win.mouse_captured = False
            win.set_exclusive_mouse(False)

    def on_activate(self) -> None:
        self.win._sync_mouse_capture()

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        win = self.win
        if win.text_input is not None:
            return
        if not win.menu.in_game:
            if (
                hasattr(win, "ui_renderer")
                and win.ui_renderer
                and win.ui_renderer.on_mouse_press(x, y, button, modifiers)
            ):
                win.menu_ui._play_ui_sound()
            return
        if win.menu.in_game and win.inventory_open:
            crafting_slot = win._inv_ctrl.crafting_slot_at(x, y)
            if crafting_slot is not None:
                win._inv_ctrl.handle_crafting_click(crafting_slot, button)
            elif win._inv_ctrl.crafting_result_at(x, y):
                win._inv_ctrl.take_crafting_result()
            elif (slot := win._inv_ctrl.slot_at(x, y)) is not None:
                win._inv_ctrl.handle_inventory_click(
                    slot,
                    button,
                    quick_move=bool(modifiers & key.MOD_SHIFT),
                )
            return
        if not win.menu.in_game or not win.mouse_captured or win.inventory_open:
            return
        if button == mouse.LEFT:
            target = win.entities.target_mob(win.camera.position, win.camera.direction)
            if target is not None:
                kind = win.entities.world.mob_ai[target].kind.value
                position = win.entities.world.transforms[target].position
                drops = win.entities.damage(target, 4.0, win.player.eye_position)
                if drops:
                    win.events.publish(EntityDied(target, kind, position))
                else:
                    win.events.publish(EntityDamaged(target, kind, position, 4.0))
                win.inventory_status = "Mob defeated" if drops else "Hit mob"
                return
        hit = win.world_renderer.raycast(win.camera.position, win.camera.direction)
        structure_hit = win.structure_world.raycast_entity(
            win.camera.position,
            win.camera.direction,
        )
        if (
            button == mouse.RIGHT
            and structure_hit is not None
            and (hit is None or structure_hit[1] < hit.distance)
        ):
            win._net.toggle_structure(structure_hit[0])
            return
        if hit is None:
            return
        if button == mouse.LEFT:
            block_id = win.world_renderer.get_block(*hit.block)
            if win.world_renderer.registry.by_id(block_id).is_fluid:
                win.inventory_status = "Water cannot be mined"
                return
            if win.world_renderer.set_block(hit.block, 0):
                win.events.publish(BlockBroken(block_id, hit.block))
                win._net.send_block_action(hit.block, 0)
                drop = win.item_registry.drop_for_block(block_id)
                if drop is not None:
                    win.entities.spawn_item(
                        (
                            float(hit.block[0]) + 0.5,
                            float(hit.block[1]) + 0.5,
                            float(hit.block[2]) + 0.5,
                        ),
                        drop,
                    )
        elif button == mouse.RIGHT:
            if win.world_renderer.get_block(*hit.block) == 10:
                win._inv_ctrl.open(3)
                win._sync_mouse_capture()
                return
            selected = win.hotbar.selected
            if selected is None or win.player.intersects_block(hit.previous):
                return
            definition = win.item_registry.by_id(selected.item_id)
            if definition.block_id is None:
                return
            if win.world_renderer.set_block(hit.previous, definition.block_id):
                win.events.publish(BlockPlaced(definition.block_id, hit.previous))
                win._net.send_block_action(hit.previous, definition.block_id)
                win.inventory.take_from_slot(win.hotbar.selected_index)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        del x, y, scroll_x
        win = self.win
        if win.text_input is not None:
            return
        if win.menu.screen is Screen.SINGLEPLAYER:
            if scroll_y > 0:
                win.menu_ui.world_list_index = max(0, win.menu_ui.world_list_index - 1)
            elif scroll_y < 0:
                win.menu_ui.world_list_index = min(
                    max(0, len(win.menu_ui.world_list_items) - 1), win.menu_ui.world_list_index + 1
                )
            return
        if win.menu.in_game and not win.inventory_open and scroll_y:
            win.hotbar.cycle(-1 if scroll_y > 0 else 1)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> None:
        win = self.win
        if not win.menu.in_game and hasattr(win, "ui_renderer") and win.ui_renderer:
            win.ui_renderer.on_mouse_release(x, y, button, modifiers)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        win = self.win
        win.mouse_x = x
        win.mouse_y = y
        if win.text_input is not None:
            return
        if (
            not win.menu.in_game
            and hasattr(win, "ui_renderer")
            and win.ui_renderer
            and win.ui_renderer.on_mouse_motion(x, y, dx, dy)
        ):
            return
        if win.mouse_captured:
            win.camera.rotate(
                float(dx),
                float(dy),
                win.settings.camera.mouse_sensitivity,
            )

    def apply_rebind(self, symbol: int) -> None:
        win = self.win
        action = win.rebinding_action
        if action is None:
            return
        conflict = next(
            (name for name, bound_symbol in win.control_bindings.items() if bound_symbol == symbol),
            None,
        )
        if conflict is not None and conflict != action:
            win.menu.status = f"Key already assigned to {conflict}."
            win.rebinding_action = None
            return
        name = key.symbol_string(symbol)
        controls = win.settings.controls
        if action == "forward":
            controls = replace(controls, forward=name)
        elif action == "backward":
            controls = replace(controls, backward=name)
        elif action == "left":
            controls = replace(controls, left=name)
        elif action == "right":
            controls = replace(controls, right=name)
        else:
            controls = replace(controls, jump=name)
        win.settings = replace(win.settings, controls=controls)
        win.control_bindings[action] = symbol
        win.rebinding_action = None
        win.menu.status = f"{action.title()} bound to {name}."
        save_user_settings(win.settings)
