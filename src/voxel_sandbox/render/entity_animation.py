from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from voxel_sandbox.engine.ecs import MobState
from voxel_sandbox.render.entity_models import EntityModelDef, Vec3


@dataclass(frozen=True, slots=True)
class PartPose:
    offset: Vec3 = (0.0, 0.0, 0.0)
    rotation: Vec3 = (0.0, 0.0, 0.0)


type Pose = dict[str, PartPose]


@dataclass(frozen=True, slots=True)
class AnimationClip:
    key: str
    duration: float
    loop: bool


class AnimationClipRegistry:
    def __init__(self, clips: tuple[AnimationClip, ...]) -> None:
        self.clips = {clip.key: clip for clip in clips}

    @classmethod
    def from_toml(cls, path: Path) -> AnimationClipRegistry:
        with path.open("rb") as file:
            data = tomllib.load(file)
        if data.get("version") != 1:
            raise ValueError("Unsupported animation clip format version")
        raw_clips = data.get("clips")
        if not isinstance(raw_clips, list):
            raise ValueError("Animation file must contain [[clips]]")
        clips: list[AnimationClip] = []
        for raw_clip in cast("list[object]", raw_clips):
            if not isinstance(raw_clip, dict):
                raise ValueError("Animation clips must be tables")
            values = cast("dict[str, object]", raw_clip)
            duration = values["duration"]
            if not isinstance(duration, int | float) or duration <= 0.0:
                raise ValueError("Animation duration must be positive")
            clips.append(AnimationClip(str(values["key"]), float(duration), bool(values["loop"])))
        return cls(tuple(clips))


class PoseBlender:
    @staticmethod
    def blend(first: Pose, second: Pose, amount: float) -> Pose:
        return blend_poses(first, second, amount)


class AnimationGraph:
    def __init__(self, clips: AnimationClipRegistry) -> None:
        self.clips = clips

    def evaluate(
        self,
        model: EntityModelDef,
        state: MobState,
        phase: float,
        speed: float,
    ) -> Pose:
        clip_key = {
            MobState.ATTACK: "attack",
            MobState.HURT: "hurt",
            MobState.DEATH: "death",
            MobState.GRAZE: "graze",
        }.get(state, "walk" if speed > 0.05 else "idle")
        clip = self.clips.clips[clip_key]
        clip_time = phase % clip.duration if clip.loop else min(phase, clip.duration)
        return animated_pose(model, state, clip_time, speed)


def head_look_controller(yaw: float, pitch: float) -> PartPose:
    return PartPose(rotation=(max(-0.6, min(pitch, 0.6)), max(-0.8, min(yaw, 0.8)), 0.0))


def wing_controller(time: float, speed: float) -> PartPose:
    return PartPose(rotation=(0.0, 0.0, math.sin(time * (5.0 + speed * 3.0)) * 0.9))


def crawling_gait_controller(time: float, side: float) -> PartPose:
    return PartPose(rotation=(math.sin(time * 7.0 + side * math.pi) * 0.45, side * 0.25, 0.0))


def blend_poses(first: Pose, second: Pose, amount: float) -> Pose:
    weight = max(0.0, min(amount, 1.0))
    result: Pose = {}
    for name in first.keys() | second.keys():
        left = first.get(name, PartPose())
        right = second.get(name, PartPose())
        result[name] = PartPose(
            _mix_vec(left.offset, right.offset, weight),
            _mix_vec(left.rotation, right.rotation, weight),
        )
    return result


def animated_pose(
    model: EntityModelDef,
    state: MobState,
    animation_time: float,
    speed: float,
    look_yaw: float = 0.0,
) -> Pose:
    pose: Pose = {}
    cycle = animation_time * (2.2 + speed * 1.2)
    swing = math.sin(cycle) * min(0.48, 0.10 + speed * 0.14)
    step_lift = (1.0 - math.cos(cycle * 2.0)) * min(0.018, speed * 0.012)
    weight_shift = math.sin(cycle) * min(0.035, speed * 0.025)
    bob = math.sin(animation_time * 1.7) * 0.006 + step_lift
    pose["body"] = PartPose(
        offset=(0.0, bob, 0.0),
        rotation=(weight_shift * 0.35, 0.0, weight_shift),
    )
    head_pitch = math.sin(animation_time * 1.1) * 0.045
    if state is MobState.GRAZE:
        chewing = math.sin(animation_time * 5.2)
        pose["body"] = PartPose(offset=(0.0, 0.0, 0.0))
        pose["head"] = PartPose(
            offset=(0.0, -0.38 + chewing * 0.015, -0.08),
            rotation=(-0.72 - chewing * 0.08, look_yaw, 0.0),
        )
    else:
        pose["head"] = PartPose(rotation=(head_pitch, look_yaw, 0.0))
    for name, phase in (
        ("leg_front_left", swing),
        ("leg_back_right", swing),
        ("leg_front_right", -swing),
        ("leg_back_left", -swing),
        ("leg_left", swing),
        ("leg_right", -swing),
        ("arm_left", -swing * 0.75),
        ("arm_right", swing * 0.75),
    ):
        if any(part.name == name for part in model.parts):
            pose[name] = PartPose(rotation=(phase, 0.0, 0.0))
    if model.key == "hostile" and state is not MobState.ATTACK:
        pose["arm_left"] = PartPose(rotation=(0.88 + swing * 0.18, 0.0, 0.0))
        pose["arm_right"] = PartPose(rotation=(0.88 - swing * 0.18, 0.0, 0.0))
    if any(part.name == "tail" for part in model.parts):
        pose["tail"] = PartPose(rotation=(0.08, math.sin(animation_time * 2.0) * 0.28, 0.0))
    if state is MobState.ATTACK:
        attack = math.sin(min(animation_time % 1.0, 0.65) / 0.65 * math.pi)
        pose["body"] = PartPose(
            offset=(0.0, bob, -attack * 0.12), rotation=(-attack * 0.18, 0.0, 0.0)
        )
        pose["arm_left"] = PartPose(rotation=(-1.2 * attack, 0.0, 0.0))
        pose["arm_right"] = PartPose(rotation=(-1.2 * attack, 0.0, 0.0))
    elif state is MobState.HURT:
        pose["body"] = PartPose(rotation=(0.0, 0.0, math.sin(animation_time * 28.0) * 0.18))
    elif state is MobState.DEATH:
        pose["body"] = PartPose(offset=(0.0, -0.32, 0.0), rotation=(0.0, 0.0, 1.35))
    return pose


def resolved_part_transform(
    model: EntityModelDef,
    part_name: str,
    pose: Pose,
) -> tuple[Vec3, Vec3]:
    parts = {part.name: part for part in model.parts}
    part = parts[part_name]
    local_pose = pose.get(part.name, PartPose())
    offset = _add_vec(part.offset, local_pose.offset)
    rotation = local_pose.rotation
    visited = {part.name}
    while part.parent is not None:
        if part.parent in visited:
            raise ValueError(f"Cyclic model hierarchy at {part.parent}")
        visited.add(part.parent)
        parent = parts[part.parent]
        parent_pose = pose.get(parent.name, PartPose())
        offset = _rotate_vec(offset, parent_pose.rotation)
        offset = _add_vec(_add_vec(parent.offset, parent_pose.offset), offset)
        rotation = _add_vec(parent_pose.rotation, rotation)
        part = parent
    return offset, rotation


def _mix_vec(first: Vec3, second: Vec3, amount: float) -> Vec3:
    return tuple(first[index] + (second[index] - first[index]) * amount for index in range(3))  # type: ignore[return-value]


def _add_vec(first: Vec3, second: Vec3) -> Vec3:
    return first[0] + second[0], first[1] + second[1], first[2] + second[2]


def _rotate_vec(value: Vec3, rotation: Vec3) -> Vec3:
    x, y, z = value
    cx, sx = math.cos(rotation[0]), math.sin(rotation[0])
    cy, sy = math.cos(rotation[1]), math.sin(rotation[1])
    cz, sz = math.cos(rotation[2]), math.sin(rotation[2])
    y, z = cx * y + sx * z, -sx * y + cx * z
    x, z = cy * x - sy * z, sy * x + cy * z
    x, y = cz * x + sz * y, -sz * x + cz * y
    return x, y, z
