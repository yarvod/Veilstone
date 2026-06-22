from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from voxel_sandbox.__main__ import main
from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.infrastructure.storage import PlayerSnapshot, WorldStorage

pytestmark = pytest.mark.smoke


def test_primary_player_entry_starts_and_stops() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    assert main(["--smoke-test"]) == 0


def test_dedicated_server_starts_and_stops() -> None:
    assert main(["server", "--smoke-test"]) == 0


def test_invalid_saved_position_recovers_without_losing_inventory() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.window import GameWindow

    registry = create_core_item_registry()
    inventory = Inventory()
    inventory.set(5, ItemStack(3, 7), registry)
    with tempfile.TemporaryDirectory(prefix="veilstone-position-recovery-") as directory:
        save_root = Path(directory)
        storage = WorldStorage(save_root)
        storage.ensure_world(name="Recovery Test", seed="veilstone-dev")
        storage.save_player(
            PlayerSnapshot(
                position=(-37.0, -2354.0, 130.0),
                health=12.0,
                selected_slot=5,
                slots=tuple(inventory),
            )
        )

        window = GameWindow(AppSettings(), visible=False, save_root=save_root)
        try:
            assert window.player.y >= 0.0
            assert window.inventory[5] == ItemStack(3, 7)
            assert window.player_health == 12.0
            assert window.hotbar.selected_index == 5
            corrected = storage.load_player(registry)
            assert corrected is not None
            assert corrected.position == (window.player.x, window.player.y, window.player.z)
        finally:
            window.close()


def test_new_world_starts_empty_and_in_bright_morning() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-new-world-defaults-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            assert all(window.inventory[index] is None for index in range(9))
            assert window.hotbar.selected is None
            assert window.world_renderer.time_of_day == pytest.approx(0.18)
            assert window.world_renderer.daylight >= 0.90
        finally:
            window.close()


def test_main_menu_text_renders_with_blending() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-menu-text-test-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.MAIN
            window.switch_to()
            window.on_draw()
            window.mgl_context.finish()

            image = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
            width = image.width
            raw = image.get_data("RGBA", width * 4)

            def get_pixel(x: int, y: int) -> tuple[int, int, int, int]:
                offset = (y * width + x) * 4
                val = tuple(raw[offset : offset + 4])
                return (val[0], val[1], val[2], val[3])

            sample_rows = [
                int(
                    window.ui_renderer.buttons[0].bounds.y
                    + window.ui_renderer.buttons[0].bounds.height // 2
                ),
                int(
                    window.ui_renderer.buttons[1].bounds.y
                    + window.ui_renderer.buttons[1].bounds.height // 2
                ),
                int(
                    window.ui_renderer.title_label.bounds.y
                    + window.ui_renderer.title_label.bounds.height // 2
                ),
            ]
            bright = 0
            for y in sample_rows:
                # Scan a few more pixels to avoid text gaps
                for x in range(width // 2 - 40, width // 2 + 41, 20):
                    r, g, b, a = get_pixel(x, y)
                    if a > 0 and (r + g + b) >= 100:
                        bright += 1
            assert bright >= 2, "Main menu text should render visibly in the framebuffer"
        finally:
            window.close()


@pytest.mark.parametrize("quality", ["off", "low"])
def test_shadow_quality_modes_render(quality: str) -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    settings = AppSettings()
    settings = replace(
        settings,
        graphics=replace(settings.graphics, shadow_quality=quality),
    )
    with tempfile.TemporaryDirectory(prefix=f"veilstone-shadow-{quality}-") as directory:
        window = GameWindow(settings, visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.switch_to()
            window.on_draw()
            window.mgl_context.finish()
            assert (window.world_renderer.shadow_map is None) is (quality == "off")
        finally:
            window.close()


def test_first_person_viewmodel_renders_hand_and_held_block() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.application.player_camera import PerspectiveMode
    from voxel_sandbox.render.first_person_viewmodel import FirstPersonViewmodelRenderer
    from voxel_sandbox.render.player_viewmodel import PlayerViewmodelRenderData
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    class SpyViewmodelRenderer:
        def __init__(self) -> None:
            self.calls: list[PlayerViewmodelRenderData] = []

        def render(
            self,
            data: PlayerViewmodelRenderData,
            *,
            width: int,
            height: int,
            block_texture: object | None = None,
            atlas_uvs: dict[str, tuple[float, float, float, float]] | None = None,
        ) -> int:
            self.calls.append(data)
            return len(data.parts)

        def release(self) -> None:
            pass

    with tempfile.TemporaryDirectory(prefix="veilstone-viewmodel-smoke-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        original_viewmodel_renderer = window.viewmodel_renderer
        spy = SpyViewmodelRenderer()
        window.viewmodel_renderer = cast(FirstPersonViewmodelRenderer, spy)
        try:
            window.menu.screen = Screen.GAME
            window.perspective_mode = PerspectiveMode.FIRST_PERSON
            window.inventory.set(
                window.hotbar.selected_index,
                ItemStack(3, 1),
                window.item_registry,
            )
            window.switch_to()
            window.on_draw()
            window.mgl_context.finish()

            assert window.mgl_context.viewport == (0, 0, *window._framebuffer_size())
            assert spy.calls
            assert [part.name for part in spy.calls[-1].parts] == [
                "right_arm",
                "right_hand",
                "held_item_block",
            ]
        finally:
            window.viewmodel_renderer = original_viewmodel_renderer
            window.close()


def test_network_input_is_throttled_and_includes_held_item() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")

    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-network-input-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.network_session = MagicMock()
            window.authority = MagicMock()
            window.inventory.set(0, ItemStack(3, 2), window.item_registry)
            window.hotbar.select(0)

            window.fixed_update(0.01)
            window.fixed_update(0.02)
            window.authority.send_input.assert_not_called()

            window.fixed_update(0.02)

            window.authority.send_input.assert_called_once()
            _position, _yaw, held_item = window.authority.send_input.call_args.args
            assert held_item == {"item_id": 3, "count": 2, "hand": "right"}
        finally:
            window.close()


def test_articulated_mobs_render_multiple_textured_parts() -> None:
    import moderngl
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.engine.ecs import MobKind
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-articulated-mobs-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            for entity in tuple(window.entities.world.mob_ai.entities()):
                window.entities.world.destroy(entity)
            window.entities.spawn_mob(MobKind.PASSIVE, window.camera.position)
            window.entities.spawn_mob(MobKind.HOSTILE, window.camera.position)
            window.menu.screen = Screen.GAME
            draws = window.entity_renderer.render(
                window.entities.world,
                window.camera,
                window.width,
                window.height,
                window.settings.camera.field_of_view,
                0.25,
                light_sampler=lambda _position, _height: (0.0, 0.0),
                daylight=0.0,
                light_direction=(0.0, 1.0, 0.0),
            )
            window.mgl_context.finish()

            assert draws >= 15
            assert window.entity_renderer.shader.program is not None
            program = window.entity_renderer.shader.program
            assert cast("moderngl.Uniform", program["entity_sky_light"]).value == 0.0
            assert cast("moderngl.Uniform", program["entity_block_light"]).value == 0.0
            assert cast("moderngl.Uniform", program["daylight"]).value == 0.0
            assert cast("moderngl.Uniform", program["light_direction"]).value == (0.0, 1.0, 0.0)
        finally:
            window.close()


def test_runtime_structures_render_from_authoritative_state() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-runtime-structures-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            assert window.authority is not None
            for index, key_name in enumerate(("gate", "altar", "bridge")):
                entity = window.structure_world.spawn(key_name, (index * 8, 40, 0))
                window.authority.toggle_structure(entity.entity_id)
            draws = window.structure_renderer.render(
                window.structure_world,
                window.camera,
                window.width,
                window.height,
                window.settings.camera.field_of_view,
                window.world_renderer.texture,
                window.world_renderer.atlas_uvs,
            )
            window.mgl_context.finish()

            assert draws == 29
        finally:
            window.close()


def test_game_commands_change_time_and_remove_hostile_mobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.engine.ecs import MobKind
    from voxel_sandbox.render import gameplay_controller as gc_module
    from voxel_sandbox.render import window as window_module

    def discard_settings(_settings: AppSettings, **_kwargs: object) -> None:
        pass

    monkeypatch.setattr(gc_module, "save_user_settings", discard_settings)
    with tempfile.TemporaryDirectory(prefix="veilstone-command-test-") as directory:
        window = window_module.GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            hostile = window.entities.spawn_mob(MobKind.HOSTILE, window.camera.position)
            window._gameplay.execute_command("/time set midnight")
            assert window.world_renderer.time_of_day == 0.75

            window._gameplay.execute_command("/difficulty peaceful")
            assert window.settings.gameplay.difficulty == "peaceful"
            assert hostile not in window.entities.world.alive

            window._gameplay.execute_command("/help")
            assert window.inventory_status.startswith("/time set")
        finally:
            window.close()


def test_inventory_grid_and_item_icons_render() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from pyglet.window import key

    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-inventory-ui-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.on_key_press(key.E, 0)
            window.on_draw()
            window.mgl_context.finish()

            assert window.inventory_open
            assert len(window.crafting_grid) == 4
            assert len(window._inv_ctrl.item_icon_images) == len(window.item_registry)
            assert len(window._inv_ctrl.heart_sprites) == 10
            window.inventory.set(9, ItemStack(3, 5), window.item_registry)
            slot_x, slot_y = window._inv_ctrl._inventory_slot_position(0)
            window.mouse_x = slot_x + 24
            window.mouse_y = slot_y + 24
            window.on_draw()
            window.mgl_context.finish()
            item_name = window.item_registry.by_id(3).name
            assert window._inv_ctrl.hover_tooltip_label.text == f"{item_name} x5"
            window.on_key_press(None, 0)
        finally:
            window.close()
