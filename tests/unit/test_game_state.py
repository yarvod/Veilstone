"""Unit tests for GameState machine (Phase 3.3)."""

from __future__ import annotations

import pytest

from voxel_sandbox.engine.game_state import GameState, GameStateMachine, InvalidTransition

# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_default_initial_state() -> None:
    machine = GameStateMachine()
    assert machine.current is GameState.MENU


def test_custom_initial_state() -> None:
    machine = GameStateMachine(GameState.PLAYING)
    assert machine.current is GameState.PLAYING


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------


def test_menu_to_playing() -> None:
    machine = GameStateMachine(GameState.MENU)
    machine.transition(GameState.PLAYING)
    assert machine.current is GameState.PLAYING


def test_playing_to_paused() -> None:
    machine = GameStateMachine(GameState.PLAYING)
    machine.transition(GameState.PAUSED)
    assert machine.current is GameState.PAUSED


def test_paused_to_playing() -> None:
    machine = GameStateMachine(GameState.PAUSED)
    machine.transition(GameState.PLAYING)
    assert machine.current is GameState.PLAYING


def test_playing_to_menu() -> None:
    machine = GameStateMachine(GameState.PLAYING)
    machine.transition(GameState.MENU)
    assert machine.current is GameState.MENU


def test_paused_to_menu() -> None:
    machine = GameStateMachine(GameState.PAUSED)
    machine.transition(GameState.MENU)
    assert machine.current is GameState.MENU


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------


def test_menu_to_paused_raises() -> None:
    machine = GameStateMachine(GameState.MENU)
    with pytest.raises(InvalidTransition):
        machine.transition(GameState.PAUSED)


def test_menu_to_menu_raises() -> None:
    machine = GameStateMachine(GameState.MENU)
    with pytest.raises(InvalidTransition):
        machine.transition(GameState.MENU)


def test_playing_to_playing_raises() -> None:
    machine = GameStateMachine(GameState.PLAYING)
    with pytest.raises(InvalidTransition):
        machine.transition(GameState.PLAYING)


def test_paused_to_paused_raises() -> None:
    machine = GameStateMachine(GameState.PAUSED)
    with pytest.raises(InvalidTransition):
        machine.transition(GameState.PAUSED)


# ---------------------------------------------------------------------------
# can_transition
# ---------------------------------------------------------------------------


def test_can_transition_valid() -> None:
    machine = GameStateMachine(GameState.PLAYING)
    assert machine.can_transition(GameState.PAUSED) is True
    assert machine.can_transition(GameState.MENU) is True


def test_can_transition_invalid() -> None:
    machine = GameStateMachine(GameState.MENU)
    assert machine.can_transition(GameState.PAUSED) is False
    assert machine.can_transition(GameState.MENU) is False


# ---------------------------------------------------------------------------
# try_transition (non-raising)
# ---------------------------------------------------------------------------


def test_try_transition_valid_returns_true() -> None:
    machine = GameStateMachine(GameState.MENU)
    result = machine.try_transition(GameState.PLAYING)
    assert result is True
    assert machine.current is GameState.PLAYING


def test_try_transition_invalid_returns_false_no_change() -> None:
    machine = GameStateMachine(GameState.MENU)
    result = machine.try_transition(GameState.PAUSED)
    assert result is False
    assert machine.current is GameState.MENU


# ---------------------------------------------------------------------------
# Convenience properties
# ---------------------------------------------------------------------------


def test_is_playing_only_when_playing() -> None:
    assert GameStateMachine(GameState.PLAYING).is_playing is True
    assert GameStateMachine(GameState.MENU).is_playing is False
    assert GameStateMachine(GameState.PAUSED).is_playing is False


def test_is_paused_only_when_paused() -> None:
    assert GameStateMachine(GameState.PAUSED).is_paused is True
    assert GameStateMachine(GameState.MENU).is_paused is False
    assert GameStateMachine(GameState.PLAYING).is_paused is False


def test_is_in_menu_only_when_menu() -> None:
    assert GameStateMachine(GameState.MENU).is_in_menu is True
    assert GameStateMachine(GameState.PLAYING).is_in_menu is False
    assert GameStateMachine(GameState.PAUSED).is_in_menu is False


# ---------------------------------------------------------------------------
# Full lifecycle sequence
# ---------------------------------------------------------------------------


def test_full_game_lifecycle() -> None:
    machine = GameStateMachine()
    assert machine.is_in_menu

    machine.transition(GameState.PLAYING)
    assert machine.is_playing

    machine.transition(GameState.PAUSED)
    assert machine.is_paused

    machine.transition(GameState.PLAYING)
    assert machine.is_playing

    machine.transition(GameState.MENU)
    assert machine.is_in_menu
