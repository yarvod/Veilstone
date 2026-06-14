from __future__ import annotations

from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.engine.ecs import MobState
from voxel_sandbox.render.entity_animation import (
    AnimationClipRegistry,
    AnimationGraph,
    PartPose,
    PoseBlender,
    crawling_gait_controller,
    head_look_controller,
    resolved_part_transform,
    wing_controller,
)
from voxel_sandbox.render.entity_models import EntityModelRegistry


def _registries() -> tuple[EntityModelRegistry, AnimationClipRegistry]:
    models = EntityModelRegistry.from_toml(
        resource_path("config/entity_models.toml"), resource_path("assets")
    )
    clips = AnimationClipRegistry.from_toml(resource_path("config/entity_animations.toml"))
    return models, clips


def test_original_mob_models_are_textured_and_articulated() -> None:
    models, _clips = _registries()
    passive = models.get("passive")
    hostile = models.get("hostile")

    assert passive.texture.name == "cow-skin.png"
    assert hostile.texture.name == "zombie-skin.png"
    assert len(passive.parts) == 9
    assert len(hostile.parts) == 9
    assert {part.name for part in passive.parts} >= {"head", "tail", "leg_front_left"}
    assert {part.name for part in hostile.parts} >= {"jaw", "arm_left", "ear_right"}
    assert all(part.material == "skin" for part in passive.parts)
    assert all(part.uv != (0.0, 0.0, 1.0, 1.0) for part in hostile.parts)
    assert len(models.get("remote_player").parts) == 6


def test_animation_graph_produces_distinct_walk_attack_hurt_and_death_poses() -> None:
    models, clips = _registries()
    model = models.get("hostile")
    graph = AnimationGraph(clips)

    walk = graph.evaluate(model, MobState.CHASE, 0.2, 2.0)
    attack = graph.evaluate(model, MobState.ATTACK, 0.2, 0.0)
    hurt = graph.evaluate(model, MobState.HURT, 0.1, 0.0)
    death = graph.evaluate(model, MobState.DEATH, 0.5, 0.0)

    assert walk["leg_left"] != attack.get("leg_left")
    assert attack["jaw"].rotation[0] > 0.0
    assert hurt["body"].rotation != death["body"].rotation


def test_pose_blending_hierarchy_and_extra_controllers() -> None:
    models, _clips = _registries()
    blended = PoseBlender.blend(
        {"head": PartPose(rotation=(0.0, 0.0, 0.0))},
        {"head": PartPose(rotation=(1.0, 0.0, 0.0))},
        0.25,
    )
    offset, _rotation = resolved_part_transform(models.get("passive"), "ear_left", blended)

    assert blended["head"].rotation[0] == 0.25
    assert offset[1] > 0.9
    assert head_look_controller(2.0, -2.0).rotation == (-0.6, 0.8, 0.0)
    assert wing_controller(0.3, 1.0).rotation != (0.0, 0.0, 0.0)
    assert crawling_gait_controller(0.3, -1.0).rotation != (0.0, 0.0, 0.0)
