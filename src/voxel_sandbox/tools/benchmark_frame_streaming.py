from __future__ import annotations

import cProfile
import pstats
import tempfile
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import cast

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.render.perf import (
    FrameBottleneck,
    RenderQueueSnapshot,
    StreamingStageSample,
    frame_bottleneck,
)
from voxel_sandbox.render.render_quality import (
    RenderQualityProfile,
    build_custom_profile,
    resolve_render_quality_profile,
)

_BOTTLENECK_ORDER: tuple[FrameBottleneck, ...] = ("update", "render", "balanced", "idle")
type ProfileKey = tuple[str, int, str]
type ProfileStat = tuple[int, int, float, float, object]


@dataclass(frozen=True, slots=True)
class ProfileRow:
    cumulative_ms: float
    self_ms: float
    calls: int
    function: str


def percentile_ms(timings: list[float], percentile: float) -> float:
    if not timings:
        return 0.0
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("Percentile must be between 0 and 100")
    ordered = sorted(timings)
    rank = (len(ordered) - 1) * percentile / 100.0
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def fps_from_frame_ms(frame_ms: float) -> float:
    return 1000.0 / frame_ms if frame_ms > 0.0 else 0.0


def frame_pacing_delay(frame_seconds: float, target_fps: float = 60.0) -> float:
    if target_fps <= 0.0:
        raise ValueError("Target FPS must be positive")
    return max(0.0, 1.0 / target_fps - frame_seconds)


def target_chunk_count(render_distance: int) -> int:
    if render_distance < 0:
        raise ValueError("Render distance cannot be negative")
    return (render_distance * 2 + 1) ** 2


def format_bottleneck_distribution(samples: Iterable[tuple[float, float]]) -> str:
    counts = Counter(frame_bottleneck(update_ms, render_ms) for update_ms, render_ms in samples)
    return "bottlenecks=" + " ".join(f"{label}:{counts[label]}" for label in _BOTTLENECK_ORDER)


def format_quality_summary(profile: RenderQualityProfile) -> str:
    def enabled(value: bool) -> str:
        return "on" if value else "off"

    return (
        f"quality={profile.preset} shadows={profile.shadow_quality} "
        f"smooth={enabled(profile.smooth_lighting)} "
        f"ao={enabled(profile.ambient_occlusion)} fog={enabled(profile.fog)} "
        f"clouds={enabled(profile.clouds)} wind={enabled(profile.vegetation_wind)} "
        f"water={enabled(profile.water_detail)} materials={profile.material_quality} "
        f"terrain_filter={'linear' if profile.linear_texture_minification else 'nearest'}"
    )


def benchmark_world_ready(
    queues: RenderQueueSnapshot,
    *,
    target_chunks: int | None = None,
) -> bool:
    if queues.loaded_chunks <= 0 or queues.visible_sections <= 0:
        return False
    if target_chunks is None:
        return True
    return (
        queues.loaded_chunks >= target_chunks
        and queues.pending_chunks == 0
        and queues.pending_meshes == 0
        and queues.pending_stream_relights == 0
        and queues.pending_stream_remeshes == 0
    )


def active_display_available() -> bool:
    import pyglet

    return bool(pyglet.display.get_display().get_screens())


def benchmark_player_position(
    frame: int,
    *,
    path: str,
    movement_speed: float,
) -> tuple[float, float]:
    if path not in {"stress", "walk"}:
        raise ValueError(f"Unknown benchmark path: {path}")
    if movement_speed < 0.0:
        raise ValueError("Benchmark movement speed cannot be negative")
    x = 8.5 + frame * movement_speed / 60.0
    z = 8.5 if path == "walk" else 8.5 + ((frame // 24) % 3) * 8.0
    return x, z


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


def save_framebuffer_png(
    framebuffer: object,
    width: int,
    height: int,
    output: str | Path,
) -> Path:
    from PIL import Image

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pixels = cast(bytes, framebuffer.read(components=4, alignment=1))  # type: ignore[attr-defined]
    image = Image.frombytes("RGBA", (width, height), pixels)
    image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    image.save(destination)
    return destination


def format_streaming_stage_summary(samples: list[StreamingStageSample]) -> str:
    if not samples:
        return "streaming_stages=unavailable"
    fields = ("streamer_ms", "integration_ms", "relight_ms", "remesh_ms")
    summary = ["streaming_stages"]
    for field in fields:
        values = [getattr(sample, field) for sample in samples]
        label = field.removesuffix("_ms")
        summary.append(
            f"{label}_p95={percentile_ms(values, 95):.3f}ms {label}_max={max(values):.3f}ms"
        )
    worst_index = max(range(len(samples)), key=lambda index: samples[index].total_ms)
    worst = samples[worst_index]
    summary.append(
        f"worst_frame={worst_index} worst_total={worst.total_ms:.3f}ms "
        f"worst_streamer={worst.streamer_ms:.3f}ms "
        f"worst_integration={worst.integration_ms:.3f}ms "
        f"worst_relight={worst.relight_ms:.3f}ms worst_remesh={worst.remesh_ms:.3f}ms"
    )
    return " ".join(summary)


def run_benchmark(
    settings: AppSettings,
    frames: int = 240,
    warmup_frames: int = 30,
    render_distance: int | None = None,
    quality_preset: str | None = None,
    width: int = 320,
    height: int = 180,
    generation_workers: int | None = None,
    meshing_workers: int | None = None,
    path: str = "stress",
    movement_speed: float = 45.0,
    startup_timeout: float = 10.0,
    startup_mode: str = "visible",
    backend: str = "window",
    profile_update: bool = False,
    profile_limit: int = 15,
    screenshot_output: str | Path | None = None,
) -> int:
    if width < 1 or height < 1:
        raise ValueError("Benchmark resolution must be positive")
    if frames < 1 or warmup_frames < 0:
        raise ValueError("Benchmark frames must be positive and warmup cannot be negative")
    if startup_timeout <= 0.0:
        raise ValueError("Benchmark startup timeout must be positive")
    if startup_mode not in {"visible", "full"}:
        raise ValueError(f"Unknown benchmark startup mode: {startup_mode}")
    if backend not in {"window", "standalone"}:
        raise ValueError(f"Unknown frame streaming benchmark backend: {backend}")
    benchmark_player_position(0, path=path, movement_speed=movement_speed)

    world = settings.world
    graphics = settings.graphics
    if render_distance is not None:
        world = replace(world, render_distance=render_distance)
    if generation_workers is not None:
        world = replace(world, generation_workers=generation_workers)
    if meshing_workers is not None:
        world = replace(world, meshing_workers=meshing_workers)
    if quality_preset is not None:
        graphics = replace(graphics, quality_preset=quality_preset)
    settings = replace(settings, world=world, graphics=graphics)
    quality = resolve_render_quality_profile(
        graphics.quality_preset,
        custom=build_custom_profile(
            shadow_quality=graphics.shadow_quality,
            smooth_lighting=graphics.smooth_lighting,
            ambient_occlusion=graphics.ambient_occlusion,
            fog=graphics.fog,
            clouds=graphics.clouds,
            material_quality=graphics.material_quality,
        ),
    )
    effective_render_distance = (
        render_distance
        if render_distance is not None
        else quality.render_distance
        if quality.render_distance is not None
        else world.render_distance
    )
    if backend == "standalone":
        return _run_standalone_benchmark(
            settings,
            quality,
            frames=frames,
            warmup_frames=warmup_frames,
            width=width,
            height=height,
            path=path,
            movement_speed=movement_speed,
            startup_timeout=startup_timeout,
            startup_mode=startup_mode,
            render_distance=effective_render_distance,
            profile_update=profile_update,
            profile_limit=profile_limit,
            screenshot_output=screenshot_output,
        )
    if not active_display_available():
        print("frame streaming benchmark: unavailable (no active display)")
        return 2

    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-benchmark-") as directory:
        window = GameWindow(settings, visible=False, save_root=Path(directory))
        try:
            from voxel_sandbox.render.ui.menu import Screen

            window.switch_to()
            window.menu.screen = Screen.GAME
            if render_distance is not None:
                window.world_renderer.set_render_distance(effective_render_distance)
            if window.player is None:
                raise RuntimeError("Frame streaming benchmark requires a local player")
            player = window.player
            framebuffer = window.mgl_context.simple_framebuffer((width, height), components=4)
            framebuffer.use()
            startup_frames = 0
            startup_deadline = perf_counter() + startup_timeout
            startup_target = (
                target_chunk_count(effective_render_distance) if startup_mode == "full" else None
            )
            while True:
                window.fixed_update(1.0 / 60.0)
                window.world_renderer.render(
                    window.camera,
                    width,
                    height,
                    settings.camera.field_of_view,
                )
                startup_frames += 1
                startup_queues = window.world_renderer.perf_queues()
                if benchmark_world_ready(startup_queues, target_chunks=startup_target):
                    break
                if perf_counter() >= startup_deadline:
                    raise RuntimeError(
                        "Frame streaming benchmark startup timed out before the world "
                        "became renderable: "
                        f"chunks={startup_queues.loaded_chunks} "
                        f"pending_chunks={startup_queues.pending_chunks} "
                        f"mesh_queue={startup_queues.pending_meshes} "
                        f"visible_sections={startup_queues.visible_sections}"
                    )
                time.sleep(0.005)
            timings: list[float] = []
            update_timings: list[float] = []
            render_timings: list[float] = []
            queue_samples: list[RenderQueueSnapshot] = []
            streaming_stage_samples: list[StreamingStageSample] = []
            queue_start = window.world_renderer.perf_queues()
            update_profile = cProfile.Profile() if profile_update else None
            window.world_renderer.enable_streaming_stage_profiling(profile_update)
            for frame in range(frames + warmup_frames):
                player.x, player.z = benchmark_player_position(
                    frame,
                    path=path,
                    movement_speed=movement_speed,
                )
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
                    width,
                    height,
                    settings.camera.field_of_view,
                )
                end = perf_counter()
                if frame < warmup_frames:
                    time.sleep(frame_pacing_delay(end - start))
                    continue
                update_timings.append((render_start - update_start) * 1000.0)
                render_timings.append((end - render_start) * 1000.0)
                timings.append((end - start) * 1000.0)
                queue_samples.append(window.world_renderer.perf_queues())
                if profile_update:
                    streaming_stage_samples.append(
                        window.world_renderer.last_streaming_stage_sample
                    )
                time.sleep(frame_pacing_delay(end - start))
            bottleneck_summary = format_bottleneck_distribution(
                zip(update_timings, render_timings, strict=True)
            )
            frame_p95 = percentile_ms(timings, 95)
            frame_p99 = percentile_ms(timings, 99)
            queues = window.world_renderer.perf_queues()
            print(
                f"frame streaming {frames} frames warmup={warmup_frames}: "
                f"pacing=60hz avg={sum(timings) / frames:.3f} ms "
                f"p50={percentile_ms(timings, 50):.3f} ms "
                f"p95={frame_p95:.3f} ms p95_fps={fps_from_frame_ms(frame_p95):.1f} "
                f"p99={frame_p99:.3f} ms p99_fps={fps_from_frame_ms(frame_p99):.1f} "
                f"max={max(timings):.3f} ms "
                f"update_p95={percentile_ms(update_timings, 95):.3f} ms "
                f"update_max={max(update_timings):.3f} ms "
                f"render_p95={percentile_ms(render_timings, 95):.3f} ms "
                f"render_max={max(render_timings):.3f} ms "
                f"resolution={width}x{height} "
                f"render_distance={effective_render_distance} "
                f"target_chunks={target_chunk_count(effective_render_distance)} "
                f"workers=generation:{world.generation_workers},meshing:{world.meshing_workers} "
                f"path={path} movement_speed={movement_speed:.3f} "
                f"startup_mode={startup_mode} startup_frames={startup_frames} "
                f"{format_quality_summary(quality)} "
                f"{bottleneck_summary} "
                f"chunks={queues.loaded_chunks} "
                f"pending_chunks={queues.pending_chunks} "
                f"pending_chunks_max={max(sample.pending_chunks for sample in queue_samples)} "
                f"mesh_queue_start={queue_start.pending_meshes} "
                f"mesh_queue_max={max(sample.pending_meshes for sample in queue_samples)} "
                f"mesh_queue={queues.pending_meshes} "
                f"relight_queue={queues.pending_stream_relights} "
                f"remesh_queue={queues.pending_stream_remeshes} "
                f"visible_sections={queues.visible_sections}"
            )
            if update_profile is not None:
                print(format_veilstone_profile(update_profile, profile_limit))
                print(format_streaming_stage_summary(streaming_stage_samples))
            if screenshot_output is not None:
                screenshot = save_framebuffer_png(framebuffer, width, height, screenshot_output)
                print(f"screenshot={screenshot}")
            framebuffer.release()
            return 0
        finally:
            window.close()


def _run_standalone_benchmark(
    settings: AppSettings,
    quality: RenderQualityProfile,
    *,
    frames: int,
    warmup_frames: int,
    width: int,
    height: int,
    path: str,
    movement_speed: float,
    startup_timeout: float,
    startup_mode: str,
    render_distance: int,
    profile_update: bool,
    profile_limit: int,
    screenshot_output: str | Path | None,
) -> int:
    import math

    import moderngl

    from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkCoord
    from voxel_sandbox.render.camera import FirstPersonCamera
    from voxel_sandbox.render.world_scene import DemoWorldRenderer

    world = settings.world
    graphics = settings.graphics
    context = moderngl.create_standalone_context(require=330)
    framebuffer = context.simple_framebuffer((width, height), components=4)
    framebuffer.use()
    context.viewport = (0, 0, width, height)
    context.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
    try:
        with tempfile.TemporaryDirectory(prefix="veilstone-standalone-benchmark-") as directory:
            renderer = DemoWorldRenderer(
                context,
                seed=world.seed,
                render_distance=render_distance,
                generation_workers=world.generation_workers,
                generation_backend=world.generation_backend,
                uploads_per_frame=world.chunk_uploads_per_frame,
                meshing_workers=world.meshing_workers,
                meshing_backend=world.meshing_backend,
                mesh_uploads_per_frame=world.mesh_uploads_per_frame,
                greedy_meshing=graphics.greedy_meshing,
                smooth_lighting=quality.smooth_lighting,
                ambient_occlusion=quality.ambient_occlusion,
                fog=quality.fog,
                fog_start=graphics.fog_start,
                fog_end=graphics.fog_end,
                day_cycle_seconds=graphics.day_cycle_seconds,
                shadow_quality=quality.shadow_quality,
                shadow_bias=graphics.shadow_bias,
                save_root=Path(directory),
                resource_pack_path=graphics.resource_pack_path,
                material_quality=quality.material_quality,
                water_detail=quality.water_detail,
                linear_texture_minification=quality.linear_texture_minification,
                opaque_batch_chunks=quality.opaque_batch_chunks,
            )
            renderer.vegetation_wind_enabled = quality.vegetation_wind
            try:
                spawn_x, spawn_y, spawn_z = renderer.spawn_position
                camera = FirstPersonCamera(
                    x=spawn_x,
                    y=spawn_y + 1.62,
                    z=spawn_z,
                    yaw_degrees=0.0,
                    pitch_degrees=-20.0,
                )
                startup_frames = 0
                startup_deadline = perf_counter() + startup_timeout
                startup_target = (
                    target_chunk_count(render_distance) if startup_mode == "full" else None
                )
                while True:
                    camera.x, camera.z = benchmark_player_position(
                        0,
                        path=path,
                        movement_speed=movement_speed,
                    )
                    camera.y = renderer.terrain_height_at(camera.x, camera.z) + 1.62
                    center = ChunkCoord(
                        math.floor(camera.x / SECTION_SIZE),
                        math.floor(camera.z / SECTION_SIZE),
                    )
                    renderer.update(1.0 / 60.0)
                    renderer.update_streaming(center)
                    context.clear(*renderer.clear_color, depth=1.0)
                    renderer.render(camera, width, height, settings.camera.field_of_view)
                    context.finish()
                    startup_frames += 1
                    startup_queues = renderer.perf_queues()
                    if benchmark_world_ready(startup_queues, target_chunks=startup_target):
                        break
                    if perf_counter() >= startup_deadline:
                        raise RuntimeError(
                            "Standalone frame streaming startup timed out before the world "
                            "became renderable: "
                            f"chunks={startup_queues.loaded_chunks} "
                            f"pending_chunks={startup_queues.pending_chunks} "
                            f"mesh_queue={startup_queues.pending_meshes} "
                            f"visible_sections={startup_queues.visible_sections}"
                        )
                    time.sleep(0.005)

                timings: list[float] = []
                update_timings: list[float] = []
                render_timings: list[float] = []
                render_submit_timings: list[float] = []
                gpu_wait_timings: list[float] = []
                queue_samples: list[RenderQueueSnapshot] = []
                streaming_stage_samples: list[StreamingStageSample] = []
                queue_start = renderer.perf_queues()
                update_profile = cProfile.Profile() if profile_update else None
                renderer.enable_streaming_stage_profiling(profile_update)
                for frame in range(frames + warmup_frames):
                    camera.x, camera.z = benchmark_player_position(
                        frame,
                        path=path,
                        movement_speed=movement_speed,
                    )
                    camera.y = renderer.terrain_height_at(camera.x, camera.z) + 1.62
                    start = perf_counter()
                    update_start = perf_counter()
                    if update_profile is not None and frame >= warmup_frames:
                        update_profile.enable()
                    renderer.update(1.0 / 60.0)
                    center = ChunkCoord(
                        math.floor(camera.x / SECTION_SIZE),
                        math.floor(camera.z / SECTION_SIZE),
                    )
                    renderer.update_streaming(center)
                    if update_profile is not None and frame >= warmup_frames:
                        update_profile.disable()
                    render_start = perf_counter()
                    context.clear(*renderer.clear_color, depth=1.0)
                    renderer.render(camera, width, height, settings.camera.field_of_view)
                    gpu_wait_start = perf_counter()
                    context.finish()
                    end = perf_counter()
                    if frame < warmup_frames:
                        time.sleep(frame_pacing_delay(end - start))
                        continue
                    update_timings.append((render_start - update_start) * 1000.0)
                    render_timings.append((end - render_start) * 1000.0)
                    render_submit_timings.append((gpu_wait_start - render_start) * 1000.0)
                    gpu_wait_timings.append((end - gpu_wait_start) * 1000.0)
                    timings.append((end - start) * 1000.0)
                    queue_samples.append(renderer.perf_queues())
                    if profile_update:
                        streaming_stage_samples.append(renderer.last_streaming_stage_sample)
                    time.sleep(frame_pacing_delay(end - start))

                bottleneck_summary = format_bottleneck_distribution(
                    zip(update_timings, render_timings, strict=True)
                )
                frame_p95 = percentile_ms(timings, 95)
                frame_p99 = percentile_ms(timings, 99)
                queues = renderer.perf_queues()
                print(
                    f"frame streaming {frames} frames warmup={warmup_frames}: "
                    "backend=standalone-world coverage=world-only gpu_sync=finish pacing=60hz "
                    f"avg={sum(timings) / frames:.3f} ms "
                    f"p50={percentile_ms(timings, 50):.3f} ms "
                    f"p95={frame_p95:.3f} ms p95_fps={fps_from_frame_ms(frame_p95):.1f} "
                    f"p99={frame_p99:.3f} ms p99_fps={fps_from_frame_ms(frame_p99):.1f} "
                    f"max={max(timings):.3f} ms "
                    f"update_p95={percentile_ms(update_timings, 95):.3f} ms "
                    f"update_max={max(update_timings):.3f} ms "
                    f"render_p95={percentile_ms(render_timings, 95):.3f} ms "
                    f"render_max={max(render_timings):.3f} ms "
                    f"render_submit_p95={percentile_ms(render_submit_timings, 95):.3f} ms "
                    f"gpu_wait_p95={percentile_ms(gpu_wait_timings, 95):.3f} ms "
                    f"resolution={width}x{height} "
                    f"render_distance={render_distance} "
                    f"target_chunks={target_chunk_count(render_distance)} "
                    f"workers=generation:{world.generation_workers},"
                    f"meshing:{world.meshing_workers} "
                    f"path={path} movement_speed={movement_speed:.3f} "
                    f"startup_mode={startup_mode} startup_frames={startup_frames} "
                    f"{format_quality_summary(quality)} "
                    f"{bottleneck_summary} "
                    f"chunks={queues.loaded_chunks} "
                    f"pending_chunks={queues.pending_chunks} "
                    f"pending_chunks_max={max(sample.pending_chunks for sample in queue_samples)} "
                    f"mesh_queue_start={queue_start.pending_meshes} "
                    f"mesh_queue_max={max(sample.pending_meshes for sample in queue_samples)} "
                    f"mesh_queue={queues.pending_meshes} "
                    f"relight_queue={queues.pending_stream_relights} "
                    f"remesh_queue={queues.pending_stream_remeshes} "
                    f"visible_sections={queues.visible_sections} "
                    f"draw_calls={renderer.draw_calls}"
                )
                if update_profile is not None:
                    print(format_veilstone_profile(update_profile, profile_limit))
                    print(format_streaming_stage_summary(streaming_stage_samples))
                if screenshot_output is not None:
                    screenshot = save_framebuffer_png(framebuffer, width, height, screenshot_output)
                    print(f"screenshot={screenshot}")
                return 0
            finally:
                renderer.release()
    finally:
        framebuffer.release()
        context.release()
