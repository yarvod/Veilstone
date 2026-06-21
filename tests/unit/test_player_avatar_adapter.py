from __future__ import annotations

from voxel_sandbox.application.player_render import PlayerRenderSnapshot
from voxel_sandbox.render.player_avatar import (
    build_player_avatar_render_data,
    build_player_avatar_world,
)


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


def test_build_player_avatar_world_contains_single_renderable_entity() -> None:
    snapshot = PlayerRenderSnapshot(
        position=(4.0, 5.0, 6.0),
        eye_position=(4.0, 6.62, 6.0),
        yaw_degrees=90.0,
        width=0.6,
        height=1.8,
        in_water=False,
        on_ground=True,
        vertical_velocity=0.0,
    )

    world = build_player_avatar_world(snapshot)
    entities = world.query(world.transforms, world.render_models)

    assert len(entities) == 1
    entity = entities[0]
    assert world.transforms[entity].position == snapshot.position
    assert world.render_models[entity].key == "remote_player"
