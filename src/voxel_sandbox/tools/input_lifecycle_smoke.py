from __future__ import annotations

import json
import math
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from voxel_sandbox.app.settings import AppSettings


@dataclass(frozen=True, slots=True)
class InputLifecycleMetadata:
    screenshot: str
    display_status: str
    walk_distance: float
    post_release_drift: float
    pause_keys_cleared: bool
    post_resume_drift: float
    resume_clicks: int
    resume_captured: bool
    first_motion_yaw_delta: float
    inventory_keys_cleared: bool
    focus_keys_cleared: bool
    focus_recaptured: bool
    invariants_passed: bool = False


def build_input_lifecycle_metadata(
    *,
    screenshot: Path,
    walk_distance: float,
    post_release_drift: float,
    pause_keys_cleared: bool,
    post_resume_drift: float,
    resume_clicks: int,
    resume_captured: bool,
    first_motion_yaw_delta: float,
    inventory_keys_cleared: bool,
    focus_keys_cleared: bool,
    focus_recaptured: bool,
) -> InputLifecycleMetadata:
    return InputLifecycleMetadata(
        screenshot=str(screenshot),
        display_status="available",
        walk_distance=round(walk_distance, 4),
        post_release_drift=round(post_release_drift, 4),
        pause_keys_cleared=pause_keys_cleared,
        post_resume_drift=round(post_resume_drift, 4),
        resume_clicks=resume_clicks,
        resume_captured=resume_captured,
        first_motion_yaw_delta=round(first_motion_yaw_delta, 4),
        inventory_keys_cleared=inventory_keys_cleared,
        focus_keys_cleared=focus_keys_cleared,
        focus_recaptured=focus_recaptured,
    )


def validate_input_lifecycle_metadata(
    metadata: InputLifecycleMetadata,
) -> InputLifecycleMetadata:
    if metadata.display_status != "available" or not metadata.screenshot:
        raise ValueError("Input lifecycle smoke requires an available display and screenshot")
    if metadata.walk_distance <= 0.05:
        raise ValueError("Input lifecycle smoke did not move the player")
    if metadata.post_release_drift >= 0.02:
        raise ValueError("Movement remained active after ordinary key release")
    if not metadata.pause_keys_cleared:
        raise ValueError("Pause did not clear held movement and sprint keys")
    if metadata.post_resume_drift >= 0.02:
        raise ValueError("Movement resumed from stale input after Resume")
    if metadata.resume_clicks < 2 or not metadata.resume_captured:
        raise ValueError("Repeated single-click Resume did not restore mouse capture")
    if abs(metadata.first_motion_yaw_delta) <= 0.01:
        raise ValueError("First mouse motion after Resume did not rotate the camera")
    if not metadata.inventory_keys_cleared:
        raise ValueError("Inventory transition did not clear movement keys")
    if not metadata.focus_keys_cleared or not metadata.focus_recaptured:
        raise ValueError("Focus transition did not reset input and recapture the mouse")
    return replace(metadata, invariants_passed=True)


def write_input_lifecycle_metadata(path: Path, metadata: InputLifecycleMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_input_lifecycle_smoke(
    settings: AppSettings,
    *,
    output_dir: Path | None = None,
) -> int:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        print("input-lifecycle-smoke: skipped (no active display)")
        return 0

    from pyglet.window import key

    from voxel_sandbox.app.composition import UserSettingsStore, build_app_runtime
    from voxel_sandbox.engine.game_state import GameState
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    root = output_dir or Path("saves/input_lifecycle_smoke")
    root.mkdir(parents=True, exist_ok=True)
    run_settings = replace(
        settings,
        world=replace(
            settings.world,
            generation_backend="thread",
            meshing_backend="thread",
        ),
    )
    runtime = build_app_runtime(
        run_settings,
        data_root=root,
        settings_store=UserSettingsStore(root / "settings.toml"),
    )
    with tempfile.TemporaryDirectory(
        prefix="veilstone-input-lifecycle-world-",
        dir=root,
    ) as world_directory:
        window = GameWindow(
            run_settings,
            visible=True,
            save_root=Path(world_directory),
            app_runtime=runtime,
        )
        try:
            window.switch_to()
            window.menu.screen = Screen.GAME
            window.game_state.try_transition(GameState.PLAYING)
            window.on_activate()

            def frame(*, update: bool = True) -> None:
                window.dispatch_events()
                if update:
                    window.fixed_update(1.0 / 60.0)
                window.on_draw()
                window.flip()

            for _ in range(12):
                frame(update=False)

            walk_start = _horizontal_position(window)
            window.on_key_press(key.W, 0)
            for _ in range(45):
                frame()
            window.on_key_release(key.W, 0)
            walk_released = _horizontal_position(window)
            for _ in range(15):
                frame()
            walk_stopped = _horizontal_position(window)

            window.on_key_press(key.W, 0)
            window.on_key_press(key.LSHIFT, 0)
            window.on_key_press(key.ESCAPE, 0)
            pause_keys_cleared = not window.key_state.is_pressed(
                key.W
            ) and not window.key_state.is_pressed(key.LSHIFT)
            resume_clicks = 0
            for _ in range(2):
                for _ in range(3):
                    frame(update=False)
                _click_resume(window)
                resume_clicks += 1
                if window.menu.screen is not Screen.GAME:
                    raise RuntimeError("Resume click did not return to gameplay")
                if resume_clicks == 1:
                    window.on_key_press(key.ESCAPE, 0)
            resume_start = _horizontal_position(window)
            for _ in range(15):
                frame()
            resume_stopped = _horizontal_position(window)
            resume_captured = bool(window.mouse_captured)
            yaw_before = float(window.camera.yaw_degrees)
            window.on_mouse_motion(0, 0, 24, -6)
            yaw_delta = float(window.camera.yaw_degrees) - yaw_before

            window.on_key_press(key.W, 0)
            window.on_key_press(key.LSHIFT, 0)
            window.on_key_press(key.E, 0)
            inventory_keys_cleared = not window.key_state.is_pressed(
                key.W
            ) and not window.key_state.is_pressed(key.LSHIFT)
            window.on_key_press(key.E, 0)

            window.on_key_press(key.W, 0)
            window.on_key_press(key.LSHIFT, 0)
            window.on_deactivate()
            focus_keys_cleared = not window.key_state.is_pressed(
                key.W
            ) and not window.key_state.is_pressed(key.LSHIFT)
            window.on_activate()
            focus_recaptured = bool(window.mouse_captured)

            window.on_key_press(key.F3, 0)
            for _ in range(5):
                frame(update=False)
            before = set((root / "screenshots").glob("*.png"))
            window.on_key_press(key.F2, 0)
            created = sorted(set((root / "screenshots").glob("*.png")) - before)
            if len(created) != 1:
                raise RuntimeError(f"Input lifecycle F2 screenshot count mismatch: {len(created)}")
            metadata = validate_input_lifecycle_metadata(
                build_input_lifecycle_metadata(
                    screenshot=created[0],
                    walk_distance=math.dist(walk_start, walk_released),
                    post_release_drift=math.dist(walk_released, walk_stopped),
                    pause_keys_cleared=pause_keys_cleared,
                    post_resume_drift=math.dist(resume_start, resume_stopped),
                    resume_clicks=resume_clicks,
                    resume_captured=resume_captured,
                    first_motion_yaw_delta=yaw_delta,
                    inventory_keys_cleared=inventory_keys_cleared,
                    focus_keys_cleared=focus_keys_cleared,
                    focus_recaptured=focus_recaptured,
                )
            )
            metadata_path = root / "input_lifecycle_smoke.json"
            write_input_lifecycle_metadata(metadata_path, metadata)
            print(f"metadata={metadata_path}")
            print(f"screenshot={metadata.screenshot}")
            print(f"walk_distance={metadata.walk_distance:.4f}")
            print(f"post_release_drift={metadata.post_release_drift:.4f}")
            print(f"pause_keys_cleared={str(metadata.pause_keys_cleared).lower()}")
            print(f"post_resume_drift={metadata.post_resume_drift:.4f}")
            print(f"resume_clicks={metadata.resume_clicks}")
            print(f"resume_captured={str(metadata.resume_captured).lower()}")
            print(f"first_motion_yaw_delta={metadata.first_motion_yaw_delta:.4f}")
            print(f"inventory_keys_cleared={str(metadata.inventory_keys_cleared).lower()}")
            print(f"focus_keys_cleared={str(metadata.focus_keys_cleared).lower()}")
            print(f"focus_recaptured={str(metadata.focus_recaptured).lower()}")
        finally:
            window.close()
    return 0


def _click_resume(window: Any) -> None:
    from pyglet.window import mouse

    resume = window.ui_renderer.buttons[0]
    x = resume.bounds.x + resume.bounds.width // 2
    y = resume.bounds.y + resume.bounds.height // 2
    window.on_mouse_motion(x, y, 0, 0)
    window.on_mouse_press(x, y, mouse.LEFT, 0)
    window.on_mouse_release(x, y, mouse.LEFT, 0)


def _horizontal_position(window: Any) -> tuple[float, float]:
    return float(window.player.x), float(window.player.z)
