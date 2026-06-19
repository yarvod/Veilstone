# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportPrivateUsage=false

from __future__ import annotations

import logging
import math
import queue
from pathlib import Path
from typing import Final, cast

import moderngl
import numpy as np
import pyglet
from pyglet.window import key

from voxel_sandbox.app.composition import AppRuntime, build_app_runtime, build_local_world_runtime
from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.audio import AudioEvent, AudioEventKind
from voxel_sandbox.domain.crafting import CraftingGrid, RecipeBook
from voxel_sandbox.domain.inventory import Hotbar, Inventory
from voxel_sandbox.domain.items import ItemStack
from voxel_sandbox.engine.authority import (
    WorldAuthority,
)
from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkCoord
from voxel_sandbox.engine.events import (
    BlockBroken,
    BlockPlaced,
    EntityDamaged,
    EntityDied,
)
from voxel_sandbox.engine.game_state import GameState, GameStateMachine
from voxel_sandbox.engine.physics import PlayerInput
from voxel_sandbox.network import (
    ClientSession,
    LanServer,
)
from voxel_sandbox.network.discovery import DiscoveryResponder
from voxel_sandbox.network.interpolation import SnapshotInterpolator
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.entity_renderer import EntityRenderer
from voxel_sandbox.render.gameplay_controller import GameplayController
from voxel_sandbox.render.hud_controller import HudController, HudWindowAdapter
from voxel_sandbox.render.input_state import (
    InputHandler,
    KeyState,
    configure_layout_independent_game_keys,
)
from voxel_sandbox.render.inventory_ui import InventoryController, InventoryLogic, InventoryState
from voxel_sandbox.render.menu_ui import MenuUI
from voxel_sandbox.render.network_controller import NetworkController
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram
from voxel_sandbox.render.sky_renderer import SkyRenderer
from voxel_sandbox.render.structure_renderer import StructureRenderer
from voxel_sandbox.render.texture_packs.service import RenderTexturePackService
from voxel_sandbox.render.ui.menu import MenuController
from voxel_sandbox.render.ui.renderer import UiRenderer
from voxel_sandbox.render.ui.text_input import TextInput
from voxel_sandbox.render.world_manager import WorldManager
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
        app_runtime: AppRuntime | None = None,
    ) -> None:
        if app_runtime is not None:
            settings = app_runtime.settings
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
        self.app_runtime = app_runtime or build_app_runtime(settings)
        if self.app_runtime.texture_packs is None:
            self.app_runtime.texture_packs = RenderTexturePackService()
        self._gameplay = GameplayController(self)
        self.audio = self.app_runtime.audio
        self.audio_director = self.app_runtime.audio_director
        self.events = self.app_runtime.event_bus
        self._subscribe_audio_events()
        self._footstep_accumulator = 0.0
        self.control_bindings = self._control_symbols()
        self.rebinding_action: str | None = None
        self.active_save_root = save_root or self.app_runtime.data_root / "dev_world"
        self.pending_world_name = ""
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.debug_shader = ShaderProgram(
            self.mgl_context,
            ShaderFiles.from_directory(shader_root, "debug"),
        )
        self.camera = FirstPersonCamera()
        self.sky_renderer = SkyRenderer(self.mgl_context, clouds=settings.graphics.clouds)
        self.world_renderer = self._create_world_renderer(self.active_save_root)
        self.menu = MenuController()
        self.game_state = GameStateMachine()
        self.ui_renderer = UiRenderer(self.width, self.height)
        spawn_x, spawn_y, spawn_z = self._rebuild_world_runtime()
        self._sync_camera_to_player()
        self.key_state = KeyState()
        self.item_registry = self.app_runtime.content_registries.item_registry
        self.inventory = Inventory()
        self.hotbar = Hotbar(self.inventory)
        self.inventory.set(0, ItemStack(3, 32), self.item_registry)
        self.inventory.set(1, ItemStack(7, 8), self.item_registry)
        self.inventory.set(2, ItemStack(8, 1), self.item_registry)
        self.inventory.set(3, ItemStack(4, 4), self.item_registry)
        self.player_health = 20.0
        self._worlds = WorldManager(self)
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
            if not self._worlds.restore_player_position(saved_player.position):
                recovered_saved_position = saved_player.position
            self._sync_camera_to_player()
        recipes_path = resource_path("config/recipes.toml")
        self.recipe_book = RecipeBook.from_toml(recipes_path, self.item_registry)
        self._gameplay._maintain_population((spawn_x, spawn_y, spawn_z))
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
        self._inv_state = InventoryState(
            inventory=self.inventory,
            item_registry=self.item_registry,
            recipe_book=self.recipe_book,
        )
        self._inv = InventoryLogic(self._inv_state)
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_captured = False
        self.debug_overlay_visible = False
        self.hud_batch = pyglet.graphics.Batch()
        self.hud_bg_group = pyglet.graphics.Group(order=0)
        self.hud_fg_group = pyglet.graphics.Group(order=1)
        self.hud_text_group = pyglet.graphics.Group(order=2)
        self._hud = HudController(HudWindowAdapter(self))
        self._inv_ctrl = InventoryController(self)
        self._net = NetworkController(self)
        self.menu_ui = MenuUI(self)
        self._net.start_local_authority()
        if connect is not None:
            self._net.connect_remote(connect, player_name)
        if recovered_saved_position is not None:
            LOGGER.warning("Recovered invalid saved player position: %s", recovered_saved_position)
            self._worlds._save_player()
        pyglet.clock.schedule_interval(self.fixed_update, FIXED_UPDATE_SECONDS)
        if settings.development.shader_hot_reload:
            pyglet.clock.schedule_interval(self.reload_shaders, 0.5)
        LOGGER.info("ModernGL context: %s", self.mgl_context.info.get("GL_VERSION", "unknown"))
        self._input = InputHandler(self)

    def close(self) -> None:
        pyglet.clock.unschedule(self.fixed_update)
        pyglet.clock.unschedule(self.reload_shaders)
        self._net.stop_services()
        self._worlds._save_player()
        self.world_renderer.autosave()
        self.debug_shader.release()
        self.sky_renderer.release()
        self.entity_renderer.release()
        self.structure_renderer.release()
        self.world_renderer.release()
        self.audio.close()
        super().close()

    def reload_shaders(self, delta_time: float) -> None:
        del delta_time
        self.debug_shader.reload_if_changed()

    def _is_solid_combined(self, x: int, y: int, z: int) -> bool:
        return self.world_renderer.is_solid_block(x, y, z) or (
            hasattr(self, "structure_world") and self.structure_world.is_solid_cell(x, y, z)
        )

    def _is_fluid_at(self, x: int, y: int, z: int) -> bool:
        block_id = self.world_renderer.get_block(x, y, z)
        if block_id == 0:
            return False
        return self.world_renderer.registry.by_id(block_id).is_fluid

    def fixed_update(self, delta_time: float) -> None:
        self._net.apply_lan_block_actions()
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
        invalid_position_reason = self._worlds.invalid_player_position_reason()
        if invalid_position_reason is not None:
            previous_position = (self.player.x, self.player.y, self.player.z)
            self._worlds.move_player_to_spawn()
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
            self._net.process_messages()
            self._net.update_remote_players()
            if self._network_accumulator >= 0.05:
                self._network_accumulator %= 0.05
                try:
                    if self.authority is not None:
                        self.authority.send_input(
                            (self.player.x, self.player.y, self.player.z),
                            math.radians(self.camera.yaw_degrees) + math.pi / 2.0,
                        )
                    if self.world_renderer.remote_mode:
                        self._net.request_remote_chunk()
                except (ConnectionError, OSError):
                    self.inventory_status = "Connection interrupted; reconnecting..."
        self._autosave_accumulator += delta_time
        if self._autosave_accumulator >= 5.0:
            self._autosave_accumulator %= 5.0
            self._worlds._save_player()
            self.world_renderer.autosave()
        self._population_accumulator += delta_time
        if self._population_accumulator >= 5.0:
            self._population_accumulator %= 5.0
            self._gameplay._maintain_population((self.player.x, self.player.y, self.player.z))
        player_damage = self.entities.update(
            delta_time,
            (self.player.x, self.player.y, self.player.z),
            self.world_renderer.generator.height_at,
            self._gameplay._is_entity_hazard,
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
            self.world_renderer.streamer.get_block,
            is_solid=self._is_solid_combined,
            is_fluid=self._is_fluid_at,
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
        clear_color = (
            self.world_renderer.clear_color if self.menu.in_game else (0.025, 0.04, 0.075, 1.0)
        )
        if not self.menu.in_game:
            self.mgl_context.screen.use()
            self.mgl_context.viewport = (0, 0, max(self.width, 1), max(self.height, 1))
            self.mgl_context.clear(*clear_color, depth=1.0)
            self.menu_ui._prepare_ui_draw()
            self.menu_ui._draw_menu()
            self.mgl_context.disable(moderngl.BLEND)
            self.mgl_context.enable(moderngl.DEPTH_TEST)
            return
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
        self.mgl_context.disable(moderngl.DEPTH_TEST)
        self.menu_ui._prepare_ui_draw()
        if not getattr(self.settings.development, "disable_hud", False):
            self._hud.draw(entity_draws)
        self.mgl_context.enable(moderngl.DEPTH_TEST)

    def on_key_press(self, symbol: int | None, modifiers: int) -> None:
        self._input.on_key_press(symbol, modifiers)

    def on_text(self, text: str) -> None:
        self._input.on_text(text)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        self._input.on_key_release(symbol, modifiers)

    def on_deactivate(self) -> None:
        self._input.on_deactivate()

    def on_activate(self) -> None:
        self._input.on_activate()

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        self._input.on_mouse_press(x, y, button, modifiers)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        self._input.on_mouse_scroll(x, y, scroll_x, scroll_y)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> None:
        self._input.on_mouse_release(x, y, button, modifiers)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        self._input.on_mouse_motion(x, y, dx, dy)

    def _sync_game_state(self) -> None:
        from voxel_sandbox.render.ui.menu import Screen

        if self.menu.screen is Screen.GAME:
            self.game_state.try_transition(GameState.PLAYING)
        elif self.menu.screen is Screen.PAUSE:
            self.game_state.try_transition(GameState.PAUSED)
        else:
            self.game_state.try_transition(GameState.MENU)

    def _sync_mouse_capture(self) -> None:
        should_capture = self.menu.in_game and not self.inventory_open and self.text_input is None
        if not should_capture:
            self.key_state.clear()
        if should_capture != self.mouse_captured:
            self.mouse_captured = should_capture
            self.set_exclusive_mouse(should_capture)

    def _subscribe_audio_events(self) -> None:
        self.events.subscribe(BlockBroken, self._play_block_event)
        self.events.subscribe(BlockPlaced, self._play_block_event)
        self.events.subscribe(EntityDamaged, self._play_entity_damaged_event)
        self.events.subscribe(EntityDied, self._play_entity_died_event)

    def _play_block_event(self, event: BlockBroken | BlockPlaced) -> None:
        material = self.world_renderer.registry.by_id(event.block_id).material.value
        key_name = f"block.{material}"
        key_name = key_name if key_name in self.audio.registry else "footstep"
        self.audio.emit(
            AudioEvent(
                AudioEventKind.SOUND,
                key_name,
                (
                    float(event.position[0]) + 0.5,
                    float(event.position[1]) + 0.5,
                    float(event.position[2]) + 0.5,
                ),
            )
        )

    def _play_entity_damaged_event(self, event: EntityDamaged) -> None:
        self.audio.emit(
            AudioEvent(
                AudioEventKind.SOUND,
                f"mob.{event.kind}_hurt",
                event.position,
            )
        )

    def _play_entity_died_event(self, event: EntityDied) -> None:
        self.audio.emit(
            AudioEvent(
                AudioEventKind.SOUND,
                f"mob.{event.kind}_death",
                event.position,
            )
        )

    def _control_symbols(self) -> dict[str, int]:
        controls = self.settings.controls
        return {
            "forward": cast(int, getattr(key, controls.forward, key.W)),
            "backward": cast(int, getattr(key, controls.backward, key.S)),
            "left": cast(int, getattr(key, controls.left, key.A)),
            "right": cast(int, getattr(key, controls.right, key.D)),
            "jump": cast(int, getattr(key, controls.jump, key.SPACE)),
        }

    def _sync_camera_to_player(self) -> None:
        self.camera.x, self.camera.y, self.camera.z = self.player.eye_position

    def _rebuild_world_runtime(self) -> tuple[float, float, float]:
        spawn_x, spawn_y, spawn_z = self.world_renderer.spawn_position
        self.world_runtime = build_local_world_runtime(
            spawn_position=(spawn_x, spawn_y, spawn_z),
            entity_seed=self.world_renderer.generator.seed.value,
            storage=self.world_renderer.storage,
            block_registry=self.world_renderer.registry,
            generation=self.world_renderer.generator,
            streaming=self.world_renderer.streamer,
            renderer=self.world_renderer,
        )
        self.player = self.world_runtime.player_state
        self.entities = self.world_runtime.entity_simulation
        return spawn_x, spawn_y, spawn_z

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
            resource_pack_path=settings.graphics.resource_pack_path,
        )


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
        window._sync_game_state()
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
