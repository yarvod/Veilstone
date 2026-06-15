from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

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
from voxel_sandbox.render.entity_renderer import cube_vertices


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
    assert len(hostile.parts) == 6
    assert {part.name for part in passive.parts} >= {"head", "tail", "leg_front_left"}
    assert {part.name for part in hostile.parts} >= {"head", "arm_left", "leg_right"}
    assert all(part.material == "skin" for part in passive.parts)
    assert all(
        part.face_uvs is not None
        and all(face_uv != (0.0, 0.0, 1.0, 1.0) for face_uv in part.face_uvs)
        for part in hostile.parts
    )
    assert passive.parts[1].face_uvs is not None
    assert passive.parts[1].face_uvs[0] != passive.parts[1].face_uvs[2]
    assert hostile.parts[1].face_uvs is not None
    assert hostile.parts[1].face_uvs[0] != hostile.parts[1].face_uvs[3]
    assert hostile.parts[2].face_uvs is not None
    assert hostile.parts[2].face_uvs[2] != hostile.parts[2].face_uvs[3]
    assert len(models.get("remote_player").parts) == 6
    assert models.get("remote_player").texture.name == "player-skin.png"


def test_named_uv_regions_and_face_groups_resolve_with_explicit_precedence(
    tmp_path: Path,
) -> None:
    config = tmp_path / "models.toml"
    config.write_text(
        """
version = 1

[[models]]
key = "test"
texture = "test.png"
base_color = [1, 1, 1]

[models.uv_regions]
default = [0.0, 0.0, 0.1, 0.1]
sides = [0.1, 0.0, 0.1, 0.1]
x_axis = [0.2, 0.0, 0.1, 0.1]
front = [0.3, 0.0, 0.1, 0.1]

[[models.parts]]
name = "body"
offset = [0, 0, 0]
size = [1, 1, 1]
uv_all = "default"
uv_sides = "sides"
uv_x = "x_axis"
uv_front = "front"
""".strip(),
        encoding="utf-8",
    )

    part = EntityModelRegistry.from_toml(config, tmp_path).get("test").parts[0]

    assert part.face_uvs == (
        (0.3, 0.0, 0.1, 0.1),
        (0.1, 0.0, 0.1, 0.1),
        (0.2, 0.0, 0.1, 0.1),
        (0.2, 0.0, 0.1, 0.1),
        (0.0, 0.0, 0.1, 0.1),
        (0.0, 0.0, 0.1, 0.1),
    )


def test_unknown_named_uv_region_is_rejected(tmp_path: Path) -> None:
    config = tmp_path / "models.toml"
    config.write_text(
        """
version = 1

[[models]]
key = "test"
texture = "test.png"
base_color = [1, 1, 1]

[[models.parts]]
name = "body"
offset = [0, 0, 0]
size = [1, 1, 1]
uv_front = "missing"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unknown entity UV region: missing"):
        EntityModelRegistry.from_toml(config, tmp_path)


def test_generated_mob_skins_keep_faces_out_of_profile_tiles() -> None:
    with Image.open(resource_path("assets/entities/zombie-skin.png")) as zombie:
        assert zombie.size == (256, 256)
        assert zombie.getpixel((18, 34)) == (19, 24, 17)
        assert zombie.getpixel((64 + 18, 34)) != (19, 24, 17)
    with Image.open(resource_path("assets/entities/cow-skin.png")) as cow:
        assert cow.size == (256, 256)
        assert cow.getpixel((20, 64 + 48)) == (55, 38, 29)
        assert cow.getpixel((64 + 20, 64 + 48)) != (55, 38, 29)
    with Image.open(resource_path("assets/entities/player-skin.png")) as player:
        assert player.size == (256, 256)
        assert player.getpixel((18, 31)) == (52, 92, 122)
        assert player.getpixel((64 + 18, 31)) != (52, 92, 122)


def test_entity_cube_front_is_upright_and_side_faces_are_not_mirrored() -> None:
    vertices = cube_vertices()
    front = {vertex[:3]: vertex[3:5] for vertex in vertices[:6]}
    left = {vertex[:3]: vertex[3:5] for vertex in vertices[12:18]}

    assert front[(-0.5, 0.5, -0.5)] == (0.0, 0.0)
    assert front[(0.5, 0.5, -0.5)] == (1.0, 0.0)
    assert front[(-0.5, -0.5, -0.5)] == (0.0, 1.0)
    assert left[(-0.5, 0.5, 0.5)] == (1.0, 0.0)
    assert left[(-0.5, 0.5, -0.5)] == (0.0, 0.0)


def test_animation_graph_produces_distinct_walk_attack_hurt_and_death_poses() -> None:
    models, clips = _registries()
    model = models.get("hostile")
    graph = AnimationGraph(clips)

    walk = graph.evaluate(model, MobState.CHASE, 0.2, 2.0)
    attack = graph.evaluate(model, MobState.ATTACK, 0.2, 0.0)
    hurt = graph.evaluate(model, MobState.HURT, 0.1, 0.0)
    death = graph.evaluate(model, MobState.DEATH, 0.5, 0.0)
    graze = graph.evaluate(models.get("passive"), MobState.GRAZE, 0.5, 0.0)

    assert walk["leg_left"] != attack.get("leg_left")
    assert walk["arm_left"].rotation[0] < -0.7
    assert attack["arm_left"].rotation[0] < -0.5
    assert hurt["body"].rotation != death["body"].rotation
    assert graze["head"].offset[1] < -0.3
    assert graze["head"].rotation[0] < -0.6


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
