# pyright: reportUnknownMemberType=false
from __future__ import annotations

from pathlib import Path
from typing import cast

import moderngl
import numpy as np

from voxel_sandbox.render.player_viewmodel import PlayerViewmodelRenderData
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram


class FirstPersonViewmodelRenderer:
    def __init__(self, context: moderngl.Context) -> None:
        self.context = context
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(context, ShaderFiles.from_directory(shader_root, "viewmodel"))
        if self.shader.program is None:
            raise RuntimeError("Viewmodel shader failed to compile")
        self.vertex_buffer = context.buffer(_cube_vertices().astype("f4").tobytes())
        self.vertex_array = context.vertex_array(
            self.shader.program,
            [(self.vertex_buffer, "3f 3f", "in_position", "in_normal")],
        )

    def render(
        self,
        data: PlayerViewmodelRenderData,
        *,
        width: int,
        height: int,
    ) -> int:
        program = self.shader.program
        if program is None:
            return 0
        cast("moderngl.Uniform", program["aspect_ratio"]).value = max(width, 1) / max(height, 1)
        draws = 0
        for part in data.parts:
            cast("moderngl.Uniform", program["part_position"]).value = part.position
            cast("moderngl.Uniform", program["part_scale"]).value = part.scale
            cast("moderngl.Uniform", program["part_rotation_degrees"]).value = part.rotation_degrees
            cast("moderngl.Uniform", program["part_color"]).value = part.color
            self.vertex_array.render(moderngl.TRIANGLES)
            draws += 1
        return draws

    def release(self) -> None:
        self.vertex_array.release()
        self.vertex_buffer.release()
        self.shader.release()


def _cube_vertices() -> np.ndarray:
    faces = [
        (
            (0.0, 0.0, 1.0),
            [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)],
        ),
        (
            (0.0, 0.0, -1.0),
            [
                (0.5, -0.5, -0.5),
                (-0.5, -0.5, -0.5),
                (-0.5, 0.5, -0.5),
                (0.5, 0.5, -0.5),
            ],
        ),
        (
            (1.0, 0.0, 0.0),
            [(0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5)],
        ),
        (
            (-1.0, 0.0, 0.0),
            [
                (-0.5, -0.5, -0.5),
                (-0.5, -0.5, 0.5),
                (-0.5, 0.5, 0.5),
                (-0.5, 0.5, -0.5),
            ],
        ),
        (
            (0.0, 1.0, 0.0),
            [(-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5)],
        ),
        (
            (0.0, -1.0, 0.0),
            [
                (-0.5, -0.5, -0.5),
                (0.5, -0.5, -0.5),
                (0.5, -0.5, 0.5),
                (-0.5, -0.5, 0.5),
            ],
        ),
    ]
    vertices: list[tuple[float, float, float, float, float, float]] = []
    for normal, corners in faces:
        for index in (0, 1, 2, 0, 2, 3):
            position = corners[index]
            vertices.append((*position, *normal))
    return np.array(vertices, dtype=np.float32)
