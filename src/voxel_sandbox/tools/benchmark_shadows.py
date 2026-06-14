from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path
from statistics import quantiles
from time import perf_counter, sleep

from voxel_sandbox.app.settings import AppSettings

SHADOW_FRAME_BUDGET_MS = 12.0


def run_benchmark(settings: AppSettings, frames: int = 180) -> int:
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    medium = replace(settings, graphics=replace(settings.graphics, shadow_quality="medium"))
    with tempfile.TemporaryDirectory(prefix="veilstone-shadow-benchmark-") as directory:
        window = GameWindow(medium, visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.switch_to()
            for _ in range(60):
                window.fixed_update(1.0 / 60.0)
                window.dispatch_event("on_draw")
                window.mgl_context.finish()
                sleep(0.002)
            timings: list[float] = []
            for _ in range(frames):
                start = perf_counter()
                window.fixed_update(1.0 / 60.0)
                window.dispatch_event("on_draw")
                window.mgl_context.finish()
                timings.append((perf_counter() - start) * 1000.0)
            p95 = quantiles(timings, n=20)[18]
            average = sum(timings) / frames
            print(
                f"medium shadows {frames} frames: avg={average:.2f} ms "
                f"p95={p95:.2f} ms max={max(timings):.2f} ms "
                f"budget={SHADOW_FRAME_BUDGET_MS:.1f} ms"
            )
            return 0 if p95 <= SHADOW_FRAME_BUDGET_MS else 1
        finally:
            window.close()
