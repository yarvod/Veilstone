from __future__ import annotations

from voxel_sandbox.application.player_render import PlayerRenderSnapshot
from voxel_sandbox.render.player_avatar import build_player_avatar_render_data


def test_build_player_avatar_render_data_maps_snapshot_to_entity_inputs() -> None:
    snapshot = PlayerRenderSnapshot(
        position=(1.0, 2.0, 3.0),
        eye_position=(1.0, 3.62, 3.0),
        yaw_degrees=45.0,
        width=0.6,
        height=1.8,
        in_water=False,
        on_ground=True,
        vertical_velocity=0.0,
    )

    data = build_player_avatar_render_data(snapshot)

    assert data.transform.position == snapshot.position
    assert data.transform.yaw == 45.0
    assert data.model.key == "remote_player"
    assert data.model.scale == (0.6, 1.8, 0.6)
