from __future__ import annotations


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
