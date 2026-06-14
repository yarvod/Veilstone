# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import math
from pathlib import Path
from typing import cast

import moderngl
import numpy as np
from PIL import Image

from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.engine.ecs import EntityWorld, MobState, RenderModel
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.entity_animation import (
    AnimationClipRegistry,
    AnimationGraph,
    resolved_part_transform,
)
from voxel_sandbox.render.entity_models import EntityModelDef, EntityModelRegistry
from voxel_sandbox.render.math3d import camera_matrix
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram


class EntityRenderer:
    def __init__(self, context: moderngl.Context) -> None:
        self.context = context
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(context, ShaderFiles.from_directory(shader_root, "entity"))
        self.shadow_shader = ShaderProgram(
            context, ShaderFiles.from_directory(shader_root, "entity_shadow_depth")
        )
        if self.shader.program is None or self.shadow_shader.program is None:
            raise RuntimeError("Entity shader failed to compile")
        vertices = np.asarray(_cube_vertices(), dtype=np.float32)
        self.vertex_buffer = context.buffer(vertices.tobytes())
        self.vertex_array = context.vertex_array(
            self.shader.program,
            [(self.vertex_buffer, "3f 2f", "in_position", "in_uv")],
        )
        self.shadow_vertex_array = context.vertex_array(
            self.shadow_shader.program,
            [(self.vertex_buffer, "3f 2x4", "in_position")],
        )
        self.models = EntityModelRegistry.from_toml(
            resource_path("config/entity_models.toml"), resource_path("assets")
        )
        self.animation_graph = AnimationGraph(
            AnimationClipRegistry.from_toml(resource_path("config/entity_animations.toml"))
        )
        self.texture, self.texture_rects = _load_texture_atlas(
            context,
            tuple(self.models.get(key) for key in ("passive", "hostile", "remote_player")),
        )

    def render(
        self,
        world: EntityWorld,
        camera: FirstPersonCamera,
        width: int,
        height: int,
        field_of_view: float,
        animation_time: float,
    ) -> int:
        program = self.shader.program
        if program is None:
            return 0
        matrix = camera_matrix(camera, max(width, 1) / max(height, 1), field_of_view)
        cast("moderngl.Uniform", program["camera_matrix"]).write(matrix.T.astype("f4").tobytes())
        cast("moderngl.Uniform", program["entity_texture"]).value = 0
        draws = 0
        for entity, render_model in world.render_models.items():
            transform = world.transforms.get(entity)
            if transform is None:
                continue
            model = self._model(render_model.key)
            if model is None:
                draws += self._render_fallback(
                    program, transform.position, render_model, animation_time
                )
                continue
            distance = math.dist(camera.position, transform.position)
            if distance > 56.0:
                continue
            animation = world.animations.get(entity)
            ai = world.mob_ai.get(entity)
            state = ai.state if ai is not None else MobState.IDLE
            phase = (
                animation.state_phase
                if animation is not None
                and state in {MobState.ATTACK, MobState.HURT, MobState.DEATH}
                else animation.phase
                if animation is not None
                else animation_time
            )
            speed = animation.speed if animation is not None else 0.0
            pose = self.animation_graph.evaluate(model, state, phase, speed)
            self.texture.use(0)
            cast("moderngl.Uniform", program["use_texture"]).value = 1
            cast("moderngl.Uniform", program["entity_position"]).value = transform.position
            cast("moderngl.Uniform", program["entity_yaw"]).value = transform.yaw
            cast("moderngl.Uniform", program["entity_color"]).value = model.base_color
            parts = (
                model.parts
                if distance <= 28.0
                else tuple(part for part in model.parts if part.name in {"body", "head"})
            )
            for part in parts:
                offset, rotation = resolved_part_transform(model, part.name, pose)
                cast("moderngl.Uniform", program["part_offset"]).value = offset
                cast("moderngl.Uniform", program["part_scale"]).value = part.size
                cast("moderngl.Uniform", program["part_pivot"]).value = part.pivot
                cast("moderngl.Uniform", program["part_rotation"]).value = rotation
                cast("moderngl.Uniform", program["texture_rect"]).value = _part_texture_rect(
                    self.texture_rects[model.key], part.uv
                )
                cast("moderngl.Uniform", program["entity_color"]).value = (
                    model.base_color[0] * part.tint[0],
                    model.base_color[1] * part.tint[1],
                    model.base_color[2] * part.tint[2],
                )
                self.vertex_array.render(moderngl.TRIANGLES)
                draws += 1
        return draws

    def render_shadow(
        self,
        world: EntityWorld,
        light_matrix: np.ndarray,
        animation_time: float,
    ) -> int:
        program = self.shadow_shader.program
        if program is None:
            return 0
        cast("moderngl.Uniform", program["light_matrix"]).write(
            light_matrix.T.astype("f4").tobytes()
        )
        draws = 0
        for entity, render_model in world.render_models.items():
            transform = world.transforms.get(entity)
            if transform is None:
                continue
            model = self._model(render_model.key)
            if model is None:
                draws += self._render_fallback_shadow(
                    program, transform.position, render_model, animation_time
                )
                continue
            animation = world.animations.get(entity)
            ai = world.mob_ai.get(entity)
            pose = self.animation_graph.evaluate(
                model,
                ai.state if ai is not None else MobState.IDLE,
                animation.state_phase
                if animation is not None
                and ai is not None
                and ai.state in {MobState.ATTACK, MobState.HURT, MobState.DEATH}
                else animation.phase
                if animation is not None
                else animation_time,
                animation.speed if animation is not None else 0.0,
            )
            cast("moderngl.Uniform", program["entity_position"]).value = transform.position
            cast("moderngl.Uniform", program["entity_yaw"]).value = transform.yaw
            for part in model.parts:
                offset, rotation = resolved_part_transform(model, part.name, pose)
                cast("moderngl.Uniform", program["part_offset"]).value = offset
                cast("moderngl.Uniform", program["part_scale"]).value = part.size
                cast("moderngl.Uniform", program["part_pivot"]).value = part.pivot
                cast("moderngl.Uniform", program["part_rotation"]).value = rotation
                self.shadow_vertex_array.render(moderngl.TRIANGLES)
                draws += 1
        return draws

    def _model(self, key: str) -> EntityModelDef | None:
        try:
            return self.models.get(key)
        except KeyError:
            return None

    def _render_fallback(
        self,
        program: moderngl.Program,
        position: tuple[float, float, float],
        model: RenderModel,
        time: float,
    ) -> int:
        scale = model.scale
        color = model.color
        is_item = scale[0] < 0.4
        cast("moderngl.Uniform", program["entity_position"]).value = position
        cast("moderngl.Uniform", program["entity_yaw"]).value = time * 1.8 if is_item else 0.0
        cast("moderngl.Uniform", program["part_offset"]).value = (
            0.0,
            0.14 + math.sin(time * 2.5 + position[0]) * 0.06 if is_item else scale[1] * 0.5,
            0.0,
        )
        cast("moderngl.Uniform", program["part_scale"]).value = scale
        cast("moderngl.Uniform", program["part_pivot"]).value = (0.0, 0.0, 0.0)
        cast("moderngl.Uniform", program["part_rotation"]).value = (0.0, 0.0, 0.0)
        cast("moderngl.Uniform", program["entity_color"]).value = color
        cast("moderngl.Uniform", program["use_texture"]).value = 0
        cast("moderngl.Uniform", program["texture_rect"]).value = (0.0, 0.0, 1.0, 1.0)
        self.vertex_array.render(moderngl.TRIANGLES)
        return 1

    def _render_fallback_shadow(
        self,
        program: moderngl.Program,
        position: tuple[float, float, float],
        model: RenderModel,
        time: float,
    ) -> int:
        scale = model.scale
        is_item = scale[0] < 0.4
        cast("moderngl.Uniform", program["entity_position"]).value = position
        cast("moderngl.Uniform", program["entity_yaw"]).value = time * 1.8 if is_item else 0.0
        cast("moderngl.Uniform", program["part_offset"]).value = (0.0, scale[1] * 0.5, 0.0)
        cast("moderngl.Uniform", program["part_scale"]).value = scale
        cast("moderngl.Uniform", program["part_pivot"]).value = (0.0, 0.0, 0.0)
        cast("moderngl.Uniform", program["part_rotation"]).value = (0.0, 0.0, 0.0)
        self.shadow_vertex_array.render(moderngl.TRIANGLES)
        return 1

    def release(self) -> None:
        self.texture.release()
        self.shadow_vertex_array.release()
        self.vertex_array.release()
        self.vertex_buffer.release()
        self.shadow_shader.release()
        self.shader.release()


def _load_texture_atlas(
    context: moderngl.Context,
    models: tuple[EntityModelDef, ...],
) -> tuple[moderngl.Texture, dict[str, tuple[float, float, float, float]]]:
    images = [(model, Image.open(model.texture).convert("RGB")) for model in models]
    width = sum(image.width for _model, image in images)
    height = max(image.height for _model, image in images)
    atlas = Image.new("RGB", (width, height))
    rectangles: dict[str, tuple[float, float, float, float]] = {}
    cursor = 0
    for model, image in images:
        atlas.paste(image, (cursor, 0))
        rectangles[model.key] = (cursor / width, 0.0, image.width / width, image.height / height)
        cursor += image.width
    texture = context.texture(atlas.size, 3, atlas.tobytes())
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    texture.repeat_x = True
    texture.repeat_y = True
    return texture, rectangles


def _part_texture_rect(
    model_rect: tuple[float, float, float, float],
    part_rect: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    return (
        model_rect[0] + part_rect[0] * model_rect[2],
        model_rect[1] + part_rect[1] * model_rect[3],
        part_rect[2] * model_rect[2],
        part_rect[3] * model_rect[3],
    )


def _cube_vertices() -> tuple[tuple[float, float, float, float, float], ...]:
    corners = (
        (-0.5, -0.5, -0.5),
        (0.5, -0.5, -0.5),
        (0.5, 0.5, -0.5),
        (-0.5, 0.5, -0.5),
        (-0.5, -0.5, 0.5),
        (0.5, -0.5, 0.5),
        (0.5, 0.5, 0.5),
        (-0.5, 0.5, 0.5),
    )
    faces = ((0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7), (1, 5, 6, 2), (3, 2, 6, 7), (4, 5, 1, 0))
    uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    return tuple(
        (*corners[index], *uvs[uv_index])
        for face in faces
        for index, uv_index in (
            (face[0], 0),
            (face[1], 1),
            (face[2], 2),
            (face[0], 0),
            (face[2], 2),
            (face[3], 3),
        )
    )
