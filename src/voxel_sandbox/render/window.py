# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import moderngl
import pyglet
from pyglet.window import key, mouse

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.render.camera import FirstPersonCamera, MovementIntent
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram

LOGGER = logging.getLogger(__name__)
FIXED_UPDATE_SECONDS: Final = 1.0 / 60.0


class GameWindow(pyglet.window.Window):
    def __init__(self, settings: AppSettings, *, visible: bool = True) -> None:
        config = pyglet.gl.Config(
            major_version=3,
            minor_version=3,
            forward_compatible=True,
            double_buffer=True,
            depth_size=24,
        )
        super().__init__(
            width=settings.window.width,
            height=settings.window.height,
            caption=settings.window.title,
            fullscreen=settings.window.fullscreen,
            resizable=True,
            vsync=settings.window.vsync,
            visible=visible,
            config=config,
        )
        self.mgl_context = moderngl.create_context(require=330)
        self.mgl_context.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        self.settings = settings
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.debug_shader = ShaderProgram(
            self.mgl_context,
            ShaderFiles.from_directory(shader_root, "debug"),
        )
        self.camera = FirstPersonCamera()
        self.held_keys: set[int] = set()
        self.mouse_captured = visible
        if visible:
            self.set_exclusive_mouse(True)
        self.fps_display = pyglet.window.FPSDisplay(self)
        self.debug_label = pyglet.text.Label(
            "",
            x=10,
            y=self.height - 10,
            anchor_x="left",
            anchor_y="top",
            font_name="Menlo",
            font_size=11,
            color=(225, 235, 255, 255),
        )
        pyglet.clock.schedule_interval(self.fixed_update, FIXED_UPDATE_SECONDS)
        if settings.development.shader_hot_reload:
            pyglet.clock.schedule_interval(self.reload_shaders, 0.5)
        LOGGER.info("ModernGL context: %s", self.mgl_context.info.get("GL_VERSION", "unknown"))

    def close(self) -> None:
        pyglet.clock.unschedule(self.fixed_update)
        pyglet.clock.unschedule(self.reload_shaders)
        self.debug_shader.release()
        super().close()

    def reload_shaders(self, delta_time: float) -> None:
        del delta_time
        self.debug_shader.reload_if_changed()

    def fixed_update(self, delta_time: float) -> None:
        forward = float(key.W in self.held_keys) - float(key.S in self.held_keys)
        right = float(key.D in self.held_keys) - float(key.A in self.held_keys)
        up = float(key.SPACE in self.held_keys) - float(
            key.LSHIFT in self.held_keys or key.RSHIFT in self.held_keys
        )
        self.camera.move(
            MovementIntent(forward=forward, right=right, up=up),
            self.settings.camera.movement_speed,
            delta_time,
        )

    def on_draw(self) -> None:
        self.mgl_context.clear(0.025, 0.04, 0.075, 1.0, depth=1.0)
        x, y, z = self.camera.position
        self.debug_label.text = (
            f"Position {x:7.2f} {y:7.2f} {z:7.2f}\n"
            f"Yaw {self.camera.yaw_degrees:6.1f}  Pitch {self.camera.pitch_degrees:5.1f}"
        )
        self.debug_label.y = self.height - 10
        self.debug_label.draw()
        self.fps_display.draw()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        del modifiers
        if symbol == key.ESCAPE:
            self.mouse_captured = not self.mouse_captured
            self.set_exclusive_mouse(self.mouse_captured)
            return
        if symbol == key.F5:
            self.debug_shader.reload(force=True)
            return
        self.held_keys.add(symbol)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        del modifiers
        self.held_keys.discard(symbol)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        del x, y, modifiers
        if button == mouse.LEFT and not self.mouse_captured:
            self.mouse_captured = True
            self.set_exclusive_mouse(True)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        del x, y
        if self.mouse_captured:
            self.camera.rotate(
                float(dx),
                float(dy),
                self.settings.camera.mouse_sensitivity,
            )


def run_window(settings: AppSettings, *, smoke_test: bool = False) -> None:
    window = GameWindow(settings, visible=not smoke_test)
    if smoke_test:
        window.switch_to()
        window.dispatch_events()
        window.dispatch_event("on_draw")
        window.flip()
        window.close()
        return
    pyglet.app.run(1.0 / 120.0)
