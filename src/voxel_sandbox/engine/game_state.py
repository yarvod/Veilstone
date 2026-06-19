from __future__ import annotations

from enum import Enum, auto


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()


_VALID_TRANSITIONS: dict[GameState, frozenset[GameState]] = {
    GameState.MENU: frozenset({GameState.PLAYING}),
    GameState.PLAYING: frozenset({GameState.PAUSED, GameState.MENU}),
    GameState.PAUSED: frozenset({GameState.PLAYING, GameState.MENU}),
}


class InvalidTransition(Exception):
    pass


class GameStateMachine:
    def __init__(self, initial: GameState = GameState.MENU) -> None:
        self._current = initial

    @property
    def current(self) -> GameState:
        return self._current

    @property
    def is_playing(self) -> bool:
        return self._current is GameState.PLAYING

    @property
    def is_paused(self) -> bool:
        return self._current is GameState.PAUSED

    @property
    def is_in_menu(self) -> bool:
        return self._current is GameState.MENU

    def can_transition(self, target: GameState) -> bool:
        return target in _VALID_TRANSITIONS.get(self._current, frozenset())

    def transition(self, target: GameState) -> None:
        if not self.can_transition(target):
            raise InvalidTransition(f"Cannot transition from {self._current.name} to {target.name}")
        self._current = target

    def try_transition(self, target: GameState) -> bool:
        if self.can_transition(target):
            self._current = target
            return True
        return False
