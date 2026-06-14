# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from typing import cast

import moderngl

from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram


class PostProcessRenderer:
    def __init__(self, context: moderngl.Context, *, enabled: bool) -> None:
        self.context = context
        self.enabled = enabled
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(context, ShaderFiles.from_directory(shader_root, "postprocess"))
        if self.shader.program is None:
            raise RuntimeError("Postprocess shader failed to compile")
        self.vertex_array = context.vertex_array(self.shader.program, [])
        self.color_texture: moderngl.Texture | None = None
        self.depth_buffer: moderngl.Renderbuffer | None = None
        self.framebuffer: moderngl.Framebuffer | None = None
        self.size = (0, 0)

    def begin(self, width: int, height: int) -> bool:
        if not self.enabled:
            self.context.screen.use()
            return False
        self._ensure_size(max(width, 1), max(height, 1))
        assert self.framebuffer is not None
        self.framebuffer.use()
        self.context.viewport = (0, 0, max(width, 1), max(height, 1))
        return True

    def present(self, width: int, height: int) -> None:
        if not self.enabled:
            return
        assert self.color_texture is not None
        program = self.shader.program
        if program is None:
            return
        self.context.screen.use()
        self.context.viewport = (0, 0, max(width, 1), max(height, 1))
        self.context.disable(moderngl.DEPTH_TEST)
        self.color_texture.use(0)
        cast("moderngl.Uniform", program["scene_color"]).value = 0
        self.vertex_array.render(moderngl.TRIANGLES, vertices=3)
        self.context.enable(moderngl.DEPTH_TEST)

    def release(self) -> None:
        self._release_targets()
        self.vertex_array.release()
        self.shader.release()

    def _ensure_size(self, width: int, height: int) -> None:
        if self.size == (width, height):
            return
        self._release_targets()
        self.color_texture = self.context.texture((width, height), 4)
        self.color_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.depth_buffer = self.context.depth_renderbuffer((width, height))
        self.framebuffer = self.context.framebuffer(
            color_attachments=(self.color_texture,),
            depth_attachment=self.depth_buffer,
        )
        self.size = width, height

    def _release_targets(self) -> None:
        if self.framebuffer is not None:
            self.framebuffer.release()
            self.framebuffer = None
        if self.depth_buffer is not None:
            self.depth_buffer.release()
            self.depth_buffer = None
        if self.color_texture is not None:
            self.color_texture.release()
            self.color_texture = None
        self.size = (0, 0)
