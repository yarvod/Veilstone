from __future__ import annotations

import logging
import sys
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Protocol, cast

from voxel_sandbox.app.settings import save_user_settings
from voxel_sandbox.application.player_animation import PlayerInteraction
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.events import (
    BlockBroken,
    BlockInteractionStarted,
    BlockPlaced,
    EntityDamaged,
    EntityDied,
)
from voxel_sandbox.render.ui.menu import Screen
from voxel_sandbox.render.ui.text_input import TextPurpose

key: Any
mouse: Any

try:
    from pyglet.window import key as _pyglet_key
    from pyglet.window import mouse as _pyglet_mouse

    key = cast(Any, _pyglet_key)
    mouse = cast(Any, _pyglet_mouse)
except (ImportError, IndexError):

    class _FallbackKey:
        BACKSPACE = 8
        C = ord("C")
        DOWN = 1002
        E = ord("E")
        ENTER = 13
        ESCAPE = 27
        F1 = 2001
        F2 = 2002
        F3 = 2003
        F5 = 2005
        F6 = 2006
        F7 = 2007
        F8 = 2008
        F9 = 2009
        MOD_CTRL = 2
        MOD_SHIFT = 1
        Q = ord("Q")
        RETURN = 13
        S = ord("S")
        SLASH = ord("/")
        SPACE = 32
        T = ord("T")
        UP = 1001
        W = ord("W")

        @staticmethod
        def symbol_string(symbol: int) -> str:
            return str(symbol)

    class _FallbackMouse:
        LEFT = 1
        RIGHT = 4

    key = _FallbackKey
    mouse = _FallbackMouse

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


class InventoryInputPort(Protocol):
    def open(self, grid_size: int) -> None: ...

    def close(self) -> None: ...

    def handle_crafting_click(
        self,
        index: int,
        button: int,
        *,
        quick_move: bool = False,
    ) -> None: ...

    def take_crafting_result(self, *, quick_move: bool = False) -> None: ...

    def handle_inventory_click(self, index: int, button: int, *, quick_move: bool) -> None: ...

    def drop_selected_item(self) -> None: ...

    def crafting_slot_at(self, x: int, y: int) -> int | None: ...

    def crafting_result_at(self, x: int, y: int) -> bool: ...

    def slot_at(self, x: int, y: int) -> int | None: ...


class NetworkInputPort(Protocol):
    def toggle_structure(self, structure: object) -> None: ...

    def send_block_action(self, position: object, block_id: int) -> None: ...


class InputView(Protocol):
    rebinding_action: str | None
    text_input: Any | None
    menu: Any
    menu_ui: Any
    key_state: KeyState
    inventory_open: bool
    settings: Any
    mouse_captured: bool
    ui_renderer: Any
    cursor_stack: Any
    entities: Any
    camera: Any
    world_renderer: Any
    structure_world: Any
    world_runtime: Any
    block_registry: BlockRegistry
    control_bindings: Any
    events: Any
    event_bus: Any
    inventory: Any
    inventory_status: str
    item_registry: Any
    player: Any
    mouse_x: int
    mouse_y: int
    inventory_input: InventoryInputPort
    network_input: NetworkInputPort

    def submit_text_input(self) -> None: ...

    def sync_mouse_capture(self) -> None: ...

    def play_ui_sound(self) -> None: ...

    def load_world(self, name: str) -> None: ...

    def handle_menu_command(self, command: object) -> None: ...

    def sync_game_state(self) -> None: ...

    def save_screenshot(self) -> object: ...

    def cycle_perspective(self) -> None: ...

    def toggle_debug_overlay(self) -> None: ...

    def toggle_hud_visibility(self) -> None: ...

    def reload_debug_shader(self) -> None: ...

    def select_hotbar_slot(self, slot: int) -> None: ...

    def selected_hotbar_stack(self) -> Any: ...

    def selected_hotbar_index(self) -> int: ...

    def cycle_hotbar(self, direction: int) -> None: ...

    def start_player_interaction(self, interaction: PlayerInteraction) -> None: ...

    def end_player_interaction(self) -> None: ...

    def set_exclusive_mouse(self, exclusive: bool) -> None: ...


class InputWindowAdapter:
    def __init__(self, window: GameWindow) -> None:
        object.__setattr__(self, "_window", window)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._window, name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._window, name, value)

    @property
    def inventory_input(self) -> InventoryInputPort:
        return cast(InventoryInputPort, object.__getattribute__(self._window, "_inv_ctrl"))

    @property
    def network_input(self) -> NetworkInputPort:
        return cast(NetworkInputPort, object.__getattribute__(self._window, "_net"))

    def submit_text_input(self) -> None:
        self._window.menu_ui._submit_text_input()

    def sync_mouse_capture(self) -> None:
        self._window._sync_mouse_capture()

    def play_ui_sound(self) -> None:
        self._window.menu_ui._play_ui_sound()

    def load_world(self, name: str) -> None:
        self._window._worlds.load_world(name)

    def handle_menu_command(self, command: object) -> None:
        self._window.menu_ui._handle_menu_command(command)

    def sync_game_state(self) -> None:
        self._window._sync_game_state()

    def toggle_debug_overlay(self) -> None:
        self._window.debug_overlay_visible = not self._window.debug_overlay_visible

    def toggle_hud_visibility(self) -> None:
        self._window.hud_hidden = not self._window.hud_hidden

    def reload_debug_shader(self) -> None:
        self._window.debug_shader.reload(force=True)

    def select_hotbar_slot(self, slot: int) -> None:
        self._window.hotbar.select(slot)

    def selected_hotbar_stack(self) -> Any:
        return self._window.hotbar.selected

    def selected_hotbar_index(self) -> int:
        return int(self._window.hotbar.selected_index)

    def cycle_hotbar(self, direction: int) -> None:
        self._window.hotbar.cycle(direction)


class InputHandler:
    """Contains all input event logic, keeping GameWindow a thin coordinator."""

    def __init__(self, win: InputView) -> None:
        self.win = win
        self._inventory_drag_button: int | None = None
        self._inventory_drag_start: tuple[int, int] | None = None
        self._inventory_drag_moved = False

    def on_key_press(self, symbol: int | None, modifiers: int) -> None:
        win = self.win
        if symbol is None:
            LOGGER.debug("Ignored key event without a symbol")
            return
        if win.rebinding_action is not None:
            self.apply_rebind(symbol)
            return
        if win.text_input is not None:
            if symbol in {key.ENTER, key.RETURN}:
                win.submit_text_input()
            elif symbol == key.ESCAPE:
                win.text_input = None
            elif symbol == key.BACKSPACE:
                win.text_input.backspace()
            win.sync_mouse_capture()
            return
        if not win.menu.in_game:
            if symbol in {key.UP, key.W}:
                if win.menu.screen is Screen.SINGLEPLAYER and win.menu_ui.world_list_items:
                    win.menu_ui.world_list_index = max(0, win.menu_ui.world_list_index - 1)
                else:
                    win.menu.move_selection(-1)
                win.play_ui_sound()
            elif symbol in {key.DOWN, key.S}:
                if win.menu.screen is Screen.SINGLEPLAYER and win.menu_ui.world_list_items:
                    win.menu_ui.world_list_index = min(
                        len(win.menu_ui.world_list_items) - 1, win.menu_ui.world_list_index + 1
                    )
                else:
                    win.menu.move_selection(1)
                win.play_ui_sound()
            elif symbol in {key.ENTER, key.RETURN, key.SPACE}:
                win.play_ui_sound()
                if (
                    win.menu.screen is Screen.SINGLEPLAYER
                    and win.menu_ui.world_list_items
                    and 0 <= win.menu_ui.world_list_index < len(win.menu_ui.world_list_items)
                ):
                    name, _ = win.menu_ui.world_list_items[win.menu_ui.world_list_index]
                    win.load_world(name)
                else:
                    win.handle_menu_command(win.menu.activate())
            elif symbol == key.ESCAPE:
                win.play_ui_sound()
                win.menu.back()
                win.sync_game_state()
            win.sync_mouse_capture()
            return
        if symbol == key.E:
            if win.inventory_open:
                win.inventory_input.close()
            else:
                win.inventory_input.open(2)
            win.key_state.clear()
            win.sync_mouse_capture()
            return
        if win.inventory_open:
            if symbol == key.ESCAPE:
                win.inventory_input.close()
                win.sync_mouse_capture()
            elif symbol == key.C:
                win.inventory_input.take_crafting_result()
            elif ord("1") <= symbol <= ord("9"):
                win.select_hotbar_slot(symbol - ord("1"))
            return
        if symbol == key.ESCAPE:
            win.menu.back()
            win.sync_game_state()
            win.sync_mouse_capture()
            return
        if symbol == key.F5 and modifiers & key.MOD_CTRL:
            win.reload_debug_shader()
            return
        if symbol == key.F5:
            win.cycle_perspective()
            return
        if symbol == key.F1:
            win.toggle_hud_visibility()
            return
        if symbol == key.F2:
            win.save_screenshot()
            return
        if symbol == key.F3:
            win.toggle_debug_overlay()
            return
        if ord("1") <= symbol <= ord("9"):
            win.select_hotbar_slot(symbol - ord("1"))
            return
        if symbol == key.Q:
            win.inventory_input.drop_selected_item()
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
        self.win.sync_mouse_capture()

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
                win.play_ui_sound()
            return
        if win.menu.in_game and win.inventory_open:
            self._inventory_drag_button = None
            self._inventory_drag_start = None
            self._inventory_drag_moved = False
            can_start_drag = button == mouse.LEFT and not bool(modifiers & key.MOD_SHIFT)
            crafting_slot = win.inventory_input.crafting_slot_at(x, y)
            if crafting_slot is not None:
                win.inventory_input.handle_crafting_click(
                    crafting_slot,
                    button,
                    quick_move=button == mouse.LEFT and bool(modifiers & key.MOD_SHIFT),
                )
            elif win.inventory_input.crafting_result_at(x, y):
                win.inventory_input.take_crafting_result(
                    quick_move=button == mouse.LEFT and bool(modifiers & key.MOD_SHIFT)
                )
            elif (slot := win.inventory_input.slot_at(x, y)) is not None:
                win.inventory_input.handle_inventory_click(
                    slot,
                    button,
                    quick_move=bool(modifiers & key.MOD_SHIFT),
                )
            if can_start_drag and win.cursor_stack is not None:
                self._inventory_drag_button = button
                self._inventory_drag_start = (x, y)
            return
        if not win.menu.in_game or not win.mouse_captured or win.inventory_open:
            return
        if button == mouse.LEFT:
            target = win.entities.target_mob(win.camera.position, win.camera.direction)
            if target is not None:
                win.start_player_interaction(PlayerInteraction.ATTACK)
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
            win.network_input.toggle_structure(structure_hit[0])
            return
        if hit is None:
            return
        if button == mouse.LEFT:
            block_id = win.world_renderer.get_block(*hit.block)
            block_registry = cast(BlockRegistry, win.world_runtime.block_registry)
            if block_registry.by_id(block_id).is_fluid:
                win.inventory_status = "Water cannot be mined"
                return
            if win.world_renderer.set_block(hit.block, 0):
                win.events.publish(
                    BlockInteractionStarted(
                        "break",
                        block_id,
                        hit.block,
                        hit.block,
                        hit.normal,
                    )
                )
                win.events.publish(BlockBroken(block_id, hit.block))
                win.network_input.send_block_action(hit.block, 0)
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
                win.inventory_input.open(3)
                win.sync_mouse_capture()
                return
            selected = win.selected_hotbar_stack()
            if selected is None or win.player.intersects_block(hit.previous):
                return
            definition = win.item_registry.by_id(selected.item_id)
            if definition.block_id is None:
                return
            if win.world_renderer.set_block(hit.previous, definition.block_id):
                win.events.publish(
                    BlockInteractionStarted(
                        "place",
                        definition.block_id,
                        hit.previous,
                        hit.block,
                        hit.normal,
                    )
                )
                win.events.publish(BlockPlaced(definition.block_id, hit.previous))
                win.network_input.send_block_action(hit.previous, definition.block_id)
                win.inventory.take_from_slot(win.selected_hotbar_index())

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
            win.cycle_hotbar(-1 if scroll_y > 0 else 1)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> None:
        win = self.win
        if (
            win.menu.in_game
            and win.inventory_open
            and button == self._inventory_drag_button
            and self._inventory_drag_moved
            and win.cursor_stack is not None
        ):
            crafting_slot = win.inventory_input.crafting_slot_at(x, y)
            if crafting_slot is not None:
                win.inventory_input.handle_crafting_click(crafting_slot, button)
            elif (slot := win.inventory_input.slot_at(x, y)) is not None:
                win.inventory_input.handle_inventory_click(slot, button, quick_move=False)
        self._inventory_drag_button = None
        self._inventory_drag_start = None
        self._inventory_drag_moved = False
        if not win.menu.in_game and hasattr(win, "ui_renderer") and win.ui_renderer:
            win.ui_renderer.on_mouse_release(x, y, button, modifiers)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        win = self.win
        win.mouse_x = x
        win.mouse_y = y
        if self._inventory_drag_start is not None:
            start_x, start_y = self._inventory_drag_start
            if abs(x - start_x) + abs(y - start_y) >= 8:
                self._inventory_drag_moved = True
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

    def on_mouse_drag(self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int) -> None:
        del buttons, modifiers
        self.on_mouse_motion(x, y, dx, dy)

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
