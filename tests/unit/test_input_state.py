from __future__ import annotations

from unittest.mock import patch

from pyglet.window import key

from voxel_sandbox.render.input_state import KeyState, configure_layout_independent_game_keys


def test_key_state_clear_releases_all_pressed_keys() -> None:
    state = KeyState()
    state.press(1)
    state.press(2)

    state.clear()

    assert not state.is_pressed(1)
    assert not state.is_pressed(2)


def test_macos_game_keys_use_physical_wasd_positions() -> None:
    from pyglet.libs.darwin import quartzkey

    previous = {
        code: quartzkey.keymap.get(code)
        for code in (quartzkey.QZ_w, quartzkey.QZ_a, quartzkey.QZ_s, quartzkey.QZ_d)
    }
    try:
        with patch("voxel_sandbox.render.input_state.sys.platform", "darwin"):
            configure_layout_independent_game_keys()

        assert quartzkey.keymap[quartzkey.QZ_w] == key.W
        assert quartzkey.keymap[quartzkey.QZ_a] == key.A
        assert quartzkey.keymap[quartzkey.QZ_s] == key.S
        assert quartzkey.keymap[quartzkey.QZ_d] == key.D
    finally:
        for code, symbol in previous.items():
            if symbol is None:
                quartzkey.keymap.pop(code, None)
            else:
                quartzkey.keymap[code] = symbol
