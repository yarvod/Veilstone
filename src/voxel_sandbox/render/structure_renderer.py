# pyright: reportUnknownMemberType=false

from __future__ import annotations

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
        vertices = np.asarray(_cube_vertices(), dtype=np.float32)
        self.vertex_buffer = context.buffer(vertices.tobytes())
        self.vertex_array = context.vertex_array(
            self.shader.program,
            [(self.vertex_buffer, "3f 2f 1f", "in_position", "in_uv", "in_face")],
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
    ) -> int:
        program = self.shader.program
        if program is None:
            return 0
        matrix = camera_matrix(camera, max(width, 1) / max(height, 1), field_of_view)
        cast("moderngl.Uniform", program["camera_matrix"]).write(matrix.T.astype("f4").tobytes())
        cast("moderngl.Uniform", program["entity_texture"]).value = 0
        cast("moderngl.Uniform", program["use_texture"]).value = 1
        cast("moderngl.Uniform", program["entity_color"]).value = (0.86, 0.86, 0.86)
        cast("moderngl.Uniform", program["part_scale"]).value = (1.0, 1.0, 1.0)
        cast("moderngl.Uniform", program["part_pivot"]).value = (0.0, 0.0, 0.0)
        cast("moderngl.Uniform", program["part_rotation"]).value = (0.0, 0.0, 0.0)
        texture.use(0)
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
        self.vertex_array.release()
        self.vertex_buffer.release()
        self.shader.release()


def _atlas_rect(
    bounds: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    return bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]


def _cube_vertices() -> tuple[tuple[float, float, float, float, float, float], ...]:
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
        (0, 1, 2, 3),
        (5, 4, 7, 6),
        (4, 0, 3, 7),
        (1, 5, 6, 2),
        (3, 2, 6, 7),
        (4, 5, 1, 0),
    )
    uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    return tuple(
        (*corners[index], *uvs[uv_index], float(face_index))
        for face_index, face in enumerate(faces)
        for index, uv_index in (
            (face[0], 0),
            (face[2], 2),
            (face[1], 1),
            (face[0], 0),
            (face[3], 3),
            (face[2], 2),
        )
    )
