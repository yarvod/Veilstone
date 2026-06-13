# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from typing import cast

import moderngl
import numpy as np

from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram

EDGES = np.asarray(
    (
        (0, 0, 0),
        (1, 0, 0),
        (1, 0, 0),
        (1, 1, 0),
        (1, 1, 0),
        (0, 1, 0),
        (0, 1, 0),
        (0, 0, 0),
        (0, 0, 1),
        (1, 0, 1),
        (1, 0, 1),
        (1, 1, 1),
        (1, 1, 1),
        (0, 1, 1),
        (0, 1, 1),
        (0, 0, 1),
        (0, 0, 0),
        (0, 0, 1),
        (1, 0, 0),
        (1, 0, 1),
        (1, 1, 0),
        (1, 1, 1),
        (0, 1, 0),
        (0, 1, 1),
    ),
    dtype=np.float32,
)


class BlockHighlightRenderer:
    def __init__(self, context: moderngl.Context) -> None:
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(context, ShaderFiles.from_directory(shader_root, "highlight"))
        if self.shader.program is None:
            raise RuntimeError("Highlight shader failed to compile")
        self.buffer = context.buffer(EDGES.tobytes())
        self.vertex_array = context.vertex_array(
            self.shader.program,
            [(self.buffer, "3f", "in_position")],
        )

    def render(
        self,
        camera_matrix: np.ndarray[tuple[int, int], np.dtype[np.float32]],
        block: tuple[int, int, int],
    ) -> None:
        if self.shader.program is None:
            return
        matrix_uniform = cast("moderngl.Uniform", self.shader.program["camera_matrix"])
        origin_uniform = cast("moderngl.Uniform", self.shader.program["block_origin"])
        matrix_uniform.write(camera_matrix.T.astype("f4").tobytes())
        origin_uniform.value = block
        self.vertex_array.render(moderngl.LINES)

    def release(self) -> None:
        self.vertex_array.release()
        self.buffer.release()
        self.shader.release()
