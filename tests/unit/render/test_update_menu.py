# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false

from __future__ import annotations

from pathlib import Path
from queue import Queue
from threading import Event
from types import SimpleNamespace
from typing import Any

from voxel_sandbox.app.updates import GitHubRelease, ReleaseAsset
from voxel_sandbox.render.menu_ui import MenuUI
from voxel_sandbox.render.ui.menu import MenuController, Screen


class RecordingUiRenderer:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def update_world_list(
        self,
        worlds: list[tuple[str, Any]],
        selected_index: int,
        on_select: Any,
        on_play: Any,
        on_create: Any,
        on_edit: Any,
        on_delete: Any,
        on_cancel: Any,
        *,
        primary_label: str = "Play",
        secondary_label: str = "Create",
        edit_label: str = "Edit",
        delete_label: str = "Delete",
        cancel_label: str = "Cancel",
    ) -> None:
        self.calls.append(
            {
                "worlds": worlds,
                "selected_index": selected_index,
                "on_play": on_play,
                "on_create": on_create,
                "primary_label": primary_label,
                "secondary_label": secondary_label,
                "cancel_label": cancel_label,
            }
        )


def _make_menu_ui() -> tuple[MenuUI, Any, RecordingUiRenderer]:
    menu = MenuController()
    menu.screen = Screen.UPDATES
    renderer = RecordingUiRenderer()
    win = SimpleNamespace(
        menu=menu,
        ui_renderer=renderer,
        _sync_game_state=lambda: None,
    )
    menu_ui = MenuUI.__new__(MenuUI)
    menu_ui.win = win
    menu_ui.update_release_items = []
    menu_ui.update_release_index = 0
    menu_ui._updates_loaded = False
    menu_ui.downloaded_update_path = None
    menu_ui._update_events = Queue()
    menu_ui._update_worker = None
    menu_ui._update_cancel_event = Event()
    return menu_ui, win, renderer


def test_update_screen_starts_with_check_action(monkeypatch: Any) -> None:
    release = GitHubRelease(
        tag_name="v0.2.0",
        name="Veilstone v0.2.0",
        html_url="https://example.test/release",
        assets=(),
    )
    monkeypatch.setattr("voxel_sandbox.render.menu_ui.fetch_releases", lambda: (release,))

    menu_ui, win, renderer = _make_menu_ui()
    menu_ui._draw_update_list()

    call = renderer.calls[-1]
    assert call["worlds"] == [("Check GitHub releases", None)]
    assert call["primary_label"] == "Check"

    call["on_play"]()
    assert menu_ui._update_worker is not None
    menu_ui._update_worker.join(timeout=1.0)
    menu_ui._draw_update_list()

    assert menu_ui.update_release_items == [release]
    assert menu_ui._updates_loaded is True
    assert "latest v0.2.0" in win.menu.status


def test_update_screen_downloads_selected_release(monkeypatch: Any, tmp_path: Path) -> None:
    asset = ReleaseAsset("Veilstone_Test_v0_2_0.zip", "https://example.test/asset.zip", 4)
    release = GitHubRelease(
        tag_name="v0.2.0",
        name="Veilstone v0.2.0",
        html_url="https://example.test/release",
        assets=(asset,),
    )
    target = tmp_path / asset.name

    def select_asset(_release: GitHubRelease) -> ReleaseAsset:
        return asset

    def download_asset(_asset: ReleaseAsset, *, progress_callback: Any = None) -> Path:
        if progress_callback is not None:
            progress_callback(4, 4)
        return target

    monkeypatch.setattr("voxel_sandbox.render.menu_ui.select_platform_asset", select_asset)
    monkeypatch.setattr("voxel_sandbox.render.menu_ui.download_release_asset", download_asset)

    menu_ui, win, _renderer = _make_menu_ui()
    menu_ui.update_release_items = [release]
    menu_ui._updates_loaded = True

    menu_ui._start_selected_update_download()
    assert menu_ui._update_worker is not None
    menu_ui._update_worker.join(timeout=1.0)
    menu_ui._poll_update_events()

    assert menu_ui.downloaded_update_path == target
    assert win.menu.status == f"Downloaded v0.2.0 to {target}."


def test_update_screen_can_cancel_running_download(monkeypatch: Any, tmp_path: Path) -> None:
    asset = ReleaseAsset("Veilstone_Test_v0_2_0.zip", "https://example.test/asset.zip", 4)
    release = GitHubRelease(
        tag_name="v0.2.0",
        name="Veilstone v0.2.0",
        html_url="https://example.test/release",
        assets=(asset,),
    )
    started = Event()

    def select_asset(_release: GitHubRelease) -> ReleaseAsset:
        return asset

    def download_asset(_asset: ReleaseAsset, *, progress_callback: Any = None) -> Path:
        started.set()
        menu_ui._update_cancel_event.wait(timeout=1.0)
        assert progress_callback is not None
        progress_callback(1, 4)
        return tmp_path / asset.name

    monkeypatch.setattr("voxel_sandbox.render.menu_ui.select_platform_asset", select_asset)
    monkeypatch.setattr("voxel_sandbox.render.menu_ui.download_release_asset", download_asset)

    menu_ui, win, _renderer = _make_menu_ui()
    menu_ui.update_release_items = [release]
    menu_ui._updates_loaded = True

    menu_ui._start_selected_update_download()
    assert started.wait(timeout=1.0)
    menu_ui._cancel_update_task()
    assert menu_ui._update_worker is not None
    menu_ui._update_worker.join(timeout=1.0)
    menu_ui._poll_update_events()

    assert menu_ui.downloaded_update_path is None
    assert win.menu.status == "Download cancelled."
