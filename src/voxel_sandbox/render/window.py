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
from voxel_sandbox.render.ui.menu import MenuCommand, MenuController
from voxel_sandbox.render.world_scene import DemoWorldRenderer

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
        self.world_renderer = DemoWorldRenderer(self.mgl_context)
        self.camera = FirstPersonCamera()
        self.menu = MenuController()
        self.held_keys: set[int] = set()
        self.mouse_captured = False
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
        self.menu_title = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            font_name="Menlo",
            font_size=30,
            color=(220, 230, 255, 255),
        )
        self.menu_status = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            font_name="Menlo",
            font_size=10,
            color=(160, 180, 215, 255),
        )
        self.menu_labels = [
            pyglet.text.Label(
                "",
                anchor_x="center",
                anchor_y="center",
                font_name="Menlo",
                font_size=16,
            )
            for _ in range(6)
        ]
        pyglet.clock.schedule_interval(self.fixed_update, FIXED_UPDATE_SECONDS)
        if settings.development.shader_hot_reload:
            pyglet.clock.schedule_interval(self.reload_shaders, 0.5)
        LOGGER.info("ModernGL context: %s", self.mgl_context.info.get("GL_VERSION", "unknown"))

    def close(self) -> None:
        pyglet.clock.unschedule(self.fixed_update)
        pyglet.clock.unschedule(self.reload_shaders)
        self.debug_shader.release()
        self.world_renderer.release()
        super().close()

    def reload_shaders(self, delta_time: float) -> None:
        del delta_time
        self.debug_shader.reload_if_changed()

    def fixed_update(self, delta_time: float) -> None:
        if not self.menu.in_game:
            return
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
        if not self.menu.in_game:
            self._draw_menu()
            return
        self.world_renderer.render(
            self.camera,
            self.width,
            self.height,
            self.settings.camera.field_of_view,
        )
        x, y, z = self.camera.position
        fps = pyglet.clock.get_frequency()
        frame_time_ms = 1000.0 / fps if fps > 0.0 else 0.0
        self.debug_label.text = (
            f"FPS {fps:5.1f}  Frame {frame_time_ms:5.2f} ms\n"
            f"Position {x:7.2f} {y:7.2f} {z:7.2f}\n"
            f"Yaw {self.camera.yaw_degrees:6.1f}  Pitch {self.camera.pitch_degrees:5.1f}"
            f"\nFaces {self.world_renderer.mesh.face_count}  "
            f"Triangles {self.world_renderer.mesh.triangle_count}  Draws 1"
        )
        self.debug_label.y = self.height - 10
        self.debug_label.draw()
        self.fps_display.draw()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        del modifiers
        if not self.menu.in_game:
            if symbol in {key.UP, key.W}:
                self.menu.move_selection(-1)
            elif symbol in {key.DOWN, key.S}:
                self.menu.move_selection(1)
            elif symbol in {key.ENTER, key.RETURN, key.SPACE}:
                self._handle_menu_command(self.menu.activate())
            elif symbol == key.ESCAPE:
                self.menu.back()
            self._sync_mouse_capture()
            return
        if symbol == key.ESCAPE:
            self.menu.back()
            self._sync_mouse_capture()
            return
        if symbol == key.F5:
            self.debug_shader.reload(force=True)
            return
        self.held_keys.add(symbol)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        del modifiers
        self.held_keys.discard(symbol)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        del modifiers
        if button == mouse.LEFT and not self.menu.in_game:
            index = self._menu_index_at(x, y)
            if index is not None:
                self.menu.select(index)
                self._handle_menu_command(self.menu.activate())
                self._sync_mouse_capture()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        if not self.menu.in_game:
            index = self._menu_index_at(x, y)
            if index is not None:
                self.menu.select(index)
            return
        if self.mouse_captured:
            self.camera.rotate(
                float(dx),
                float(dy),
                self.settings.camera.mouse_sensitivity,
            )

    def _draw_menu(self) -> None:
        center_x = self.width // 2
        self.menu_title.text = self.menu.title
        self.menu_title.x = center_x
        self.menu_title.y = self.height * 3 // 4
        self.menu_title.draw()

        for index, label in enumerate(self.menu_labels):
            if index >= len(self.menu.items):
                label.text = ""
                continue
            label.text = self.menu.items[index].label
            label.x = center_x
            label.y = self._menu_item_y(index)
            label.color = (
                (245, 220, 140, 255)
                if index == self.menu.selected_index
                else (
                    205,
                    215,
                    235,
                    255,
                )
            )
            label.draw()

        self.menu_status.text = self.menu.status
        self.menu_status.x = center_x
        self.menu_status.y = self.height // 4
        self.menu_status.draw()

    def _menu_item_y(self, index: int) -> int:
        return self.height // 2 + 45 - index * 48

    def _menu_index_at(self, x: int, y: int) -> int | None:
        if abs(x - self.width // 2) > 180:
            return None
        for index in range(len(self.menu.items)):
            if abs(y - self._menu_item_y(index)) <= 20:
                return index
        return None

    def _handle_menu_command(self, command: MenuCommand) -> None:
        if command is MenuCommand.CLOSE:
            self.close()

    def _sync_mouse_capture(self) -> None:
        should_capture = self.menu.in_game
        if should_capture != self.mouse_captured:
            self.mouse_captured = should_capture
            self.set_exclusive_mouse(should_capture)


def run_window(settings: AppSettings, *, smoke_test: bool = False) -> None:
    window = GameWindow(settings, visible=not smoke_test)
    if smoke_test:
        window.switch_to()
        window.dispatch_events()
        window.dispatch_event("on_draw")
        window.flip()
        from voxel_sandbox.render.ui.menu import Screen

        window.menu.screen = Screen.GAME
        window.dispatch_event("on_draw")
        window.flip()
        window.close()
        return
    pyglet.app.run(1.0 / 120.0)
