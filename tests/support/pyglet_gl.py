from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


@contextmanager
def shader_capable_gl_window() -> Generator[Any]:
    """Keep one hidden shader-capable window/context alive for a test scope."""
    import pyglet

    window = pyglet.window.Window(width=1, height=1, visible=False)
    try:
        window.switch_to()
        yield window
    finally:
        window.close()


def has_shader_capable_gl() -> bool:
    """Return whether Pyglet can create an OpenGL shader in this environment."""
    try:
        import pyglet
        from pyglet.gl import GL_VERTEX_SHADER, glCreateShader
        from pyglet.gl.lib import MissingFunctionException

        display = pyglet.display.get_display()
        if not display.get_screens():
            return False
        with shader_capable_gl_window():
            try:
                shader = glCreateShader(GL_VERTEX_SHADER)
                return bool(shader)
            except MissingFunctionException:
                return False
    except Exception:
        return False
