# pyright: reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.render.menu_ui import MenuUI
from voxel_sandbox.render.ui.menu import MenuCommand, MenuController, Screen


def test_mouse_resume_syncs_game_state_and_mouse_capture() -> None:
    calls: list[str] = []
    menu = MenuController()
    menu.screen = Screen.PAUSE

    class FakeUiRenderer:
        def update(self, _menu, _label, on_click, _hover) -> None:
            on_click(0)

        def draw(self) -> None:
            pass

    win = SimpleNamespace(
        menu=menu,
        ui_renderer=FakeUiRenderer(),
        text_input=None,
        _sync_game_state=lambda: calls.append("game_state"),
        _sync_mouse_capture=lambda: calls.append("mouse_capture"),
    )
    menu_ui = MenuUI.__new__(MenuUI)
    menu_ui.win = win
    menu_ui.text_input_overlay = SimpleNamespace(opacity=255)
    menu_ui.text_input_panel = SimpleNamespace(opacity=255)

    menu_ui._draw_menu()

    assert menu.screen is Screen.GAME
    assert calls == ["game_state", "mouse_capture"]


def test_render_distance_menu_label_and_cycle(monkeypatch) -> None:
    saved: list[AppSettings] = []
    monkeypatch.setattr("voxel_sandbox.render.menu_ui.save_user_settings", saved.append)

    menu = MenuController()
    menu.screen = Screen.SETTINGS
    menu.select(5)

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
    assert menu_ui._menu_item_label(5) == "Render Distance: 4 chunks"

    menu_ui._handle_menu_command(MenuCommand.CYCLE_RENDER_DISTANCE)

    assert win.settings.world.render_distance == 6
    assert world_renderer.render_distance == 6
    assert saved[-1].world.render_distance == 6
    assert win.menu.status == "Render distance saved 6 chunks; applied."


def test_quality_preset_menu_label_and_cycle(monkeypatch) -> None:
    saved: list[AppSettings] = []
    monkeypatch.setattr("voxel_sandbox.render.menu_ui.save_user_settings", saved.append)
    menu = MenuController()
    menu.screen = Screen.SETTINGS

    class FakeWorldRenderer:
        def __init__(self) -> None:
            self.applied: list[tuple[str, str]] = []
            self.linear_texture_minification: bool | None = None
            self.fog_enabled = False
            self.vegetation_wind_enabled = True
            self.water_detail_enabled = True

        def apply_material_quality(
            self, material_quality: str, resource_pack_path: str = ""
        ) -> None:
            self.applied.append((material_quality, resource_pack_path))

        def apply_texture_minification(self, linear_minification: bool) -> None:
            self.linear_texture_minification = linear_minification

    world_renderer = FakeWorldRenderer()
    sky_renderer = SimpleNamespace(clouds=True)
    win = SimpleNamespace(
        settings=AppSettings(),
        menu=menu,
        world_renderer=world_renderer,
        sky_renderer=sky_renderer,
    )
    menu_ui = MenuUI.__new__(MenuUI)
    menu_ui.win = win

    assert menu.activate() is MenuCommand.CYCLE_QUALITY_PRESET
    assert menu_ui._menu_item_label(0) == "Quality Preset: custom"

    menu_ui._handle_menu_command(MenuCommand.CYCLE_QUALITY_PRESET)

    assert win.settings.graphics.quality_preset == "low_60"
    assert win.settings.graphics.shadow_quality == "off"
    assert win.settings.graphics.smooth_lighting is False
    assert win.settings.graphics.ambient_occlusion is False
    assert win.settings.graphics.material_quality == "color-only"
    assert world_renderer.applied == [("color-only", "")]
    assert world_renderer.linear_texture_minification is False
    assert world_renderer.fog_enabled is True
    assert world_renderer.vegetation_wind_enabled is False
    assert world_renderer.water_detail_enabled is False
    assert sky_renderer.clouds is False
    assert saved[-1].graphics.quality_preset == "low_60"
    assert win.menu.status == (
        "Quality preset low_60 saved; live material/texture/fog/clouds/wind/water applied; "
        "shadows/smooth/AO/render distance apply restart."
    )


def test_materials_menu_label_and_cycle() -> None:
    menu = MenuController()
    menu.screen = Screen.SETTINGS
    menu.select(1)

    class FakeWorldRenderer:
        def __init__(self) -> None:
            self.applied: list[tuple[str, str]] = []

        def apply_material_quality(
            self, material_quality: str, resource_pack_path: str = ""
        ) -> None:
            self.applied.append((material_quality, resource_pack_path))

    class FakeSettingsStore:
        def __init__(self) -> None:
            self.saved: list[AppSettings] = []

        def save(self, settings: AppSettings) -> None:
            self.saved.append(settings)

    world_renderer = FakeWorldRenderer()
    settings_store = FakeSettingsStore()
    win = SimpleNamespace(
        settings=AppSettings(),
        menu=menu,
        world_renderer=world_renderer,
        app_runtime=SimpleNamespace(settings_store=settings_store),
    )
    menu_ui = MenuUI.__new__(MenuUI)
    menu_ui.win = win

    menu.select(2)

    assert menu.activate() is MenuCommand.CYCLE_MATERIALS
    assert menu_ui._menu_item_label(2) == "Materials: color-only"

    menu_ui._handle_menu_command(MenuCommand.CYCLE_MATERIALS)

    assert win.settings.graphics.material_quality == "material-preview"
    assert win.settings.graphics.quality_preset == "custom"
    assert world_renderer.applied == [("material-preview", "")]
    assert settings_store.saved[-1].graphics.material_quality == "material-preview"
    assert settings_store.saved[-1].graphics.quality_preset == "custom"
    assert win.menu.status == "Material quality applied: material-preview"

    menu_ui._handle_menu_command(MenuCommand.CYCLE_MATERIALS)

    assert win.settings.graphics.material_quality == "color-only"
    assert menu_ui._menu_item_label(2) == "Materials: color-only"


def test_development_graphics_menu_labels_and_toggles(monkeypatch) -> None:
    saved: list[AppSettings] = []
    monkeypatch.setattr("voxel_sandbox.render.menu_ui.save_user_settings", saved.append)
    menu = MenuController()
    menu.screen = Screen.DEVELOPMENT

    class FakeWorldRenderer:
        def __init__(self) -> None:
            self.smooth_lighting = True
            self.ambient_occlusion = True
            self.fog_enabled = True
            self.greedy_meshing = True

        def toggle_smooth_lighting(self) -> None:
            self.smooth_lighting = not self.smooth_lighting

        def toggle_ambient_occlusion(self) -> None:
            self.ambient_occlusion = not self.ambient_occlusion

        def toggle_fog(self) -> None:
            self.fog_enabled = not self.fog_enabled

        def toggle_mesher(self) -> None:
            self.greedy_meshing = not self.greedy_meshing

    win = SimpleNamespace(
        settings=AppSettings(),
        menu=menu,
        world_renderer=FakeWorldRenderer(),
    )
    menu_ui = MenuUI.__new__(MenuUI)
    menu_ui.win = win

    assert menu_ui._menu_item_label(0) == "Smooth Lighting: on"
    assert menu_ui._menu_item_label(1) == "Ambient Occlusion: on"
    assert menu_ui._menu_item_label(2) == "Fog: on"
    assert menu_ui._menu_item_label(3) == "Mesher: greedy"

    menu_ui._handle_menu_command(MenuCommand.TOGGLE_SMOOTH_LIGHTING)
    assert win.world_renderer.smooth_lighting is False
    assert win.settings.graphics.smooth_lighting is False
    assert saved[-1].graphics.smooth_lighting is False
    assert win.menu.status == "Smooth lighting disabled."

    menu_ui._handle_menu_command(MenuCommand.TOGGLE_MESHER)
    assert win.world_renderer.greedy_meshing is False
    assert win.settings.graphics.greedy_meshing is False
    assert saved[-1].graphics.greedy_meshing is False
    assert win.menu.status == "Mesher saved as visible."
