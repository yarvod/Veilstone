# pyright: reportUnknownMemberType=false

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import moderngl
import numpy as np

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.blocks.structures import StructureWorld, structure_part_transform
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.math3d import camera_matrix
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram


class StructureRenderer:
    def __init__(self, context: moderngl.Context, registry: BlockRegistry) -> None:
        self.registry = registry
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(context, ShaderFiles.from_directory(shader_root, "entity"))
        if self.shader.program is None:
            raise RuntimeError("Structure shader failed to compile")
        self.neutral_shadow_texture = context.depth_texture((1, 1))
        self.neutral_shadow_texture.compare_func = "<="
        neutral_shadow_framebuffer = context.framebuffer(
            depth_attachment=self.neutral_shadow_texture
        )
        neutral_shadow_framebuffer.clear(depth=1.0)
        neutral_shadow_framebuffer.release()
        vertices = np.asarray(_cube_vertices(), dtype=np.float32)
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

    def render(
        self,
        world: StructureWorld,
        camera: FirstPersonCamera,
        width: int,
        height: int,
        field_of_view: float,
        texture: moderngl.Texture,
        atlas_uvs: dict[str, tuple[float, float, float, float]],
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
        cast("moderngl.Uniform", program["use_texture"]).value = 1
        cast("moderngl.Uniform", program["entity_color"]).value = (0.86, 0.86, 0.86)
        cast("moderngl.Uniform", program["part_scale"]).value = (1.0, 1.0, 1.0)
        cast("moderngl.Uniform", program["part_pivot"]).value = (0.0, 0.0, 0.0)
        cast("moderngl.Uniform", program["part_rotation"]).value = (0.0, 0.0, 0.0)
        texture.use(0)
        active_shadow_texture.use(1)
        draws = 0
        for entity in world.entities.values():
            definition = world.definitions[entity.key]
            cast("moderngl.Uniform", program["entity_position"]).value = tuple(
                float(value) for value in entity.origin
            )
            for part in definition.parts:
                offset, rotation = structure_part_transform(definition, entity, part)
                cast("moderngl.Uniform", program["entity_yaw"]).value = rotation
                cast("moderngl.Uniform", program["part_offset"]).value = (
                    offset[0] + 0.5,
                    offset[1] + 0.5,
                    offset[2] + 0.5,
                )
                world_position = (
                    entity.origin[0] + offset[0] + 0.5,
                    entity.origin[1] + offset[1],
                    entity.origin[2] + offset[2] + 0.5,
                )
                sky_light, block_light = (
                    light_sampler(world_position, 1.0) if light_sampler is not None else (1.0, 0.0)
                )
                cast("moderngl.Uniform", program["entity_sky_light"]).value = sky_light
                cast("moderngl.Uniform", program["entity_block_light"]).value = block_light
                block = self.registry.by_key(part.block_key)
                rectangles = (
                    _atlas_rect(atlas_uvs[block.texture_side]),
                    _atlas_rect(atlas_uvs[block.texture_side]),
                    _atlas_rect(atlas_uvs[block.texture_side]),
                    _atlas_rect(atlas_uvs[block.texture_side]),
                    _atlas_rect(atlas_uvs[block.texture_top]),
                    _atlas_rect(atlas_uvs[block.texture_bottom]),
                )
                for face, rectangle in zip(
                    ("front", "back", "left", "right", "top", "bottom"),
                    rectangles,
                    strict=True,
                ):
                    cast("moderngl.Uniform", program[f"texture_rect_{face}"]).value = rectangle
                self.vertex_array.render(moderngl.TRIANGLES)
                draws += 1
        return draws

    def release(self) -> None:
        self.neutral_shadow_texture.release()
        self.vertex_array.release()
        self.vertex_buffer.release()
        self.shader.release()


def _atlas_rect(
    bounds: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    return bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]


def _cube_vertices() -> tuple[tuple[float, ...], ...]:
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
    uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    return tuple(
        (*corners[index], *uvs[uv_index], float(face_index), *normal)
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
