from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import pyglet
from pyglet.window import key

from voxel_sandbox.render.math3d import camera_matrix
from voxel_sandbox.render.ui.menu import platform_font_name

try:
    import resource
except ImportError:  # pragma: no cover - Windows does not provide resource.
    resource = None

_UI_FONT = platform_font_name(sys.platform)


@dataclass(slots=True)
class HudFrameSnapshot:
    width: int
    height: int
    inventory_open: bool


class HudView(Protocol):
    """Narrow window-facing surface used by HUD rendering."""

    width: int
    height: int
    hud_batch: Any
    hud_text_group: Any
    world_renderer: Any
    world_runtime: Any
    player: Any
    camera: Any
    settings: Any
    game_state: Any
    network_session: Any
    network_players: Any
    remote_player_entities: Any
    entities: Any
    debug_overlay_visible: bool
    inventory_open: bool
    hotbar: Any
    item_registry: Any
    key_state: Any
    menu_ui: Any
    player_health: float
    text_input: str
    _inv_ctrl: Any

    def frame_snapshot(self) -> HudFrameSnapshot: ...


@dataclass(slots=True)
class HudWindowAdapter:
    """Compatibility adapter exposing only the HUD-facing window surface."""

    _window: Any

    @property
    def width(self) -> int:
        return self._window.width

    @property
    def height(self) -> int:
        return self._window.height

    @property
    def hud_batch(self) -> Any:
        return self._window.hud_batch

    @property
    def hud_text_group(self) -> Any:
        return self._window.hud_text_group

    @property
    def world_renderer(self) -> Any:
        return self._window.world_renderer

    @property
    def world_runtime(self) -> Any:
        return self._window.world_runtime

    @property
    def player(self) -> Any:
        return self._window.player

    @property
    def camera(self) -> Any:
        return self._window.camera

    @property
    def settings(self) -> Any:
        return self._window.settings

    @property
    def game_state(self) -> Any:
        return self._window.game_state

    @property
    def network_session(self) -> Any:
        return self._window.network_session

    @property
    def network_players(self) -> Any:
        return self._window.network_players

    @property
    def remote_player_entities(self) -> Any:
        return self._window.remote_player_entities

    @property
    def entities(self) -> Any:
        return self._window.entities

    @property
    def debug_overlay_visible(self) -> bool:
        return self._window.debug_overlay_visible

    @property
    def inventory_open(self) -> bool:
        return self._window.inventory_open

    @property
    def hotbar(self) -> Any:
        return self._window.hotbar

    @property
    def item_registry(self) -> Any:
        return self._window.item_registry

    @property
    def key_state(self) -> Any:
        return self._window.key_state

    @property
    def menu_ui(self) -> Any:
        return self._window.menu_ui

    @property
    def player_health(self) -> float:
        return self._window.player_health

    @property
    def text_input(self) -> str:
        return self._window.text_input

    @property
    def _inv_ctrl(self) -> Any:
        return self._window._inv_ctrl

    def frame_snapshot(self) -> HudFrameSnapshot:
        return HudFrameSnapshot(
            width=self._window.width,
            height=self._window.height,
            inventory_open=self._window.inventory_open,
        )


class HudController:
    """Owns HUD labels and draws the in-game overlay."""

    def __init__(self, win: HudView) -> None:
        self.win = win
        self._last_update_time = time.time()
        self.debug_label = pyglet.text.Label(
            "",
            x=10,
            y=win.height - 10,
            anchor_x="left",
            anchor_y="top",
            multiline=True,
            width=500,
            font_name=_UI_FONT,
            font_size=11,
            color=(255, 255, 255, 255),
            batch=win.hud_batch,
            group=win.hud_text_group,
        )
        self.hud_top_left_label = pyglet.text.Label(
            "",
            x=10,
            y=win.height - 10,
            anchor_x="left",
            anchor_y="top",
            multiline=True,
            width=500,
            font_name=_UI_FONT,
            font_size=13,
            color=(255, 255, 255, 255),
            batch=win.hud_batch,
            group=win.hud_text_group,
        )
        self.player_list_label = pyglet.text.Label(
            "",
            x=win.width // 2,
            y=win.height // 2,
            anchor_x="center",
            anchor_y="center",
            multiline=True,
            width=600,
            font_name=_UI_FONT,
            font_size=16,
            color=(255, 255, 255, 255),
        )
        self.crosshair = pyglet.text.Label(
            "+",
            anchor_x="center",
            anchor_y="center",
            font_name=_UI_FONT,
            font_size=18,
            color=(245, 235, 190, 255),
            batch=win.hud_batch,
            group=win.hud_text_group,
        )
        self.player_name_label = pyglet.text.Label(
            "",
            font_name=_UI_FONT,
            font_size=14,
            anchor_x="center",
            anchor_y="center",
            color=(255, 255, 255, 255),
        )

    def draw(self, entity_draws: int) -> None:
        win = self.win
        frame = win.frame_snapshot()
        x, y, z = win.camera.position
        fps = pyglet.clock.get_frequency()
        frame_ms = 1000.0 / fps if fps > 0 else 0.0
        now = time.perf_counter()
        if win.debug_overlay_visible and (
            not self.debug_label.text or now - self._last_update_time >= 0.2
        ):
            self._last_update_time = now
            block_x, block_y, block_z = int(x), int(y), int(z)
            chunk_x, chunk_z = block_x // 16, block_z // 16
            facing = _facing_from_yaw(win.camera.yaw_degrees)
            biome = _biome_key_at(win, block_x, block_z)
            memory = _process_memory_label()
            new_debug_text = (
                f"FPS {fps:5.1f} Frame {frame_ms:5.1f} ms\n"
                f"Position {x:7.2f} {y:7.2f} {z:7.2f}\n"
                f"Grounded {win.player.on_ground}  VelocityY {win.player.velocity_y:5.2f}\n"
                f"Yaw {win.camera.yaw_degrees:6.1f}  Pitch {win.camera.pitch_degrees:5.1f} "
                f"Facing {facing}\n"
                f"Biome {biome} Memory {memory} "
                f"Render distance {win.settings.world.render_distance} "
                f"Mesh uploads/frame {win.settings.world.mesh_uploads_per_frame}"
                f"\nChunks {win.world_renderer.loaded_chunks}  "
                f"Pending {win.world_renderer.pending_chunks}  "
                f"Mesh queue {win.world_renderer.pending_meshes}  "
                f"Visible sections {win.world_renderer.visible_sections}\n"
                f"Faces {win.world_renderer.face_count}  "
                f"Triangles {win.world_renderer.triangle_count}  "
                f"Draws {win.world_renderer.draw_calls}\n"
                f"Daylight {win.world_renderer.daylight:4.2f}  "
                f"Smooth {win.world_renderer.smooth_lighting}  "
                f"AO {win.world_renderer.ambient_occlusion}  "
                f"Fog {win.world_renderer.fog_enabled}  "
                f"Mesher {'greedy' if win.world_renderer.greedy_meshing else 'visible'}\n"
                f"Health {win.player_health:4.1f}  "
                f"Entities {len(win.entities.world.alive)}  "
                f"Mobs {len(win.entities.world.mob_ai)}  "
                f"Drops {len(win.entities.world.items)}  Entity draws {entity_draws}\n"
                f"Block {block_x:d} {block_y:d} {block_z:d} "
                f"Chunk {chunk_x:d} {chunk_z:d} "
                f"Remote players {len(win.remote_player_entities)}\n"
                f"Network {'client' if win.network_session is not None else 'singleplayer'} "
                f"Known players {len(win.network_players)}\n"
                f"Runtime Python {sys.version_info.major}.{sys.version_info.minor} "
                f"{sys.platform}  Frame {frame.width}x{frame.height}\n"
                f"Animation states {self._animation_debug_summary()}\n"
                f"Selected {self._selected_item_name()}  "
                "[1-9 hotbar, E inventory, C craft, Q drop]"
            )
            if win.world_renderer.selection is not None:
                new_debug_text += f"\nTarget {win.world_renderer.selection.block}"
            if self.debug_label.text != new_debug_text:
                self.debug_label.text = new_debug_text
            new_hud_text = f"FPS: {fps:5.1f} | XYZ: {x:7.2f} / {y:7.2f} / {z:7.2f}"
            if self.hud_top_left_label.text != new_hud_text:
                self.hud_top_left_label.text = new_hud_text

        if win.debug_overlay_visible:
            self.debug_label.visible = True
            self.hud_top_left_label.visible = False
            self.debug_label.y = win.height - 10
        else:
            self.debug_label.visible = False
            self.hud_top_left_label.visible = True
            self.hud_top_left_label.y = win.height - 10

        if win.key_state.is_pressed(key.TAB):
            names = ["Players Online:"]
            if win.network_session is not None:
                names.append("You (Local)")
                local_id = win.network_session.player_id
                for p_id, p in win.network_players.items():
                    if p_id == local_id:
                        continue
                    names.append(str(p.get("name", f"Player {p_id}")))
            else:
                names.append("You (Singleplayer)")
            self.player_list_label.text = "\n".join(names)
            self.player_list_label.x = frame.width // 2
            self.player_list_label.y = frame.height // 2
            self.player_list_label.draw()

        matrix = camera_matrix(
            win.camera,
            max(frame.width, 1) / max(frame.height, 1),
            win.settings.camera.field_of_view,
        )
        for player_id, entity in win.remote_player_entities.items():
            transform = win.entities.world.transforms.get(entity)
            if transform is None:
                continue
            pos = np.array([transform.x, transform.y + 2.1, transform.z, 1.0], dtype=np.float32)
            clip = matrix @ pos
            w = clip[3]
            if w > 0:
                ndc_x = clip[0] / w
                ndc_y = clip[1] / w
                if -1 <= ndc_x <= 1 and -1 <= ndc_y <= 1:
                    screen_x = (ndc_x + 1) * frame.width / 2
                    screen_y = (ndc_y + 1) * frame.height / 2
                    name = win.network_players.get(player_id, {}).get("name", f"Player {player_id}")
                    self.player_name_label.text = str(name)
                    self.player_name_label.x = screen_x
                    self.player_name_label.y = screen_y
                    self.player_name_label.draw()

        self.crosshair.visible = not frame.inventory_open
        self.crosshair.x = frame.width // 2
        self.crosshair.y = frame.height // 2
        win._inv_ctrl.draw_hotbar()
        win._inv_ctrl.draw_health()
        win._inv_ctrl.draw_held_item()
        win._inv_ctrl.update_hud_status()
        if frame.inventory_open:
            win._inv_ctrl.draw_inventory()
        if win.text_input is not None:
            win.menu_ui._draw_text_input()
        win.hud_batch.draw()

    def _animation_debug_summary(self) -> str:
        counts: dict[str, int] = {}
        for _entity, ai in self.win.entities.world.mob_ai.items():
            counts[ai.state.value] = counts.get(ai.state.value, 0) + 1
        return " ".join(f"{state}:{count}" for state, count in sorted(counts.items())) or "none"

    def _selected_item_name(self) -> str:
        win = self.win
        selected = win.hotbar.selected
        if selected is None:
            return "empty"
        definition = win.item_registry.by_id(selected.item_id)
        return f"{definition.name} x{selected.count}"


def _facing_from_yaw(yaw_degrees: float) -> str:
    yaw = yaw_degrees % 360.0
    if 45.0 <= yaw < 135.0:
        return "west"
    if 135.0 <= yaw < 225.0:
        return "north"
    if 225.0 <= yaw < 315.0:
        return "east"
    return "south"


def _biome_key_at(win: HudView, block_x: int, block_z: int) -> str:
    try:
        return str(win.world_runtime.generation.biome_key_at(block_x, block_z))
    except (AttributeError, LookupError, ValueError):
        return "unknown"


def _process_memory_label() -> str:
    if resource is None:
        return "n/a"
    usage = resource.getrusage(resource.RUSAGE_SELF)
    max_rss = float(usage.ru_maxrss)
    if sys.platform == "darwin":
        max_rss /= 1024 * 1024
    else:
        max_rss /= 1024
    return f"{max_rss:.0f} MB"
