from __future__ import annotations


def has_shader_capable_gl() -> bool:
    """Return whether Pyglet can create an OpenGL shader in this environment."""
    try:
        import pyglet
        from pyglet.gl import GL_VERTEX_SHADER, glCreateShader
        from pyglet.gl.lib import MissingFunctionException

        display = pyglet.display.get_display()
        if not display.get_screens():
            return False
        window = pyglet.window.Window(width=1, height=1, visible=False)
        try:
            shader = glCreateShader(GL_VERTEX_SHADER)
            return bool(shader)
        except MissingFunctionException:
            return False
        finally:
            window.close()
    except Exception:
        return False
