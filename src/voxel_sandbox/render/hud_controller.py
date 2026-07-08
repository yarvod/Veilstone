from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import pyglet
from pyglet.window import key

from voxel_sandbox.render.math3d import camera_matrix
from voxel_sandbox.render.perf import RuntimePerfSnapshot
from voxel_sandbox.render.player_nameplate import (
    PlayerNameplateRenderData,
    build_remote_player_nameplate_render_data,
)
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


@dataclass(slots=True)
class DebugSlowTelemetry:
    memory: str = "n/a"
    runtime: str = ""
    device: str = "unknown"


@dataclass(frozen=True, slots=True)
class HudDebugTextSnapshot:
    text: str


@dataclass(frozen=True, slots=True)
class HudPlayerListSnapshot:
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


class InventoryHudPort(Protocol):
    def draw_hotbar(self) -> None: ...

    def draw_health(self) -> None: ...

    def draw_held_item(self) -> None: ...

    def update_hud_status(self) -> None: ...

    def draw_inventory(self) -> None: ...


class HudView(Protocol):
    """Narrow window-facing surface used by HUD rendering."""

    width: int
    height: int
    hud_batch: Any
    hud_text_group: Any
    camera: Any
    settings: Any
    debug_overlay_visible: bool
    inventory_open: bool
    key_state: Any
    menu_ui: Any
    player_health: float
    text_input: str | None
    inventory_hud: InventoryHudPort
    debug_device_label: str
    runtime_perf_snapshot: RuntimePerfSnapshot

    def frame_snapshot(self) -> HudFrameSnapshot: ...

    def debug_overlay_snapshot(
        self,
        *,
        entity_draws: int,
        slow_telemetry: DebugSlowTelemetry,
    ) -> HudDebugTextSnapshot: ...

    def player_list_snapshot(self) -> HudPlayerListSnapshot: ...

    def remote_nameplate_snapshots(self) -> tuple[PlayerNameplateRenderData, ...]: ...


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
    def camera(self) -> Any:
        return self._window.camera

    @property
    def settings(self) -> Any:
        return self._window.settings

    @property
    def debug_overlay_visible(self) -> bool:
        return self._window.debug_overlay_visible

    @property
    def inventory_open(self) -> bool:
        return self._window.inventory_open

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
    def text_input(self) -> str | None:
        return self._window.text_input

    @property
    def inventory_hud(self) -> InventoryHudPort:
        return cast(InventoryHudPort, object.__getattribute__(self._window, "_inv_ctrl"))

    @property
    def debug_device_label(self) -> str:
        info = getattr(self._window.mgl_context, "info", {})
        renderer = str(info.get("GL_RENDERER") or info.get("GL_VENDOR") or "unknown")
        version = str(info.get("GL_VERSION") or "unknown")
        return f"{renderer} ({version})"

    @property
    def runtime_perf_snapshot(self) -> RuntimePerfSnapshot:
        return self._window.runtime_perf_snapshot

    def frame_snapshot(self) -> HudFrameSnapshot:
        return HudFrameSnapshot(
            width=self._window.width,
            height=self._window.height,
            inventory_open=self._window.inventory_open,
        )

    def debug_overlay_snapshot(
        self,
        *,
        entity_draws: int,
        slow_telemetry: DebugSlowTelemetry,
    ) -> HudDebugTextSnapshot:
        win = self._window
        perf = win.runtime_perf_snapshot
        x, y, z = win.camera.position
        block_x, block_y, block_z = int(x), int(y), int(z)
        chunk_x, chunk_z = block_x // 16, block_z // 16
        facing = _facing_from_yaw(win.camera.yaw_degrees)
        biome = _biome_key_at(win, block_x, block_z)
        text = (
            f"FPS {perf.fps:5.1f} Frame {perf.frame_ms:5.1f} ms "
            f"Update {perf.update_ms:5.1f} Render {perf.render_ms:5.1f}\n"
            f"Position {x:7.2f} {y:7.2f} {z:7.2f}\n"
            f"Grounded {win.player.on_ground} VelocityY {win.player.velocity_y:5.2f}\n"
            f"Yaw {win.camera.yaw_degrees:6.1f} Pitch {win.camera.pitch_degrees:5.1f} "
            f"Facing {facing}\n"
            f"Biome {biome} Memory {slow_telemetry.memory} "
            f"Render distance {win.settings.world.render_distance} "
            f"Mesh uploads/frame {win.settings.world.mesh_uploads_per_frame} "
            f"Resource pack {_resource_pack_label(win.settings)}"
            f"\nChunks {perf.queues.loaded_chunks} "
            f"Pending {perf.queues.pending_chunks} "
            f"Mesh queue {perf.queues.pending_meshes} "
            f"Stream remesh {perf.queues.pending_stream_remeshes} "
            f"Visible sections {perf.queues.visible_sections}\n"
            f"Faces {win.world_renderer.face_count} "
            f"Triangles {win.world_renderer.triangle_count} "
            f"Draws {win.world_renderer.draw_calls}\n"
            f"Daylight {win.world_renderer.daylight:4.2f} "
            f"Smooth {win.world_renderer.smooth_lighting} "
            f"AO {win.world_renderer.ambient_occlusion} "
            f"Fog {win.world_renderer.fog_enabled} "
            f"Mesher {'greedy' if win.world_renderer.greedy_meshing else 'visible'}\n"
            f"Material profile {_material_profile_summary(win.world_renderer)}\n"
            f"Health {win.player_health:4.1f} "
            f"Entities {len(win.entities.world.alive)} "
            f"Mobs {len(win.entities.world.mob_ai)} "
            f"Drops {len(win.entities.world.items)} Entity draws {entity_draws}\n"
            f"Block {block_x:d} {block_y:d} {block_z:d} "
            f"Chunk {chunk_x:d} {chunk_z:d} "
            f"Remote players {len(win.remote_player_entities)}\n"
            f"Network {'client' if win.network_session is not None else 'singleplayer'} "
            f"Known players {len(win.network_players)}\n"
            f"Runtime {slow_telemetry.runtime} Frame {win.width}x{win.height}\n"
            f"Device {slow_telemetry.device}\n"
            f"Animation states {_animation_debug_summary(win.entities.world.mob_ai)}\n"
            f"Selected {_selected_item_name(win.hotbar, win.item_registry)} "
            "[1-9 hotbar, E inventory, C craft, Q drop]"
        )
        if win.world_renderer.selection is not None:
            text += f"\nTarget {win.world_renderer.selection.block}"
        return HudDebugTextSnapshot(text=text)

    def player_list_snapshot(self) -> HudPlayerListSnapshot:
        win = self._window
        names = ["Players Online:"]
        if win.network_session is not None:
            names.append("You (Local)")
            local_id = win.network_session.player_id
            for player_id, player in win.network_players.items():
                if player_id == local_id:
                    continue
                names.append(str(player.get("name", f"Player {player_id}")))
        else:
            names.append("You (Singleplayer)")
        return HudPlayerListSnapshot(lines=tuple(names))

    def remote_nameplate_snapshots(self) -> tuple[PlayerNameplateRenderData, ...]:
        win = self._window
        snapshots: list[PlayerNameplateRenderData] = []
        for player_id, entity in win.remote_player_entities.items():
            transform = win.entities.world.transforms.get(entity)
            if transform is None:
                continue
            name = win.network_players.get(player_id, {}).get("name", f"Player {player_id}")
            render_data = build_remote_player_nameplate_render_data(
                player_id=player_id,
                name=str(name),
                player_position=transform.position,
                camera_position=win.camera.position,
            )
            if render_data is not None:
                snapshots.append(render_data)
        return tuple(snapshots)


class HudController:
    """Owns HUD labels and draws the in-game overlay."""

    def __init__(self, win: HudView) -> None:
        self.win = win
        self._last_update_time = time.time()
        self._last_slow_telemetry_time = 0.0
        self._slow_telemetry = DebugSlowTelemetry()
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
        perf = win.runtime_perf_snapshot
        x, y, z = win.camera.position
        now = time.perf_counter()
        if win.debug_overlay_visible and (
            not self.debug_label.text or now - self._last_update_time >= 0.2
        ):
            self._last_update_time = now
            if now - self._last_slow_telemetry_time >= 1.0 or not self._slow_telemetry.runtime:
                self._last_slow_telemetry_time = now
                self._slow_telemetry = DebugSlowTelemetry(
                    memory=_process_memory_label(),
                    runtime=(
                        f"Python {sys.version_info.major}.{sys.version_info.minor} {sys.platform}"
                    ),
                    device=win.debug_device_label,
                )
            debug_snapshot = win.debug_overlay_snapshot(
                entity_draws=entity_draws,
                slow_telemetry=self._slow_telemetry,
            )
            new_debug_text = debug_snapshot.text
            if self.debug_label.text != new_debug_text:
                self.debug_label.text = new_debug_text
        new_hud_text = f"FPS: {perf.fps:5.1f} | XYZ: {x:7.2f} / {y:7.2f} / {z:7.2f}"
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
            self.player_list_label.text = win.player_list_snapshot().text
            self.player_list_label.x = frame.width // 2
            self.player_list_label.y = frame.height // 2
            self.player_list_label.draw()

        matrix = camera_matrix(
            win.camera,
            max(frame.width, 1) / max(frame.height, 1),
            win.settings.camera.field_of_view,
        )
        for render_data in win.remote_nameplate_snapshots():
            pos = np.array([*render_data.world_position, 1.0], dtype=np.float32)
            clip = matrix @ pos
            w = clip[3]
            if w > 0:
                ndc_x = clip[0] / w
                ndc_y = clip[1] / w
                if -1 <= ndc_x <= 1 and -1 <= ndc_y <= 1:
                    screen_x = (ndc_x + 1) * frame.width / 2
                    screen_y = (ndc_y + 1) * frame.height / 2
                    self.player_name_label.text = render_data.text
                    self.player_name_label.x = screen_x
                    self.player_name_label.y = screen_y
                    self.player_name_label.color = (
                        255,
                        255,
                        255,
                        int(255 * render_data.alpha),
                    )
                    self.player_name_label.draw()

        self.crosshair.visible = not frame.inventory_open
        self.crosshair.x = frame.width // 2
        self.crosshair.y = frame.height // 2
        win.inventory_hud.draw_hotbar()
        win.inventory_hud.draw_health()
        win.inventory_hud.draw_held_item()
        win.inventory_hud.update_hud_status()
        if frame.inventory_open:
            win.inventory_hud.draw_inventory()
        if win.text_input is not None:
            win.menu_ui._draw_text_input()
        win.hud_batch.draw()


def _animation_debug_summary(mob_ai: Any) -> str:
    counts: dict[str, int] = {}
    for _entity, ai in mob_ai.items():
        counts[ai.state.value] = counts.get(ai.state.value, 0) + 1
    return " ".join(f"{state}:{count}" for state, count in sorted(counts.items())) or "none"


def _material_profile_summary(world_renderer: Any) -> str:
    pipeline = getattr(world_renderer, "material_pipeline", None)
    if pipeline is None:
        return "color-only bundle off"
    bundle_state = "on" if pipeline.build_material_bundle else "off"
    return f"{pipeline.profile.value} bundle {bundle_state}"


def _selected_item_name(hotbar: Any, item_registry: Any) -> str:
    selected = hotbar.selected
    if selected is None:
        return "empty"
    definition = item_registry.by_id(selected.item_id)
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


def _resource_pack_label(settings: Any) -> str:
    path = str(getattr(settings.graphics, "resource_pack_path", "") or "")
    if not path:
        return "Default"
    pack_path = Path(path)
    return pack_path.stem if pack_path.suffix.lower() == ".zip" else pack_path.name


def _biome_key_at(win: Any, block_x: int, block_z: int) -> str:
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
