# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from typing import cast

import moderngl
import numpy as np

from voxel_sandbox.engine.ecs import EntityWorld
from voxel_sandbox.render.camera import FirstPersonCamera
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
            [(self.vertex_buffer, "3f", "in_position")],
        )
        self.shadow_vertex_array = context.vertex_array(
            self.shadow_shader.program,
            [(self.vertex_buffer, "3f", "in_position")],
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
        position_uniform = cast("moderngl.Uniform", program["entity_position"])
        scale_uniform = cast("moderngl.Uniform", program["entity_scale"])
        color_uniform = cast("moderngl.Uniform", program["entity_color"])
        item_uniform = cast("moderngl.Uniform", program["is_item"])
        cast("moderngl.Uniform", program["animation_time"]).value = animation_time
        draws = 0
        for entity, model in world.render_models.items():
            transform = world.transforms.get(entity)
            if transform is None:
                continue
            position_uniform.value = transform.position
            scale_uniform.value = model.scale
            color_uniform.value = model.color
            item_uniform.value = int(entity in world.items)
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
        position_uniform = cast("moderngl.Uniform", program["entity_position"])
        scale_uniform = cast("moderngl.Uniform", program["entity_scale"])
        item_uniform = cast("moderngl.Uniform", program["is_item"])
        cast("moderngl.Uniform", program["animation_time"]).value = animation_time
        draws = 0
        for entity, model in world.render_models.items():
            transform = world.transforms.get(entity)
            if transform is None:
                continue
            position_uniform.value = transform.position
            scale_uniform.value = model.scale
            item_uniform.value = int(entity in world.items)
            self.shadow_vertex_array.render(moderngl.TRIANGLES)
            draws += 1
        return draws

    def release(self) -> None:
        self.shadow_vertex_array.release()
        self.vertex_array.release()
        self.vertex_buffer.release()
        self.shadow_shader.release()
        self.shader.release()


def _cube_vertices() -> tuple[tuple[float, float, float], ...]:
    corners = (
        (-0.5, 0.0, -0.5),
        (0.5, 0.0, -0.5),
        (0.5, 1.0, -0.5),
        (-0.5, 1.0, -0.5),
        (-0.5, 0.0, 0.5),
        (0.5, 0.0, 0.5),
        (0.5, 1.0, 0.5),
        (-0.5, 1.0, 0.5),
    )
    faces = (
        (0, 1, 2, 3),
        (5, 4, 7, 6),
        (4, 0, 3, 7),
        (1, 5, 6, 2),
        (3, 2, 6, 7),
        (4, 5, 1, 0),
    )
    return tuple(
        corners[index]
        for face in faces
        for index in (face[0], face[1], face[2], face[0], face[2], face[3])
    )
