from __future__ import annotations

import math

from voxel_sandbox.application.player_nameplate import build_player_nameplate_snapshot
from voxel_sandbox.render.player_nameplate import build_player_nameplate_render_data


def test_nameplate_snapshot_places_label_above_player() -> None:
    snapshot = build_player_nameplate_snapshot(
        player_id=7,
        name="Alex",
        player_position=(1.0, 2.0, 3.0),
        camera_position=(1.0, 2.0, 3.0),
    )

    assert snapshot.name == "Alex"
    assert snapshot.world_position[0] == 1.0
    assert math.isclose(snapshot.world_position[1], 4.15)
    assert snapshot.world_position[2] == 3.0
    assert snapshot.visible is True
    assert snapshot.alpha == 1.0


def test_nameplate_snapshot_fades_out_with_distance() -> None:
    snapshot = build_player_nameplate_snapshot(
        player_id=2,
        name="Steve",
        player_position=(0.0, 0.0, 40.0),
        camera_position=(0.0, 0.0, 0.0),
        fade_start=20.0,
        max_distance=50.0,
    )

    assert 0.0 < snapshot.alpha < 1.0
    assert snapshot.visible is True


def test_nameplate_snapshot_hides_beyond_max_distance() -> None:
    snapshot = build_player_nameplate_snapshot(
        player_id=2,
        name="Steve",
        player_position=(0.0, 0.0, 80.0),
        camera_position=(0.0, 0.0, 0.0),
        max_distance=50.0,
    )

    assert snapshot.alpha == 0.0
    assert snapshot.visible is False


def test_empty_name_falls_back_to_player_id() -> None:
    snapshot = build_player_nameplate_snapshot(
        player_id=3,
        name=" ",
        player_position=(0.0, 0.0, 0.0),
        camera_position=(0.0, 0.0, 0.0),
    )

    assert snapshot.name == "Player 3"


def test_render_data_skips_hidden_nameplate() -> None:
    hidden = build_player_nameplate_snapshot(
        player_id=1,
        name="Hidden",
        player_position=(0.0, 0.0, 90.0),
        camera_position=(0.0, 0.0, 0.0),
    )

    assert build_player_nameplate_render_data(hidden) is None


def test_render_data_maps_visible_nameplate() -> None:
    visible = build_player_nameplate_snapshot(
        player_id=1,
        name="Visible",
        player_position=(0.0, 0.0, 0.0),
        camera_position=(0.0, 0.0, 0.0),
    )

    data = build_player_nameplate_render_data(visible)

    assert data is not None
    assert data.text == "Visible"
    assert data.world_position == visible.world_position
    assert data.alpha == visible.alpha
