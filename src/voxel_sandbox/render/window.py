# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import logging
import math
import queue
import time
from pathlib import Path
from typing import Final, cast

import moderngl
import pyglet
from pyglet.window import key, mouse

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.domain.crafting import RecipeBook
from voxel_sandbox.domain.inventory import Hotbar, Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, ChunkCoord
from voxel_sandbox.engine.ecs import EntitySimulation, RenderModel, Transform
from voxel_sandbox.engine.physics import PlayerController, PlayerInput
from voxel_sandbox.infrastructure.storage import PlayerSnapshot
from voxel_sandbox.network import (
    ClientSession,
    LanServer,
    Message,
    decode_chunk_blocks,
    discover_worlds,
)
from voxel_sandbox.network.discovery import DiscoveryResponder
from voxel_sandbox.network.interpolation import SnapshotInterpolator, reconcile_position
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.entity_renderer import EntityRenderer
from voxel_sandbox.render.input_state import KeyState, configure_layout_independent_game_keys
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram
from voxel_sandbox.render.ui.menu import MenuCommand, MenuController
from voxel_sandbox.render.ui.text_input import TextInput, TextPurpose
from voxel_sandbox.render.world_scene import DemoWorldRenderer

LOGGER = logging.getLogger(__name__)
FIXED_UPDATE_SECONDS: Final = 1.0 / 60.0


class GameWindow(pyglet.window.Window):
    def __init__(
        self,
        settings: AppSettings,
        *,
        visible: bool = True,
        save_root: Path | None = None,
        connect: str | None = None,
        player_name: str = "Player",
    ) -> None:
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
            save_root=save_root or Path(__file__).parents[3] / "saves" / "dev_world",
        )
        self.menu = MenuController()
        spawn_x, spawn_y, spawn_z = self.world_renderer.spawn_position
        self.player = PlayerController(x=spawn_x, y=spawn_y, z=spawn_z)
        self._sync_camera_to_player()
        self.key_state = KeyState()
        self.item_registry = create_core_item_registry()
        self.inventory = Inventory()
        self.hotbar = Hotbar(self.inventory)
        self.inventory.set(0, ItemStack(3, 32), self.item_registry)
        self.inventory.set(1, ItemStack(7, 8), self.item_registry)
        self.inventory.set(2, ItemStack(8, 1), self.item_registry)
        self.inventory.set(3, ItemStack(4, 4), self.item_registry)
        self.player_health = 20.0
        recovered_saved_position: tuple[float, float, float] | None = None
        saved_player = self.world_renderer.storage.load_player(self.item_registry)
        if saved_player is not None:
            self.world_renderer.storage.restore_inventory(
                saved_player,
                self.inventory,
                self.item_registry,
            )
            self.player_health = saved_player.health
            self.hotbar.select(saved_player.selected_slot)
            if not self._restore_player_position(saved_player.position):
                recovered_saved_position = saved_player.position
            self._sync_camera_to_player()
        recipes_path = Path(__file__).parents[3] / "config" / "recipes.toml"
        self.recipe_book = RecipeBook.from_toml(recipes_path, self.item_registry)
        self.entities = EntitySimulation(seed=self.world_renderer.generator.seed.value)
        self.entities.maintain_population(
            (spawn_x, spawn_y, spawn_z),
            self.world_renderer.generator.height_at,
            self._is_entity_hazard,
        )
        self.entity_renderer = EntityRenderer(self.mgl_context)
        self._population_accumulator = 0.0
        self._autosave_accumulator = 0.0
        self._network_accumulator = 0.0
        self.network_session: ClientSession | None = None
        self.lan_server: LanServer | None = None
        self.lan_discovery: DiscoveryResponder | None = None
        self.lan_block_actions: queue.SimpleQueue[tuple[tuple[int, int, int], int]] = (
            queue.SimpleQueue()
        )
        self.remote_player_entities: dict[int, int] = {}
        self.remote_player_interpolation: dict[int, SnapshotInterpolator] = {}
        self.remote_chunks_received = 0
        self.requested_remote_chunks: set[ChunkCoord] = set()
        self.network_players: dict[object, object] = {}
        self.last_snapshot_sequence = 0
        self.player_name = player_name[:32] or "Player"
        self.inventory_open = False
        self.text_input: TextInput | None = None
        self.crafting_grid_size = 2
        self.inventory_status = (
            "Recovered invalid saved position" if recovered_saved_position is not None else ""
        )
        self.cursor_stack: ItemStack | None = None
        self.mouse_x = 0
        self.mouse_y = 0
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
        self.hotbar_labels = [
            pyglet.text.Label(
                "",
                anchor_x="center",
                anchor_y="center",
                font_name="Menlo",
                font_size=9,
                color=(225, 230, 240, 255),
            )
            for _ in range(9)
        ]
        self.inventory_title = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            font_name="Menlo",
            font_size=16,
            color=(245, 220, 140, 255),
        )
        self.inventory_labels = [
            pyglet.text.Label(
                "",
                anchor_x="center",
                anchor_y="center",
                font_name="Menlo",
                font_size=8,
                color=(215, 220, 235, 255),
            )
            for _ in range(len(self.inventory))
        ]
        self.cursor_item_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="bottom",
            font_name="Menlo",
            font_size=9,
            color=(245, 220, 140, 255),
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
        self.text_input_label = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            align="center",
            multiline=True,
            width=600,
            font_name="Menlo",
            font_size=14,
            color=(245, 220, 140, 255),
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
        if connect is not None:
            self._connect_remote(connect, player_name)
        if recovered_saved_position is not None:
            LOGGER.warning("Recovered invalid saved player position: %s", recovered_saved_position)
            self._save_player()
        pyglet.clock.schedule_interval(self.fixed_update, FIXED_UPDATE_SECONDS)
        if settings.development.shader_hot_reload:
            pyglet.clock.schedule_interval(self.reload_shaders, 0.5)
        LOGGER.info("ModernGL context: %s", self.mgl_context.info.get("GL_VERSION", "unknown"))

    def close(self) -> None:
        pyglet.clock.unschedule(self.fixed_update)
        pyglet.clock.unschedule(self.reload_shaders)
        if self.network_session is not None:
            self.network_session.close()
        if self.lan_discovery is not None:
            self.lan_discovery.stop()
        if self.lan_server is not None:
            self.lan_server.stop()
        self._save_player()
        self.world_renderer.autosave()
        self.debug_shader.release()
        self.entity_renderer.release()
        self.world_renderer.release()
        super().close()

    def reload_shaders(self, delta_time: float) -> None:
        del delta_time
        self.debug_shader.reload_if_changed()

    def fixed_update(self, delta_time: float) -> None:
        self._apply_lan_block_actions()
        if not self.menu.in_game:
            return
        if not self._player_position_within_world():
            self._move_player_to_spawn()
            self.inventory_status = "Recovered from outside the world"
        self.world_renderer.update(delta_time)
        self._network_accumulator += delta_time
        if self.network_session is not None:
            self._process_network_messages()
            self._update_remote_players()
            if self._network_accumulator >= 0.05:
                self._network_accumulator %= 0.05
                self.network_session.send(
                    {
                        "type": "input",
                        "position": [self.player.x, self.player.y, self.player.z],
                    }
                )
                self._request_remote_chunk()
        self._autosave_accumulator += delta_time
        if self._autosave_accumulator >= 5.0:
            self._autosave_accumulator %= 5.0
            self._save_player()
            self.world_renderer.autosave()
        self._population_accumulator += delta_time
        if self._population_accumulator >= 1.0:
            self._population_accumulator %= 1.0
            self.entities.maintain_population(
                (self.player.x, self.player.y, self.player.z),
                self.world_renderer.generator.height_at,
                self._is_entity_hazard,
            )
        self.player_health -= self.entities.update(
            delta_time,
            (self.player.x, self.player.y, self.player.z),
            self.world_renderer.generator.height_at,
            self._is_entity_hazard,
        )
        if self.player_health <= 0.0:
            spawn_x, spawn_y, spawn_z = self.world_renderer.spawn_position
            self.player.x, self.player.y, self.player.z = spawn_x, spawn_y, spawn_z
            self.player.velocity_y = 0.0
            self.player_health = 20.0
            self.inventory_status = "Respawned"
        picked_up = self.entities.pickup_items(
            (self.player.x, self.player.y + 0.5, self.player.z),
            1.5,
            self.inventory,
            self.item_registry,
        )
        if picked_up:
            self.inventory_status = "Picked up " + ", ".join(
                f"{self.item_registry.by_id(stack.item_id).name} x{stack.count}"
                for stack in picked_up
            )
        if self.inventory_open:
            return
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
        entity_draws = self.entity_renderer.render(
            self.entities.world,
            self.camera,
            self.width,
            self.height,
            self.settings.camera.field_of_view,
            self.world_renderer.animation_time,
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
            f"Health {self.player_health:4.1f}  "
            f"Entities {len(self.entities.world.alive)}  "
            f"Mobs {len(self.entities.world.mob_ai)}  "
            f"Drops {len(self.entities.world.items)}  Entity draws {entity_draws}\n"
            f"Selected {self._selected_item_name()}  "
            "[1-9 hotbar, E inventory, C craft, Q drop]"
        )
        if self.world_renderer.selection is not None:
            self.debug_label.text += f"\nTarget {self.world_renderer.selection.block}"
        self.debug_label.y = self.height - 10
        self.debug_label.draw()
        self.crosshair.x = self.width // 2
        self.crosshair.y = self.height // 2
        self.crosshair.draw()
        self._draw_hotbar()
        if self.inventory_open:
            self._draw_inventory()
        if self.text_input is not None:
            self._draw_text_input()
        self.fps_display.draw()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        del modifiers
        if self.text_input is not None:
            if symbol in {key.ENTER, key.RETURN}:
                self._submit_text_input()
            elif symbol == key.ESCAPE:
                self.text_input = None
            elif symbol == key.BACKSPACE:
                self.text_input.backspace()
            self._sync_mouse_capture()
            return
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
        if symbol == key.E:
            if self.inventory_open:
                self._close_inventory()
            else:
                self.inventory_open = True
                self.crafting_grid_size = 2
                self.inventory_status = "Player crafting: 2x2"
            self.key_state.clear()
            self._sync_mouse_capture()
            return
        if self.inventory_open:
            if symbol == key.ESCAPE:
                self._close_inventory()
                self._sync_mouse_capture()
            elif symbol == key.C:
                self._craft_first_available()
            elif ord("1") <= symbol <= ord("9"):
                self.hotbar.select(symbol - ord("1"))
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
        if ord("1") <= symbol <= ord("9"):
            self.hotbar.select(symbol - ord("1"))
            return
        if symbol == key.Q:
            self._drop_selected_item()
            return
        if symbol == key.T:
            self._begin_text_input(TextPurpose.CHAT, "Chat message", maximum_length=256)
            return
        self.key_state.press(symbol)

    def on_text(self, text: str) -> None:
        if self.text_input is not None:
            self.text_input.append(text)

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
        if button == mouse.LEFT and not self.menu.in_game:
            index = self._menu_index_at(x, y)
            if index is not None:
                self.menu.select(index)
                self._handle_menu_command(self.menu.activate())
                self._sync_mouse_capture()
            return
        if self.menu.in_game and self.inventory_open:
            slot = self._inventory_slot_at(x, y)
            if slot is not None:
                self._handle_inventory_click(
                    slot,
                    button,
                    quick_move=bool(modifiers & key.MOD_SHIFT),
                )
            return
        if not self.menu.in_game or not self.mouse_captured or self.inventory_open:
            return
        if button == mouse.LEFT:
            target = self.entities.target_mob(self.camera.position, self.camera.direction)
            if target is not None:
                drops = self.entities.damage(target, 4.0)
                self.inventory_status = "Mob defeated" if drops else "Hit mob"
                return
        hit = self.world_renderer.raycast(self.camera.position, self.camera.direction)
        if hit is None:
            return
        if button == mouse.LEFT:
            block_id = self.world_renderer.get_block(*hit.block)
            if self.world_renderer.set_block(hit.block, 0):
                self._send_block_action(hit.block, 0)
                drop = self.item_registry.drop_for_block(block_id)
                if drop is not None:
                    self.entities.spawn_item(
                        (
                            float(hit.block[0]) + 0.5,
                            float(hit.block[1]) + 0.5,
                            float(hit.block[2]) + 0.5,
                        ),
                        drop,
                    )
        elif button == mouse.RIGHT:
            if self.world_renderer.get_block(*hit.block) == 10:
                self.inventory_open = True
                self.crafting_grid_size = 3
                self.inventory_status = "Runecraft Table: 3x3 crafting"
                self._sync_mouse_capture()
                return
            selected = self.hotbar.selected
            if selected is None or self.player.intersects_block(hit.previous):
                return
            definition = self.item_registry.by_id(selected.item_id)
            if definition.block_id is None:
                return
            if self.world_renderer.set_block(hit.previous, definition.block_id):
                self._send_block_action(hit.previous, definition.block_id)
                self.inventory.take_from_slot(self.hotbar.selected_index)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        del x, y, scroll_x
        if self.menu.in_game and not self.inventory_open and scroll_y:
            self.hotbar.cycle(-1 if scroll_y > 0 else 1)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
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
        if self.text_input is not None:
            self._draw_text_input()

    def _draw_text_input(self) -> None:
        assert self.text_input is not None
        self.text_input_label.text = self.text_input.display
        self.text_input_label.x = self.width // 2
        self.text_input_label.y = self.height // 3
        self.text_input_label.draw()

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
        elif command is MenuCommand.DISCOVER_LAN:
            worlds = discover_worlds()
            if not worlds:
                self.menu.status = "No LAN worlds found. Start Open to LAN or a dedicated server."
                return
            world = worlds[0]
            try:
                self._connect_remote(f"{world.host}:{world.port}", self.player_name)
            except (OSError, ValueError) as error:
                self.menu.status = f"LAN connection failed: {error}"
        elif command is MenuCommand.DIRECT_CONNECT:
            self._begin_text_input(
                TextPurpose.DIRECT_CONNECT,
                "Server address (HOST:PORT)",
                initial="127.0.0.1:25565",
            )
        elif command is MenuCommand.EDIT_NICKNAME:
            self._begin_text_input(
                TextPurpose.NICKNAME,
                "Nickname",
                initial=self.player_name,
                maximum_length=32,
            )
        elif command is MenuCommand.OPEN_LAN:
            self.open_to_lan()

    def _sync_mouse_capture(self) -> None:
        should_capture = self.menu.in_game and not self.inventory_open and self.text_input is None
        if not should_capture:
            self.key_state.clear()
        if should_capture != self.mouse_captured:
            self.mouse_captured = should_capture
            self.set_exclusive_mouse(should_capture)

    def _sync_camera_to_player(self) -> None:
        self.camera.x, self.camera.y, self.camera.z = self.player.eye_position

    def _selected_item_name(self) -> str:
        selected = self.hotbar.selected
        if selected is None:
            return "empty"
        definition = self.item_registry.by_id(selected.item_id)
        return f"{definition.name} x{selected.count}"

    def _begin_text_input(
        self,
        purpose: TextPurpose,
        prompt: str,
        *,
        initial: str = "",
        maximum_length: int = 128,
    ) -> None:
        self.text_input = TextInput(purpose, prompt, initial, maximum_length)
        self.key_state.clear()
        self._sync_mouse_capture()

    def _submit_text_input(self) -> None:
        field = self.text_input
        if field is None:
            return
        value = field.value.strip()
        if field.purpose is TextPurpose.NICKNAME:
            self.player_name = value[:32] or "Player"
            self.menu.status = f"Nickname: {self.player_name}"
            self.text_input = None
        elif field.purpose is TextPurpose.DIRECT_CONNECT:
            if not value:
                self.menu.status = "Server address is required."
                return
            try:
                self._connect_remote(value, self.player_name)
            except (OSError, ValueError) as error:
                self.menu.status = f"Connection failed: {error}"
                return
            self.text_input = None
        elif field.purpose is TextPurpose.CHAT:
            if value and self.network_session is not None:
                try:
                    self.network_session.send({"type": "chat", "text": value})
                except (ConnectionError, OSError) as error:
                    self.inventory_status = f"Chat failed: {error}"
            elif value:
                self.inventory_status = "Chat is available in multiplayer."
            self.text_input = None
        self._sync_mouse_capture()

    def _drop_selected_item(self) -> None:
        stack = self.inventory.take_from_slot(self.hotbar.selected_index)
        if stack is None:
            return
        direction = self.camera.direction
        position = (
            self.camera.position[0] + direction[0] * 1.5,
            self.camera.position[1] + direction[1] * 1.5,
            self.camera.position[2] + direction[2] * 1.5,
        )
        self.entities.spawn_item(position, stack)
        self.inventory_status = f"Dropped {self.item_registry.by_id(stack.item_id).name}"

    def _craft_first_available(self) -> None:
        for recipe in reversed(self.recipe_book.recipes):
            if self.recipe_book.craft_from_inventory(
                recipe.key,
                self.inventory,
                self.item_registry,
                grid_size=self.crafting_grid_size,
            ):
                result = self.item_registry.by_id(recipe.result.item_id)
                self.inventory_status = f"Crafted {result.name} x{recipe.result.count}"
                return
        self.inventory_status = "No available recipe for this crafting grid"

    def _draw_hotbar(self) -> None:
        slot_width = 105
        start_x = self.width // 2 - slot_width * 4
        for index, label in enumerate(self.hotbar_labels):
            stack = self.inventory[index]
            marker = ">" if index == self.hotbar.selected_index else " "
            if stack is None:
                text = "empty"
            else:
                text = f"{self.item_registry.by_id(stack.item_id).name[:10]} x{stack.count}"
            label.text = f"{marker}{index + 1}:{text}"
            label.x = start_x + index * slot_width
            label.y = 26
            label.color = (
                (245, 220, 140, 255)
                if index == self.hotbar.selected_index
                else (205, 215, 235, 255)
            )
            label.draw()

    def _draw_inventory(self) -> None:
        self.inventory_title.text = (
            f"Inventory / {self.crafting_grid_size}x{self.crafting_grid_size} crafting - "
            "C: craft first available, E/Esc: close"
        )
        self.inventory_title.x = self.width // 2
        self.inventory_title.y = self.height * 3 // 4
        self.inventory_title.draw()
        start_x = self.width // 2 - 4 * 120
        start_y = self.height * 2 // 3
        for index, label in enumerate(self.inventory_labels):
            stack = self.inventory[index]
            label.text = (
                f"{index + 1}: empty"
                if stack is None
                else f"{index + 1}: {self.item_registry.by_id(stack.item_id).name} x{stack.count}"
            )
            label.x = start_x + (index % self.inventory.width) * 120
            label.y = start_y - (index // self.inventory.width) * 42
            label.draw()
        self.menu_status.text = self.inventory_status
        self.menu_status.x = self.width // 2
        self.menu_status.y = self.height // 3
        self.menu_status.draw()
        if self.cursor_stack is not None:
            definition = self.item_registry.by_id(self.cursor_stack.item_id)
            self.cursor_item_label.text = f"{definition.name} x{self.cursor_stack.count}"
            self.cursor_item_label.x = self.mouse_x + 12
            self.cursor_item_label.y = self.mouse_y + 12
            self.cursor_item_label.draw()

    def _inventory_slot_at(self, x: int, y: int) -> int | None:
        start_x = self.width // 2 - 4 * 120
        start_y = self.height * 2 // 3
        for index in range(len(self.inventory)):
            slot_x = start_x + (index % self.inventory.width) * 120
            slot_y = start_y - (index // self.inventory.width) * 42
            if abs(x - slot_x) <= 56 and abs(y - slot_y) <= 16:
                return index
        return None

    def _handle_inventory_click(self, index: int, button: int, *, quick_move: bool) -> None:
        if quick_move and button == mouse.LEFT and self.cursor_stack is None:
            target_range = range(9, len(self.inventory)) if index < 9 else range(9)
            for target in target_range:
                self.inventory.move(index, target, self.item_registry)
                if self.inventory[index] is None:
                    break
            return
        current = self.inventory[index]
        if button == mouse.LEFT:
            if self.cursor_stack is None:
                if current is not None:
                    self.cursor_stack = self.inventory.take_from_slot(index, current.count)
                return
            if current is None:
                self.inventory.set(index, self.cursor_stack, self.item_registry)
                self.cursor_stack = None
                return
            if current.item_id != self.cursor_stack.item_id:
                self.inventory.set(index, self.cursor_stack, self.item_registry)
                self.cursor_stack = current
                return
            maximum = self.item_registry.by_id(current.item_id).max_stack
            moved = min(maximum - current.count, self.cursor_stack.count)
            if moved:
                self.inventory.set(
                    index,
                    current.with_count(current.count + moved),
                    self.item_registry,
                )
                remaining = self.cursor_stack.count - moved
                self.cursor_stack = self.cursor_stack.with_count(remaining) if remaining else None
        elif button == mouse.RIGHT:
            if self.cursor_stack is None:
                self.cursor_stack = self.inventory.split(index)
                return
            if current is None:
                self.inventory.set(
                    index,
                    self.cursor_stack.with_count(1),
                    self.item_registry,
                )
            elif (
                current.item_id == self.cursor_stack.item_id
                and current.count < self.item_registry.by_id(current.item_id).max_stack
            ):
                self.inventory.set(
                    index,
                    current.with_count(current.count + 1),
                    self.item_registry,
                )
            else:
                return
            remaining = self.cursor_stack.count - 1
            self.cursor_stack = self.cursor_stack.with_count(remaining) if remaining else None

    def _close_inventory(self) -> None:
        if self.cursor_stack is not None:
            remainder = self.inventory.add(self.cursor_stack, self.item_registry)
            if remainder is not None:
                self.entities.spawn_item(
                    (self.player.x, self.player.y + 0.5, self.player.z),
                    remainder,
                )
            self.cursor_stack = None
        self.inventory_open = False
        self.inventory_status = ""

    def _is_entity_hazard(self, x: int, y: int, z: int) -> bool:
        block_id = self.world_renderer.get_block(x, y, z)
        return self.world_renderer.registry.by_id(block_id).is_fluid

    def _restore_player_position(self, position: tuple[float, float, float]) -> bool:
        if not self._position_within_world(position):
            self._move_player_to_spawn()
            return False
        x, y, z = position
        self.world_renderer.ensure_collision_area_loaded(x, z, self.player.width / 2.0)
        self.player.x, self.player.y, self.player.z = x, y, z
        self.player.velocity_y = 0.0
        self.player.on_ground = False
        if self.player.collides(self.world_renderer.is_solid_block):
            self._move_player_to_spawn()
            return False
        return True

    def _player_position_within_world(self) -> bool:
        return self._position_within_world((self.player.x, self.player.y, self.player.z))

    def _position_within_world(self, position: tuple[float, float, float]) -> bool:
        x, y, z = position
        return (
            all(math.isfinite(value) for value in position)
            and 0.0 <= y <= CHUNK_HEIGHT - self.player.height
            and abs(x) <= 30_000_000.0
            and abs(z) <= 30_000_000.0
        )

    def _move_player_to_spawn(self) -> None:
        spawn_x, spawn_y, spawn_z = self.world_renderer.spawn_position
        self.player.x, self.player.y, self.player.z = spawn_x, spawn_y, spawn_z
        self.player.velocity_y = 0.0
        self.player.on_ground = False

    def _save_player(self) -> None:
        self.world_renderer.storage.save_player(
            PlayerSnapshot(
                (self.player.x, self.player.y, self.player.z),
                self.player_health,
                self.hotbar.selected_index,
                tuple(self.inventory),
            )
        )

    def _connect_remote(self, target: str, player_name: str) -> None:
        host, separator, raw_port = target.rpartition(":")
        if not separator or not host:
            raise ValueError("Connect address must use HOST:PORT")
        session = ClientSession()
        joined = session.connect(host, int(raw_port), name=player_name[:32] or "Player")
        self.network_session = session
        self.world_renderer.enable_remote_mode()
        self.inventory_status = f"Connected as player {joined['player_id']}"
        session.send({"type": "request_chunk", "coord": [0, 0]})
        self.requested_remote_chunks.add(ChunkCoord(0, 0))
        from voxel_sandbox.render.ui.menu import Screen

        self.menu.screen = Screen.GAME
        self._sync_mouse_capture()

    def _process_network_messages(self) -> None:
        assert self.network_session is not None
        for message in self.network_session.poll():
            self._apply_network_message(message)

    def _apply_network_message(self, message: Message) -> None:
        message_type = message.get("type")
        if message_type == "chunk":
            coord = message.get("coord")
            payload = message.get("blocks")
            if (
                isinstance(coord, list)
                and len(cast(list[object], coord)) == 2
                and all(isinstance(value, int) for value in cast(list[object], coord))
                and isinstance(payload, bytes)
            ):
                values = cast(list[int], coord)
                self.world_renderer.install_remote_chunk(
                    decode_chunk_blocks(ChunkCoord(values[0], values[1]), payload)
                )
                self.remote_chunks_received += 1
        elif message_type == "block_delta":
            position = message.get("position")
            block_id = message.get("block_id")
            if (
                isinstance(position, list)
                and len(cast(list[object], position)) == 3
                and all(isinstance(value, int) for value in cast(list[object], position))
                and isinstance(block_id, int)
            ):
                values = cast(list[int], position)
                self.world_renderer.set_block((values[0], values[1], values[2]), block_id)
        elif message_type == "entity_snapshot":
            players = message.get("players")
            sequence = message.get("sequence", 0)
            full = message.get("full", True)
            removed = message.get("removed", [])
            if (
                isinstance(players, dict)
                and isinstance(sequence, int)
                and sequence > self.last_snapshot_sequence
            ):
                self.last_snapshot_sequence = sequence
                if full is True:
                    self.network_players = dict(cast(dict[object, object], players))
                else:
                    self.network_players.update(cast(dict[object, object], players))
                    if isinstance(removed, list):
                        for player_id in cast(list[object], removed):
                            self.network_players.pop(player_id, None)
                self._sync_remote_players(self.network_players)
        elif message_type == "chat":
            self.inventory_status = f"Chat: {message.get('text', '')}"

    def _sync_remote_players(self, players: dict[object, object]) -> None:
        local_id = self.network_session.player_id if self.network_session is not None else None
        visible_ids: set[int] = set()
        for raw_id, raw_player in players.items():
            if not isinstance(raw_id, int) or not isinstance(raw_player, dict):
                continue
            player = cast(dict[object, object], raw_player)
            position = player.get("position")
            if not isinstance(position, list) or len(cast(list[object], position)) != 3:
                continue
            values = cast(list[object], position)
            if not all(isinstance(value, int | float) for value in values):
                continue
            coordinates = cast(list[int | float], values)
            position_tuple = (
                float(coordinates[0]),
                float(coordinates[1]),
                float(coordinates[2]),
            )
            if raw_id == local_id:
                corrected = reconcile_position(
                    (self.player.x, self.player.y, self.player.z),
                    position_tuple,
                )
                self.player.x, self.player.y, self.player.z = corrected
                self._sync_camera_to_player()
                continue
            entity = self.remote_player_entities.get(raw_id)
            if entity is None:
                entity = self.entities.world.create()
                self.remote_player_entities[raw_id] = entity
                self.remote_player_interpolation[raw_id] = SnapshotInterpolator()
                self.entities.world.render_models.set(
                    entity,
                    RenderModel("remote_player", (0.72, 0.58, 0.88), (0.65, 1.8, 0.65)),
                )
                self.entities.world.transforms.set(
                    entity,
                    Transform(float(coordinates[0]), float(coordinates[1]), float(coordinates[2])),
                )
            self.remote_player_interpolation[raw_id].push(
                time.monotonic(),
                position_tuple,
            )
            visible_ids.add(raw_id)
        for player_id in set(self.remote_player_entities) - visible_ids:
            self.entities.world.destroy(self.remote_player_entities.pop(player_id))
            self.remote_player_interpolation.pop(player_id, None)

    def _update_remote_players(self) -> None:
        now = time.monotonic()
        for player_id, interpolation in self.remote_player_interpolation.items():
            position = interpolation.sample(now)
            entity = self.remote_player_entities.get(player_id)
            if position is None or entity is None:
                continue
            transform = self.entities.world.transforms.get(entity)
            if transform is not None:
                transform.x, transform.y, transform.z = position

    def _send_block_action(self, block: tuple[int, int, int], block_id: int) -> None:
        if self.network_session is not None:
            self.network_session.send(
                {"type": "block_action", "position": list(block), "block_id": block_id}
            )
        elif self.lan_server is not None:
            self.lan_server.apply_block_action(block, block_id)

    def open_to_lan(self) -> None:
        if self.lan_server is not None:
            host, port = self.lan_server.address
            self.menu.status = f"World already open to LAN on {host}:{port}"
            return
        self.world_renderer.autosave()
        server = LanServer(
            "0.0.0.0",
            0,
            seed=self.world_renderer.seed_text,
            storage=self.world_renderer.storage,
            block_action_sink=lambda position, block_id: self.lan_block_actions.put(
                (position, block_id)
            ),
        )
        server.start()
        try:
            discovery = DiscoveryResponder(
                "0.0.0.0",
                25565,
                world_name="Veilstone Singleplayer World",
                game_port=server.address[1],
                player_count=lambda: server.player_count + 1,
            )
            discovery.start()
        except OSError as error:
            server.stop()
            self.menu.status = f"Could not open LAN discovery port 25565: {error}"
            return
        self.lan_server = server
        self.lan_discovery = discovery
        self.menu.world_open_to_lan = True
        self.menu.status = f"Open to LAN on port {server.address[1]}"

    def _apply_lan_block_actions(self) -> None:
        while True:
            try:
                block, block_id = self.lan_block_actions.get_nowait()
            except queue.Empty:
                return
            self.world_renderer.set_block(block, block_id)

    def _request_remote_chunk(self) -> None:
        if self.network_session is None:
            return
        center = ChunkCoord(int(self.player.x) // 16, int(self.player.z) // 16)
        desired = [
            ChunkCoord(center.x + dx, center.z + dz) for dx in range(-2, 3) for dz in range(-2, 3)
        ]
        for coord in sorted(
            desired,
            key=lambda item: (item.x - center.x) ** 2 + (item.z - center.z) ** 2,
        ):
            if coord in self.requested_remote_chunks:
                continue
            self.requested_remote_chunks.add(coord)
            self.network_session.send({"type": "request_chunk", "coord": [coord.x, coord.z]})
            return


def run_window(
    settings: AppSettings,
    *,
    smoke_test: bool = False,
    connect: str | None = None,
    player_name: str = "Player",
) -> None:
    temporary_save = None
    if smoke_test or connect is not None:
        import tempfile

        temporary_save = tempfile.TemporaryDirectory(prefix="veilstone-smoke-")
    window = GameWindow(
        settings,
        visible=not smoke_test,
        save_root=Path(temporary_save.name) if temporary_save is not None else None,
        connect=connect,
        player_name=player_name,
    )
    if smoke_test:
        window.switch_to()
        window.dispatch_events()
        window.dispatch_event("on_draw")
        window.flip()
        from voxel_sandbox.render.ui.menu import Screen

        window.menu.screen = Screen.GAME
        window.dispatch_event("on_draw")
        window.flip()
        window.dispatch_event("on_key_press", key.E, 0)
        window.dispatch_event("on_key_press", key.C, 0)
        window.dispatch_event("on_draw")
        window.flip()
        window.close()
        assert temporary_save is not None
        temporary_save.cleanup()
        return
    try:
        pyglet.app.run(1.0 / 120.0)
    finally:
        if temporary_save is not None:
            temporary_save.cleanup()
