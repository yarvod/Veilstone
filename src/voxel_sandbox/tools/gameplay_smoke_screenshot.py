from __future__ import annotations

import json
import math
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from voxel_sandbox.app.settings import AppSettings


@dataclass(frozen=True, slots=True)
class GameplaySmokeMetadata:
    screenshot: str
    seed: str
    render_distance: int
    resource_pack: str
    frames: int
    start_position: tuple[float, float, float]
    end_position: tuple[float, float, float]
    moved_distance: float
    queue_summary: dict[str, int]
    debug_overlay_enabled: bool
    display_status: str


def build_smoke_metadata(
    *,
    screenshot: Path,
    settings: AppSettings,
    frames: int,
    start_position: tuple[float, float, float],
    end_position: tuple[float, float, float],
    queue_summary: dict[str, int],
    debug_overlay_enabled: bool = True,
    display_status: str = "available",
) -> GameplaySmokeMetadata:
    return GameplaySmokeMetadata(
        screenshot=str(screenshot),
        seed=settings.world.seed,
        render_distance=settings.world.render_distance,
        resource_pack=_resource_pack_label(settings),
        frames=frames,
        start_position=start_position,
        end_position=end_position,
        moved_distance=math.dist(start_position, end_position),
        queue_summary=dict(sorted(queue_summary.items())),
        debug_overlay_enabled=debug_overlay_enabled,
        display_status=display_status,
    )


def write_smoke_metadata(path: Path, metadata: GameplaySmokeMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_smoke(
    settings: AppSettings,
    *,
    frames: int = 90,
    render_distance: int | None = None,
    metadata_path: Path | None = None,
) -> int:
    import pyglet
    from pyglet.window import key

    if not pyglet.display.get_display().get_screens():
        print("gameplay-smoke-screenshot: skipped (no active display)")
        return 0

    from voxel_sandbox.engine.game_state import GameState
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    world_settings = settings.world
    if render_distance is not None:
        world_settings = replace(world_settings, render_distance=render_distance)
    settings = replace(
        settings,
        world=replace(
            world_settings,
            generation_backend="thread",
            meshing_backend="thread",
        ),
    )

    with tempfile.TemporaryDirectory(prefix="veilstone-gameplay-smoke-") as directory:
        window = GameWindow(settings, visible=False, save_root=Path(directory))
        try:
            window.switch_to()
            window.menu.screen = Screen.GAME
            window.debug_overlay_visible = True
            window.game_state.try_transition(GameState.PLAYING)

            start = _player_position(window)
            window.key_state.press(key.W)
            for _ in range(frames):
                window.fixed_update(1.0 / 60.0)
                window.on_draw()
                window.flip()
            window.key_state.release(key.W)

            end = _player_position(window)
            window.mgl_context.finish()
            screenshot = window.save_screenshot()
            perf = window.runtime_perf_snapshot
            metadata = build_smoke_metadata(
                screenshot=screenshot,
                settings=settings,
                frames=frames,
                start_position=start,
                end_position=end,
                queue_summary={
                    "loaded_chunks": perf.queues.loaded_chunks,
                    "pending_chunks": perf.queues.pending_chunks,
                    "pending_meshes": perf.queues.pending_meshes,
                    "pending_stream_remeshes": perf.queues.pending_stream_remeshes,
                    "visible_sections": perf.queues.visible_sections,
                },
            )
            metadata_path = metadata_path or screenshot.with_suffix(".json")
            write_smoke_metadata(metadata_path, metadata)
            print(f"screenshot={screenshot}")
            print(f"metadata={metadata_path}")
            print(f"moved={metadata.moved_distance:.3f}")
            print(
                "queues="
                f"loaded:{perf.queues.loaded_chunks} "
                f"pending:{perf.queues.pending_chunks} "
                f"mesh:{perf.queues.pending_meshes} "
                f"visible:{perf.queues.visible_sections}"
            )
        finally:
            window.close()

    return 0


def _player_position(window: Any) -> tuple[float, float, float]:
    return (float(window.player.x), float(window.player.y), float(window.player.z))


def _resource_pack_label(settings: AppSettings) -> str:
    path = settings.graphics.resource_pack_path
    if not path:
        return "Default"
    pack_path = Path(path)
    return pack_path.stem if pack_path.suffix.lower() == ".zip" else pack_path.name
