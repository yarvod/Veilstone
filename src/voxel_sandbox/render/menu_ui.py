# pyright: reportPrivateUsage=false, reportUnknownArgumentType=false

from __future__ import annotations

import sys
import time
from dataclasses import replace
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, cast

import moderngl
import pyglet

from voxel_sandbox.app.paths import resource_packs_root
from voxel_sandbox.app.settings import save_user_settings
from voxel_sandbox.app.update_installer import (
    UpdateInstallError,
    launch_update_installer,
    prepare_update_install,
)
from voxel_sandbox.app.updates import (
    GitHubRelease,
    download_release_asset,
    fetch_releases,
    select_platform_asset,
)
from voxel_sandbox.application.material_quality import ApplyMaterialQualityUseCase
from voxel_sandbox.application.resource_packs import (
    ApplyResourcePackUseCase,
    TexturePackServicePort,
)
from voxel_sandbox.audio import AudioEvent, AudioEventKind
from voxel_sandbox.audio.runtime import volume_map
from voxel_sandbox.infrastructure.storage import WorldStorage
from voxel_sandbox.network import discover_worlds
from voxel_sandbox.render.texture_packs.models import ImportReport
from voxel_sandbox.render.ui.menu import MenuCommand, Screen, platform_font_name
from voxel_sandbox.render.ui.text_input import TextInput, TextPurpose
from voxel_sandbox.render.world_manager import WorldManager
from voxel_sandbox.version import __version__

if TYPE_CHECKING:
    from voxel_sandbox.render.window import GameWindow

UpdateEvent = tuple[str, object]


class _UpdateCancelled(Exception):
    pass


class MenuUI:
    _FONT = platform_font_name(sys.platform)

    def __init__(self, win: GameWindow) -> None:
        self.win = win
        self.text_input_overlay = pyglet.shapes.Rectangle(0, 0, 0, 0, color=(0, 0, 0))
        self.text_input_overlay.opacity = 128
        self.text_input_panel = pyglet.shapes.BorderedRectangle(
            0, 0, 0, 0, 4, color=(24, 28, 38), border_color=(120, 130, 150)
        )
        self.text_input_title_label = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="top",
            font_name=self._FONT,
            font_size=15,
            color=(235, 235, 245, 255),
        )
        self.text_input_label = pyglet.text.Label(
            "",
            anchor_x="center",
            anchor_y="center",
            align="center",
            multiline=True,
            width=600,
            font_name=self._FONT,
            font_size=17,
            color=(245, 220, 140, 255),
        )
        self.command_input_label = pyglet.text.Label(
            "",
            anchor_x="left",
            anchor_y="bottom",
            align="left",
            multiline=True,
            width=760,
            font_name=self._FONT,
            font_size=17,
            color=(245, 220, 140, 255),
        )
        self.world_list_index = 0
        self.world_list_items: list[tuple[str, Path]] = list(WorldManager._saved_worlds())
        self._world_list_cache_time = time.perf_counter()
        self.texture_pack_items: list[tuple[str, Path | None]] = self._discover_texture_packs()
        self._texture_pack_cache_time = time.perf_counter()
        self.texture_pack_index = 0
        self._tp_screen_active = False  # True while TEXTURE_PACKS screen is open
        self.update_release_items: list[GitHubRelease] = []
        self.update_release_index = 0
        self._updates_loaded = False
        self.downloaded_update_path: Path | None = None
        self._update_events: Queue[UpdateEvent] = Queue()
        self._update_worker: Thread | None = None
        self._update_cancel_event = Event()

    # ── OpenGL state ──────────────────────────────────────────────────────────

    def _prepare_ui_draw(self) -> None:
        win = self.win
        win.mgl_context.disable(moderngl.DEPTH_TEST)
        win.mgl_context.enable(moderngl.BLEND)
        win.mgl_context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    # ── Menu rendering ────────────────────────────────────────────────────────

    def _draw_menu(self) -> None:
        win = self.win

        def on_item_click(index: int) -> None:
            win.menu.select(index)
            self._handle_menu_command(win.menu.activate())

        win.ui_renderer.update(
            win.menu,
            self._menu_item_label,
            on_item_click,
            self._play_ui_sound,
        )

        if win.menu.screen is Screen.SINGLEPLAYER:
            self._draw_world_list(win.width // 2)
        elif win.menu.screen is Screen.TEXTURE_PACKS:
            self._draw_texture_pack_list()
        elif win.menu.screen is Screen.UPDATES:
            self._draw_update_list()

        win.ui_renderer.draw()
        if win.text_input is not None:
            self._draw_text_input_modal()
        elif win.text_input is None:
            self.text_input_overlay.opacity = 0
            self.text_input_panel.opacity = 0

    def _draw_text_input_modal(self) -> None:
        win = self.win
        assert win.text_input is not None
        overlay_margin = 40
        panel_width = min(680, win.width - overlay_margin * 2)
        panel_height = min(220, win.height // 2)
        panel_x = (win.width - panel_width) // 2
        panel_y = (win.height - panel_height) // 2

        self.text_input_overlay.x = 0
        self.text_input_overlay.y = 0
        self.text_input_overlay.width = win.width
        self.text_input_overlay.height = win.height
        self.text_input_overlay.color = (0, 0, 0)
        self.text_input_overlay.opacity = 150
        self.text_input_overlay.draw()

        self.text_input_panel.x = panel_x
        self.text_input_panel.y = panel_y
        self.text_input_panel.width = panel_width
        self.text_input_panel.height = panel_height
        self.text_input_panel.draw()

        title = win.text_input.purpose.name.replace("_", " ").title()
        self.text_input_title_label.text = title
        self.text_input_title_label.x = win.width // 2
        self.text_input_title_label.y = panel_y + panel_height - 16
        self.text_input_title_label.draw()

        self._draw_text_input()

    def _draw_text_input(self) -> None:
        win = self.win
        assert win.text_input is not None
        if win.menu.in_game and win.text_input.purpose in {TextPurpose.CHAT, TextPurpose.COMMAND}:
            self.command_input_label.text = win.text_input.display
            self.command_input_label.width = min(760, win.width - 40)
            self.command_input_label.x = 20
            self.command_input_label.y = 76
            self.command_input_label.draw()
        else:
            self.text_input_label.text = win.text_input.display
            self.text_input_label.anchor_x = "center"
            self.text_input_label.anchor_y = "center"
            self.text_input_label.width = 600
            self.text_input_label.x = win.width // 2
            self.text_input_label.y = win.height // 3
            self.text_input_label.draw()

    def _menu_item_label(self, index: int) -> str:
        win = self.win
        item = win.menu.items[index]
        smooth_lighting = getattr(
            win.world_renderer,
            "smooth_lighting",
            win.settings.graphics.smooth_lighting,
        )
        ambient_occlusion = getattr(
            win.world_renderer,
            "ambient_occlusion",
            win.settings.graphics.ambient_occlusion,
        )
        fog_enabled = getattr(
            win.world_renderer,
            "fog_enabled",
            win.settings.graphics.fog,
        )
        greedy_meshing = getattr(
            win.world_renderer,
            "greedy_meshing",
            win.settings.graphics.greedy_meshing,
        )
        values = {
            "cycle_shadows": win.settings.graphics.shadow_quality,
            "cycle_materials": win.settings.graphics.material_quality,
            "toggle_clouds": "on" if win.settings.graphics.clouds else "off",
            "toggle_vsync": "on" if win.settings.window.vsync else "off",
            "cycle_render_distance": f"{win.settings.world.render_distance} chunks",
            "cycle_difficulty": win.settings.gameplay.difficulty,
            "rebind_forward": win.settings.controls.forward,
            "rebind_backward": win.settings.controls.backward,
            "rebind_left": win.settings.controls.left,
            "rebind_right": win.settings.controls.right,
            "rebind_jump": win.settings.controls.jump,
            "cycle_master_volume": f"{win.settings.audio.master:.0%}",
            "cycle_effects_volume": f"{win.settings.audio.effects:.0%}",
            "cycle_music_volume": f"{win.settings.audio.music:.0%}",
            "cycle_ambience_volume": f"{win.settings.audio.ambience:.0%}",
            "toggle_smooth_lighting": "on" if smooth_lighting else "off",
            "toggle_ambient_occlusion": "on" if ambient_occlusion else "off",
            "toggle_fog": "on" if fog_enabled else "off",
            "toggle_mesher": "greedy" if greedy_meshing else "visible",
        }
        value = values.get(item.action or "")
        return item.label if value is None else f"{item.label}: {value}"

    # ── World list ────────────────────────────────────────────────────────────

    def _refresh_world_list(self) -> None:
        now = time.perf_counter()
        if now - self._world_list_cache_time > 2.0:
            self.world_list_items = list(WorldManager._saved_worlds())
            self._world_list_cache_time = now

    def _draw_world_list(self, center_x: int) -> None:
        win = self.win
        self._refresh_world_list()
        count = len(self.world_list_items)
        if count > 0:
            self.world_list_index = min(self.world_list_index, max(0, count - 1))
        else:
            self.world_list_index = -1

        def on_select(idx: int) -> None:
            self.world_list_index = idx

        def on_play() -> None:
            if self.world_list_items and 0 <= self.world_list_index < count:
                name, _ = self.world_list_items[self.world_list_index]
                win._worlds.load_world(name)

        def on_create() -> None:
            self._handle_menu_command(MenuCommand.CREATE_WORLD)

        def on_edit() -> None:
            if self.world_list_items and 0 <= self.world_list_index < count:
                name, _ = self.world_list_items[self.world_list_index]
                self._begin_text_input(
                    TextPurpose.RENAME_WORLD,
                    "Rename world",
                    initial=name,
                    maximum_length=48,
                )

        def on_delete() -> None:
            if self.world_list_items and 0 <= self.world_list_index < count:
                self._begin_text_input(
                    TextPurpose.DELETE_WORLD,
                    "Type DELETE to confirm deleting:",
                    maximum_length=6,
                )

        def on_cancel() -> None:
            win.menu.back()

        if count == 0:
            win.ui_renderer.update_world_list(
                [], -1, on_select, on_play, on_create, on_edit, on_delete, on_cancel
            )
            return

        start_index = max(0, self.world_list_index - 3)
        end_index = start_index + 8
        if end_index > count:
            end_index = count
            start_index = max(0, end_index - 8)

        visible_items = self.world_list_items[start_index:end_index]

        def mapped_on_select(visible_idx: int) -> None:
            on_select(start_index + visible_idx)

        win.ui_renderer.update_world_list(
            visible_items,
            self.world_list_index - start_index,
            mapped_on_select,
            on_play,
            on_create,
            on_edit,
            on_delete,
            on_cancel,
        )

    # ── Texture pack list ───────────────────────────────────────────────────

    def _resource_packs_dir(self) -> Path:
        return resource_packs_root()

    def _legacy_resource_packs_dir(self) -> Path:
        return Path("resource_packs")

    def _discover_texture_packs(self) -> list[tuple[str, Path | None]]:
        packs: list[tuple[str, Path | None]] = [("Default", None)]
        seen: set[Path | None] = {None}
        texture_packs = cast(TexturePackServicePort, self.win.app_runtime.texture_packs)

        def add_discovered(root: Path) -> None:
            for label, path in texture_packs.discover(root):
                if path is not None and path.name.casefold() == "default":
                    continue
                key = None if path is None else path.resolve()
                if key in seen:
                    continue
                packs.append((label, path))
                seen.add(key)

        resource_root = self._resource_packs_dir()
        add_discovered(resource_root)
        legacy_root = self._legacy_resource_packs_dir()
        if legacy_root == resource_root or not legacy_root.exists():
            return packs
        add_discovered(legacy_root)
        return packs

    def _refresh_texture_pack_list(self) -> None:
        now = time.perf_counter()
        if now - self._texture_pack_cache_time > 2.0:
            self.texture_pack_items = self._discover_texture_packs()
            self._texture_pack_cache_time = now
            # Clamp index in case pack count changed.
            count = len(self.texture_pack_items)
            self.texture_pack_index = max(0, min(self.texture_pack_index, count - 1))

    def _draw_texture_pack_list(self) -> None:
        win = self.win
        self._refresh_texture_pack_list()
        count = len(self.texture_pack_items)
        if count == 0:
            return
        self.texture_pack_index = max(0, min(self.texture_pack_index, count - 1))

        # Sync selection to active pack only on first entry into this screen.
        if not self._tp_screen_active:
            self._tp_screen_active = True
            active_path = win.settings.graphics.resource_pack_path
            for i, (_, path) in enumerate(self.texture_pack_items):
                if (str(path) if path else "") == active_path:
                    self.texture_pack_index = i
                    break

        active_path = win.settings.graphics.resource_pack_path

        def on_select(idx: int) -> None:
            self.texture_pack_index = idx

        def on_apply() -> None:
            self._apply_selected_texture_pack()

        def on_import() -> None:
            self._import_texture_pack()

        def on_cancel() -> None:
            self._tp_screen_active = False
            win.menu.back()
            win._sync_game_state()

        start_index = max(0, self.texture_pack_index - 3)
        end_index = min(count, start_index + 8)
        start_index = max(0, end_index - 8)

        # Build display items: mark the active pack with ✓
        visible_raw = self.texture_pack_items[start_index:end_index]
        visible_items: list[tuple[str, Path | None]] = []
        for name, path in visible_raw:
            pack_path_str = "" if path is None else str(path)
            marker = " [active]" if pack_path_str == active_path else ""
            visible_items.append((name + marker, path))

        def mapped_on_select(visible_idx: int) -> None:
            on_select(start_index + visible_idx)

        win.ui_renderer.update_world_list(
            visible_items,
            self.texture_pack_index - start_index,
            mapped_on_select,
            on_apply,
            on_import,
            lambda: None,
            lambda: None,
            on_cancel,
            primary_label="Apply Pack",
            secondary_label="Import...",
            edit_label="",
            delete_label="",
            cancel_label="Back",
        )

    # ── Update list ───────────────────────────────────────────────────────────

    def _draw_update_list(self) -> None:
        win = self.win
        self._poll_update_events()

        def on_select(idx: int) -> None:
            self.update_release_index = idx

        def on_check() -> None:
            self._start_update_release_check()

        def on_download() -> None:
            self._start_selected_update_download()

        def on_install() -> None:
            self._apply_downloaded_update()

        def on_cancel_task() -> None:
            self._cancel_update_task()

        def on_cancel() -> None:
            win.menu.back()
            win._sync_game_state()

        task_active = self._update_worker_active()
        secondary_action = on_cancel_task if task_active else on_check
        secondary_label = "Cancel" if task_active else "Refresh"

        if not self._updates_loaded:
            items: list[tuple[str, None]] = [("Check GitHub releases", None)]
            win.ui_renderer.update_world_list(
                items,
                0,
                on_select,
                on_check,
                secondary_action,
                lambda: None,
                lambda: None,
                on_cancel,
                primary_label="Check",
                secondary_label=secondary_label,
                edit_label="",
                delete_label="",
                cancel_label="Back",
            )
            return

        count = len(self.update_release_items)
        if count == 0:
            win.ui_renderer.update_world_list(
                [("No releases found", None)],
                0,
                on_select,
                on_check,
                secondary_action,
                lambda: None,
                lambda: None,
                on_cancel,
                primary_label="Check",
                secondary_label=secondary_label,
                edit_label="",
                delete_label="",
                cancel_label="Back",
            )
            return

        self.update_release_index = max(0, min(self.update_release_index, count - 1))
        start_index = max(0, self.update_release_index - 3)
        end_index = min(count, start_index + 8)
        start_index = max(0, end_index - 8)
        visible_releases = self.update_release_items[start_index:end_index]
        visible_items = [
            (self._update_release_label(release), release) for release in visible_releases
        ]

        def mapped_on_select(visible_idx: int) -> None:
            on_select(start_index + visible_idx)

        win.ui_renderer.update_world_list(
            visible_items,
            self.update_release_index - start_index,
            mapped_on_select,
            on_download,
            secondary_action,
            on_install,
            lambda: None,
            on_cancel,
            primary_label="Download",
            secondary_label=secondary_label,
            edit_label="Install" if self.downloaded_update_path is not None else "",
            delete_label="",
            cancel_label="Back",
        )

    def _start_update_release_check(self) -> None:
        win = self.win
        if self._update_worker_active():
            win.menu.status = "Update task already running..."
            return
        self._update_cancel_event.clear()
        win.menu.status = "Checking GitHub releases..."

        def worker() -> None:
            try:
                releases = fetch_releases()
            except Exception as error:
                self._update_events.put(("error", f"Update check failed: {error}"))
                return
            self._update_events.put(("releases", releases))

        self._update_worker = Thread(target=worker, name="VeilstoneUpdateCheck", daemon=True)
        self._update_worker.start()

    def _start_selected_update_download(self) -> None:
        win = self.win
        if self._update_worker_active():
            win.menu.status = "Update task already running..."
            return
        self._update_cancel_event.clear()
        if not self.update_release_items:
            self._start_update_release_check()
            return
        if not (0 <= self.update_release_index < len(self.update_release_items)):
            win.menu.status = "No update release selected."
            return

        release = self.update_release_items[self.update_release_index]
        asset = select_platform_asset(release)
        if asset is None:
            win.menu.status = f"No zip asset for this platform in {release.tag_name}."
            return

        win.menu.status = f"Downloading {asset.name}..."

        def progress(received: int, total: int | None) -> None:
            if self._update_cancel_event.is_set():
                raise _UpdateCancelled
            self._update_events.put(
                ("progress", self._update_progress_status(asset.name, received, total))
            )

        def worker() -> None:
            try:
                path = download_release_asset(asset, progress_callback=progress)
            except _UpdateCancelled:
                self._update_events.put(("error", "Download cancelled."))
                return
            except Exception as error:
                self._update_events.put(("error", f"Download failed: {error}"))
                return
            self._update_events.put(("downloaded", (release.tag_name, path)))

        self._update_worker = Thread(target=worker, name="VeilstoneUpdateDownload", daemon=True)
        self._update_worker.start()

    def _poll_update_events(self) -> None:
        while True:
            try:
                event, payload = self._update_events.get_nowait()
            except Empty:
                return

            if event == "error":
                self._updates_loaded = True
                self.win.menu.status = str(payload)
            elif event == "progress":
                self.win.menu.status = str(payload)
            elif event == "releases":
                releases = cast(tuple[GitHubRelease, ...], payload)
                self.update_release_items = list(releases)
                self._updates_loaded = True
                self.update_release_index = 0
                self.downloaded_update_path = None
                self._set_update_release_status()
            elif event == "downloaded":
                tag_name, path = cast(tuple[str, Path], payload)
                self.downloaded_update_path = path
                self.win.menu.status = f"Downloaded {tag_name} to {path}."

    def _set_update_release_status(self) -> None:
        if not self.update_release_items:
            self.win.menu.status = "No GitHub releases found."
            return
        latest = self.update_release_items[0]
        asset = select_platform_asset(latest)
        suffix = "" if asset is not None else " (no zip for this platform)"
        self.win.menu.status = f"Current {__version__}; latest {latest.tag_name}{suffix}."

    def _update_worker_active(self) -> bool:
        return self._update_worker is not None and self._update_worker.is_alive()

    def _cancel_update_task(self) -> None:
        if not self._update_worker_active():
            self.win.menu.status = "No update task running."
            return
        self._update_cancel_event.set()
        self.win.menu.status = "Cancelling update task..."

    def _apply_downloaded_update(self) -> None:
        win = self.win
        if self._update_worker_active():
            win.menu.status = "Wait for the current update task to finish."
            return
        if self.downloaded_update_path is None:
            win.menu.status = "Download an update before installing."
            return
        if not self.downloaded_update_path.is_file():
            win.menu.status = "Downloaded update archive is missing."
            return

        try:
            plan = prepare_update_install(self.downloaded_update_path)
            launch_update_installer(plan)
        except UpdateInstallError as error:
            win.menu.status = f"Install unavailable: {error}"
            return
        except OSError as error:
            win.menu.status = f"Install launch failed: {error}"
            return

        win.menu.status = "Installing update; Veilstone will restart."
        win.close()

    def _update_progress_status(self, asset_name: str, received: int, total: int | None) -> str:
        if total:
            percent = min(100.0, (received / total) * 100.0)
            return f"Downloading {asset_name}: {percent:.0f}%"
        return f"Downloading {asset_name}: {received // 1024} KiB"

    def _update_release_label(self, release: GitHubRelease) -> str:
        asset = select_platform_asset(release)
        tags: list[str] = []
        if release.tag_name.strip().removeprefix("v") == __version__.strip().removeprefix("v"):
            tags.append("current")
        if release.prerelease:
            tags.append("prerelease")
        if asset is None:
            tags.append("no platform zip")
        if self.downloaded_update_path and asset and self.downloaded_update_path.name == asset.name:
            tags.append("downloaded")
        suffix = f" [{', '.join(tags)}]" if tags else ""
        return f"{release.tag_name} - {release.name}{suffix}"

    def _apply_selected_texture_pack(self) -> None:
        win = self.win
        if not (0 <= self.texture_pack_index < len(self.texture_pack_items)):
            win.menu.status = "No texture pack selected."
            return

        label, pack_path = self.texture_pack_items[self.texture_pack_index]
        report: ImportReport | None = None

        def capture_report(next_report: ImportReport) -> None:
            nonlocal report
            report = next_report

        result = ApplyResourcePackUseCase(
            texture_packs=cast(TexturePackServicePort, win.app_runtime.texture_packs),
            settings_store=win.app_runtime.settings_store,
        ).execute(
            path=None if pack_path is None else str(pack_path),
            settings=win.settings,
            renderer=win.world_renderer,
            block_registry=win.world_runtime.block_registry,
            cache_root=win.active_save_root.parent / "texture_cache",
            report_callback=capture_report,
        )
        if not result.applied:
            win.menu.status = result.status.replace("Resource pack", "Texture pack", 1)
            return

        win.settings = result.settings
        win.menu.status = self._texture_pack_status(label, report)

    def _import_texture_pack(self) -> None:
        win = self.win
        dest_dir = self._resource_packs_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            import tkinter as tk
            from tkinter import filedialog
        except ImportError:
            win.menu.status = "Import requires tkinter (not available)."
            return

        root_tk = cast(Any, tk.Tk())
        root_tk.withdraw()
        root_tk.lift()
        root_tk.attributes("-topmost", True)

        # Ask for ZIP first; fall back to directory selection.
        path_str = filedialog.askopenfilename(
            parent=root_tk,
            title="Select Resource Pack ZIP",
            filetypes=[("Resource Pack", "*.zip"), ("All Files", "*.*")],
        )
        if not path_str:
            path_str = filedialog.askdirectory(
                parent=root_tk,
                title="Select Resource Pack Folder",
            )
        root_tk.destroy()

        if not path_str:
            return

        src = Path(path_str)
        if not src.exists():
            win.menu.status = "Selected path does not exist."
            return

        dest = dest_dir / src.name
        try:
            if src.is_file():
                import shutil

                shutil.copy2(src, dest)
            else:
                import shutil

                shutil.copytree(src, dest, dirs_exist_ok=True)
        except OSError as error:
            win.menu.status = f"Import failed: {error}"
            return

        # Refresh list and select the imported pack.
        self.texture_pack_items = self._discover_texture_packs()
        self._texture_pack_cache_time = time.perf_counter()
        for i, (_, path) in enumerate(self.texture_pack_items):
            if path is not None and path.name == src.name:
                self.texture_pack_index = i
                break
        win.menu.status = f"Imported: {src.name}"

    def _texture_pack_status(self, label: str, report: ImportReport | None) -> str:
        if report is None:
            if label == "Default":
                return "Default texture pack applied."
            return f"Texture pack applied: {label}."
        details: list[str] = []
        if report.fallback:
            details.append(f"{len(report.fallback)} fallback")
        if report.missing:
            details.append(f"{len(report.missing)} missing")
        if report.warnings:
            details.append(f"{len(report.warnings)} warnings")
        suffix = f" ({', '.join(details)})" if details else ""
        return f"Texture pack applied: {label}{suffix}."

    # ── Menu command handler ──────────────────────────────────────────────────

    def _handle_menu_command(self, command: MenuCommand) -> None:
        win = self.win
        if command is MenuCommand.CLOSE:
            win.close()
        elif command is MenuCommand.DISCOVER_LAN:
            worlds = discover_worlds()
            if not worlds:
                win.menu.status = "No LAN worlds found. Start Open to LAN or a dedicated server."
                return
            world = worlds[0]
            try:
                win._net.connect_remote(f"{world.host}:{world.port}", win.player_name)
            except (OSError, ValueError) as error:
                win.menu.status = f"LAN connection failed: {error}"
        elif command is MenuCommand.DIRECT_CONNECT:
            self._begin_text_input(
                TextPurpose.DIRECT_CONNECT,
                "Server address (HOST:PORT)",
                initial="127.0.0.1:25565",
            )
        elif command is MenuCommand.EDIT_NICKNAME:
            self._begin_text_input(
                TextPurpose.NICKNAME,
                "Nickname",
                initial=win.player_name,
                maximum_length=32,
            )
        elif command is MenuCommand.OPEN_LAN:
            win._net.open_to_lan()
        elif command is MenuCommand.CYCLE_SHADOWS:
            qualities = ("off", "low", "medium")
            current = win.settings.graphics.shadow_quality
            current_index = qualities.index(current) if current in qualities else 1
            next_quality = qualities[(current_index + 1) % len(qualities)]
            win.settings = replace(
                win.settings,
                graphics=replace(win.settings.graphics, shadow_quality=next_quality),
            )
            win.menu.status = f"Shadow quality saved as {next_quality}; applies after restart."
            save_user_settings(win.settings)
        elif command is MenuCommand.CYCLE_MATERIALS:
            qualities = ("color-only", "material-preview")
            current = win.settings.graphics.material_quality
            current_index = qualities.index(current) if current in qualities else 0
            next_quality = qualities[(current_index + 1) % len(qualities)]
            result = ApplyMaterialQualityUseCase(
                settings_store=win.app_runtime.settings_store,
            ).execute(
                quality=next_quality,
                settings=win.settings,
                renderer=win.world_renderer,
            )
            if result.applied:
                win.settings = result.settings
            win.menu.status = result.status
        elif command is MenuCommand.TOGGLE_CLOUDS:
            enabled = not win.settings.graphics.clouds
            win.settings = replace(
                win.settings,
                graphics=replace(win.settings.graphics, clouds=enabled),
            )
            win.sky_renderer.clouds = enabled
            save_user_settings(win.settings)
        elif command is MenuCommand.TOGGLE_VSYNC:
            enabled = not win.settings.window.vsync
            win.settings = replace(
                win.settings,
                window=replace(win.settings.window, vsync=enabled),
            )
            win.set_vsync(enabled)
            save_user_settings(win.settings)
        elif command is MenuCommand.CYCLE_RENDER_DISTANCE:
            self._cycle_render_distance()
        elif command is MenuCommand.CYCLE_DIFFICULTY:
            difficulty = "peaceful" if win.settings.gameplay.difficulty == "normal" else "normal"
            win._gameplay._set_difficulty(difficulty)
            win.menu.status = f"Difficulty saved as {difficulty}."
        elif command in {
            MenuCommand.CYCLE_MASTER_VOLUME,
            MenuCommand.CYCLE_EFFECTS_VOLUME,
            MenuCommand.CYCLE_MUSIC_VOLUME,
            MenuCommand.CYCLE_AMBIENCE_VOLUME,
        }:
            self._cycle_audio_volume(command)
        elif command in {
            MenuCommand.TOGGLE_SMOOTH_LIGHTING,
            MenuCommand.TOGGLE_AMBIENT_OCCLUSION,
            MenuCommand.TOGGLE_FOG,
            MenuCommand.TOGGLE_MESHER,
        }:
            self._toggle_development_graphics(command)
        elif command is MenuCommand.CREATE_WORLD:
            self._begin_text_input(
                TextPurpose.WORLD_NAME,
                "World name",
                initial="New World",
                maximum_length=48,
            )
        elif command in {
            MenuCommand.REBIND_FORWARD,
            MenuCommand.REBIND_BACKWARD,
            MenuCommand.REBIND_LEFT,
            MenuCommand.REBIND_RIGHT,
            MenuCommand.REBIND_JUMP,
        }:
            win.rebinding_action = {
                MenuCommand.REBIND_FORWARD: "forward",
                MenuCommand.REBIND_BACKWARD: "backward",
                MenuCommand.REBIND_LEFT: "left",
                MenuCommand.REBIND_RIGHT: "right",
                MenuCommand.REBIND_JUMP: "jump",
            }[command]
            win.menu.status = f"Press a key for {win.rebinding_action}."

    def _cycle_render_distance(self) -> None:
        win = self.win
        choices = (2, 4, 6, 8, 10, 12)
        current = win.settings.world.render_distance
        next_distance = next((value for value in choices if value > current), choices[0])
        win.settings = replace(
            win.settings,
            world=replace(win.settings.world, render_distance=next_distance),
        )
        changed_live = win.world_renderer.set_render_distance(next_distance)
        suffix = "applied." if changed_live else "already active."
        win.menu.status = f"Render distance saved {next_distance} chunks; {suffix}"
        save_user_settings(win.settings)

    def _toggle_development_graphics(self, command: MenuCommand) -> None:
        win = self.win
        match command:
            case MenuCommand.TOGGLE_SMOOTH_LIGHTING:
                win.world_renderer.toggle_smooth_lighting()
                enabled = bool(win.world_renderer.smooth_lighting)
                win.settings = replace(
                    win.settings,
                    graphics=replace(win.settings.graphics, smooth_lighting=enabled),
                )
                status = f"Smooth lighting {'enabled' if enabled else 'disabled'}."
            case MenuCommand.TOGGLE_AMBIENT_OCCLUSION:
                win.world_renderer.toggle_ambient_occlusion()
                enabled = bool(win.world_renderer.ambient_occlusion)
                win.settings = replace(
                    win.settings,
                    graphics=replace(win.settings.graphics, ambient_occlusion=enabled),
                )
                status = f"Ambient occlusion {'enabled' if enabled else 'disabled'}."
            case MenuCommand.TOGGLE_FOG:
                win.world_renderer.toggle_fog()
                enabled = bool(win.world_renderer.fog_enabled)
                win.settings = replace(
                    win.settings,
                    graphics=replace(win.settings.graphics, fog=enabled),
                )
                status = f"Fog {'enabled' if enabled else 'disabled'}."
            case MenuCommand.TOGGLE_MESHER:
                win.world_renderer.toggle_mesher()
                enabled = bool(win.world_renderer.greedy_meshing)
                win.settings = replace(
                    win.settings,
                    graphics=replace(win.settings.graphics, greedy_meshing=enabled),
                )
                status = f"Mesher saved as {'greedy' if enabled else 'visible'}."
            case _:
                return
        win.menu.status = status
        save_user_settings(win.settings)

    # ── Audio helpers ─────────────────────────────────────────────────────────

    def _play_ui_sound(self) -> None:
        self.win.audio.emit(AudioEvent(AudioEventKind.SOUND, "ui.click"))

    def _cycle_audio_volume(self, command: MenuCommand) -> None:
        win = self.win
        fields = {
            MenuCommand.CYCLE_MASTER_VOLUME: "master",
            MenuCommand.CYCLE_EFFECTS_VOLUME: "effects",
            MenuCommand.CYCLE_MUSIC_VOLUME: "music",
            MenuCommand.CYCLE_AMBIENCE_VOLUME: "ambience",
        }
        field = fields[command]
        current = getattr(win.settings.audio, field)
        next_volume = 0.0 if current >= 0.99 else round(current + 0.1, 1)
        audio_settings = replace(win.settings.audio, **{field: next_volume})
        win.settings = replace(win.settings, audio=audio_settings)
        win.audio.set_volumes(volume_map(audio_settings))
        win.menu.status = f"{field.title()} volume saved as {next_volume:.0%}."
        save_user_settings(win.settings)

    # ── Text input ────────────────────────────────────────────────────────────

    def _begin_text_input(
        self,
        purpose: TextPurpose,
        prompt: str,
        *,
        initial: str = "",
        maximum_length: int = 128,
    ) -> None:
        win = self.win
        win.text_input = TextInput(purpose, prompt, initial, maximum_length)
        win.key_state.clear()
        win._sync_mouse_capture()

    def _submit_text_input(self) -> None:
        win = self.win
        field = win.text_input
        if field is None:
            return
        value = field.value.strip()
        if field.purpose is TextPurpose.NICKNAME:
            win.player_name = value[:32] or "Player"
            if win.authority is not None:
                win.authority.set_player_name(win.player_name)
            win.menu.status = f"Nickname: {win.player_name}"
            win.text_input = None
        elif field.purpose is TextPurpose.DIRECT_CONNECT:
            if not value:
                win.menu.status = "Server address is required."
                return
            try:
                win._net.connect_remote(value, win.player_name)
            except (OSError, ValueError) as error:
                win.menu.status = f"Connection failed: {error}"
                return
            win.text_input = None
        elif field.purpose is TextPurpose.CHAT:
            if value and win.authority is not None:
                try:
                    win.authority.send_chat(value)
                except (ConnectionError, OSError) as error:
                    win.inventory_status = f"Chat failed: {error}"
            elif value:
                win.inventory_status = "Chat is available in multiplayer."
            win.text_input = None
        elif field.purpose is TextPurpose.COMMAND:
            win._gameplay.execute_command(value)
            win.text_input = None
        elif field.purpose is TextPurpose.WORLD_NAME:
            if not value:
                win.menu.status = "World name is required."
                return
            win.pending_world_name = value[:48]
            win.text_input = TextInput(
                TextPurpose.WORLD_SEED,
                "World seed",
                win.pending_world_name,
                64,
            )
            return
        elif field.purpose is TextPurpose.WORLD_SEED:
            seed = value or win.pending_world_name
            win._worlds.create_world(win.pending_world_name, seed)
            win.text_input = None
        elif field.purpose is TextPurpose.RENAME_WORLD:
            if not (0 <= self.world_list_index < len(self.world_list_items)):
                win.menu.status = "No world selected to rename."
                win.text_input = None
                win._sync_mouse_capture()
                return
            name, path = self.world_list_items[self.world_list_index]
            storage = WorldStorage(path)
            meta = storage.load_metadata()
            if meta is None:
                win.menu.status = "Failed to read world metadata."
                win.text_input = None
                win._sync_mouse_capture()
                return
            storage.ensure_world(name=value or meta.name, seed=meta.seed)
            win.menu.status = f"Renamed world to {value or meta.name}."
            self._world_list_cache_time = 0.0
            self._refresh_world_list()
            win.text_input = None
        elif field.purpose is TextPurpose.DELETE_WORLD:
            if value == "DELETE":
                if not (0 <= self.world_list_index < len(self.world_list_items)):
                    win.menu.status = "No world selected to delete."
                    win.text_input = None
                    win._sync_mouse_capture()
                    return
                name, path = self.world_list_items[self.world_list_index]
                WorldManager.delete_world(path)
                win.menu.status = f"Deleted world {name}."
                self._world_list_cache_time = 0.0
                self._refresh_world_list()
                self.world_list_index = max(
                    0, min(self.world_list_index, len(self.world_list_items) - 1)
                )
            else:
                win.menu.status = "Delete cancelled (type DELETE to confirm)."
            win.text_input = None
