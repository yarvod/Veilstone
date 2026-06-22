from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.render.menu_ui import MenuUI
from voxel_sandbox.render.ui.menu import MenuCommand, MenuController, Screen


def test_render_distance_menu_label_and_cycle(monkeypatch) -> None:
    saved: list[AppSettings] = []
    monkeypatch.setattr("voxel_sandbox.render.menu_ui.save_user_settings", saved.append)

    menu = MenuController()
    menu.screen = Screen.SETTINGS
    menu.select(3)

    class FakeWorldRenderer:
        def __init__(self) -> None:
            self.render_distance: int | None = None

        def set_render_distance(self, render_distance: int) -> bool:
            self.render_distance = render_distance
            return True

    world_renderer = FakeWorldRenderer()
    win = SimpleNamespace(
        settings=replace(AppSettings(), world=replace(AppSettings().world, render_distance=4)),
        menu=menu,
        world_renderer=world_renderer,
    )
    menu_ui = MenuUI.__new__(MenuUI)
    menu_ui.win = win

    assert menu.activate() is MenuCommand.CYCLE_RENDER_DISTANCE
    assert menu_ui._menu_item_label(3) == "Render Distance: 4 chunks"

    menu_ui._handle_menu_command(MenuCommand.CYCLE_RENDER_DISTANCE)

    assert win.settings.world.render_distance == 6
    assert world_renderer.render_distance == 6
    assert saved[-1].world.render_distance == 6
    assert win.menu.status == "Render distance saved 6 chunks; applied."
