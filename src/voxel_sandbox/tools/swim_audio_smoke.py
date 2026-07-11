# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import math
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, cast

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.generation import TerrainGenerator
from voxel_sandbox.engine.physics import PlayerController


@dataclass(frozen=True, slots=True)
class SwimAudioSmokeMetadata:
    screenshot: str
    display_status: str
    audio_backend: str
    stroke_events: int
    played_swim_sounds: int
    water_entries: int
    water_exits: int
    played_splash_sounds: int
    swim_distance: float
    in_water_after_swim: bool
    invariants_passed: bool = False


def build_swim_audio_smoke_metadata(
    *,
    screenshot: Path,
    audio_backend: str,
    stroke_events: int,
    played_swim_sounds: int,
    water_entries: int,
    water_exits: int,
    played_splash_sounds: int,
    swim_distance: float,
    in_water_after_swim: bool,
) -> SwimAudioSmokeMetadata:
    return SwimAudioSmokeMetadata(
        screenshot=str(screenshot),
        display_status="available",
        audio_backend=audio_backend,
        stroke_events=stroke_events,
        played_swim_sounds=played_swim_sounds,
        water_entries=water_entries,
        water_exits=water_exits,
        played_splash_sounds=played_splash_sounds,
        swim_distance=round(swim_distance, 4),
        in_water_after_swim=in_water_after_swim,
    )


def validate_swim_audio_smoke_metadata(
    metadata: SwimAudioSmokeMetadata,
) -> SwimAudioSmokeMetadata:
    if metadata.display_status != "available" or not metadata.screenshot:
        raise ValueError("Swim audio smoke requires a visible screenshot")
    if metadata.audio_backend != "PygletAudioBackend":
        raise ValueError("Swim audio smoke did not use the real Pyglet audio backend")
    if metadata.stroke_events != 2 or metadata.played_swim_sounds != 2:
        raise ValueError("Swim stroke cadence or audio routing count mismatch")
    if metadata.water_entries != 1 or metadata.water_exits != 1:
        raise ValueError("Water transition count mismatch")
    if metadata.played_splash_sounds != 2:
        raise ValueError("Water transition splash count mismatch")
    if metadata.swim_distance <= 1.0 or not metadata.in_water_after_swim:
        raise ValueError("Visible swim input did not move through water")
    return replace(metadata, invariants_passed=True)


def write_swim_audio_smoke_metadata(
    path: Path,
    metadata: SwimAudioSmokeMetadata,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_swim_audio_smoke(
    settings: AppSettings,
    *,
    output_dir: Path | None = None,
) -> int:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        print("swim-audio-smoke: skipped (no active display)")
        return 0

    from pyglet.window import key

    from voxel_sandbox.app.composition import UserSettingsStore, build_app_runtime
    from voxel_sandbox.engine.events import PlayerSwimStroke, PlayerWaterTransition
    from voxel_sandbox.engine.game_state import GameState
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow
    from voxel_sandbox.tools.water_surface_smoke import (
        _scene_chunk_coordinates,
        apply_water_smoke_scene,
        choose_water_scene_base_y,
    )

    root = output_dir or Path("saves/swim_audio_smoke")
    root.mkdir(parents=True, exist_ok=True)
    run_settings = replace(
        settings,
        audio=replace(
            settings.audio,
            master=1.0,
            effects=1.0,
            music=0.0,
            ambience=0.0,
        ),
        graphics=replace(settings.graphics, day_cycle_seconds=0.0),
        world=replace(
            settings.world,
            seed="veilstone-swim-audio-smoke",
            render_distance=2,
            generation_backend="thread",
            meshing_backend="thread",
        ),
    )
    runtime = build_app_runtime(
        run_settings,
        data_root=root,
        settings_store=UserSettingsStore(root / "settings.toml"),
    )
    with tempfile.TemporaryDirectory(prefix="veilstone-swim-audio-world-", dir=root) as directory:
        window = GameWindow(
            run_settings,
            visible=True,
            save_root=Path(directory),
            app_runtime=runtime,
        )
        stroke_events: list[PlayerSwimStroke] = []
        water_transitions: list[PlayerWaterTransition] = []
        played_keys: list[str] = []
        window.events.subscribe(PlayerSwimStroke, stroke_events.append)
        window.events.subscribe(PlayerWaterTransition, water_transitions.append)
        backend = window.audio.backend
        original_play = backend.play

        def track_play(resource: Any, volume: float, position: Any) -> None:
            played_keys.append(str(resource.key))
            original_play(resource, volume, position)

        backend.play = track_play
        try:
            renderer = window.world_renderer
            renderer.ensure_collision_area_loaded(8.5, 9.5, 0.0)
            generation = cast(TerrainGenerator, window.world_runtime.generation)
            registry = cast(BlockRegistry, window.world_runtime.block_registry)
            base_y = choose_water_scene_base_y(generation.height_at)
            scene = apply_water_smoke_scene(
                renderer.set_block,
                registry,
                base_y=base_y,
            )
            rebuilt = renderer.rebuild_loaded_chunk_meshes_sync(_scene_chunk_coordinates(scene))
            if rebuilt <= 0 or renderer.water_mesh_triangles <= 0:
                raise RuntimeError("Swim audio smoke did not build visible pool geometry")

            player = cast(PlayerController, window.player)
            player.x, player.y, player.z = 8.5, base_y + 1.05, 10.5
            window.camera.yaw_degrees = 0.0
            window.camera.pitch_degrees = -12.0
            window.menu.screen = Screen.GAME
            window.debug_overlay_visible = True
            window.game_state.try_transition(GameState.PLAYING)
            window._sync_mouse_capture()
            window.switch_to()
            window.on_activate()

            def frame() -> None:
                window.dispatch_events()
                window.fixed_update(1.0 / 60.0)
                window.on_draw()
                window.flip()

            for _ in range(5):
                frame()
            start = (float(player.x), float(player.z))
            window.on_key_press(key.W, 0)
            for _ in range(75):
                frame()
            window.on_key_release(key.W, 0)
            frame()
            end = (float(player.x), float(player.z))
            in_water_after_swim = bool(player.in_water)

            window.camera.yaw_degrees = 180.0
            window.camera.pitch_degrees = -30.0
            for _ in range(3):
                frame()
            screenshot = _save_f2_screenshot(window, root)

            player.x, player.y, player.z = 3.5, base_y + 2.05, 10.5
            for _ in range(3):
                frame()

            entries = sum(event.entered for event in water_transitions)
            exits = sum(not event.entered for event in water_transitions)
            metadata = validate_swim_audio_smoke_metadata(
                build_swim_audio_smoke_metadata(
                    screenshot=screenshot,
                    audio_backend=type(backend).__name__,
                    stroke_events=len(stroke_events),
                    played_swim_sounds=played_keys.count("player.swim"),
                    water_entries=entries,
                    water_exits=exits,
                    played_splash_sounds=played_keys.count("player.splash"),
                    swim_distance=math.dist(start, end),
                    in_water_after_swim=in_water_after_swim,
                )
            )
            metadata_path = root / "swim_audio_smoke.json"
            write_swim_audio_smoke_metadata(metadata_path, metadata)
            print(f"metadata={metadata_path}")
            print(f"audio_backend={metadata.audio_backend}")
            print(f"stroke_events={metadata.stroke_events}")
            print(f"played_swim_sounds={metadata.played_swim_sounds}")
            print(f"water_entries={metadata.water_entries}")
            print(f"water_exits={metadata.water_exits}")
            print(f"played_splash_sounds={metadata.played_splash_sounds}")
            print(f"swim_distance={metadata.swim_distance:.4f}")
            print(f"screenshot={metadata.screenshot}")
        finally:
            window.close()
    return 0


def _save_f2_screenshot(window: Any, root: Path) -> Path:
    from pyglet.window import key

    screenshots = root / "screenshots"
    before = set(screenshots.glob("*.png"))
    window.on_key_press(key.F2, 0)
    created = sorted(set(screenshots.glob("*.png")) - before)
    if len(created) != 1:
        raise RuntimeError(f"Swim audio F2 screenshot count mismatch: {len(created)}")
    return created[0]
