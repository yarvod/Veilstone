"""Unit tests for WorldManager (Phase 4.1)."""
# pyright: reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voxel_sandbox.render.world_manager import WorldManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_win(spawn=(0.0, 64.0, 0.0)):
    win = MagicMock()
    win.world_renderer.spawn_position = spawn
    win.world_renderer.is_solid_block.return_value = False
    win.player.x, win.player.y, win.player.z = 0.0, 64.0, 0.0
    win.player.velocity_y = 0.0
    win.player.on_ground = False
    win.player.width = 0.6
    win.player.collides.return_value = False
    return win


# ---------------------------------------------------------------------------
# _world_slug (pure function)
# ---------------------------------------------------------------------------


def test_world_slug_simple() -> None:
    assert WorldManager._world_slug("my world") == "my-world"


def test_world_slug_uppercase() -> None:
    assert WorldManager._world_slug("My World") == "my-world"


def test_world_slug_punctuation_stripped() -> None:
    assert WorldManager._world_slug("Test World!") == "test-world"


def test_world_slug_single_word() -> None:
    assert WorldManager._world_slug("veilstone") == "veilstone"


def test_world_slug_numbers_kept() -> None:
    assert WorldManager._world_slug("World 42") == "world-42"


def test_world_slug_empty_falls_back() -> None:
    assert WorldManager._world_slug("  ") == "world"


# ---------------------------------------------------------------------------
# _position_within_world (pure logic)
# ---------------------------------------------------------------------------


def test_position_within_world_normal() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((0.0, 64.0, 0.0)) is True


def test_position_below_min_y() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((0.0, -300.0, 0.0)) is False


def test_position_above_max_y() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((0.0, 2000.0, 0.0)) is False


def test_position_at_y_boundary_low() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((0.0, -256.0, 0.0)) is True
    assert wm._position_within_world((0.0, -256.1, 0.0)) is False


def test_position_at_y_boundary_high() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((0.0, 1024.0, 0.0)) is True
    assert wm._position_within_world((0.0, 1024.1, 0.0)) is False


def test_position_x_too_large() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((35_000_000.0, 64.0, 0.0)) is False


def test_position_z_too_large() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((0.0, 64.0, -31_000_000.0)) is False


def test_position_nan_is_invalid() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((float("nan"), 64.0, 0.0)) is False


def test_position_inf_is_invalid() -> None:
    win = _make_win()
    wm = WorldManager(win)
    assert wm._position_within_world((float("inf"), 64.0, 0.0)) is False


# ---------------------------------------------------------------------------
# invalid_player_position_reason
# ---------------------------------------------------------------------------


def test_valid_position_has_no_reason() -> None:
    win = _make_win()
    win.player.x, win.player.y, win.player.z = 10.0, 65.0, -5.0
    assert WorldManager(win).invalid_player_position_reason() is None


def test_nan_coordinate_gives_reason() -> None:
    win = _make_win()
    win.player.x, win.player.y, win.player.z = float("nan"), 64.0, 0.0
    reason = WorldManager(win).invalid_player_position_reason()
    assert reason is not None
    assert "non-finite" in reason


def test_y_too_low_gives_reason() -> None:
    win = _make_win()
    win.player.x, win.player.y, win.player.z = 0.0, -500.0, 0.0
    reason = WorldManager(win).invalid_player_position_reason()
    assert reason is not None
    assert "vertical" in reason


def test_x_outside_safety_gives_reason() -> None:
    win = _make_win()
    win.player.x, win.player.y, win.player.z = 35_000_000.0, 64.0, 0.0
    reason = WorldManager(win).invalid_player_position_reason()
    assert reason is not None
    assert "horizontal" in reason


# ---------------------------------------------------------------------------
# move_player_to_spawn
# ---------------------------------------------------------------------------


def test_move_player_to_spawn_sets_position() -> None:
    win = _make_win(spawn=(10.0, 70.0, -5.0))
    win.player.x, win.player.y, win.player.z = 100.0, 100.0, 100.0
    WorldManager(win).move_player_to_spawn()
    assert win.player.x == pytest.approx(10.0)
    assert win.player.y == pytest.approx(70.0)
    assert win.player.z == pytest.approx(-5.0)
    assert win.player.velocity_y == 0.0
    assert win.player.on_ground is False


# ---------------------------------------------------------------------------
# restore_player_position
# ---------------------------------------------------------------------------


def test_restore_valid_position_returns_true() -> None:
    win = _make_win()
    win.player.collides.return_value = False
    result = WorldManager(win).restore_player_position((5.0, 65.0, 3.0))
    assert result is True
    assert win.player.x == pytest.approx(5.0)
    assert win.player.y == pytest.approx(65.0)
    assert win.player.z == pytest.approx(3.0)


def test_restore_out_of_bounds_position_returns_false_and_spawns() -> None:
    win = _make_win(spawn=(0.0, 64.0, 0.0))
    result = WorldManager(win).restore_player_position((0.0, -500.0, 0.0))
    assert result is False
    # player was moved to spawn
    assert win.player.x == pytest.approx(0.0)
    assert win.player.y == pytest.approx(64.0)


def test_restore_colliding_position_returns_false_and_spawns() -> None:
    win = _make_win(spawn=(1.0, 64.0, 1.0))
    win.player.collides.return_value = True
    result = WorldManager(win).restore_player_position((5.0, 65.0, 3.0))
    assert result is False


# ---------------------------------------------------------------------------
# _saved_worlds (filesystem)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_worlds_cache():
    WorldManager._invalidate_worlds_cache()
    yield
    WorldManager._invalidate_worlds_cache()


def test_saved_worlds_empty_when_no_dir(tmp_path: Path) -> None:
    with patch(
        "voxel_sandbox.render.world_manager.application_data_root",
        return_value=tmp_path / "nonexistent",
    ):
        result = WorldManager._saved_worlds()
    assert result == ()


def test_saved_worlds_finds_valid_saves(tmp_path: Path) -> None:
    from voxel_sandbox.infrastructure.storage import WorldStorage

    world_dir = tmp_path / "test-world"
    WorldStorage(world_dir).ensure_world(name="Test World", seed="42")

    with patch(
        "voxel_sandbox.render.world_manager.application_data_root",
        return_value=tmp_path,
    ):
        result = WorldManager._saved_worlds()

    names = [name for name, _ in result]
    assert "Test World" in names


def test_unique_world_root_does_not_reuse_existing_save(tmp_path: Path) -> None:
    from voxel_sandbox.infrastructure.storage import WorldStorage

    WorldStorage(tmp_path / "same-name").ensure_world(name="Same Name", seed="old")

    with patch(
        "voxel_sandbox.render.world_manager.application_data_root",
        return_value=tmp_path,
    ):
        assert WorldManager._unique_world_root("Same Name") == tmp_path / "same-name-2"


def test_create_world_uses_unique_root_for_duplicate_names(tmp_path: Path) -> None:
    from voxel_sandbox.infrastructure.storage import WorldStorage

    WorldStorage(tmp_path / "same-name").ensure_world(name="Same Name", seed="old")
    win = _make_win()
    manager = WorldManager(win)

    with (
        patch(
            "voxel_sandbox.render.world_manager.application_data_root",
            return_value=tmp_path,
        ),
        patch.object(manager, "_switch_world") as switch_world,
    ):
        manager.create_world("Same Name", "new-seed")

    assert (tmp_path / "same-name-2" / "level.toml").exists()
    switch_world.assert_called_once_with(tmp_path / "same-name-2")


def test_delete_world_removes_directory_and_invalidates_cache(tmp_path: Path) -> None:
    from voxel_sandbox.infrastructure.storage import WorldStorage

    world_dir = tmp_path / "gone"
    WorldStorage(world_dir).ensure_world(name="Gone", seed="seed")
    WorldManager._worlds_cache = (("Gone", world_dir),)

    WorldManager.delete_world(world_dir)

    assert not world_dir.exists()
    assert WorldManager._worlds_cache is None


def test_saved_worlds_ignores_dirs_without_metadata(tmp_path: Path) -> None:
    (tmp_path / "no-metadata").mkdir()
    with patch(
        "voxel_sandbox.render.world_manager.application_data_root",
        return_value=tmp_path,
    ):
        result = WorldManager._saved_worlds()
    assert result == ()


def test_saved_worlds_is_cached(tmp_path: Path) -> None:
    with patch(
        "voxel_sandbox.render.world_manager.application_data_root",
        return_value=tmp_path / "nonexistent",
    ) as mock_root:
        WorldManager._saved_worlds()
        WorldManager._saved_worlds()
        assert mock_root.call_count == 1
