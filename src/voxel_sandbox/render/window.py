# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import logging
import math
import queue
import sys
import time
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import Final, cast

import moderngl
import numpy as np
import pyglet
from pyglet.window import key, mouse

from voxel_sandbox.app.commands import (
    CommandError,
    ListStructuresCommand,
    SetDifficultyCommand,
    SetTimeCommand,
    SpawnStructureCommand,
    TeleportCommand,
    ToggleStructureCommand,
    parse_command,
)
from voxel_sandbox.app.paths import application_data_root, resource_path
from voxel_sandbox.app.settings import AppSettings, save_user_settings
from voxel_sandbox.audio import AudioDirector, AudioEvent, AudioEventKind
from voxel_sandbox.audio.runtime import create_audio_bus, volume_map
from voxel_sandbox.domain.blocks.structures import StructureSnapshot, StructureWorld
from voxel_sandbox.domain.crafting import CraftingGrid, RecipeBook
from voxel_sandbox.domain.inventory import Hotbar, Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkCoord
from voxel_sandbox.engine.ecs import AnimationState, EntitySimulation, RenderModel, Transform
from voxel_sandbox.engine.physics import PlayerController, PlayerInput
from voxel_sandbox.infrastructure.storage import PlayerSnapshot, WorldStorage
from voxel_sandbox.network import (
    ClientSession,
    LanServer,
    Message,
    decode_chunk_blocks,
    discover_worlds,
)
from voxel_sandbox.network.discovery import DiscoveryResponder
from voxel_sandbox.network.interpolation import SnapshotInterpolator
from voxel_sandbox.engine.authority import WorldAuthority, LocalWorldAuthority, NetworkWorldAuthority
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.entity_renderer import EntityRenderer
from voxel_sandbox.render.input_state import KeyState, configure_layout_independent_game_keys
from voxel_sandbox.render.postprocess import PostProcessRenderer
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram
from voxel_sandbox.render.sky_renderer import SkyRenderer
from voxel_sandbox.render.structure_renderer import StructureRenderer
from voxel_sandbox.render.ui.item_icons import (
    HEART_SIZE,
    ICON_SIZE,
    create_hand_image,
    create_heart_icons,
    create_item_icons,
)
from voxel_sandbox.render.ui.menu import MenuCommand, MenuController, Screen, platform_font_name
from voxel_sandbox.render.ui.renderer import UiRenderer
from voxel_sandbox.render.ui.text_input import TextInput, TextPurpose
import shutil
from voxel_sandbox.render.world_scene import DemoWorldRenderer

LOGGER = logging.getLogger(__name__)
FIXED_UPDATE_SECONDS: Final = 1.0 / 60.0


UI_FONT_NAME: Final = platform_font_name(sys.platform)


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
        self.audio = create_audio_bus(settings.audio)
        self.audio_director = AudioDirector(self.audio)
        self._footstep_accumulator = 0.0
        self.control_bindings = self._control_symbols()
        self.rebinding_action: str | None = None
        self.active_save_root = save_root or application_data_root() / "dev_world"
        self.pending_world_name = ""
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.debug_shader = ShaderProgram(
            self.mgl_context,
            ShaderFiles.from_directory(shader_root, "debug"),
        )
        self.camera = FirstPersonCamera()
        self.sky_renderer = SkyRenderer(self.mgl_context, clouds=settings.graphics.clouds)
        self.postprocess_renderer = PostProcessRenderer(
            self.mgl_context,
            enabled=settings.graphics.postprocess,
        )
        self.world_renderer = self._create_world_renderer(self.active_save_root)
        self.menu = MenuController()
        self.ui_renderer = UiRenderer(self.width, self.height)
        self._prof_frame_start = 0.0
        self._prof_fixed_update = 0.0
        self._prof_world_render = 0.0
        self._prof_ui_render = 0.0
        self._prof_streaming_update = 0.0
        self._prof_network_poll = 0.0
        self._prof_display_text = ""
        self._prof_last_update_time = time.time()
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
        recipes_path = resource_path("config/recipes.toml")
        self.recipe_book = RecipeBook.from_toml(recipes_path, self.item_registry)
        self.entities = EntitySimulation(seed=self.world_renderer.generator.seed.value)
        self._maintain_population((spawn_x, spawn_y, spawn_z))
        self.entity_renderer = EntityRenderer(self.mgl_context)
        self.structure_world = self.world_renderer.storage.load_structure_world()
        self.structure_renderer = StructureRenderer(
            self.mgl_context,
            self.world_renderer.registry,
        )
        self.last_structure_revision = self.structure_world.revision
        self._population_accumulator = 0.0
        self._autosave_accumulator = 0.0
        self._network_accumulator = 0.0
        self.network_session: ClientSession | None = None
        self.lan_server: LanServer | None = None
        self.authority: WorldAuthority | None = None
        self.lan_discovery: DiscoveryResponder | None = None
        self.lan_block_actions: queue.SimpleQueue[tuple[tuple[int, int, int], int]] = (
            queue.SimpleQueue()
        )
        self.remote_player_entities: dict[int, int] = {}
        self.remote_player_interpolation: dict[int, SnapshotInterpolator] = {}
        self.remote_chunks_received = 0
        self.requested_remote_chunks: set[ChunkCoord] = set()
        self.network_players: dict[int, dict[str, object]] = {}
        self.last_snapshot_sequence = 0
        self.player_name = player_name[:32] or "Player"
        self.inventory_open = False
        self.text_input: TextInput | None = None
        self.crafting_grid_size = 2
        self.crafting_grid = CraftingGrid(2, 2)
        self.inventory_status = (
            "Recovered invalid saved position" if recovered_saved_position is not None else ""
        )
        self.cursor_stack: ItemStack | None = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_captured = False
        self.debug_overlay_visible = False
        self.hud_batch = pyglet.graphics.Batch()
        self.hud_bg_group = pyglet.graphics.Group(order=0)
        self.hud_fg_group = pyglet.graphics.Group(order=1)
        self.hud_text_group = pyglet.graphics.Group(order=2)
        self.debug_label = pyglet.text.Label(
            "",
            x=10,
            y=self.height - 10,
            anchor_x="left",
            anchor_y="top",
            multiline=True,
            width=500,
            font_name=UI_FONT_NAME,
            font_size=11,
            color=(255, 255, 255, 255),
            batch=self.hud_batch,
            group=self.hud_text_group,
        )
        self.player_name_label = pyglet.text.Label(
            "",
            font_name=UI_FONT_NAME,
            font_size=14,
            anchor_x="center",
            anchor_y="center",
            color=(255, 255, 255, 255),
        )
        self.hud_top_left_label = pyglet.text.Label(
            "",
            x=10,
            y=self.height - 10,
            anchor_x="left",
            anchor_y="top",
            multiline=True,
            width=500,
            font_name=UI_FONT_NAME,
            font_size=13,
            color=(255, 255, 255, 255),
            batch=self.hud_batch,
            group=self.hud_text_group,
        )
        self.player_list_label = pyglet.text.Label(
            "",
            x=self.width // 2,
            y=self.height // 2,
            anchor_x="center",
            anchor_y="center",
            multiline=True,
            width=600,
            font_name=UI_FONT_NAME,
            font_size=16,
            color=(255, 255, 255, 255),
        )
        self.crosshair = pyglet.text.Label(
            "+",
            anchor_x="center",
            anchor_y="center",
            font_name=UI_FONT_NAME,
            font_size=18,
            color=(245, 235, 190, 255),
            batch=self.hud_batch,
            group=self.hud_text_group,
        )
        self.item_icon_images = create_item_icons(self.item_registry, self.world_renderer.registry)
        self.heart_images = create_heart_icons()
        self.heart_sprites = [
            pyglet.sprite.Sprite(
                self.heart_images[0], batch=self.hud_batch, group=self.hud_fg_group
            )
            for _ in range(10)
        ]
        default_icon = self.item_icon_images[1]
        self.hotbar_slots = [
            pyglet.shapes.BorderedRectangle(
                0, 0, 52, 52, 3, batch=self.hud_batch, group=self.hud_bg_group
            )
            for _ in range(9)
        ]
        self.hotbar_icons = [
            pyglet.sprite.Sprite(default_icon, batch=self.hud_batch, group=self.hud_fg_group)
            for _ in range(9)
        ]
        self.hotbar_count_labels = [
            pyglet.text.Label(
                "",
                anchor_x="right",
                anchor_y="bottom",
                font_name=UI_FONT_NAME,
                font_size=12,
                color=(255, 255, 255, 255),
                batch=self.hud_batch,
                group=self.hud_text_group,
            )
            for _ in range(9)
        ]
        self.hotbar_key_labels = [
            pyglet.text.Label(
                str(index + 1),
                anchor_x="left",
                anchor_y="top",
                font_name=UI_FONT_NAME,
                font_size=8,
                color=(190, 200, 215, 255),
                batch=self.hud_batch,
                group=self.hud_text_group,
            )
            for index in range(9)
        ]
        self.inventory_title = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            font_name=UI_FONT_NAME,
            font_size=22,
            color=(245, 220, 140, 255),
        )
        self.inventory_panel = pyglet.shapes.BorderedRectangle(
            0, 0, 540, 500, 4, color=(34, 38, 48), border_color=(132, 142, 158)
        )
        self.inventory_slots = [
            pyglet.shapes.BorderedRectangle(0, 0, 48, 48, 2) for _ in range(len(self.inventory))
        ]
        self.inventory_icons = [
            pyglet.sprite.Sprite(default_icon) for _ in range(len(self.inventory))
        ]
        self.inventory_count_labels = [
            pyglet.text.Label(
                "",
                anchor_x="right",
                anchor_y="bottom",
                font_name=UI_FONT_NAME,
                font_size=12,
                color=(255, 255, 255, 255),
            )
            for _ in range(len(self.inventory))
        ]
        self.crafting_slots = [pyglet.shapes.BorderedRectangle(0, 0, 48, 48, 2) for _ in range(9)]
        self.crafting_icons = [pyglet.sprite.Sprite(default_icon) for _ in range(9)]
        self.crafting_count_labels = [
            pyglet.text.Label(
                "",
                anchor_x="right",
                anchor_y="bottom",
                font_name=UI_FONT_NAME,
                font_size=12,
                color=(255, 255, 255, 255),
            )
            for _ in range(9)
        ]
        self.crafting_result_slot = pyglet.shapes.BorderedRectangle(0, 0, 56, 56, 3)
        self.crafting_result_icon = pyglet.sprite.Sprite(default_icon)
        self.crafting_result_count = pyglet.text.Label(
            "",
            anchor_x="right",
            anchor_y="bottom",
            font_name=UI_FONT_NAME,
            font_size=12,
        )
        self.crafting_label = pyglet.text.Label(
            "CRAFTING",
            anchor_x="left",
            anchor_y="bottom",
            font_name=UI_FONT_NAME,
            font_size=13,
            color=(205, 215, 230, 255),
        )
        self.crafting_arrow = pyglet.text.Label(
            ">",
            anchor_x="center",
            anchor_y="center",
            font_name=UI_FONT_NAME,
            font_size=26,
        )
        self.cursor_item_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="bottom",
            font_name=UI_FONT_NAME,
            font_size=13,
            color=(245, 220, 140, 255),
        )
        self.cursor_item_icon = pyglet.sprite.Sprite(default_icon)
        self.held_item_icon = pyglet.sprite.Sprite(
            default_icon, batch=self.hud_batch, group=self.hud_fg_group
        )
        self.held_hand_sprite = pyglet.sprite.Sprite(
            create_hand_image(), batch=self.hud_batch, group=self.hud_fg_group
        )
        self.hud_status_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="bottom",
            font_name=UI_FONT_NAME,
            font_size=13,
            color=(245, 235, 210, 255),
            batch=self.hud_batch,
            group=self.hud_text_group,
        )
        self.menu_title = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            font_name=UI_FONT_NAME,
            font_size=38,
            color=(220, 230, 255, 255),
        )
        self.menu_status = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            font_name=UI_FONT_NAME,
            font_size=13,
            color=(160, 180, 215, 255),
        )
        self.text_input_overlay = pyglet.shapes.Rectangle(
            0,
            0,
            0,
            0,
            color=(0, 0, 0),
        )
        self.text_input_overlay.opacity = 128
        self.text_input_panel = pyglet.shapes.BorderedRectangle(
            0,
            0,
            0,
            0,
            4,
            color=(24, 28, 38),
            border_color=(120, 130, 150),
        )
        self.text_input_title_label = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="top",
            font_name=UI_FONT_NAME,
            font_size=15,
            color=(235, 235, 245, 255),
        )
        self.text_input_label = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            align="center",
            multiline=True,
            width=600,
            font_name=UI_FONT_NAME,
            font_size=17,
            color=(245, 220, 140, 255),
        )
        self.command_input_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="bottom",
            align="left",
            multiline=True,
            width=760,
            font_name=UI_FONT_NAME,
            font_size=17,
            color=(245, 220, 140, 255),
        )
        self.menu_labels = [
            pyglet.text.Label(
                "",
                anchor_x="center",
                anchor_y="center",
                font_name=UI_FONT_NAME,
                font_size=20,
            )
            for _ in range(8)
        ]
        self.world_list_labels = [
            pyglet.text.Label(
                "",
                anchor_x="left",
                anchor_y="center",
                font_name=UI_FONT_NAME,
                font_size=20,
                color=(205, 215, 235, 255),
            )
            for _ in range(8)
        ]
        self.world_list_action_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="center",
            font_name=UI_FONT_NAME,
            font_size=15,
            color=(220, 220, 180, 255),
        )
        # World list UI state
        self.world_list_index = 0
        self.world_list_last_click = 0.0
        self.world_list_items: list[tuple[str, Path]] = list(self._saved_worlds())
        self._start_local_authority()
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
        self._stop_network_services()
        self._save_player()
        self.world_renderer.autosave()
        self.debug_shader.release()
        self.sky_renderer.release()
        self.postprocess_renderer.release()
        self.entity_renderer.release()
        self.structure_renderer.release()
        self.world_renderer.release()
        self.audio.close()
        super().close()

    def reload_shaders(self, delta_time: float) -> None:
        del delta_time
        self.debug_shader.reload_if_changed()

    def _is_solid_combined(self, x: int, y: int, z: int) -> bool:
        return self.world_renderer.is_solid_block(x, y, z) or self.structure_world.is_solid_cell(
            x, y, z
        )

    def fixed_update(self, delta_time: float) -> None:
        _prof_start = time.perf_counter()
        self._apply_lan_block_actions()
        if not self.menu.in_game:
            self.audio_director.set_game_state("menu")
            self.audio_director.set_biome("")
            self.audio.update(
                self.camera.position,
                self.camera.direction,
            )
            return
        self.audio_director.set_game_state(
            "night" if self.world_renderer.daylight < 0.25 else "exploration"
        )
        terrain_height = self.world_renderer.generator.height_at(
            math.floor(self.player.x), math.floor(self.player.z)
        )
        self.audio_director.set_biome("cave" if self.player.y < terrain_height - 3 else "surface")
        self.audio.update(
            self.camera.position,
            self.camera.direction,
        )
        invalid_position_reason = self._invalid_player_position_reason()
        if invalid_position_reason is not None:
            previous_position = (self.player.x, self.player.y, self.player.z)
            self._move_player_to_spawn()
            self.inventory_status = f"Recovered position: {invalid_position_reason}"
            LOGGER.error(
                "Player position recovered to spawn: reason=%s position=%s",
                invalid_position_reason,
                previous_position,
            )
        self.world_renderer.update(delta_time)
        center = ChunkCoord(
            math.floor(self.camera.x / SECTION_SIZE),
            math.floor(self.camera.z / SECTION_SIZE),
        )
        self.world_renderer.update_streaming(center)
        self._network_accumulator += delta_time
        if self.network_session is not None:
            self._process_network_messages()
            self._update_remote_players()
            if self._network_accumulator >= 0.05:
                self._network_accumulator %= 0.05
                try:
                    if self.authority is not None:
                        self.authority.send_input(
                            (self.player.x, self.player.y, self.player.z),
                            math.radians(self.camera.yaw_degrees) + math.pi / 2.0,
                        )
                    if self.world_renderer.remote_mode:
                        self._request_remote_chunk()
                except (ConnectionError, OSError):
                    self.inventory_status = "Connection interrupted; reconnecting..."
        self._autosave_accumulator += delta_time
        if self._autosave_accumulator >= 5.0:
            self._autosave_accumulator %= 5.0
            self._save_player()
            self.world_renderer.autosave()
        self._population_accumulator += delta_time
        if self._population_accumulator >= 5.0:
            self._population_accumulator %= 5.0
            self._maintain_population((self.player.x, self.player.y, self.player.z))
        player_damage = self.entities.update(
            delta_time,
            (self.player.x, self.player.y, self.player.z),
            self.world_renderer.generator.height_at,
            self._is_entity_hazard,
            self._is_solid_combined,
        )
        if player_damage > 0.0:
            self.player_health = max(0.0, self.player_health - player_damage)
            self.audio.emit(AudioEvent(AudioEventKind.SOUND, "player.hurt"))
            LOGGER.info(
                "Player damaged: amount=%.1f health=%.1f position=%s",
                player_damage,
                self.player_health,
                (self.player.x, self.player.y, self.player.z),
            )
        if self.player_health <= 0.0:
            death_position = (self.player.x, self.player.y, self.player.z)
            spawn_x, spawn_y, spawn_z = self.world_renderer.spawn_position
            self.player.x, self.player.y, self.player.z = spawn_x, spawn_y, spawn_z
            self.player.velocity_y = 0.0
            self.player_health = 20.0
            self.inventory_status = "Respawned"
            LOGGER.warning("Player respawned after death at %s", death_position)
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
        forward = float(self.key_state.is_pressed(self.control_bindings["forward"])) - float(
            self.key_state.is_pressed(self.control_bindings["backward"])
        )
        right = float(self.key_state.is_pressed(self.control_bindings["right"])) - float(
            self.key_state.is_pressed(self.control_bindings["left"])
        )
        self.player.update(
            PlayerInput(
                forward=forward,
                right=right,
                jump=self.key_state.is_pressed(self.control_bindings["jump"]),
            ),
            self.camera.yaw_degrees,
            delta_time,
            self._is_solid_combined,
        )
        moving = abs(forward) + abs(right) > 0.0
        if moving and self.player.on_ground:
            self._footstep_accumulator += delta_time
            if self._footstep_accumulator >= 0.42:
                self._footstep_accumulator %= 0.42
                block_id = self.world_renderer.get_block(
                    math.floor(self.player.x),
                    math.floor(self.player.y - 0.05),
                    math.floor(self.player.z),
                )
                material = self.world_renderer.registry.by_id(block_id).material.value
                key_name = f"block.{material}"
                key_name = key_name if key_name in self.audio.registry else "footstep"
                self.audio.emit(AudioEvent(AudioEventKind.SOUND, key_name, self.camera.position))
        else:
            self._footstep_accumulator = 0.0
        self._sync_camera_to_player()

    def on_draw(self) -> None:
        _prof_frame_start_time = time.perf_counter()
        clear_color = (
            self.world_renderer.clear_color if self.menu.in_game else (0.025, 0.04, 0.075, 1.0)
        )
        if not self.menu.in_game:
            self.mgl_context.screen.use()
            self.mgl_context.viewport = (0, 0, max(self.width, 1), max(self.height, 1))
            self.mgl_context.clear(*clear_color, depth=1.0)
            self._prepare_ui_draw()
            self._draw_menu()
            self.mgl_context.disable(moderngl.BLEND)
            self.mgl_context.enable(moderngl.DEPTH_TEST)
            return
        postprocess_active = self.postprocess_renderer.begin(self.width, self.height)
        self.mgl_context.clear(*clear_color, depth=1.0)
        self.sky_renderer.render(
            self.camera,
            self.width,
            self.height,
            self.settings.camera.field_of_view,
            self.world_renderer.daylight,
            self.world_renderer.time_of_day,
            self.world_renderer.animation_time,
        )
        entity_draws = 0

        def render_entities(light_matrix: np.ndarray) -> None:
            nonlocal entity_draws
            texture = getattr(self.world_renderer, "texture", None)
            registry = getattr(self.world_renderer, "registry", None)
            atlas_uvs = getattr(self.world_renderer, "atlas_uvs", None)
            entity_draws = self.entity_renderer.render(
                self.entities.world,
                self.camera,
                self.width,
                self.height,
                self.settings.camera.field_of_view,
                self.world_renderer.animation_time,
                self.item_registry,
                registry,
                texture,
                atlas_uvs,
                self.world_renderer.entity_light,
                self.world_renderer.daylight,
                (
                    0.55 + 0.45 * self.world_renderer.daylight,
                    0.62 + 0.38 * self.world_renderer.daylight,
                    0.78 + 0.22 * self.world_renderer.daylight,
                ),
                light_matrix,
                (
                    self.world_renderer.shadow_map.texture
                    if self.world_renderer.shadow_map is not None
                    else None
                ),
                self.world_renderer.shadow_bias,
                self.world_renderer.light_direction,
            )
            entity_draws += self.structure_renderer.render(
                self.structure_world,
                self.camera,
                self.width,
                self.height,
                self.settings.camera.field_of_view,
                self.world_renderer.texture,
                self.world_renderer.atlas_uvs,
                self.world_renderer.entity_light,
                self.world_renderer.daylight,
                (
                    0.55 + 0.45 * self.world_renderer.daylight,
                    0.62 + 0.38 * self.world_renderer.daylight,
                    0.78 + 0.22 * self.world_renderer.daylight,
                ),
                light_matrix,
                (
                    self.world_renderer.shadow_map.texture
                    if self.world_renderer.shadow_map is not None
                    else None
                ),
                self.world_renderer.shadow_bias,
                self.world_renderer.light_direction,
            )

        self.world_renderer.render(
            self.camera,
            self.width,
            self.height,
            self.settings.camera.field_of_view,
            shadow_caster=lambda light_matrix: self.entity_renderer.render_shadow(
                self.entities.world,
                light_matrix,
                self.world_renderer.animation_time,
            ),
            transparent_underlay=render_entities,
        )
        if postprocess_active:
            self.postprocess_renderer.present(self.width, self.height)
        self.mgl_context.disable(moderngl.DEPTH_TEST)
        self._prepare_ui_draw()
        x, y, z = self.camera.position
        fps = pyglet.clock.get_frequency()
        now = time.perf_counter()
        if now - self._prof_last_update_time >= 0.2:
            self._prof_last_update_time = now
            new_debug_text = (
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
                f"Animation states {self._animation_debug_summary()}\n"
                f"Selected {self._selected_item_name()}  "
                "[1-9 hotbar, E inventory, C craft, Q drop]"
            )
            if self.world_renderer.selection is not None:
                new_debug_text += f"\nTarget {self.world_renderer.selection.block}"
            if self.debug_label.text != new_debug_text:
                self.debug_label.text = new_debug_text

            new_hud_text = f"FPS: {fps:5.1f} | XYZ: {x:7.2f} / {y:7.2f} / {z:7.2f}"
            if self.hud_top_left_label.text != new_hud_text:
                self.hud_top_left_label.text = new_hud_text

        _prof_ui_start = time.perf_counter()
        if not getattr(self.settings.development, "disable_hud", False):
            if self.debug_overlay_visible:
                self.debug_label.visible = True
                self.hud_top_left_label.visible = False
                self.debug_label.y = self.height - 10
            else:
                self.debug_label.visible = False
                self.hud_top_left_label.visible = True
                self.hud_top_left_label.y = self.height - 10

            if self.key_state.is_pressed(key.TAB):
                names = ["Players Online:"]
                if self.network_session is not None:
                    names.append("You (Local)")
                    local_id = self.network_session.player_id
                    for p_id, p in self.network_players.items():
                        if p_id == local_id:
                            continue
                        names.append(str(p.get("name", f"Player {p_id}")))
                else:
                    names.append("You (Singleplayer)")
                self.player_list_label.text = "\n".join(names)
                self.player_list_label.x = self.width // 2
                self.player_list_label.y = self.height // 2
                self.player_list_label.draw()

            from voxel_sandbox.render.math3d import camera_matrix

            matrix = camera_matrix(
                self.camera,
                max(self.width, 1) / max(self.height, 1),
                self.settings.camera.field_of_view,
            )

            for player_id, entity in self.remote_player_entities.items():
                transform = self.entities.world.transforms.get(entity)
                if transform is None:
                    continue
                pos = np.array([transform.x, transform.y + 2.1, transform.z, 1.0], dtype=np.float32)
                clip = matrix @ pos
                w = clip[3]
                if w > 0:
                    ndc_x = clip[0] / w
                    ndc_y = clip[1] / w
                    if -1 <= ndc_x <= 1 and -1 <= ndc_y <= 1:
                        screen_x = (ndc_x + 1) * self.width / 2
                        screen_y = (ndc_y + 1) * self.height / 2
                        name = self.network_players.get(player_id, {}).get(
                            "name", f"Player {player_id}"
                        )
                        self.player_name_label.text = str(name)
                        self.player_name_label.x = screen_x
                        self.player_name_label.y = screen_y
                        self.player_name_label.draw()
            self.crosshair.visible = not self.inventory_open
            self.crosshair.x = self.width // 2
            self.crosshair.y = self.height // 2
            self._draw_hotbar()
            self._draw_health()
            if not self.inventory_open:
                self.held_hand_sprite.visible = True
                self.held_hand_sprite.x = self.width - 150
                self.held_hand_sprite.y = -12
                held_stack = self.inventory[self.hotbar.selected_index]
                if held_stack is not None:
                    self.held_item_icon.visible = True
                    self.held_item_icon.image = self.item_icon_images[held_stack.item_id]
                    self.held_item_icon.scale = 112 / max(1, self.held_item_icon.image.width)
                    self.held_item_icon.x = self.width - 190
                    self.held_item_icon.y = 12
                    self.held_item_icon.rotation = 12
                else:
                    self.held_item_icon.visible = False
            else:
                self.held_hand_sprite.visible = False
                self.held_item_icon.visible = False
            if self.inventory_status and not self.inventory_open:
                self.hud_status_label.visible = True
                self.hud_status_label.text = self.inventory_status
                self.hud_status_label.x = 20
                self.hud_status_label.y = 112 if self.text_input is not None else 82
            else:
                self.hud_status_label.visible = False
            if self.inventory_open:
                self._draw_inventory()
            if self.text_input is not None:
                self._draw_text_input()

            self.hud_batch.draw()

        self._prof_ui_render_last = (time.perf_counter() - _prof_ui_start) * 1000.0
        self.mgl_context.enable(moderngl.DEPTH_TEST)

    def _animation_debug_summary(self) -> str:
        counts: dict[str, int] = {}
        for _entity, ai in self.entities.world.mob_ai.items():
            counts[ai.state.value] = counts.get(ai.state.value, 0) + 1
        return " ".join(f"{state}:{count}" for state, count in sorted(counts.items())) or "none"

    def on_key_press(self, symbol: int | None, modifiers: int) -> None:
        del modifiers
        if symbol is None:
            LOGGER.debug("Ignored key event without a symbol")
            return
        if self.rebinding_action is not None:
            self._apply_rebind(symbol)
            return
        if self.text_input is not None:
            if symbol in {key.ENTER, key.RETURN}:
                self._submit_text_input()
            elif symbol == key.ESCAPE:
                self.text_input = None
            elif symbol == key.BACKSPACE:
                self.text_input.backspace()
            elif symbol in {key.UP, key.W}:
                # navigate world list in singleplayer
                if self.menu.screen is Screen.SINGLEPLAYER:
                    self.world_list_index = max(0, self.world_list_index - 1)
            elif symbol in {key.DOWN, key.S}:
                if self.menu.screen is Screen.SINGLEPLAYER:
                    self.world_list_index = min(
                        max(0, len(self.world_list_items) - 1), self.world_list_index + 1
                    )
            self._sync_mouse_capture()
            return
        if not self.menu.in_game:
            if symbol in {key.UP, key.W}:
                self.menu.move_selection(-1)
                self._play_ui_sound()
            elif symbol in {key.DOWN, key.S}:
                self.menu.move_selection(1)
                self._play_ui_sound()
            elif symbol in {key.ENTER, key.RETURN, key.SPACE}:
                self._play_ui_sound()
                self._handle_menu_command(self.menu.activate())
            elif symbol == key.ESCAPE:
                self._play_ui_sound()
                self.menu.back()
            self._sync_mouse_capture()
            return
        if symbol == key.E:
            if self.inventory_open:
                self._close_inventory()
            else:
                self._open_inventory(2)
            self.key_state.clear()
            self._sync_mouse_capture()
            return
        if self.inventory_open:
            if symbol == key.ESCAPE:
                self._close_inventory()
                self._sync_mouse_capture()
            elif symbol == key.C:
                self._take_crafting_result()
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
        if symbol == key.F3:
            self.debug_overlay_visible = not self.debug_overlay_visible
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
        if symbol == key.SLASH:
            self._begin_text_input(
                TextPurpose.COMMAND,
                "Command (/help)",
                initial="/",
                maximum_length=256,
            )
            return
        self.key_state.press(symbol)

    def on_text(self, text: str) -> None:
        if self.text_input is not None:
            if (
                self.text_input.purpose is TextPurpose.COMMAND
                and self.text_input.value == "/"
                and text == "/"
            ):
                return
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
        if self.text_input is not None:
            return
        if not self.menu.in_game:
            if hasattr(self, "ui_renderer") and self.ui_renderer:
                if self.ui_renderer.on_mouse_press(x, y, button, modifiers):
                    self._play_ui_sound()
            return
        if self.menu.in_game and self.inventory_open:
            crafting_slot = self._crafting_slot_at(x, y)
            if crafting_slot is not None:
                self._handle_crafting_click(crafting_slot, button)
            elif self._crafting_result_at(x, y):
                self._take_crafting_result()
            elif (slot := self._inventory_slot_at(x, y)) is not None:
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
                kind = self.entities.world.mob_ai[target].kind.value
                drops = self.entities.damage(target, 4.0, self.player.eye_position)
                self.audio.emit(
                    AudioEvent(
                        AudioEventKind.SOUND,
                        f"mob.{kind}_{'death' if drops else 'hurt'}",
                        self.entities.world.transforms[target].position,
                    )
                )
                self.inventory_status = "Mob defeated" if drops else "Hit mob"
                return
        hit = self.world_renderer.raycast(self.camera.position, self.camera.direction)
        structure_hit = self.structure_world.raycast_entity(
            self.camera.position,
            self.camera.direction,
        )
        if (
            button == mouse.RIGHT
            and structure_hit is not None
            and (hit is None or structure_hit[1] < hit.distance)
        ):
            self._toggle_structure(structure_hit[0])
            return
        if hit is None:
            return
        if button == mouse.LEFT:
            block_id = self.world_renderer.get_block(*hit.block)
            if self.world_renderer.registry.by_id(block_id).is_fluid:
                self.inventory_status = "Water cannot be mined"
                return
            if self.world_renderer.set_block(hit.block, 0):
                self._play_block_sound(block_id, hit.block)
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
                self._open_inventory(3)
                self._sync_mouse_capture()
                return
            selected = self.hotbar.selected
            if selected is None or self.player.intersects_block(hit.previous):
                return
            definition = self.item_registry.by_id(selected.item_id)
            if definition.block_id is None:
                return
            if self.world_renderer.set_block(hit.previous, definition.block_id):
                self._play_block_sound(definition.block_id, hit.previous)
                self._send_block_action(hit.previous, definition.block_id)
                self.inventory.take_from_slot(self.hotbar.selected_index)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        del x, y, scroll_x
        if self.text_input is not None:
            return
        if self.menu.screen is Screen.SINGLEPLAYER:
            # navigate world list with scroll
            if scroll_y > 0:
                self.world_list_index = max(0, self.world_list_index - 1)
            elif scroll_y < 0:
                self.world_list_index = min(
                    max(0, len(self.world_list_items) - 1), self.world_list_index + 1
                )
            return
        if self.menu.in_game and not self.inventory_open and scroll_y:
            self.hotbar.cycle(-1 if scroll_y > 0 else 1)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> None:
        if not self.menu.in_game:
            if hasattr(self, "ui_renderer") and self.ui_renderer:
                self.ui_renderer.on_mouse_release(x, y, button, modifiers)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if self.text_input is not None:
            return
        if not self.menu.in_game:
            if hasattr(self, "ui_renderer") and self.ui_renderer:
                if self.ui_renderer.on_mouse_motion(x, y, dx, dy):
                    self._play_ui_sound()
            return
        if self.mouse_captured:
            self.camera.rotate(
                float(dx),
                float(dy),
                self.settings.camera.mouse_sensitivity,
            )

    def _draw_menu(self) -> None:
        center_x = self.width // 2

        def on_item_click(index: int):
            self.menu.select(index)
            self._handle_menu_command(self.menu.activate())

        self.ui_renderer.update(self.menu, self._menu_item_label, on_item_click)
        self.ui_renderer.draw()

        # If we're on the singleplayer world screen, draw a selectable world list below the buttons
        if self.menu.screen is Screen.SINGLEPLAYER:
            self._draw_world_list(center_x)
        if self.text_input is not None:
            self._draw_text_input_modal()
        elif self.text_input is None:
            self.text_input_overlay.opacity = 0
            self.text_input_panel.opacity = 0

    def _draw_text_input_modal(self) -> None:
        assert self.text_input is not None
        overlay_margin = 40
        panel_width = min(680, self.width - overlay_margin * 2)
        panel_height = min(220, self.height // 2)
        panel_x = (self.width - panel_width) // 2
        panel_y = (self.height - panel_height) // 2

        self.text_input_overlay.x = 0
        self.text_input_overlay.y = 0
        self.text_input_overlay.width = self.width
        self.text_input_overlay.height = self.height
        self.text_input_overlay.color = (0, 0, 0)
        self.text_input_overlay.opacity = 150
        self.text_input_overlay.draw()

        self.text_input_panel.x = panel_x
        self.text_input_panel.y = panel_y
        self.text_input_panel.width = panel_width
        self.text_input_panel.height = panel_height
        self.text_input_panel.draw()

        title = self.text_input.purpose.name.replace("_", " ").title()
        self.text_input_title_label.text = title
        self.text_input_title_label.x = self.width // 2
        self.text_input_title_label.y = panel_y + panel_height - 16
        self.text_input_title_label.draw()

        self._draw_text_input()

    def _draw_world_list(self, center_x: int) -> None:
        self.world_list_items = list(self._saved_worlds())
        count = len(self.world_list_items)
        if count > 0:
            self.world_list_index = min(self.world_list_index, max(0, count - 1))
        else:
            self.world_list_index = -1
        
        def on_select(idx: int):
            self.world_list_index = idx
        
        def on_play():
            if self.world_list_items and 0 <= self.world_list_index < count:
                name, _ = self.world_list_items[self.world_list_index]
                self.load_world(name)
        
        def on_create():
            self._handle_menu_command("create_world")

        def on_edit():
            if self.world_list_items and 0 <= self.world_list_index < count:
                name, _ = self.world_list_items[self.world_list_index]
                self._begin_text_input(
                    TextPurpose.RENAME_WORLD,
                    "Rename world",
                    initial=name,
                    maximum_length=48,
                )

        def on_delete():
            if self.world_list_items and 0 <= self.world_list_index < count:
                self._begin_text_input(
                    TextPurpose.DELETE_WORLD,
                    "Type DELETE to confirm deleting:",
                    maximum_length=6,
                )
                
        def on_cancel():
            self._handle_menu_command("main_menu")

        if count == 0:
            self.ui_renderer.update_world_list([], -1, on_select, on_play, on_create, on_edit, on_delete, on_cancel)
            return

        start_index = max(0, self.world_list_index - 3)
        end_index = start_index + 8
        if end_index > count:
            end_index = count
            start_index = max(0, end_index - 8)

        visible_items = self.world_list_items[start_index:end_index]
        
        def mapped_on_select(visible_idx: int):
            on_select(start_index + visible_idx)

        self.ui_renderer.update_world_list(
            visible_items,
            self.world_list_index - start_index,
            mapped_on_select,
            on_play,
            on_create,
            on_edit,
            on_delete,
            on_cancel,
        )

    def _prepare_ui_draw(self) -> None:
        self.mgl_context.disable(moderngl.DEPTH_TEST)
        self.mgl_context.enable(moderngl.BLEND)
        self.mgl_context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    def _draw_text_input(self) -> None:
        assert self.text_input is not None
        if self.menu.in_game and self.text_input.purpose in {TextPurpose.CHAT, TextPurpose.COMMAND}:
            self.command_input_label.text = self.text_input.display
            self.command_input_label.width = min(760, self.width - 40)
            self.command_input_label.x = 20
            self.command_input_label.y = 76
            self.command_input_label.draw()
        else:
            self.text_input_label.text = self.text_input.display
            self.text_input_label.anchor_x = "center"
            self.text_input_label.anchor_y = "center"
            self.text_input_label.width = 600
            self.text_input_label.x = self.width // 2
            self.text_input_label.y = self.height // 3
            self.text_input_label.draw()

    def _menu_item_label(self, index: int) -> str:
        item = self.menu.items[index]
        values = {
            "cycle_shadows": self.settings.graphics.shadow_quality,
            "toggle_clouds": "on" if self.settings.graphics.clouds else "off",
            "toggle_postprocess": "on" if self.settings.graphics.postprocess else "off",
            "toggle_vsync": "on" if self.settings.window.vsync else "off",
            "cycle_difficulty": self.settings.gameplay.difficulty,
            "rebind_forward": self.settings.controls.forward,
            "rebind_backward": self.settings.controls.backward,
            "rebind_left": self.settings.controls.left,
            "rebind_right": self.settings.controls.right,
            "rebind_jump": self.settings.controls.jump,
            "cycle_master_volume": f"{self.settings.audio.master:.0%}",
            "cycle_effects_volume": f"{self.settings.audio.effects:.0%}",
            "cycle_music_volume": f"{self.settings.audio.music:.0%}",
            "cycle_ambience_volume": f"{self.settings.audio.ambience:.0%}",
        }
        value = values.get(item.action or "")
        return item.label if value is None else f"{item.label}: {value}"

    def _play_ui_sound(self) -> None:
        self.audio.emit(AudioEvent(AudioEventKind.SOUND, "ui.click"))

    def _play_block_sound(
        self,
        block_id: int,
        position: tuple[int, int, int],
    ) -> None:
        material = self.world_renderer.registry.by_id(block_id).material.value
        key_name = f"block.{material}"
        key_name = key_name if key_name in self.audio.registry else "footstep"
        self.audio.emit(
            AudioEvent(
                AudioEventKind.SOUND,
                key_name,
                (
                    float(position[0]) + 0.5,
                    float(position[1]) + 0.5,
                    float(position[2]) + 0.5,
                ),
            )
        )

    def _cycle_audio_volume(self, command: MenuCommand) -> None:
        fields = {
            MenuCommand.CYCLE_MASTER_VOLUME: "master",
            MenuCommand.CYCLE_EFFECTS_VOLUME: "effects",
            MenuCommand.CYCLE_MUSIC_VOLUME: "music",
            MenuCommand.CYCLE_AMBIENCE_VOLUME: "ambience",
        }
        field = fields[command]
        current = getattr(self.settings.audio, field)
        next_volume = 0.0 if current >= 0.99 else round(current + 0.1, 1)
        audio_settings = replace(self.settings.audio, **{field: next_volume})
        self.settings = replace(self.settings, audio=audio_settings)
        self.audio.set_volumes(volume_map(audio_settings))
        self.menu.status = f"{field.title()} volume saved as {next_volume:.0%}."
        save_user_settings(self.settings)

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
        elif command is MenuCommand.CYCLE_SHADOWS:
            qualities = ("off", "low", "medium")
            current = self.settings.graphics.shadow_quality
            current_index = qualities.index(current) if current in qualities else 1
            next_quality = qualities[(current_index + 1) % len(qualities)]
            self.settings = replace(
                self.settings,
                graphics=replace(self.settings.graphics, shadow_quality=next_quality),
            )
            self.menu.status = f"Shadow quality saved as {next_quality}; applies after restart."
            save_user_settings(self.settings)
        elif command is MenuCommand.TOGGLE_CLOUDS:
            enabled = not self.settings.graphics.clouds
            self.settings = replace(
                self.settings,
                graphics=replace(self.settings.graphics, clouds=enabled),
            )
            self.sky_renderer.clouds = enabled
            save_user_settings(self.settings)
        elif command is MenuCommand.TOGGLE_POSTPROCESS:
            enabled = not self.settings.graphics.postprocess
            self.settings = replace(
                self.settings,
                graphics=replace(self.settings.graphics, postprocess=enabled),
            )
            self.postprocess_renderer.enabled = enabled
            save_user_settings(self.settings)
        elif command is MenuCommand.TOGGLE_VSYNC:
            enabled = not self.settings.window.vsync
            self.settings = replace(
                self.settings,
                window=replace(self.settings.window, vsync=enabled),
            )
            self.set_vsync(enabled)
            save_user_settings(self.settings)
        elif command is MenuCommand.CYCLE_DIFFICULTY:
            difficulty = "peaceful" if self.settings.gameplay.difficulty == "normal" else "normal"
            self._set_difficulty(difficulty)
            self.menu.status = f"Difficulty saved as {difficulty}."
        elif command in {
            MenuCommand.CYCLE_MASTER_VOLUME,
            MenuCommand.CYCLE_EFFECTS_VOLUME,
            MenuCommand.CYCLE_MUSIC_VOLUME,
            MenuCommand.CYCLE_AMBIENCE_VOLUME,
        }:
            self._cycle_audio_volume(command)
        elif command is MenuCommand.CREATE_WORLD:
            self._begin_text_input(
                TextPurpose.WORLD_NAME,
                "World name",
                initial="New World",
                maximum_length=48,
            )
        elif command in {
            MenuCommand.REBIND_FORWARD,
            MenuCommand.REBIND_BACKWARD,
            MenuCommand.REBIND_LEFT,
            MenuCommand.REBIND_RIGHT,
            MenuCommand.REBIND_JUMP,
        }:
            self.rebinding_action = {
                MenuCommand.REBIND_FORWARD: "forward",
                MenuCommand.REBIND_BACKWARD: "backward",
                MenuCommand.REBIND_LEFT: "left",
                MenuCommand.REBIND_RIGHT: "right",
                MenuCommand.REBIND_JUMP: "jump",
            }[command]
            self.menu.status = f"Press a key for {self.rebinding_action}."

    def _sync_mouse_capture(self) -> None:
        should_capture = self.menu.in_game and not self.inventory_open and self.text_input is None
        if not should_capture:
            self.key_state.clear()
        if should_capture != self.mouse_captured:
            self.mouse_captured = should_capture
            self.set_exclusive_mouse(should_capture)

    def _control_symbols(self) -> dict[str, int]:
        controls = self.settings.controls
        return {
            "forward": cast(int, getattr(key, controls.forward, key.W)),
            "backward": cast(int, getattr(key, controls.backward, key.S)),
            "left": cast(int, getattr(key, controls.left, key.A)),
            "right": cast(int, getattr(key, controls.right, key.D)),
            "jump": cast(int, getattr(key, controls.jump, key.SPACE)),
        }

    def _apply_rebind(self, symbol: int) -> None:
        action = self.rebinding_action
        if action is None:
            return
        conflict = next(
            (
                name
                for name, bound_symbol in self.control_bindings.items()
                if bound_symbol == symbol
            ),
            None,
        )
        if conflict is not None and conflict != action:
            self.menu.status = f"Key already assigned to {conflict}."
            self.rebinding_action = None
            return
        name = key.symbol_string(symbol)
        controls = self.settings.controls
        if action == "forward":
            controls = replace(controls, forward=name)
        elif action == "backward":
            controls = replace(controls, backward=name)
        elif action == "left":
            controls = replace(controls, left=name)
        elif action == "right":
            controls = replace(controls, right=name)
        else:
            controls = replace(controls, jump=name)
        self.settings = replace(self.settings, controls=controls)
        self.control_bindings[action] = symbol
        self.rebinding_action = None
        self.menu.status = f"{action.title()} bound to {name}."
        save_user_settings(self.settings)

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
            if self.authority is not None:
                self.authority.set_player_name(self.player_name)
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
            if value and self.authority is not None:
                try:
                    self.authority.send_chat(value)
                except (ConnectionError, OSError) as error:
                    self.inventory_status = f"Chat failed: {error}"
            elif value:
                self.inventory_status = "Chat is available in multiplayer."
            self.text_input = None
        elif field.purpose is TextPurpose.COMMAND:
            self.execute_command(value)
            self.text_input = None
        elif field.purpose is TextPurpose.WORLD_NAME:
            if not value:
                self.menu.status = "World name is required."
                return
            self.pending_world_name = value[:48]
            self.text_input = TextInput(
                TextPurpose.WORLD_SEED,
                "World seed",
                self.pending_world_name,
                64,
            )
            return
        elif field.purpose is TextPurpose.WORLD_SEED:
            seed = value or self.pending_world_name
            self.create_world(self.pending_world_name, seed)
            self.text_input = None
        elif field.purpose is TextPurpose.RENAME_WORLD:
            # rename selected saved world
            if not (0 <= self.world_list_index < len(self.world_list_items)):
                self.menu.status = "No world selected to rename."
                self.text_input = None
                self._sync_mouse_capture()
                return
            name, path = self.world_list_items[self.world_list_index]
            storage = WorldStorage(path)
            meta = storage.load_metadata()
            if meta is None:
                self.menu.status = "Failed to read world metadata."
                self.text_input = None
                self._sync_mouse_capture()
                return
            storage.ensure_world(name=value or meta.name, seed=meta.seed)
            self.menu.status = f"Renamed world to {value or meta.name}."
            self.world_list_items = list(self._saved_worlds())
            self.text_input = None
        elif field.purpose is TextPurpose.DELETE_WORLD:
            # require typing DELETE exactly to delete selected
            if value == "DELETE":
                if not (0 <= self.world_list_index < len(self.world_list_items)):
                    self.menu.status = "No world selected to delete."
                    self.text_input = None
                    self._sync_mouse_capture()
                    return
                name, path = self.world_list_items[self.world_list_index]
                # remove directory
                shutil.rmtree(path)
                self.menu.status = f"Deleted world {name}."
                self.world_list_items = list(self._saved_worlds())
                self.world_list_index = max(
                    0, min(self.world_list_index, len(self.world_list_items) - 1)
                )
            else:
                self.menu.status = "Delete cancelled (type DELETE to confirm)."
            self.text_input = None
        self._sync_mouse_capture()

    def execute_command(self, source: str) -> None:
        try:
            command = parse_command(source)
        except CommandError as error:
            self.inventory_status = str(error)
            return
        if isinstance(command, SetTimeCommand):
            self.world_renderer.time_of_day = command.time_of_day
            self.inventory_status = f"Time set to {command.label}."
        elif isinstance(command, SetDifficultyCommand):
            self._set_difficulty(command.difficulty)
            self.inventory_status = f"Difficulty set to {command.difficulty}."
        elif isinstance(command, TeleportCommand):
            if self.network_session is None:
                self.inventory_status = "Teleportation requires multiplayer."
                return
            target_pos: tuple[float, float, float] | None = None
            for _p_id, p in self.network_players.items():
                if str(p.get("name", "")).casefold() == command.target_name.casefold():
                    raw_position = p.get("position")
                    if (
                        isinstance(raw_position, list)
                        and len(raw_position) == 3
                        and all(
                            isinstance(value, int | float)
                            for value in cast(list[object], raw_position)
                        )
                    ):
                        values = cast(list[int | float], raw_position)
                        target_pos = float(values[0]), float(values[1]), float(values[2])
                    break
            if target_pos is not None:
                self.player.x, self.player.y, self.player.z = target_pos
                self.inventory_status = f"Teleported to {command.target_name}."
            else:
                self.inventory_status = f"Player {command.target_name} not found."
        elif isinstance(command, SpawnStructureCommand):
            if self.lan_server is None or self.world_renderer.remote_mode:
                self.inventory_status = "Structure commands require a local authoritative world."
                return
            distance = 5.0
            origin = (
                math.floor(self.player.x + self.camera.direction[0] * distance),
                math.floor(self.player.y),
                math.floor(self.player.z + self.camera.direction[2] * distance),
            )
            entity = self.lan_server.spawn_structure(command.key, origin)
            self.structure_world = self.lan_server.structure_world
            self.inventory_status = f"Spawned {command.key} structure #{entity.entity_id}."
        elif isinstance(command, ToggleStructureCommand):
            if self.lan_server is None or self.world_renderer.remote_mode:
                self.inventory_status = "Structure commands require a local authoritative world."
                return
            try:
                entity = self.lan_server.toggle_structure(command.entity_id)
            except KeyError:
                self.inventory_status = f"Unknown structure #{command.entity_id}."
                return
            self.inventory_status = (
                f"Structure #{entity.entity_id} {'activated' if entity.active else 'stopped'}."
            )
        elif isinstance(command, ListStructuresCommand):
            structures = sorted(
                self.structure_world.entities.values(),
                key=lambda item: item.entity_id,
            )
            self.inventory_status = (
                ", ".join(f"#{item.entity_id} {item.key}" for item in structures)
                if structures
                else "No runtime structures."
            )
        else:
            self.inventory_status = (
                "/time set <...>; /difficulty <...>; /structure <spawn|toggle|list>"
            )

    def _set_difficulty(self, difficulty: str) -> None:
        self.settings = replace(
            self.settings,
            gameplay=replace(self.settings.gameplay, difficulty=difficulty),
        )
        self._maintain_population((self.player.x, self.player.y, self.player.z))
        save_user_settings(self.settings)

    def _maintain_population(self, center: tuple[float, float, float]) -> None:
        hostile_count = 0 if self.settings.gameplay.difficulty == "peaceful" else 1
        self.entities.maintain_population(
            center,
            self.world_renderer.generator.height_at,
            self._is_entity_hazard,
            hostile_count=hostile_count,
            hostile_spawn_allowed=self._hostile_spawn_allowed,
        )

    def _hostile_spawn_allowed(self, x: int, y: int, z: int) -> bool:
        light_level = self.world_renderer.spawn_light_level(x, y, z)
        return (
            light_level is not None
            and light_level <= self.settings.gameplay.hostile_spawn_light_limit
        )

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

    def _draw_hotbar(self) -> None:
        if self.inventory_open:
            for s in self.hotbar_slots:
                s.visible = False
            for s in self.hotbar_icons:
                s.visible = False
            for s in self.hotbar_count_labels:
                s.visible = False
            for s in self.hotbar_key_labels:
                s.visible = False
            return
        else:
            for s in self.hotbar_slots:
                s.visible = True
            for s in self.hotbar_icons:
                s.visible = True
            for s in self.hotbar_count_labels:
                s.visible = True
            for s in self.hotbar_key_labels:
                s.visible = True

        slot_size = 52
        start_x = self.width // 2 - (slot_size * 9) // 2
        for index, shape in enumerate(self.hotbar_slots):
            stack = self.inventory[index]
            x = start_x + index * slot_size
            self._draw_item_slot(
                shape,
                self.hotbar_icons[index],
                self.hotbar_count_labels[index],
                stack,
                x,
                16,
                slot_size,
                selected=index == self.hotbar.selected_index,
            )
            key_label = self.hotbar_key_labels[index]
            key_label.x = x + 4
            key_label.y = 64
            if getattr(key_label, "batch", None) is None:
                key_label.draw()

    def _draw_health(self) -> None:
        if self.inventory_open:
            for s in self.heart_sprites:
                s.visible = False
            return
        else:
            for s in self.heart_sprites:
                s.visible = True

        start_x = self.width // 2 - (52 * 9) // 2
        for index, sprite in enumerate(self.heart_sprites):
            remaining = self.player_health - index * 2.0
            state = 2 if remaining >= 2.0 else 1 if remaining > 0.0 else 0
            sprite.image = self.heart_images[state]
            sprite.x = start_x + index * (HEART_SIZE + 2)
            sprite.y = 74
            if getattr(sprite, "batch", None) is None:
                sprite.draw()

    def _draw_inventory(self) -> None:
        center_x = self.width // 2
        center_y = self.height // 2
        self.inventory_panel.x = center_x - 270
        self.inventory_panel.y = center_y - 270
        self.inventory_panel.height = 540
        self.inventory_panel.draw()
        self.inventory_title.text = "INVENTORY"
        self.inventory_title.x = self.width // 2
        self.inventory_title.y = center_y + 218
        self.inventory_title.draw()
        display_indices = (*range(9, len(self.inventory)), *range(9))
        for display_index, index in enumerate(display_indices):
            x, y = self._inventory_slot_position(display_index)
            stack = self.inventory[index]
            self._draw_item_slot(
                self.inventory_slots[index],
                self.inventory_icons[index],
                self.inventory_count_labels[index],
                stack,
                x,
                y,
                48,
                selected=index == self.hotbar.selected_index,
            )
        craft_origin_x, craft_origin_y = self._crafting_origin()
        self.crafting_label.text = f"CRAFTING {self.crafting_grid_size}x{self.crafting_grid_size}"
        self.crafting_label.x = craft_origin_x
        self.crafting_label.y = craft_origin_y + 58
        self.crafting_label.draw()
        for index in range(9):
            visible = index < len(self.crafting_grid)
            self.crafting_icons[index].visible = False
            self.crafting_count_labels[index].text = ""
            if not visible:
                continue
            x, y = self._crafting_slot_position(index)
            self._draw_item_slot(
                self.crafting_slots[index],
                self.crafting_icons[index],
                self.crafting_count_labels[index],
                self.crafting_grid[index],
                x,
                y,
                48,
            )
        result_x, result_y = self._crafting_result_position()
        self._draw_item_slot(
            self.crafting_result_slot,
            self.crafting_result_icon,
            self.crafting_result_count,
            self._crafting_result_stack(),
            result_x,
            result_y,
            56,
            selected=self._crafting_result_stack() is not None,
        )
        self.crafting_arrow.x = result_x - 50
        self.crafting_arrow.y = result_y + 28
        self.crafting_arrow.draw()
        self.menu_status.text = self.inventory_status
        self.menu_status.x = self.width // 2
        self.menu_status.y = center_y - 270
        self.menu_status.draw()
        if self.cursor_stack is not None:
            definition = self.item_registry.by_id(self.cursor_stack.item_id)
            self.cursor_item_icon.image = self.item_icon_images[self.cursor_stack.item_id]
            self.cursor_item_icon.scale = 38 / ICON_SIZE
            self.cursor_item_icon.x = self.mouse_x + 8
            self.cursor_item_icon.y = self.mouse_y + 8
            self.cursor_item_icon.draw()
            self.cursor_item_label.text = (
                f"{definition.name}  {self.cursor_stack.count}"
                if self.cursor_stack.count > 1
                else definition.name
            )
            self.cursor_item_label.x = self.mouse_x + 48
            self.cursor_item_label.y = self.mouse_y + 10
            self.cursor_item_label.draw()

    def _inventory_slot_at(self, x: int, y: int) -> int | None:
        display_indices = (*range(9, len(self.inventory)), *range(9))
        for display_index, index in enumerate(display_indices):
            slot_x, slot_y = self._inventory_slot_position(display_index)
            if slot_x <= x <= slot_x + 48 and slot_y <= y <= slot_y + 48:
                return index
        return None

    def _inventory_slot_position(self, display_index: int) -> tuple[int, int]:
        row, column = divmod(display_index, self.inventory.width)
        start_x = self.width // 2 - 232
        start_y = self.height // 2 - (15 if self.crafting_grid_size == 2 else 70)
        y = start_y - row * 52
        if row == 3:
            y -= 10
        return start_x + column * 52, y

    def _crafting_origin(self) -> tuple[int, int]:
        return self.width // 2 - 220, self.height // 2 + 90

    def _crafting_slot_position(self, index: int) -> tuple[int, int]:
        row, column = divmod(index, self.crafting_grid_size)
        origin_x, origin_y = self._crafting_origin()
        return origin_x + column * 52, origin_y - row * 52

    def _crafting_slot_at(self, x: int, y: int) -> int | None:
        for index in range(len(self.crafting_grid)):
            slot_x, slot_y = self._crafting_slot_position(index)
            if slot_x <= x <= slot_x + 48 and slot_y <= y <= slot_y + 48:
                return index
        return None

    def _crafting_result_position(self) -> tuple[int, int]:
        _origin_x, origin_y = self._crafting_origin()
        return self.width // 2 + 135, origin_y - (self.crafting_grid_size - 1) * 26

    def _crafting_result_at(self, x: int, y: int) -> bool:
        slot_x, slot_y = self._crafting_result_position()
        return slot_x <= x <= slot_x + 56 and slot_y <= y <= slot_y + 56

    def _crafting_result_stack(self) -> ItemStack | None:
        recipe = self.recipe_book.match(self.crafting_grid)
        return recipe.result if recipe is not None else None

    def _draw_item_slot(
        self,
        shape: pyglet.shapes.BorderedRectangle,
        icon: pyglet.sprite.Sprite,
        count_label: pyglet.text.Label,
        stack: ItemStack | None,
        x: int,
        y: int,
        size: int,
        *,
        selected: bool = False,
    ) -> None:
        shape.x = x
        shape.y = y
        shape.width = size
        shape.height = size
        shape.color = (80, 85, 100, 255) if selected else (58, 63, 76, 255)
        shape.border_color = (255, 255, 100, 255) if selected else (125, 136, 154, 255)
        if getattr(shape, "batch", None) is None:
            shape.draw()
        if stack is None:
            icon.visible = False
            count_label.text = ""
            return
        icon.visible = True
        icon.image = self.item_icon_images[stack.item_id]
        icon.scale = (size - 12) / ICON_SIZE
        icon.x = x + 6
        icon.y = y + 6
        if getattr(icon, "batch", None) is None:
            icon.draw()
        count_label.text = str(stack.count) if stack.count > 1 else ""
        count_label.x = x + size - 4
        count_label.y = y + 2
        if getattr(count_label, "batch", None) is None:
            count_label.draw()

    def _open_inventory(self, grid_size: int) -> None:
        self.inventory_open = True
        self.crafting_grid_size = grid_size
        self.crafting_grid = CraftingGrid(grid_size, grid_size)
        self.inventory_status = "Place ingredients in the grid; click the result to craft."

    def _handle_crafting_click(self, index: int, button: int) -> None:
        current = self.crafting_grid[index]
        if button == mouse.LEFT:
            if self.cursor_stack is None:
                self.cursor_stack = self.crafting_grid.take(index)
            elif current is None:
                self.crafting_grid.set_index(index, self.cursor_stack)
                self.cursor_stack = None
            elif current.item_id == self.cursor_stack.item_id:
                maximum = self.item_registry.by_id(current.item_id).max_stack
                moved = min(maximum - current.count, self.cursor_stack.count)
                if moved > 0:
                    self.crafting_grid.set_index(index, current.with_count(current.count + moved))
                    remaining = self.cursor_stack.count - moved
                    self.cursor_stack = (
                        self.cursor_stack.with_count(remaining) if remaining else None
                    )
            else:
                self.crafting_grid.set_index(index, self.cursor_stack)
                self.cursor_stack = current
            return
        if button != mouse.RIGHT:
            return
        if self.cursor_stack is None:
            if current is None:
                return
            take_count = (current.count + 1) // 2
            remaining = current.count - take_count
            self.cursor_stack = current.with_count(take_count)
            self.crafting_grid.set_index(
                index, current.with_count(remaining) if remaining else None
            )
            return
        maximum = self.item_registry.by_id(self.cursor_stack.item_id).max_stack
        if current is None:
            self.crafting_grid.set_index(index, self.cursor_stack.with_count(1))
        elif current.item_id == self.cursor_stack.item_id and current.count < maximum:
            self.crafting_grid.set_index(index, current.with_count(current.count + 1))
        else:
            return
        remaining = self.cursor_stack.count - 1
        self.cursor_stack = self.cursor_stack.with_count(remaining) if remaining else None

    def _take_crafting_result(self) -> None:
        result = self._crafting_result_stack()
        if result is None:
            self.inventory_status = "The current pattern has no recipe."
            return
        maximum = self.item_registry.by_id(result.item_id).max_stack
        if self.cursor_stack is not None and (
            self.cursor_stack.item_id != result.item_id
            or self.cursor_stack.count + result.count > maximum
        ):
            self.inventory_status = "Clear the cursor before taking this result."
            return
        crafted = self.recipe_book.craft(self.crafting_grid)
        if crafted is None:
            return
        self.cursor_stack = (
            crafted
            if self.cursor_stack is None
            else self.cursor_stack.with_count(self.cursor_stack.count + crafted.count)
        )
        definition = self.item_registry.by_id(crafted.item_id)
        self.inventory_status = f"Crafted {definition.name} x{crafted.count}."

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
        for index in range(len(self.crafting_grid)):
            stack = self.crafting_grid.take(index)
            if stack is not None:
                self._return_or_drop_stack(stack)
        if self.cursor_stack is not None:
            self._return_or_drop_stack(self.cursor_stack)
            self.cursor_stack = None
        self.inventory_open = False
        self.inventory_status = ""

    def _return_or_drop_stack(self, stack: ItemStack) -> None:
        remainder = self.inventory.add(stack, self.item_registry)
        if remainder is not None:
            self.entities.spawn_item(
                (self.player.x, self.player.y + 0.5, self.player.z),
                remainder,
            )

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
        return self._invalid_player_position_reason() is None

    def _invalid_player_position_reason(self) -> str | None:
        position = (self.player.x, self.player.y, self.player.z)
        if not all(math.isfinite(value) for value in position):
            return "non-finite coordinate"
        if not -256.0 <= self.player.y <= 1024.0:
            return f"vertical coordinate {self.player.y:.2f} outside safety bounds"
        if abs(self.player.x) > 30_000_000.0 or abs(self.player.z) > 30_000_000.0:
            return "horizontal coordinate outside safety bounds"
        return None

    def _position_within_world(self, position: tuple[float, float, float]) -> bool:
        x, y, z = position
        return (
            all(math.isfinite(value) for value in position)
            and -256.0 <= y <= 1024.0
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
        if self.lan_server is not None:
            self.lan_server.save()

    def _connect_remote(self, target: str, player_name: str) -> None:
        host, separator, raw_port = target.rpartition(":")
        if not separator or not host:
            raise ValueError("Connect address must use HOST:PORT")
        session = ClientSession(auto_reconnect=True, reconnect_attempts=10, reconnect_delay=0.1)
        joined = session.connect(host, int(raw_port), name=player_name[:32] or "Player")
        self._stop_network_services()
        self.network_session = session
        self.structure_world = StructureWorld()
        self.authority = NetworkWorldAuthority(session, self.structure_world)
        self.world_renderer.enable_remote_mode()
        self.last_structure_revision = -1
        self._replace_structure_snapshots(
            joined.get("structures", []),
            joined.get("structure_revision", 0),
        )
        self.inventory_status = f"Connected as player {joined['player_id']}"
        self.authority.request_chunk(0, 0)
        self.requested_remote_chunks.add(ChunkCoord(0, 0))
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
                normalized_players = self._normalize_network_players(players)
                if full is True:
                    self.network_players = normalized_players
                else:
                    self.network_players.update(normalized_players)
                    if isinstance(removed, list):
                        for player_id in cast(list[object], removed):
                            if isinstance(player_id, int):
                                self.network_players.pop(player_id, None)
                self._sync_remote_players(self.network_players)
        elif message_type == "structure_snapshot":
            self._replace_structure_snapshots(
                message.get("structures", []),
                message.get("revision", 0),
            )
        elif message_type == "chat":
            self.inventory_status = f"Chat: {message.get('text', '')}"
        elif message_type == "session_reconnecting":
            self.inventory_status = "Connection interrupted; reconnecting..."
        elif message_type == "session_reconnected":
            self.last_snapshot_sequence = 0
            self.network_players.clear()
            self.requested_remote_chunks.clear()
            joined = message.get("joined")
            if isinstance(joined, dict):
                self.last_structure_revision = -1
                self._replace_structure_snapshots(
                    joined.get("structures", []),
                    joined.get("structure_revision", 0),
                )
            self.inventory_status = "Reconnected to server"
            self._request_remote_chunk()
        elif message_type == "session_disconnected":
            assert self.network_session is not None
            self.network_session.close()
            self.network_session = None
            for entity in self.remote_player_entities.values():
                self.entities.world.destroy(entity)
            self.remote_player_entities.clear()
            self.remote_player_interpolation.clear()
            self.menu.screen = Screen.MULTIPLAYER
            self.menu.status = "Disconnected: reconnect attempts exhausted."
            self._sync_mouse_capture()

    @staticmethod
    def _normalize_network_players(raw_players: object) -> dict[int, dict[str, object]]:
        if not isinstance(raw_players, dict):
            return {}
        players: dict[int, dict[str, object]] = {}
        for raw_id, raw_player in cast(dict[object, object], raw_players).items():
            if isinstance(raw_id, int) and isinstance(raw_player, dict):
                players[raw_id] = {
                    str(key_name): value
                    for key_name, value in cast(dict[object, object], raw_player).items()
                }
        return players

    def _sync_remote_players(self, players: dict[int, dict[str, object]]) -> None:
        local_id = self.network_session.player_id if self.network_session is not None else None
        visible_ids: set[int] = set()
        for raw_id, raw_player in players.items():
            player = raw_player
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
                self.entities.world.animations.set(entity, AnimationState())
            animation = self.entities.world.animations.get(entity)
            transform = self.entities.world.transforms.get(entity)
            raw_yaw = player.get("yaw", 0.0)
            if transform is not None and isinstance(raw_yaw, int | float):
                transform.yaw = float(raw_yaw)
            if animation is not None:
                raw_phase = player.get("animation_phase", 0.0)
                animation.phase = float(raw_phase) if isinstance(raw_phase, int | float) else 0.0
                animation.speed = 1.8 if player.get("animation_state") == "walk" else 0.0
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
        if self.authority is not None:
            try:
                self.authority.apply_block_action(block, block_id)
            except (ConnectionError, OSError):
                self.inventory_status = "Block action pending reconnect"
        elif self.lan_server is not None:
            self.lan_server.apply_block_action(block, block_id)

    def _toggle_structure(self, entity_id: int) -> None:
        if self.world_renderer.remote_mode and self.authority is not None:
            try:
                self.authority.toggle_structure(entity_id)
                self.inventory_status = f"Requested structure #{entity_id} toggle."
            except (ConnectionError, OSError):
                self.inventory_status = "Structure interaction pending reconnect."
            return
        if self.lan_server is not None:
            entity = self.lan_server.toggle_structure(entity_id)
            self.inventory_status = (
                f"Structure #{entity.entity_id} {'activated' if entity.active else 'stopped'}."
            )
        elif self.authority is not None:
            entity = self.authority.toggle_structure(entity_id)
            if entity is not None:
                self.inventory_status = f"Structure #{entity.entity_id} {'activated' if entity.active else 'stopped'}."

    def open_to_lan(self) -> None:
        if self.lan_server is not None:
            self.menu.status = f"World already open to LAN on port {self.lan_server.address[1]}"
            return
        if self.network_session is not None:
            self.menu.status = "Cannot open a multiplayer game to LAN."
            return
        self.world_renderer.autosave()
        
        if self.world_renderer.storage is not None:
            self.world_renderer.storage.save_structure_world(self.structure_world)
        
        server = LanServer(
            "0.0.0.0",
            25565,
            seed=self.world_renderer.seed_text,
            storage=self.world_renderer.storage,
            block_action_sink=lambda position, block_id: self.lan_block_actions.put((position, block_id)),
        )
        server.start()
        self.lan_server = server
        
        session = ClientSession(auto_reconnect=True, reconnect_attempts=10, reconnect_delay=0.1)
        try:
            session.connect(
                "127.0.0.1",
                server.address[1],
                name=self.player_name,
                position=(self.player.x, self.player.y, self.player.z),
            )
        except OSError as error:
            server.stop()
            self.menu.status = f"Failed to connect to local server: {error}"
            self.lan_server = None
            return
            
        self.network_session = session
        self.authority = NetworkWorldAuthority(session, self.structure_world)
        
        try:
            discovery = DiscoveryResponder(
                "0.0.0.0",
                25565,
                world_name="Veilstone Singleplayer World",
                game_port=self.lan_server.address[1],
                player_count=lambda: self.lan_server.player_count if self.lan_server else 0,
            )
            discovery.start()
        except OSError as error:
            self.menu.status = f"Could not open LAN discovery port 25565: {error}"
            return
        self.lan_discovery = discovery
        self.menu.world_open_to_lan = True
        self.menu.status = f"Open to LAN on port {self.lan_server.address[1]}"

    def _apply_lan_block_actions(self) -> None:
        while True:
            try:
                block, block_id = self.lan_block_actions.get_nowait()
            except queue.Empty:
                return
            self.world_renderer.set_block(block, block_id)

    def _start_local_authority(self) -> None:
        self.structure_world = (
            self.world_renderer.storage.load_structure_world()
            if self.world_renderer.storage is not None
            else StructureWorld()
        )
        self.last_structure_revision = self.structure_world.revision
        self.authority = LocalWorldAuthority(
            self.structure_world,
            lambda position, block_id: self.lan_block_actions.put((position, block_id))
        )

    def _replace_structure_snapshots(self, raw_snapshots: object, raw_revision: object) -> None:
        if not isinstance(raw_snapshots, list) or not isinstance(raw_revision, int):
            return
        if raw_revision < self.last_structure_revision:
            return
        if self.structure_world is None:
            return
        snapshots: list[StructureSnapshot] = []
        for raw in cast("list[object]", raw_snapshots):
            if not isinstance(raw, dict):
                return
            snapshots.append(cast("StructureSnapshot", raw))
        self.structure_world.replace_from_snapshots(snapshots)
        self.structure_world.revision = raw_revision
        self.last_structure_revision = raw_revision

    def _create_world_renderer(self, save_root: Path) -> DemoWorldRenderer:
        settings = self.settings
        return DemoWorldRenderer(
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
            shadow_quality=settings.graphics.shadow_quality,
            shadow_bias=settings.graphics.shadow_bias,
            save_root=save_root,
        )

    def create_world(self, name: str, seed: str) -> None:
        root = application_data_root() / self._world_slug(name)
        WorldStorage(root).ensure_world(name=name, seed=seed)
        self._switch_world(root)

    def load_world(self, name: str) -> bool:
        match = next(
            (
                path
                for world_name, path in self._saved_worlds()
                if name.casefold() in {world_name.casefold(), path.name.casefold()}
            ),
            None,
        )
        if match is None:
            return False
        self._switch_world(match)
        return True

    def _switch_world(self, save_root: Path) -> None:
        self._save_player()
        self.world_renderer.autosave()
        self._stop_network_services()
        self.world_renderer.release()
        self.active_save_root = save_root
        self.world_renderer = self._create_world_renderer(save_root)
        spawn_x, spawn_y, spawn_z = self.world_renderer.spawn_position
        self.player = PlayerController(x=spawn_x, y=spawn_y, z=spawn_z)
        self.inventory = Inventory()
        self.hotbar = Hotbar(self.inventory)
        self.inventory.set(0, ItemStack(3, 32), self.item_registry)
        self.inventory.set(1, ItemStack(7, 8), self.item_registry)
        self.inventory.set(2, ItemStack(8, 1), self.item_registry)
        self.inventory.set(3, ItemStack(4, 4), self.item_registry)
        self.player_health = 20.0
        saved = self.world_renderer.storage.load_player(self.item_registry)
        if saved is not None:
            self.world_renderer.storage.restore_inventory(saved, self.inventory, self.item_registry)
            self.player_health = saved.health
            self.hotbar.select(saved.selected_slot)
            self._restore_player_position(saved.position)
        self.entities = EntitySimulation(seed=self.world_renderer.generator.seed.value)
        self._maintain_population((self.player.x, self.player.y, self.player.z))
        self.network_players.clear()
        self.remote_player_entities.clear()
        self.remote_player_interpolation.clear()
        self.requested_remote_chunks.clear()
        self.last_snapshot_sequence = 0
        self.structure_world = self.world_renderer.storage.load_structure_world()
        self.last_structure_revision = self.structure_world.revision
        self._start_local_authority()
        self.menu.screen = Screen.GAME
        self.menu.status = ""
        self._sync_camera_to_player()
        self._sync_mouse_capture()

    @staticmethod
    def _saved_worlds() -> tuple[tuple[str, Path], ...]:
        saves_root = application_data_root()
        if not saves_root.exists():
            return ()
        worlds: list[tuple[str, Path]] = []
        for path in sorted(saves_root.iterdir()):
            if not path.is_dir():
                continue
            metadata = WorldStorage(path).load_metadata()
            if metadata is not None:
                worlds.append((metadata.name, path))
        return tuple(worlds)

    @staticmethod
    def _world_slug(name: str) -> str:
        slug = "-".join(
            "".join(character.lower() for character in part if character.isalnum())
            for part in name.split()
        )
        return slug or "world"

    def _stop_network_services(self) -> None:
        if self.network_session is not None:
            self.network_session.close()
            self.network_session = None
        if self.lan_discovery is not None:
            self.lan_discovery.stop()
            self.lan_discovery = None
        if self.lan_server is not None:
            self.lan_server.stop()
            self.lan_server = None

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
            if self.authority is not None:
                self.authority.request_chunk(coord.x, coord.z)
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
