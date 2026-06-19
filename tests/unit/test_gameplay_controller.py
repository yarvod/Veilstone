"""Unit tests for GameplayController (Phase 4.1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.application.resource_packs import ApplyResourcePackUseCase
from voxel_sandbox.render.gameplay_controller import GameplayController

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def win():
    mock = MagicMock()
    mock.settings = AppSettings()
    mock.world_renderer.time_of_day = 0.5
    mock.world_renderer.day_cycle_seconds = 240.0
    mock.network_session = None
    return mock


@pytest.fixture()
def ctrl(win):
    return GameplayController(win)


# ---------------------------------------------------------------------------
# execute_command — /time set
# ---------------------------------------------------------------------------


def test_set_time_midnight(ctrl, win) -> None:
    # midnight = 18000 ticks → 18000/24000 = 0.75
    ctrl.execute_command("/time set midnight")
    assert win.world_renderer.time_of_day == pytest.approx(18000 / 24000)


def test_set_time_noon(ctrl, win) -> None:
    # noon = 6000 ticks → 6000/24000 = 0.25
    ctrl.execute_command("/time set noon")
    assert win.world_renderer.time_of_day == pytest.approx(6000 / 24000)


def test_set_time_sunrise(ctrl, win) -> None:
    # sunrise = 0 ticks
    ctrl.execute_command("/time set sunrise")
    assert win.world_renderer.time_of_day == pytest.approx(0.0)


def test_set_time_twilight_freezes_cycle(ctrl, win) -> None:
    # twilight is the only named time that sets freeze=True
    ctrl.execute_command("/time set twilight")
    assert win.world_renderer.day_cycle_seconds == pytest.approx(0.0)


def test_set_time_no_freeze_restores_cycle(ctrl, win) -> None:
    ctrl.execute_command("/time set noon")
    assert win.world_renderer.day_cycle_seconds == pytest.approx(
        win.settings.graphics.day_cycle_seconds
    )


def test_set_time_updates_inventory_status(ctrl, win) -> None:
    ctrl.execute_command("/time set midnight")
    assert "midnight" in win.inventory_status.lower()


# ---------------------------------------------------------------------------
# execute_command — /difficulty
# ---------------------------------------------------------------------------


def test_difficulty_peaceful_saved(ctrl, win) -> None:
    with patch("voxel_sandbox.render.gameplay_controller.save_user_settings") as mock_save:
        ctrl.execute_command("/difficulty peaceful")
        mock_save.assert_called_once()


def test_difficulty_peaceful_updates_status(ctrl, win) -> None:
    ctrl.execute_command("/difficulty peaceful")
    assert "peaceful" in win.inventory_status.lower()


def test_difficulty_normal_updates_settings(ctrl, win) -> None:
    with patch("voxel_sandbox.render.gameplay_controller.save_user_settings"):
        ctrl.execute_command("/difficulty normal")
    assert win.settings.gameplay.difficulty == "normal"


def test_difficulty_invalid_sets_error(ctrl, win) -> None:
    ctrl.execute_command("/difficulty hard")
    assert win.inventory_status != ""


# ---------------------------------------------------------------------------
# execute_command — unknown / bad syntax
# ---------------------------------------------------------------------------


def test_unknown_command_shows_help(ctrl, win) -> None:
    ctrl.execute_command("/help")
    assert win.inventory_status != ""


def test_bad_command_sets_error_status(ctrl, win) -> None:
    ctrl.execute_command("/time")
    assert win.inventory_status != ""


def test_completely_unknown_command_shows_help_text(ctrl, win) -> None:
    ctrl.execute_command("/xyzzy")
    assert "/" in win.inventory_status


# ---------------------------------------------------------------------------
# execute_command — /teleport (no multiplayer)
# ---------------------------------------------------------------------------


def test_teleport_without_network_fails(ctrl, win) -> None:
    win.network_session = None
    ctrl.execute_command("/tp SomePlayer")
    assert "multiplayer" in win.inventory_status.lower()


# ---------------------------------------------------------------------------
# execute_command — /resourcepack
# ---------------------------------------------------------------------------


def test_resourcepack_nonexistent_path_sets_error(ctrl, win) -> None:
    ctrl.execute_command("/resourcepack /nonexistent/path/to/pack.zip")
    assert "not found" in win.inventory_status.lower()


def test_resourcepack_default_calls_apply(ctrl, win) -> None:
    mock_atlas = MagicMock(return_value=MagicMock())
    settings_store = MagicMock()
    texture_packs = MagicMock()
    texture_packs.load_block_atlas = mock_atlas
    ctrl._apply_resource_pack = ApplyResourcePackUseCase(texture_packs, settings_store)

    ctrl.execute_command("/resourcepack default")

    mock_atlas.assert_called_once()
    win.world_renderer.apply_texture_pack.assert_called_once()
    settings_store.save.assert_called_once()


# ---------------------------------------------------------------------------
# /structure commands — no LAN server
# ---------------------------------------------------------------------------


def test_spawn_structure_without_lan_fails(ctrl, win) -> None:
    win.lan_server = None
    win.world_renderer.remote_mode = False
    ctrl.execute_command("/structure spawn gate")
    assert (
        "local" in win.inventory_status.lower() or "authoritative" in win.inventory_status.lower()
    )


def test_list_structures_returns_empty(ctrl, win) -> None:
    win.structure_world.entities = {}
    ctrl.execute_command("/structure list")
    assert "no" in win.inventory_status.lower()


# ---------------------------------------------------------------------------
# _handle_set_time (direct method call)
# ---------------------------------------------------------------------------


def test_handle_set_time_direct(ctrl, win) -> None:
    from voxel_sandbox.app.commands import SetTimeCommand

    command = SetTimeCommand(time_of_day=0.25, freeze=False, label="dusk")
    ctrl._handle_set_time(command)
    assert win.world_renderer.time_of_day == pytest.approx(0.25)
    assert "dusk" in win.inventory_status.lower()
