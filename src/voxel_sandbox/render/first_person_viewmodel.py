# pyright: reportUnknownMemberType=false
from __future__ import annotations

from pathlib import Path
from typing import cast

import moderngl
import numpy as np

from voxel_sandbox.render.player_viewmodel import PlayerViewmodelRenderData, ViewmodelPart
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
            [(self.vertex_buffer, "3f 3f 2f", "in_position", "in_normal", "in_uv")],
        )

    def render(
        self,
        data: PlayerViewmodelRenderData,
        *,
        width: int,
        height: int,
        block_texture: moderngl.Texture | None = None,
        atlas_uvs: dict[str, tuple[float, float, float, float]] | None = None,
    ) -> int:
        program = self.shader.program
        if program is None:
            return 0
        cast("moderngl.Uniform", program["aspect_ratio"]).value = max(width, 1) / max(height, 1)
        draws = 0
        for part in data.parts:
            texture_rects = _texture_rects(part, atlas_uvs)
            if block_texture is not None and texture_rects is not None:
                block_texture.use(0)
                cast("moderngl.Uniform", program["use_texture"]).value = 1
                cast("moderngl.Uniform", program["viewmodel_texture"]).value = 0
                top_rect, side_rect, bottom_rect = texture_rects
                cast("moderngl.Uniform", program["uv_rect_top"]).value = top_rect
                cast("moderngl.Uniform", program["uv_rect_side"]).value = side_rect
                cast("moderngl.Uniform", program["uv_rect_bottom"]).value = bottom_rect
            else:
                cast("moderngl.Uniform", program["use_texture"]).value = 0
                cast("moderngl.Uniform", program["uv_rect_top"]).value = (0.0, 0.0, 1.0, 1.0)
                cast("moderngl.Uniform", program["uv_rect_side"]).value = (0.0, 0.0, 1.0, 1.0)
                cast("moderngl.Uniform", program["uv_rect_bottom"]).value = (0.0, 0.0, 1.0, 1.0)
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


def _texture_rects(
    part: ViewmodelPart,
    atlas_uvs: dict[str, tuple[float, float, float, float]] | None,
) -> (
    tuple[
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
    ]
    | None
):
    top = _texture_rect(part.texture_top or part.texture_name, atlas_uvs)
    side = _texture_rect(part.texture_side or part.texture_name, atlas_uvs)
    bottom = _texture_rect(part.texture_bottom or part.texture_name, atlas_uvs)
    if top is None or side is None or bottom is None:
        return None
    return top, side, bottom


def _texture_rect(
    texture_name: str | None,
    atlas_uvs: dict[str, tuple[float, float, float, float]] | None,
) -> tuple[float, float, float, float] | None:
    if texture_name is None or atlas_uvs is None:
        return None
    rect = atlas_uvs.get(texture_name)
    if rect is None:
        return None
    u, v, width, height = rect
    return u, v, u + width, v + height


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
    uv_corners = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    vertices: list[tuple[float, float, float, float, float, float, float, float]] = []
    for normal, corners in faces:
        for index in (0, 1, 2, 0, 2, 3):
            position = corners[index]
            uv = uv_corners[index]
            vertices.append((*position, *normal, *uv))
    return np.array(vertices, dtype=np.float32)
