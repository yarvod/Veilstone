from __future__ import annotations

from voxel_sandbox.render.input_state import KeyState, macos_game_key_bindings


def test_key_state_clear_releases_all_pressed_keys() -> None:
    state = KeyState()
    state.press(1)
    state.press(2)

    state.clear()

    assert not state.is_pressed(1)
    assert not state.is_pressed(2)


def test_macos_game_keys_use_physical_wasd_positions() -> None:
    assert macos_game_key_bindings() == {
        0x0D: ord("w"),
        0x00: ord("a"),
        0x01: ord("s"),
        0x02: ord("d"),
    }
