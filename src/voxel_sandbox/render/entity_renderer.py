# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import cast

import moderngl
import numpy as np
from PIL import Image

from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.items import ItemRegistry
from voxel_sandbox.engine.ecs import EntityWorld, MobState, RenderModel
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.entity_animation import (
    AnimationClipRegistry,
    AnimationGraph,
    resolved_part_transform,
)
from voxel_sandbox.render.entity_models import (
    EntityModelDef,
    EntityModelRegistry,
    FaceUVs,
    ModelPart,
)
from voxel_sandbox.render.math3d import camera_matrix
from voxel_sandbox.render.model_snapshots import item_block_atlas_rect
from voxel_sandbox.render.player_held_item import (
    PlayerHeldItemRenderData,
    build_player_held_item_render_data,
)
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
        self.neutral_shadow_texture = context.depth_texture((1, 1))
        self.neutral_shadow_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.neutral_shadow_texture.compare_func = "<="
        neutral_shadow_framebuffer = context.framebuffer(
            depth_attachment=self.neutral_shadow_texture
        )
        neutral_shadow_framebuffer.clear(depth=1.0)
        neutral_shadow_framebuffer.release()
        vertices = np.asarray(cube_vertices(), dtype=np.float32)
        self.vertex_buffer = context.buffer(vertices.tobytes())
        self.vertex_array = context.vertex_array(
            self.shader.program,
            [
                (
                    self.vertex_buffer,
                    "3f 2f 1f 3f",
                    "in_position",
                    "in_uv",
                    "in_face",
                    "in_normal",
                )
            ],
        )
        self.shadow_vertex_array = context.vertex_array(
            self.shadow_shader.program,
            [(self.vertex_buffer, "3f 6x4", "in_position")],
        )
        self.models = EntityModelRegistry.from_toml(
            resource_path("config/entity_models.toml"),
            resource_path("resource_packs/default"),
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
        item_registry: ItemRegistry | None = None,
        block_registry: BlockRegistry | None = None,
        block_texture: moderngl.Texture | None = None,
        atlas_uvs: dict[str, tuple[float, float, float, float]] | None = None,
        light_sampler: Callable[[tuple[float, float, float], float], tuple[float, float]]
        | None = None,
        daylight: float = 1.0,
        day_tint: tuple[float, float, float] = (1.0, 1.0, 1.0),
        light_matrix: np.ndarray | None = None,
        shadow_texture: moderngl.Texture | None = None,
        shadow_bias: float = 0.0015,
        light_direction: tuple[float, float, float] = (0.4, 0.8, 0.25),
    ) -> int:
        program = self.shader.program
        if program is None:
            return 0
        matrix = camera_matrix(camera, max(width, 1) / max(height, 1), field_of_view)
        cast("moderngl.Uniform", program["camera_matrix"]).write(matrix.T.astype("f4").tobytes())
        cast("moderngl.Uniform", program["entity_texture"]).value = 0
        cast("moderngl.Uniform", program["daylight"]).value = daylight
        cast("moderngl.Uniform", program["day_tint"]).value = day_tint
        cast("moderngl.Uniform", program["light_direction"]).value = light_direction
        cast("moderngl.Uniform", program["shadow_map"]).value = 1
        cast("moderngl.Uniform", program["shadows_enabled"]).value = int(
            shadow_texture is not None and light_matrix is not None
        )
        cast("moderngl.Uniform", program["shadow_bias"]).value = shadow_bias
        active_shadow_texture = shadow_texture or self.neutral_shadow_texture
        cast("moderngl.Uniform", program["shadow_texel_size"]).value = (
            1.0 / active_shadow_texture.width
        )
        shadow_transform = (
            light_matrix if light_matrix is not None else np.identity(4, dtype=np.float32)
        )
        cast("moderngl.Uniform", program["shadow_matrix"]).write(
            shadow_transform.T.astype("f4").tobytes()
        )
        active_shadow_texture.use(1)
        draws = 0
        for entity, render_model in world.render_models.items():
            transform = world.transforms.get(entity)
            if transform is None:
                continue
            collider = world.colliders.get(entity)
            entity_height = collider.height if collider is not None else render_model.scale[1]
            sky_light, block_light = (
                light_sampler(transform.position, entity_height)
                if light_sampler is not None
                else (1.0, 0.0)
            )
            cast("moderngl.Uniform", program["entity_sky_light"]).value = sky_light
            cast("moderngl.Uniform", program["entity_block_light"]).value = block_light
            model = self._model(render_model.key)
            if model is None:
                texture_rect = None
                if (
                    block_texture is not None
                    and atlas_uvs is not None
                    and item_registry is not None
                    and block_registry is not None
                ):
                    item_entity = world.items.get(entity)
                    if item_entity is not None:
                        atlas_rect = item_block_atlas_rect(
                            item_entity.stack.item_id,
                            item_registry,
                            block_registry,
                            atlas_uvs,
                        )
                        if atlas_rect is not None:
                            texture_rect = _atlas_bounds_to_rect(atlas_rect)

                if texture_rect is not None and block_texture is not None:
                    block_texture.use(0)
                    draws += self._render_fallback(
                        program, transform.position, render_model, animation_time, texture_rect
                    )
                    self.texture.use(0)
                else:
                    draws += self._render_fallback(
                        program, transform.position, render_model, animation_time, None
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
                self._set_face_uvs(program, self.texture_rects[model.key], part)
                cast("moderngl.Uniform", program["entity_color"]).value = (
                    model.base_color[0] * part.tint[0],
                    model.base_color[1] * part.tint[1],
                    model.base_color[2] * part.tint[2],
                )
                self.vertex_array.render(moderngl.TRIANGLES)
                draws += 1
            held_item = world.held_items.get(entity)
            if held_item is not None and distance <= 28.0:
                arm_part = "arm_right" if held_item.hand == "right" else "arm_left"
                if any(part.name == arm_part for part in model.parts):
                    arm_offset, arm_rotation = resolved_part_transform(model, arm_part, pose)
                    held_item_data = build_player_held_item_render_data(
                        held_item,
                        arm_offset=arm_offset,
                        arm_rotation=arm_rotation,
                        item_registry=item_registry,
                        block_registry=block_registry,
                        atlas_uvs=atlas_uvs if block_texture is not None else None,
                    )
                    if held_item_data.texture_rect is not None and block_texture is not None:
                        block_texture.use(0)
                    else:
                        self.texture.use(0)
                    draws += self._render_held_item(program, held_item_data)
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

    def _render_held_item(
        self,
        program: moderngl.Program,
        data: PlayerHeldItemRenderData,
    ) -> int:
        cast("moderngl.Uniform", program["part_offset"]).value = data.offset
        cast("moderngl.Uniform", program["part_scale"]).value = data.scale
        cast("moderngl.Uniform", program["part_pivot"]).value = (0.0, 0.0, 0.0)
        cast("moderngl.Uniform", program["part_rotation"]).value = data.rotation
        cast("moderngl.Uniform", program["entity_color"]).value = data.color
        if data.texture_rect is not None:
            cast("moderngl.Uniform", program["use_texture"]).value = 1
            self._set_uniform_face_uvs(program, cast("FaceUVs", (data.texture_rect,) * 6))
        else:
            cast("moderngl.Uniform", program["use_texture"]).value = 0
            self._set_uniform_face_uvs(
                program,
                cast("FaceUVs", ((0.0, 0.0, 1.0, 1.0),) * 6),
            )
        self.vertex_array.render(moderngl.TRIANGLES)
        return 1

    def _render_fallback(
        self,
        program: moderngl.Program,
        position: tuple[float, float, float],
        model: RenderModel,
        time: float,
        texture_rect: tuple[float, float, float, float] | None = None,
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
        if texture_rect is not None:
            cast("moderngl.Uniform", program["use_texture"]).value = 1
            self._set_uniform_face_uvs(program, cast("FaceUVs", (texture_rect,) * 6))
        else:
            cast("moderngl.Uniform", program["use_texture"]).value = 0
            self._set_uniform_face_uvs(
                program,
                cast("FaceUVs", ((0.0, 0.0, 1.0, 1.0),) * 6),
            )
        self.vertex_array.render(moderngl.TRIANGLES)
        return 1

    def _set_face_uvs(
        self,
        program: moderngl.Program,
        model_rect: tuple[float, float, float, float],
        part: ModelPart,
    ) -> None:
        local_uvs = part.face_uvs or (part.uv,) * 6
        rectangles = tuple(_part_texture_rect(model_rect, rect) for rect in local_uvs)
        self._set_uniform_face_uvs(program, cast("FaceUVs", rectangles))

    @staticmethod
    def _set_uniform_face_uvs(
        program: moderngl.Program,
        rectangles: FaceUVs,
    ) -> None:
        for face, rectangle in zip(
            ("front", "back", "left", "right", "top", "bottom"),
            rectangles,
            strict=True,
        ):
            cast("moderngl.Uniform", program[f"texture_rect_{face}"]).value = rectangle

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
        self.neutral_shadow_texture.release()
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
    texture.repeat_x = False
    texture.repeat_y = False
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


def _atlas_bounds_to_rect(
    bounds: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    return bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]


def cube_vertices() -> tuple[tuple[float, ...], ...]:
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
    faces = (
        ((0, 1, 2, 3), (0.0, 0.0, -1.0)),
        ((5, 4, 7, 6), (0.0, 0.0, 1.0)),
        ((4, 0, 3, 7), (-1.0, 0.0, 0.0)),
        ((1, 5, 6, 2), (1.0, 0.0, 0.0)),
        ((3, 2, 6, 7), (0.0, 1.0, 0.0)),
        ((4, 5, 1, 0), (0.0, -1.0, 0.0)),
    )
    # PIL rows are uploaded directly, so V=0 is the authored top edge. Side faces
    # need their own U order to remain readable when viewed from outside the cube.
    face_uvs = (
        ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)),
        ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)),
        ((1.0, 1.0), (0.0, 1.0), (0.0, 0.0), (1.0, 0.0)),
        ((1.0, 1.0), (0.0, 1.0), (0.0, 0.0), (1.0, 0.0)),
        ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)),
    )
    return tuple(
        (*corners[index], *face_uvs[face_index][uv_index], float(face_index), *normal)
        for face_index, (face, normal) in enumerate(faces)
        for index, uv_index in (
            (face[0], 0),
            (face[2], 2),
            (face[1], 1),
            (face[0], 0),
            (face[3], 3),
            (face[2], 2),
        )
    )
