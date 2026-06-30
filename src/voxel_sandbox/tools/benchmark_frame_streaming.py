from __future__ import annotations

import tempfile
import time
from dataclasses import replace
from pathlib import Path
from statistics import quantiles
from time import perf_counter

from voxel_sandbox.app.settings import AppSettings


def _p95(timings: list[float]) -> float:
    if len(timings) < 2:
        return timings[0] if timings else 0.0
    return quantiles(timings, n=20)[18]


def run_benchmark(
    settings: AppSettings,
    frames: int = 240,
    warmup_frames: int = 30,
    render_distance: int | None = None,
) -> int:
    from voxel_sandbox.render.window import GameWindow

    if render_distance is not None:
        settings = replace(
            settings,
            world=replace(settings.world, render_distance=render_distance),
        )

    with tempfile.TemporaryDirectory(prefix="veilstone-benchmark-") as directory:
        window = GameWindow(settings, visible=False, save_root=Path(directory))
        try:
            from voxel_sandbox.render.ui.menu import Screen

            window.switch_to()
            window.menu.screen = Screen.GAME
            if window.player is None:
                raise RuntimeError("Frame streaming benchmark requires a local player")
            player = window.player
            framebuffer = window.mgl_context.simple_framebuffer((320, 180), components=4)
            framebuffer.use()
            timings: list[float] = []
            update_timings: list[float] = []
            render_timings: list[float] = []
            for frame in range(frames + warmup_frames):
                player.x = 8.5 + frame * 0.75
                player.z = 8.5 + ((frame // 24) % 3) * 8.0
                start = perf_counter()
                update_start = perf_counter()
                window.fixed_update(1.0 / 60.0)
                render_start = perf_counter()
                window.world_renderer.render(
                    window.camera,
                    320,
                    180,
                    settings.camera.field_of_view,
                )
                end = perf_counter()
                if frame < warmup_frames:
                    time.sleep(0.002)
                    continue
                update_timings.append((render_start - update_start) * 1000.0)
                render_timings.append((end - render_start) * 1000.0)
                timings.append((end - start) * 1000.0)
                time.sleep(0.002)
            print(
                f"frame streaming {frames} frames warmup={warmup_frames}: "
                f"avg={sum(timings) / frames:.3f} ms "
                f"p95={_p95(timings):.3f} ms max={max(timings):.3f} ms "
                f"update_p95={_p95(update_timings):.3f} ms "
                f"update_max={max(update_timings):.3f} ms "
                f"render_p95={_p95(render_timings):.3f} ms "
                f"render_max={max(render_timings):.3f} ms "
                f"chunks={window.world_renderer.loaded_chunks} "
                f"pending_chunks={window.world_renderer.pending_chunks} "
                f"mesh_queue={window.world_renderer.pending_meshes}"
            )
            framebuffer.release()
            return 0
        finally:
            window.close()
