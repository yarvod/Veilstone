from __future__ import annotations

import tempfile
import time
from pathlib import Path
from statistics import quantiles
from time import perf_counter

from voxel_sandbox.app.settings import AppSettings


def run_benchmark(settings: AppSettings, frames: int = 240) -> int:
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-benchmark-") as directory:
        window = GameWindow(settings, visible=False, save_root=Path(directory))
        try:
            window.switch_to()
            framebuffer = window.mgl_context.simple_framebuffer((320, 180), components=4)
            framebuffer.use()
            window.camera.x = 80.5
            timings: list[float] = []
            for _ in range(frames):
                start = perf_counter()
                window.world_renderer.render(
                    window.camera,
                    320,
                    180,
                    settings.camera.field_of_view,
                )
                timings.append((perf_counter() - start) * 1000.0)
                time.sleep(0.002)
            p95 = quantiles(timings, n=20)[18]
            print(
                f"frame streaming {frames} frames: avg={sum(timings) / frames:.3f} ms "
                f"p95={p95:.3f} ms max={max(timings):.3f} ms "
                f"chunks={window.world_renderer.loaded_chunks} "
                f"mesh_queue={window.world_renderer.pending_meshes}"
            )
            framebuffer.release()
            return 0
        finally:
            window.close()
