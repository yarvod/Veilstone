"""Tests for InputHandler — extracted input event controller."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from pyglet.window import key, mouse

from voxel_sandbox.render.input_state import InputHandler, KeyState
from voxel_sandbox.render.ui.menu import Screen
from voxel_sandbox.render.ui.text_input import TextInput, TextPurpose


def _make_win(*, in_game: bool = True, screen: Screen = Screen.SINGLEPLAYER) -> MagicMock:
    """Build a minimal GameWindow mock suitable for InputHandler tests."""
    win = MagicMock()
    win.rebinding_action = None
    win.text_input = None
    win.menu.in_game = in_game
    win.menu.screen = screen
    win.inventory_open = False
    win.mouse_captured = False
    win.debug_overlay_visible = False
    win.world_list_items = []
    win.world_list_index = 0
    win.key_state = KeyState()
    return win


class TestOnKeyPress:
    def test_none_symbol_is_ignored(self):
        win = _make_win()
        h = InputHandler(win)
        h.on_key_press(None, 0)
        win._apply_rebind.assert_not_called()

    def test_rebinding_delegates_to_apply_rebind(self):
        win = _make_win()
        win.rebinding_action = "move_forward"
        h = InputHandler(win)
        h.on_key_press(key.W, 0)
        win._apply_rebind.assert_called_once_with(key.W)

    def test_text_input_enter_submits(self):
        win = _make_win()
        win.text_input = MagicMock(spec=TextInput)
        h = InputHandler(win)
        h.on_key_press(key.ENTER, 0)
        win.menu_ui._submit_text_input.assert_called_once()

    def test_text_input_escape_clears(self):
        win = _make_win()
        win.text_input = MagicMock(spec=TextInput)
        h = InputHandler(win)
        h.on_key_press(key.ESCAPE, 0)
        assert win.text_input is None
        win._sync_mouse_capture.assert_called_once()

    def test_text_input_backspace_calls_backspace(self):
        win = _make_win()
        win.text_input = MagicMock(spec=TextInput)
        h = InputHandler(win)
        h.on_key_press(key.BACKSPACE, 0)
        win.text_input.backspace.assert_called_once()

    def test_menu_up_navigates_selection(self):
        win = _make_win(in_game=False, screen=Screen.MAIN)
        h = InputHandler(win)
        h.on_key_press(key.UP, 0)
        win.menu.move_selection.assert_called_once_with(-1)
        win.menu_ui._play_ui_sound.assert_called_once()

    def test_menu_down_navigates_selection(self):
        win = _make_win(in_game=False, screen=Screen.MAIN)
        h = InputHandler(win)
        h.on_key_press(key.DOWN, 0)
        win.menu.move_selection.assert_called_once_with(1)

    def test_menu_enter_activates_item(self):
        win = _make_win(in_game=False, screen=Screen.MAIN)
        h = InputHandler(win)
        h.on_key_press(key.ENTER, 0)
        win.menu_ui._handle_menu_command.assert_called_once_with(win.menu.activate.return_value)

    def test_menu_singleplayer_enter_loads_selected_world(self):
        win = _make_win(in_game=False, screen=Screen.SINGLEPLAYER)
        from pathlib import Path
        win.world_list_items = [("TestWorld", Path("/tmp/test"))]
        win.world_list_index = 0
        h = InputHandler(win)
        h.on_key_press(key.ENTER, 0)
        win.load_world.assert_called_once_with("TestWorld")

    def test_menu_escape_calls_back(self):
        win = _make_win(in_game=False, screen=Screen.MAIN)
        h = InputHandler(win)
        h.on_key_press(key.ESCAPE, 0)
        win.menu.back.assert_called_once()
        win.menu_ui._play_ui_sound.assert_called_once()

    def test_e_opens_inventory_when_closed(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.E, 0)
        win._inv_ctrl.open.assert_called_once_with(2)
        win.key_state.press(key.E)  # shouldn't error; key_state cleared
        win._sync_mouse_capture.assert_called_once()

    def test_e_closes_inventory_when_open(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        h = InputHandler(win)
        h.on_key_press(key.E, 0)
        win._inv_ctrl.close.assert_called_once()

    def test_inventory_escape_closes(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        h = InputHandler(win)
        h.on_key_press(key.ESCAPE, 0)
        win._inv_ctrl.close.assert_called_once()
        win._sync_mouse_capture.assert_called_once()

    def test_inventory_c_takes_crafting_result(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        h = InputHandler(win)
        h.on_key_press(key.C, 0)
        win._inv_ctrl.take_crafting_result.assert_called_once()

    def test_inventory_digit_selects_hotbar(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        h = InputHandler(win)
        h.on_key_press(ord("3"), 0)
        win.hotbar.select.assert_called_once_with(2)

    def test_in_game_escape_calls_menu_back(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.ESCAPE, 0)
        win.menu.back.assert_called_once()
        win._sync_mouse_capture.assert_called_once()

    def test_f3_toggles_debug_overlay(self):
        win = _make_win(in_game=True)
        win.debug_overlay_visible = False
        h = InputHandler(win)
        h.on_key_press(key.F3, 0)
        assert win.debug_overlay_visible is True

    def test_hotbar_digit_selects_slot(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(ord("1"), 0)
        win.hotbar.select.assert_called_once_with(0)

    def test_q_drops_item(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.Q, 0)
        win._inv_ctrl.drop_selected_item.assert_called_once()

    def test_t_begins_chat_input(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.T, 0)
        win._begin_text_input.assert_called_once_with(
            TextPurpose.CHAT, "Chat message", maximum_length=256
        )

    def test_slash_begins_command_input(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.SLASH, 0)
        win._begin_text_input.assert_called_once_with(
            TextPurpose.COMMAND, "Command (/help)", initial="/", maximum_length=256
        )

    def test_unknown_key_presses_into_key_state(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.SPACE, 0)
        assert win.key_state.is_pressed(key.SPACE)


class TestOnText:
    def test_appends_to_text_input(self):
        win = _make_win()
        win.text_input = MagicMock(spec=TextInput)
        win.text_input.purpose = TextPurpose.CHAT
        win.text_input.value = ""
        h = InputHandler(win)
        h.on_text("a")
        win.text_input.append.assert_called_once_with("a")

    def test_ignores_when_no_text_input(self):
        win = _make_win()
        h = InputHandler(win)
        h.on_text("a")  # should not raise

    def test_skips_duplicate_slash_in_command(self):
        win = _make_win()
        win.text_input = MagicMock(spec=TextInput)
        win.text_input.purpose = TextPurpose.COMMAND
        win.text_input.value = "/"
        h = InputHandler(win)
        h.on_text("/")
        win.text_input.append.assert_not_called()


class TestOnKeyRelease:
    def test_releases_key_from_state(self):
        win = _make_win()
        win.key_state.press(key.W)
        h = InputHandler(win)
        h.on_key_release(key.W, 0)
        assert not win.key_state.is_pressed(key.W)


class TestOnDeactivate:
    def test_clears_key_state(self):
        win = _make_win()
        win.key_state.press(key.W)
        h = InputHandler(win)
        h.on_deactivate()
        assert not win.key_state.is_pressed(key.W)

    def test_releases_mouse_capture(self):
        win = _make_win()
        win.mouse_captured = True
        h = InputHandler(win)
        h.on_deactivate()
        assert win.mouse_captured is False
        win.set_exclusive_mouse.assert_called_with(False)

    def test_no_set_exclusive_if_not_captured(self):
        win = _make_win()
        win.mouse_captured = False
        h = InputHandler(win)
        h.on_deactivate()
        win.set_exclusive_mouse.assert_not_called()


class TestOnActivate:
    def test_syncs_mouse_capture(self):
        win = _make_win()
        h = InputHandler(win)
        h.on_activate()
        win._sync_mouse_capture.assert_called_once()


class TestOnMouseScroll:
    def test_cycles_hotbar_up(self):
        win = _make_win(in_game=True)
        win.menu.in_game = True
        win.menu.screen = Screen.GAME
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, 1)
        win.hotbar.cycle.assert_called_once_with(-1)

    def test_cycles_hotbar_down(self):
        win = _make_win(in_game=True)
        win.menu.in_game = True
        win.menu.screen = Screen.GAME
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, -1)
        win.hotbar.cycle.assert_called_once_with(1)

    def test_no_cycle_when_inventory_open(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, 1)
        win.hotbar.cycle.assert_not_called()

    def test_no_cycle_when_text_input_active(self):
        win = _make_win(in_game=True)
        win.text_input = MagicMock()
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, 1)
        win.hotbar.cycle.assert_not_called()

    def test_singleplayer_scroll_navigates_world_list(self):
        win = _make_win(in_game=False, screen=Screen.SINGLEPLAYER)
        win.menu.screen = Screen.SINGLEPLAYER
        win.world_list_items = [("a", None), ("b", None), ("c", None)]
        win.world_list_index = 1
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, 1)
        assert win.world_list_index == 0

    def test_singleplayer_scroll_down_navigates_world_list(self):
        win = _make_win(in_game=False, screen=Screen.SINGLEPLAYER)
        win.menu.screen = Screen.SINGLEPLAYER
        win.world_list_items = [("a", None), ("b", None), ("c", None)]
        win.world_list_index = 1
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, -1)
        assert win.world_list_index == 2


class TestOnMouseMotion:
    def test_updates_mouse_position(self):
        win = _make_win(in_game=True)
        win.mouse_captured = True
        h = InputHandler(win)
        h.on_mouse_motion(100, 200, 5, 10)
        assert win.mouse_x == 100
        assert win.mouse_y == 200

    def test_rotates_camera_when_captured(self):
        win = _make_win(in_game=True)
        win.mouse_captured = True
        h = InputHandler(win)
        h.on_mouse_motion(0, 0, 3, 4)
        win.camera.rotate.assert_called_once_with(
            3.0, 4.0, win.settings.camera.mouse_sensitivity
        )

    def test_no_rotation_when_not_captured(self):
        win = _make_win(in_game=True)
        win.mouse_captured = False
        h = InputHandler(win)
        h.on_mouse_motion(0, 0, 3, 4)
        win.camera.rotate.assert_not_called()

    def test_no_rotation_when_text_input_active(self):
        win = _make_win(in_game=True)
        win.mouse_captured = True
        win.text_input = MagicMock()
        h = InputHandler(win)
        h.on_mouse_motion(0, 0, 3, 4)
        win.camera.rotate.assert_not_called()
