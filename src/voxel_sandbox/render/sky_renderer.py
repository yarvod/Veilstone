# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import math
from pathlib import Path
from typing import cast

import moderngl

from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram


class SkyRenderer:
    def __init__(self, context: moderngl.Context, *, clouds: bool) -> None:
        self.context = context
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(context, ShaderFiles.from_directory(shader_root, "sky"))
        if self.shader.program is None:
            raise RuntimeError("Sky shader failed to compile")
        self.vertex_array = context.vertex_array(self.shader.program, [])
        self.clouds = clouds

    def render(
        self,
        camera: FirstPersonCamera,
        width: int,
        height: int,
        field_of_view: float,
        daylight: float,
        time_of_day: float,
        animation_time: float,
    ) -> None:
        program = self.shader.program
        if program is None:
            return
        cast("moderngl.Uniform", program["aspect_ratio"]).value = max(width, 1) / max(height, 1)
        cast("moderngl.Uniform", program["field_of_view"]).value = field_of_view
        cast("moderngl.Uniform", program["yaw"]).value = math.radians(camera.yaw_degrees)
        cast("moderngl.Uniform", program["pitch"]).value = math.radians(camera.pitch_degrees)
        cast("moderngl.Uniform", program["daylight"]).value = daylight
        cast("moderngl.Uniform", program["time_of_day"]).value = time_of_day
        cast("moderngl.Uniform", program["animation_time"]).value = animation_time
        cast("moderngl.Uniform", program["clouds_enabled"]).value = int(self.clouds)
        self.context.disable(moderngl.DEPTH_TEST)
        self.vertex_array.render(moderngl.TRIANGLES, vertices=3)
        self.context.enable(moderngl.DEPTH_TEST)

    def release(self) -> None:
        self.vertex_array.release()
        self.shader.release()
