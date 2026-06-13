from __future__ import annotations

import sys

from pyglet.window import key


def configure_layout_independent_game_keys() -> None:
    """Bind macOS physical letter positions used by gameplay controls."""
    if sys.platform != "darwin":
        return

    from pyglet.libs.darwin import quartzkey

    quartzkey.keymap.update(
        {
            quartzkey.QZ_w: key.W,
            quartzkey.QZ_a: key.A,
            quartzkey.QZ_s: key.S,
            quartzkey.QZ_d: key.D,
        }
    )


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
