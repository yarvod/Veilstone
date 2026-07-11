from __future__ import annotations

import math

from voxel_sandbox.application.player_animation import (
    PlayerAnimationSnapshot,
    PlayerInteraction,
)
from voxel_sandbox.application.player_render import (
    PlayerHeldItemSnapshot,
    PlayerRenderSnapshot,
)
from voxel_sandbox.engine.ecs import EntityWorld, HeldItem
from voxel_sandbox.render.player_avatar import (
    apply_player_avatar_render_data,
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
        head_pitch_degrees=-20.0,
        name="LocalHero",
        health=14.0,
        max_health=20.0,
        status_flags=("airborne",),
    )

    data = build_player_avatar_render_data(snapshot)

    assert data.transform.position == snapshot.position
    assert math.isclose(data.transform.yaw, math.radians(45.0) + math.pi / 2.0)
    assert data.model.key == "remote_player"
    assert data.model.scale == (0.6, 1.8, 0.6)
    assert data.held_item is None
    assert data.name == "LocalHero"
    assert data.health == 14.0
    assert data.max_health == 20.0
    assert data.head_pitch_degrees == -20.0
    assert data.status_flags == ("airborne",)


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
    assert world.held_items.get(entity) is None


def test_build_player_avatar_world_carries_player_gait_animation() -> None:
    animation = PlayerAnimationSnapshot(
        moving=True,
        sprinting=False,
        swimming=False,
        grounded=True,
        movement_amount=0.75,
        gait_phase=1.25,
        step_index=2,
        footstep_due=False,
        swim_stroke_due=False,
        camera_bob_y=0.0,
        viewmodel_bob_y=0.0,
        interaction=PlayerInteraction.IDLE,
        interaction_progress=0.0,
        interaction_active=False,
    )
    snapshot = PlayerRenderSnapshot(
        position=(4.0, 5.0, 6.0),
        eye_position=(4.0, 6.62, 6.0),
        yaw_degrees=90.0,
        width=0.6,
        height=1.8,
        in_water=False,
        on_ground=True,
        vertical_velocity=0.0,
        animation=animation,
    )

    world = build_player_avatar_world(snapshot)
    (entity,) = world.query(world.animations)

    assert world.animations[entity].phase == 1.25
    assert world.animations[entity].speed == 0.75


def test_build_player_avatar_render_data_maps_held_item() -> None:
    snapshot = PlayerRenderSnapshot(
        position=(1.0, 2.0, 3.0),
        eye_position=(1.0, 3.62, 3.0),
        yaw_degrees=45.0,
        width=0.6,
        height=1.8,
        in_water=False,
        on_ground=True,
        vertical_velocity=0.0,
        held_item=PlayerHeldItemSnapshot(item_id=7, count=12, hand="left"),
    )

    data = build_player_avatar_render_data(snapshot)

    assert data.held_item is not None
    assert data.held_item.item_id == 7
    assert data.held_item.count == 12
    assert data.held_item.hand == "left"


def test_build_player_avatar_world_carries_held_item_component() -> None:
    snapshot = PlayerRenderSnapshot(
        position=(4.0, 5.0, 6.0),
        eye_position=(4.0, 6.62, 6.0),
        yaw_degrees=90.0,
        width=0.6,
        height=1.8,
        in_water=False,
        on_ground=True,
        vertical_velocity=0.0,
        held_item=PlayerHeldItemSnapshot(item_id=3, count=1),
    )

    world = build_player_avatar_world(snapshot)
    entities = world.query(world.transforms, world.render_models)
    entity = entities[0]

    held_item = world.held_items[entity]
    assert held_item.item_id == 3
    assert held_item.count == 1
    assert held_item.hand == "right"


def test_apply_player_avatar_render_data_removes_stale_held_item() -> None:
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
    world = EntityWorld()
    entity = world.create()
    world.held_items.set(entity, HeldItem(item_id=3, count=1))

    apply_player_avatar_render_data(
        world,
        entity,
        build_player_avatar_render_data(snapshot),
    )

    assert world.held_items.get(entity) is None
