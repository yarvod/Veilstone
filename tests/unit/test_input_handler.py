"""Tests for InputHandler — extracted input event controller."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from voxel_sandbox.application.player_animation import PlayerInteraction
from voxel_sandbox.engine.events import (
    BlockBroken,
    BlockInteractionStarted,
    BlockPlaced,
    EventBus,
)
from voxel_sandbox.engine.physics.raycast import RaycastHit
from voxel_sandbox.render.input_state import InputHandler, KeyState, key, mouse
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
    win.menu_ui.world_list_items = []
    win.menu_ui.world_list_index = 0
    win.key_state = KeyState()
    win.submit_text_input = win.menu_ui._submit_text_input
    win.sync_mouse_capture = win._sync_mouse_capture
    win.play_ui_sound = win.menu_ui._play_ui_sound
    win.load_world = win._worlds.load_world
    win.handle_menu_command = win.menu_ui._handle_menu_command
    win.sync_game_state = win._sync_game_state
    win.toggle_debug_overlay.side_effect = lambda: setattr(
        win, "debug_overlay_visible", not win.debug_overlay_visible
    )
    win.toggle_hud_visibility.side_effect = lambda: setattr(win, "hud_hidden", not win.hud_hidden)
    win.inventory_input = win._inv_ctrl
    win.network_input = win._net
    return win


class TestOnKeyPress:
    def test_none_symbol_is_ignored(self):
        win = _make_win()
        win.rebinding_action = "forward"
        h = InputHandler(win)
        with patch.object(h, "apply_rebind") as mock_rebind:
            h.on_key_press(None, 0)
            mock_rebind.assert_not_called()

    def test_rebinding_delegates_to_apply_rebind(self):
        win = _make_win()
        win.rebinding_action = "forward"
        h = InputHandler(win)
        with patch.object(h, "apply_rebind") as mock_rebind:
            h.on_key_press(key.W, 0)
            mock_rebind.assert_called_once_with(key.W)

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

        win.menu_ui.world_list_items = [("TestWorld", Path("/tmp/test"))]
        win.menu_ui.world_list_index = 0
        h = InputHandler(win)
        h.on_key_press(key.ENTER, 0)
        win._worlds.load_world.assert_called_once_with("TestWorld")

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
        win.select_hotbar_slot.assert_called_once_with(2)

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
        win.toggle_debug_overlay.assert_called_once()
        assert win.debug_overlay_visible is True

    def test_f1_toggles_hud_hidden(self):
        win = _make_win(in_game=True)
        win.hud_hidden = False
        h = InputHandler(win)
        h.on_key_press(key.F1, 0)
        win.toggle_hud_visibility.assert_called_once()
        assert win.hud_hidden is True

    def test_f2_saves_screenshot(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.F2, 0)
        win.save_screenshot.assert_called_once()

    def test_f5_cycles_perspective(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.F5, 0)
        win.cycle_perspective.assert_called_once()

    def test_ctrl_f5_keeps_shader_reload_dev_binding(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.F5, key.MOD_CTRL)
        win.reload_debug_shader.assert_called_once()
        win.cycle_perspective.assert_not_called()

    def test_plain_graphics_function_keys_do_not_toggle_renderer_settings(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        for symbol in (key.F6, key.F7, key.F8, key.F9):
            h.on_key_press(symbol, 0)
        win.world_renderer.toggle_smooth_lighting.assert_not_called()
        win.world_renderer.toggle_ambient_occlusion.assert_not_called()
        win.world_renderer.toggle_fog.assert_not_called()
        win.world_renderer.toggle_mesher.assert_not_called()

    def test_ctrl_graphics_function_keys_do_not_toggle_renderer_settings(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.F6, key.MOD_CTRL)
        h.on_key_press(key.F7, key.MOD_CTRL)
        h.on_key_press(key.F8, key.MOD_CTRL)
        h.on_key_press(key.F9, key.MOD_CTRL)
        win.world_renderer.toggle_smooth_lighting.assert_not_called()
        win.world_renderer.toggle_ambient_occlusion.assert_not_called()
        win.world_renderer.toggle_fog.assert_not_called()
        win.world_renderer.toggle_mesher.assert_not_called()

    def test_hotbar_digit_selects_slot(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(ord("1"), 0)
        win.select_hotbar_slot.assert_called_once_with(0)

    def test_q_drops_item(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.Q, 0)
        win._inv_ctrl.drop_selected_item.assert_called_once()

    def test_t_begins_chat_input(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.T, 0)
        win.menu_ui._begin_text_input.assert_called_once_with(
            TextPurpose.CHAT, "Chat message", maximum_length=256
        )

    def test_slash_begins_command_input(self):
        win = _make_win(in_game=True)
        h = InputHandler(win)
        h.on_key_press(key.SLASH, 0)
        win.menu_ui._begin_text_input.assert_called_once_with(
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


class TestOnMousePress:
    def test_left_click_mob_starts_attack_interaction(self):
        win = _make_win(in_game=True)
        win.mouse_captured = True
        target = object()
        win.entities.target_mob.return_value = target
        win.entities.world.mob_ai = {target: MagicMock(kind=MagicMock(value="hostile"))}
        win.entities.world.transforms = {target: MagicMock(position=(1.0, 2.0, 3.0))}
        win.entities.damage.return_value = []
        h = InputHandler(win)

        h.on_mouse_press(0, 0, mouse.LEFT, 0)

        win.start_player_interaction.assert_called_once_with(PlayerInteraction.ATTACK)
        win.entities.damage.assert_called_once()

    def test_left_click_block_publishes_interaction_started_before_break(self):
        win = _make_win(in_game=True)
        win.mouse_captured = True
        win.events = EventBus()
        published: list[BlockInteractionStarted | BlockBroken] = []
        win.events.subscribe(BlockInteractionStarted, published.append)
        win.events.subscribe(BlockBroken, published.append)
        win.entities.target_mob.return_value = None
        win.structure_world.raycast_entity.return_value = None
        win.world_renderer.raycast.return_value = RaycastHit(
            block=(1, 2, 3),
            previous=(1, 2, 2),
            normal=(0, 0, -1),
            distance=2.0,
            block_id=4,
        )
        win.world_renderer.get_block.return_value = 4
        win.world_renderer.set_block.return_value = True
        win.world_runtime.block_registry.by_id.return_value = MagicMock(is_fluid=False)
        win.item_registry.drop_for_block.return_value = None

        h = InputHandler(win)
        h.on_mouse_press(0, 0, mouse.LEFT, 0)

        assert published == [
            BlockInteractionStarted("break", 4, (1, 2, 3), (1, 2, 3), (0, 0, -1)),
            BlockBroken(4, (1, 2, 3)),
        ]
        win.start_player_interaction.assert_not_called()

    def test_right_click_block_publishes_interaction_started_before_place(self):
        win = _make_win(in_game=True)
        win.mouse_captured = True
        win.events = EventBus()
        published: list[BlockInteractionStarted | BlockPlaced] = []
        win.events.subscribe(BlockInteractionStarted, published.append)
        win.events.subscribe(BlockPlaced, published.append)
        win.entities.target_mob.return_value = None
        win.structure_world.raycast_entity.return_value = None
        win.world_renderer.raycast.return_value = RaycastHit(
            block=(1, 2, 3),
            previous=(1, 2, 2),
            normal=(0, 0, -1),
            distance=2.0,
            block_id=4,
        )
        win.world_renderer.get_block.return_value = 4
        win.world_renderer.set_block.return_value = True
        win.selected_hotbar_stack.return_value = MagicMock(item_id="oak_planks")
        win.selected_hotbar_index.return_value = 2
        win.player.intersects_block.return_value = False
        win.item_registry.by_id.return_value = MagicMock(block_id=5)

        h = InputHandler(win)
        h.on_mouse_press(0, 0, mouse.RIGHT, 0)

        assert published == [
            BlockInteractionStarted("place", 5, (1, 2, 2), (1, 2, 3), (0, 0, -1)),
            BlockPlaced(5, (1, 2, 2)),
        ]
        win.inventory.take_from_slot.assert_called_once_with(2)
        win.start_player_interaction.assert_not_called()


class TestOnMouseScroll:
    def test_cycles_hotbar_up(self):
        win = _make_win(in_game=True)
        win.menu.in_game = True
        win.menu.screen = Screen.GAME
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, 1)
        win.cycle_hotbar.assert_called_once_with(-1)

    def test_cycles_hotbar_down(self):
        win = _make_win(in_game=True)
        win.menu.in_game = True
        win.menu.screen = Screen.GAME
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, -1)
        win.cycle_hotbar.assert_called_once_with(1)

    def test_no_cycle_when_inventory_open(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, 1)
        win.cycle_hotbar.assert_not_called()


class TestInventoryDrag:
    def test_right_drag_distributes_once_per_distinct_inventory_slot(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win.cursor_stack = object()
        win._inv_ctrl.crafting_slot_at.return_value = None
        win._inv_ctrl.crafting_result_at.return_value = False
        win._inv_ctrl.slot_at.side_effect = [0, 1, 1, 2]
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.RIGHT, 0)
        h.on_mouse_drag(30, 10, 20, 0, mouse.RIGHT, 0)
        h.on_mouse_drag(30, 10, 0, 0, mouse.RIGHT, 0)
        h.on_mouse_drag(50, 10, 20, 0, mouse.RIGHT, 0)
        h.on_mouse_release(50, 10, mouse.RIGHT, 0)

        assert [call.args[0] for call in win._inv_ctrl.handle_inventory_click.call_args_list] == [
            0,
            1,
            2,
        ]
        assert all(
            call.args[1] == mouse.RIGHT and call.kwargs == {"quick_move": False}
            for call in win._inv_ctrl.handle_inventory_click.call_args_list
        )

    def test_right_drag_stops_when_cursor_stack_empties(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win.cursor_stack = object()
        win._inv_ctrl.crafting_slot_at.return_value = None
        win._inv_ctrl.crafting_result_at.return_value = False
        win._inv_ctrl.slot_at.side_effect = [0, 1]

        def place_one(slot: int, _button: int, *, quick_move: bool) -> None:
            assert not quick_move
            if slot == 1:
                win.cursor_stack = None

        win._inv_ctrl.handle_inventory_click.side_effect = place_one
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.RIGHT, 0)
        h.on_mouse_drag(30, 10, 20, 0, mouse.RIGHT, 0)
        h.on_mouse_drag(50, 10, 20, 0, mouse.RIGHT, 0)

        assert [call.args[0] for call in win._inv_ctrl.handle_inventory_click.call_args_list] == [
            0,
            1,
        ]

    def test_right_drag_routes_distinct_crafting_target(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win.cursor_stack = object()
        win._inv_ctrl.crafting_slot_at.side_effect = [None, 2]
        win._inv_ctrl.crafting_result_at.return_value = False
        win._inv_ctrl.slot_at.return_value = 0
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.RIGHT, 0)
        h.on_mouse_drag(30, 10, 20, 0, mouse.RIGHT, 0)

        win._inv_ctrl.handle_crafting_click.assert_called_once_with(2, mouse.RIGHT)

    def test_shift_click_crafting_input_requests_quick_move(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win._inv_ctrl.crafting_slot_at.return_value = 2
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.LEFT, key.MOD_SHIFT)

        win._inv_ctrl.handle_crafting_click.assert_called_once_with(
            2,
            mouse.LEFT,
            quick_move=True,
        )

    def test_shift_click_result_requests_crafting_quick_move(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win._inv_ctrl.crafting_slot_at.return_value = None
        win._inv_ctrl.crafting_result_at.return_value = True
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.LEFT, key.MOD_SHIFT)

        win._inv_ctrl.take_crafting_result.assert_called_once_with(quick_move=True)

    def test_click_pickup_without_drag_does_not_place_on_release(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win.cursor_stack = None
        win._inv_ctrl.crafting_slot_at.return_value = None
        win._inv_ctrl.crafting_result_at.return_value = False
        win._inv_ctrl.slot_at.return_value = 0

        def pick_up(_slot: int, _button: int, *, quick_move: bool) -> None:
            assert not quick_move
            win.cursor_stack = object()

        win._inv_ctrl.handle_inventory_click.side_effect = pick_up
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.LEFT, 0)
        h.on_mouse_release(10, 10, mouse.LEFT, 0)

        win._inv_ctrl.handle_inventory_click.assert_called_once_with(
            0, mouse.LEFT, quick_move=False
        )

    def test_drag_release_places_cursor_stack_on_target_slot(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win.cursor_stack = None
        win._inv_ctrl.crafting_slot_at.return_value = None
        win._inv_ctrl.crafting_result_at.return_value = False
        win._inv_ctrl.slot_at.side_effect = [0, 1]

        def pick_up(_slot: int, _button: int, *, quick_move: bool) -> None:
            assert not quick_move
            win.cursor_stack = object()

        win._inv_ctrl.handle_inventory_click.side_effect = pick_up
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.LEFT, 0)
        h.on_mouse_drag(30, 10, 20, 0, mouse.LEFT, 0)
        h.on_mouse_release(30, 10, mouse.LEFT, 0)

        assert win._inv_ctrl.handle_inventory_click.call_args_list[-1].args == (1, mouse.LEFT)
        assert win._inv_ctrl.handle_inventory_click.call_args_list[-1].kwargs == {
            "quick_move": False
        }

    def test_shift_click_does_not_start_inventory_drag(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win.cursor_stack = None
        win._inv_ctrl.crafting_slot_at.return_value = None
        win._inv_ctrl.crafting_result_at.return_value = False
        win._inv_ctrl.slot_at.return_value = 0

        def quick_move(_slot: int, _button: int, *, quick_move: bool) -> None:
            assert quick_move
            win.cursor_stack = object()

        win._inv_ctrl.handle_inventory_click.side_effect = quick_move
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.LEFT, key.MOD_SHIFT)
        h.on_mouse_drag(30, 10, 20, 0, mouse.LEFT, 0)
        h.on_mouse_release(30, 10, mouse.LEFT, 0)

        win._inv_ctrl.handle_inventory_click.assert_called_once_with(0, mouse.LEFT, quick_move=True)

    def test_drag_release_routes_to_crafting_slot(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        win.cursor_stack = None
        win._inv_ctrl.crafting_slot_at.side_effect = [None, 2]
        win._inv_ctrl.crafting_result_at.return_value = False
        win._inv_ctrl.slot_at.return_value = 0

        def pick_up(_slot: int, _button: int, *, quick_move: bool) -> None:
            assert not quick_move
            win.cursor_stack = object()

        win._inv_ctrl.handle_inventory_click.side_effect = pick_up
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.LEFT, 0)
        h.on_mouse_drag(30, 10, 20, 0, mouse.LEFT, 0)
        h.on_mouse_release(30, 10, mouse.LEFT, 0)

        win._inv_ctrl.handle_crafting_click.assert_called_once_with(2, mouse.LEFT)

    def test_drag_release_outside_slots_keeps_cursor_stack_carried(self):
        win = _make_win(in_game=True)
        win.inventory_open = True
        carried = object()
        win.cursor_stack = None
        win._inv_ctrl.crafting_slot_at.return_value = None
        win._inv_ctrl.crafting_result_at.return_value = False
        win._inv_ctrl.slot_at.side_effect = [0, None]

        def pick_up(_slot: int, _button: int, *, quick_move: bool) -> None:
            assert not quick_move
            win.cursor_stack = carried

        win._inv_ctrl.handle_inventory_click.side_effect = pick_up
        h = InputHandler(win)

        h.on_mouse_press(10, 10, mouse.LEFT, 0)
        h.on_mouse_drag(30, 10, 20, 0, mouse.LEFT, 0)
        h.on_mouse_release(30, 10, mouse.LEFT, 0)

        assert win.cursor_stack is carried
        win._inv_ctrl.handle_inventory_click.assert_called_once()

    def test_no_cycle_when_text_input_active(self):
        win = _make_win(in_game=True)
        win.text_input = MagicMock()
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, 1)
        win.cycle_hotbar.assert_not_called()

    def test_singleplayer_scroll_navigates_world_list(self):
        win = _make_win(in_game=False, screen=Screen.SINGLEPLAYER)
        win.menu.screen = Screen.SINGLEPLAYER
        win.menu_ui.world_list_items = [("a", None), ("b", None), ("c", None)]
        win.menu_ui.world_list_index = 1
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, 1)
        assert win.menu_ui.world_list_index == 0

    def test_singleplayer_scroll_down_navigates_world_list(self):
        win = _make_win(in_game=False, screen=Screen.SINGLEPLAYER)
        win.menu.screen = Screen.SINGLEPLAYER
        win.menu_ui.world_list_items = [("a", None), ("b", None), ("c", None)]
        win.menu_ui.world_list_index = 1
        h = InputHandler(win)
        h.on_mouse_scroll(0, 0, 0, -1)
        assert win.menu_ui.world_list_index == 2


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
        win.camera.rotate.assert_called_once_with(3.0, 4.0, win.settings.camera.mouse_sensitivity)

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
