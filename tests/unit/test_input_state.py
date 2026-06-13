from __future__ import annotations

from voxel_sandbox.render.input_state import KeyState


def test_key_state_clear_releases_all_pressed_keys() -> None:
    state = KeyState()
    state.press(1)
    state.press(2)

    state.clear()

    assert not state.is_pressed(1)
    assert not state.is_pressed(2)
