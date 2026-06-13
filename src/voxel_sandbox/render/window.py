# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import moderngl
import pyglet
from pyglet.window import key, mouse

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.engine.physics import PlayerController, PlayerInput
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.input_state import KeyState, configure_layout_independent_game_keys
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram
from voxel_sandbox.render.ui.menu import MenuCommand, MenuController
from voxel_sandbox.render.world_scene import DemoWorldRenderer

LOGGER = logging.getLogger(__name__)
FIXED_UPDATE_SECONDS: Final = 1.0 / 60.0


class GameWindow(pyglet.window.Window):
    def __init__(self, settings: AppSettings, *, visible: bool = True) -> None:
        configure_layout_independent_game_keys()
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
        self.world_renderer = DemoWorldRenderer(
            self.mgl_context,
            seed=settings.world.seed,
            render_distance=settings.world.render_distance,
            generation_workers=settings.world.generation_workers,
            generation_backend=settings.world.generation_backend,
            uploads_per_frame=settings.world.chunk_uploads_per_frame,
            meshing_workers=settings.world.meshing_workers,
            meshing_backend=settings.world.meshing_backend,
            mesh_uploads_per_frame=settings.world.mesh_uploads_per_frame,
            greedy_meshing=settings.graphics.greedy_meshing,
            smooth_lighting=settings.graphics.smooth_lighting,
            ambient_occlusion=settings.graphics.ambient_occlusion,
            fog=settings.graphics.fog,
            fog_start=settings.graphics.fog_start,
            fog_end=settings.graphics.fog_end,
            day_cycle_seconds=settings.graphics.day_cycle_seconds,
        )
        self.menu = MenuController()
        spawn_x, spawn_y, spawn_z = self.world_renderer.spawn_position
        self.player = PlayerController(x=spawn_x, y=spawn_y, z=spawn_z)
        self._sync_camera_to_player()
        self.key_state = KeyState()
        self.place_block_id = 3
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
        self.crosshair = pyglet.text.Label(
            "+",
            anchor_x="center",
            anchor_y="center",
            font_name="Menlo",
            font_size=18,
            color=(245, 235, 190, 255),
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
        self.world_renderer.update(delta_time)
        forward = float(self.key_state.is_pressed(key.W)) - float(self.key_state.is_pressed(key.S))
        right = float(self.key_state.is_pressed(key.D)) - float(self.key_state.is_pressed(key.A))
        self.player.update(
            PlayerInput(
                forward=forward,
                right=right,
                jump=self.key_state.is_pressed(key.SPACE),
            ),
            self.camera.yaw_degrees,
            delta_time,
            self.world_renderer.is_solid_block,
        )
        self._sync_camera_to_player()

    def on_draw(self) -> None:
        clear_color = (
            self.world_renderer.clear_color if self.menu.in_game else (0.025, 0.04, 0.075, 1.0)
        )
        self.mgl_context.clear(*clear_color, depth=1.0)
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
            f"Grounded {self.player.on_ground}  VelocityY {self.player.velocity_y:5.2f}\n"
            f"Yaw {self.camera.yaw_degrees:6.1f}  Pitch {self.camera.pitch_degrees:5.1f}"
            f"\nChunks {self.world_renderer.loaded_chunks}  "
            f"Pending {self.world_renderer.pending_chunks}  "
            f"Mesh queue {self.world_renderer.pending_meshes}  "
            f"Visible sections {self.world_renderer.visible_sections}\n"
            f"Faces {self.world_renderer.face_count}  "
            f"Triangles {self.world_renderer.triangle_count}  "
            f"Draws {self.world_renderer.draw_calls}\n"
            f"Daylight {self.world_renderer.daylight:4.2f}  "
            f"Smooth {self.world_renderer.smooth_lighting}  "
            f"AO {self.world_renderer.ambient_occlusion}  "
            f"Fog {self.world_renderer.fog_enabled}  "
            f"Mesher {'greedy' if self.world_renderer.greedy_meshing else 'visible'}\n"
            f"Place {self.world_renderer.registry.by_id(self.place_block_id).name}  "
            "[1 grass, 2 lantern; F6 smooth, F7 AO, F8 fog, F9 mesher]"
        )
        if self.world_renderer.selection is not None:
            self.debug_label.text += f"\nTarget {self.world_renderer.selection.block}"
        self.debug_label.y = self.height - 10
        self.debug_label.draw()
        self.crosshair.x = self.width // 2
        self.crosshair.y = self.height // 2
        self.crosshair.draw()
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
        if symbol == key.F6:
            self.world_renderer.toggle_smooth_lighting()
            return
        if symbol == key.F7:
            self.world_renderer.toggle_ambient_occlusion()
            return
        if symbol == key.F8:
            self.world_renderer.toggle_fog()
            return
        if symbol == key.F9:
            self.world_renderer.toggle_mesher()
            return
        if symbol == ord("1"):
            self.place_block_id = 3
            return
        if symbol == ord("2"):
            self.place_block_id = 7
            return
        self.key_state.press(symbol)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        del modifiers
        self.key_state.release(symbol)

    def on_deactivate(self) -> None:
        self.key_state.clear()
        if self.mouse_captured:
            self.mouse_captured = False
            self.set_exclusive_mouse(False)

    def on_activate(self) -> None:
        self._sync_mouse_capture()

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        del modifiers
        if button == mouse.LEFT and not self.menu.in_game:
            index = self._menu_index_at(x, y)
            if index is not None:
                self.menu.select(index)
                self._handle_menu_command(self.menu.activate())
                self._sync_mouse_capture()
            return
        if not self.menu.in_game or not self.mouse_captured:
            return
        hit = self.world_renderer.raycast(self.camera.position, self.camera.direction)
        if hit is None:
            return
        if button == mouse.LEFT:
            self.world_renderer.set_block(hit.block, 0)
        elif button == mouse.RIGHT and not self.player.intersects_block(hit.previous):
            self.world_renderer.set_block(hit.previous, self.place_block_id)

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
        if not should_capture:
            self.key_state.clear()
        if should_capture != self.mouse_captured:
            self.mouse_captured = should_capture
            self.set_exclusive_mouse(should_capture)

    def _sync_camera_to_player(self) -> None:
        self.camera.x, self.camera.y, self.camera.z = self.player.eye_position


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
