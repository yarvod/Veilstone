# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import math
import sys
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from voxel_sandbox.app.settings import AppSettings


@dataclass(frozen=True, slots=True)
class FirstClickSmokeMetadata:
    initial_motion: bool
    platform: str
    cocoa_accepts_first_mouse: bool | None
    settings_actions: int
    settings_back_actions: int
    singleplayer_actions: int
    world_list_cancel_actions: int
    resume_actions: int
    resume_captured: bool
    first_motion_yaw_delta: float
    walk_distance: float
    menu_screenshot: str
    game_screenshot: str
    display_status: str = "available"
    invariants_passed: bool = False


def build_first_click_smoke_metadata(
    *,
    initial_motion: bool,
    platform: str,
    cocoa_accepts_first_mouse: bool | None,
    action_counts: dict[str, int],
    resume_captured: bool,
    first_motion_yaw_delta: float,
    walk_distance: float,
    menu_screenshot: Path,
    game_screenshot: Path,
) -> FirstClickSmokeMetadata:
    return FirstClickSmokeMetadata(
        initial_motion=initial_motion,
        platform=platform,
        cocoa_accepts_first_mouse=cocoa_accepts_first_mouse,
        settings_actions=action_counts.get("settings", 0),
        settings_back_actions=action_counts.get("settings_back", 0),
        singleplayer_actions=action_counts.get("singleplayer", 0),
        world_list_cancel_actions=action_counts.get("world_list_cancel", 0),
        resume_actions=action_counts.get("resume", 0),
        resume_captured=resume_captured,
        first_motion_yaw_delta=round(first_motion_yaw_delta, 4),
        walk_distance=round(walk_distance, 4),
        menu_screenshot=str(menu_screenshot),
        game_screenshot=str(game_screenshot),
    )


def validate_first_click_smoke_metadata(
    metadata: FirstClickSmokeMetadata,
) -> FirstClickSmokeMetadata:
    if metadata.display_status != "available":
        raise ValueError("First-click smoke requires an active display")
    if metadata.platform == "darwin" and metadata.cocoa_accepts_first_mouse is not True:
        raise ValueError("Cocoa view does not accept the first activating mouse click")
    action_counts = (
        metadata.settings_actions,
        metadata.settings_back_actions,
        metadata.singleplayer_actions,
        metadata.world_list_cancel_actions,
        metadata.resume_actions,
    )
    if action_counts != (1, 1, 1, 1, 1):
        raise ValueError(f"Single-click action count mismatch: {action_counts}")
    if not metadata.resume_captured:
        raise ValueError("Resume did not restore exclusive mouse capture")
    if abs(metadata.first_motion_yaw_delta) <= 0.01:
        raise ValueError("First mouse motion after Resume did not rotate the camera")
    if metadata.walk_distance <= 0.05:
        raise ValueError("Visible gameplay pass did not move the player")
    if not metadata.menu_screenshot or not metadata.game_screenshot:
        raise ValueError("First-click smoke requires menu and gameplay screenshots")
    return replace(metadata, invariants_passed=True)


def write_first_click_smoke_metadata(
    path: Path,
    metadata: FirstClickSmokeMetadata,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_first_click_smoke(
    settings: AppSettings,
    *,
    initial_motion: bool = False,
    output_dir: Path | None = None,
) -> int:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        print("first-click-smoke: skipped (no active display)")
        return 0

    from pyglet.window import key

    from voxel_sandbox.app.composition import UserSettingsStore, build_app_runtime
    from voxel_sandbox.engine.game_state import GameState
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    root = output_dir or Path("saves/first_click_smoke")
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
    action_counts: dict[str, int] = {}
    with tempfile.TemporaryDirectory(prefix="veilstone-first-click-world-", dir=root) as directory:
        window = GameWindow(
            run_settings,
            visible=True,
            save_root=Path(directory),
            app_runtime=runtime,
        )
        try:
            window.switch_to()
            window.on_activate()

            def frame(*, update: bool = False) -> None:
                window.dispatch_events()
                if update:
                    window.fixed_update(1.0 / 60.0)
                window.on_draw()
                window.flip()

            for _ in range(8):
                frame()

            cocoa_acceptance = _cocoa_accepts_first_mouse(window)
            _click_widget(
                window,
                window.ui_renderer.buttons[2],
                action="settings",
                action_counts=action_counts,
                move_pointer=initial_motion,
            )
            _require_screen(window, Screen.SETTINGS, "First Settings click did not open Settings")
            for _ in range(3):
                frame()
            menu_screenshot = _save_named_screenshot(window, "menu")

            _click_widget(
                window,
                _menu_button(window, "Back"),
                action="settings_back",
                action_counts=action_counts,
            )
            _require_screen(
                window,
                Screen.MAIN,
                "Settings Back click did not return to the main menu",
            )
            frame()
            _click_widget(
                window,
                _menu_button(window, "Singleplayer"),
                action="singleplayer",
                action_counts=action_counts,
            )
            _require_screen(
                window,
                Screen.SINGLEPLAYER,
                "Singleplayer click did not open the world list",
            )
            frame()
            _click_widget(
                window,
                window.ui_renderer._action_cancel,
                action="world_list_cancel",
                action_counts=action_counts,
            )
            _require_screen(
                window,
                Screen.MAIN,
                "World-list Cancel click did not return to the main menu",
            )

            window.menu.screen = Screen.GAME
            window.game_state.try_transition(GameState.PLAYING)
            window._sync_mouse_capture()
            for _ in range(10):
                frame()
            window.on_key_press(key.ESCAPE, 0)
            _require_screen(window, Screen.PAUSE, "Escape did not open the pause menu")
            frame()
            _click_widget(
                window,
                _menu_button(window, "Resume"),
                action="resume",
                action_counts=action_counts,
            )
            _require_screen(window, Screen.GAME, "Resume click did not return to gameplay")
            resume_captured = bool(window.mouse_captured)
            yaw_before = float(window.camera.yaw_degrees)
            window.on_mouse_motion(0, 0, 24, -6)
            yaw_delta = float(window.camera.yaw_degrees) - yaw_before

            walk_start = _horizontal_position(window)
            window.on_key_press(key.W, 0)
            for _ in range(45):
                frame(update=True)
            window.on_key_release(key.W, 0)
            walk_end = _horizontal_position(window)
            for _ in range(5):
                frame()
            game_screenshot = _save_f2_screenshot(window, root)

            metadata = validate_first_click_smoke_metadata(
                build_first_click_smoke_metadata(
                    initial_motion=initial_motion,
                    platform=sys.platform,
                    cocoa_accepts_first_mouse=cocoa_acceptance,
                    action_counts=action_counts,
                    resume_captured=resume_captured,
                    first_motion_yaw_delta=yaw_delta,
                    walk_distance=math.dist(walk_start, walk_end),
                    menu_screenshot=menu_screenshot,
                    game_screenshot=game_screenshot,
                )
            )
            metadata_path = root / "first_click_smoke.json"
            write_first_click_smoke_metadata(metadata_path, metadata)
            print(f"metadata={metadata_path}")
            print(f"initial_motion={str(metadata.initial_motion).lower()}")
            print(f"cocoa_accepts_first_mouse={metadata.cocoa_accepts_first_mouse}")
            print(
                "action_counts="
                f"{metadata.settings_actions},{metadata.settings_back_actions},"
                f"{metadata.singleplayer_actions},{metadata.world_list_cancel_actions},"
                f"{metadata.resume_actions}"
            )
            print(f"resume_captured={str(metadata.resume_captured).lower()}")
            print(f"first_motion_yaw_delta={metadata.first_motion_yaw_delta:.4f}")
            print(f"walk_distance={metadata.walk_distance:.4f}")
            print(f"menu_screenshot={metadata.menu_screenshot}")
            print(f"game_screenshot={metadata.game_screenshot}")
        finally:
            window.close()
    return 0


def _click_widget(
    window: Any,
    widget: Any,
    *,
    action: str,
    action_counts: dict[str, int],
    move_pointer: bool = True,
) -> None:
    from pyglet.window import mouse

    callback = widget.on_click_callback
    if callback is None:
        raise RuntimeError(f"{action} widget has no click callback")

    def counted_callback() -> None:
        action_counts[action] = action_counts.get(action, 0) + 1
        callback()

    widget.on_click_callback = counted_callback
    x = int(widget.bounds.x + widget.bounds.width / 2)
    y = int(widget.bounds.y + widget.bounds.height / 2)
    if move_pointer:
        window.on_mouse_motion(x, y, 0, 0)
    window.on_mouse_press(x, y, mouse.LEFT, 0)
    window.on_mouse_release(x, y, mouse.LEFT, 0)


def _menu_button(window: Any, label: str) -> Any:
    for button in window.ui_renderer.buttons:
        if button.text == label or button.text.startswith(f"{label}:"):
            return button
    raise RuntimeError(f"Menu button not found: {label}")


def _require_screen(window: Any, expected: Any, message: str) -> None:
    if window.menu.screen is not expected:
        raise RuntimeError(message)


def _cocoa_accepts_first_mouse(window: Any) -> bool | None:
    if sys.platform != "darwin":
        return None
    view = window._nswindow.contentView()
    return bool(view.acceptsFirstMouse_(None))


def _save_named_screenshot(window: Any, prefix: str) -> Path:
    screenshot = Path(window.save_screenshot())
    named = screenshot.with_name(f"{prefix}_{screenshot.name}")
    screenshot.replace(named)
    return named


def _save_f2_screenshot(window: Any, root: Path) -> Path:
    from pyglet.window import key

    screenshots = root / "screenshots"
    before = set(screenshots.glob("*.png"))
    window.on_key_press(key.F2, 0)
    created = sorted(set(screenshots.glob("*.png")) - before)
    if len(created) != 1:
        raise RuntimeError(f"First-click F2 screenshot count mismatch: {len(created)}")
    return created[0]


def _horizontal_position(window: Any) -> tuple[float, float]:
    return float(window.player.x), float(window.player.z)
