from __future__ import annotations

import sys


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
