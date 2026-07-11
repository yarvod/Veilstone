from __future__ import annotations

import cProfile
import pstats
import tempfile
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import quantiles
from time import perf_counter
from typing import cast

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.render.perf import FrameBottleneck, frame_bottleneck

_BOTTLENECK_ORDER: tuple[FrameBottleneck, ...] = ("update", "render", "balanced", "idle")
type ProfileKey = tuple[str, int, str]
type ProfileStat = tuple[int, int, float, float, object]


@dataclass(frozen=True, slots=True)
class ProfileRow:
    cumulative_ms: float
    self_ms: float
    calls: int
    function: str


def _p95(timings: list[float]) -> float:
    if len(timings) < 2:
        return timings[0] if timings else 0.0
    return quantiles(timings, n=20)[18]


def format_bottleneck_distribution(samples: Iterable[tuple[float, float]]) -> str:
    counts = Counter(frame_bottleneck(update_ms, render_ms) for update_ms, render_ms in samples)
    return "bottlenecks=" + " ".join(f"{label}:{counts[label]}" for label in _BOTTLENECK_ORDER)


def veilstone_profile_rows(profile: cProfile.Profile, limit: int = 15) -> tuple[ProfileRow, ...]:
    if limit < 1:
        raise ValueError("Profile row limit must be positive")
    rows: list[ProfileRow] = []
    raw_stats = cast(
        "dict[ProfileKey, ProfileStat]",
        vars(pstats.Stats(profile))["stats"],
    )
    for (filename, line, function), (
        _primitive,
        calls,
        self_s,
        cumulative_s,
        _callers,
    ) in raw_stats.items():
        path = Path(filename)
        if "voxel_sandbox" not in path.parts:
            continue
        package_index = path.parts.index("voxel_sandbox")
        package_path = "/".join(path.parts[package_index:])
        rows.append(
            ProfileRow(
                cumulative_ms=cumulative_s * 1000.0,
                self_ms=self_s * 1000.0,
                calls=calls,
                function=f"{package_path}:{line}:{function}",
            )
        )
    rows.sort(key=lambda row: (-row.cumulative_ms, -row.self_ms, row.function))
    return tuple(rows[:limit])


def format_veilstone_profile(profile: cProfile.Profile, limit: int = 15) -> str:
    rows = veilstone_profile_rows(profile, limit)
    lines = [f"update profile top={limit} scope=voxel_sandbox sort=cumulative"]
    lines.extend(
        f"cum={row.cumulative_ms:.3f} ms self={row.self_ms:.3f} ms calls={row.calls} {row.function}"
        for row in rows
    )
    return "\n".join(lines)


def run_benchmark(
    settings: AppSettings,
    frames: int = 240,
    warmup_frames: int = 30,
    render_distance: int | None = None,
    profile_update: bool = False,
    profile_limit: int = 15,
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
            update_profile = cProfile.Profile() if profile_update else None
            for frame in range(frames + warmup_frames):
                player.x = 8.5 + frame * 0.75
                player.z = 8.5 + ((frame // 24) % 3) * 8.0
                start = perf_counter()
                update_start = perf_counter()
                if update_profile is not None and frame >= warmup_frames:
                    update_profile.enable()
                window.fixed_update(1.0 / 60.0)
                if update_profile is not None and frame >= warmup_frames:
                    update_profile.disable()
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
            bottleneck_summary = format_bottleneck_distribution(
                zip(update_timings, render_timings, strict=True)
            )
            print(
                f"frame streaming {frames} frames warmup={warmup_frames}: "
                f"avg={sum(timings) / frames:.3f} ms "
                f"p95={_p95(timings):.3f} ms max={max(timings):.3f} ms "
                f"update_p95={_p95(update_timings):.3f} ms "
                f"update_max={max(update_timings):.3f} ms "
                f"render_p95={_p95(render_timings):.3f} ms "
                f"render_max={max(render_timings):.3f} ms "
                f"{bottleneck_summary} "
                f"chunks={window.world_renderer.loaded_chunks} "
                f"pending_chunks={window.world_renderer.pending_chunks} "
                f"mesh_queue={window.world_renderer.pending_meshes}"
            )
            if update_profile is not None:
                print(format_veilstone_profile(update_profile, profile_limit))
            framebuffer.release()
            return 0
        finally:
            window.close()
