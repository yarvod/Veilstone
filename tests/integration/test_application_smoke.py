from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path
from typing import cast

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


def test_optional_postprocess_renders_and_resizes() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    settings = AppSettings()
    settings = replace(
        settings,
        graphics=replace(settings.graphics, postprocess=True),
    )
    with tempfile.TemporaryDirectory(prefix="veilstone-postprocess-test-") as directory:
        window = GameWindow(settings, visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.switch_to()
            window.on_draw()
            window.mgl_context.finish()
            assert window.postprocess_renderer.size == (window.width, window.height)

            window.set_size(640, 360)
            window.on_draw()
            window.mgl_context.finish()
            assert window.postprocess_renderer.size == (window.width, window.height)
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
            height = image.height
            raw = image.get_data("RGBA", width * 4)

            def get_pixel(x: int, y: int) -> tuple[int, int, int, int]:
                offset = (y * width + x) * 4
                return tuple(raw[offset : offset + 4])

            sample_rows = [
                int(window.menu_labels[0].y),
                int(window.menu_labels[1].y),
                int(window.menu_title.y),
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
            assert window.lan_server is not None
            for index, key_name in enumerate(("gate", "altar", "bridge")):
                entity = window.lan_server.spawn_structure(key_name, (index * 8, 40, 0))
                window.lan_server.toggle_structure(entity.entity_id)
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
    from voxel_sandbox.render import window as window_module

    def discard_settings(_settings: AppSettings) -> None:
        pass

    monkeypatch.setattr(window_module, "save_user_settings", discard_settings)
    with tempfile.TemporaryDirectory(prefix="veilstone-command-test-") as directory:
        window = window_module.GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            hostile = window.entities.spawn_mob(MobKind.HOSTILE, window.camera.position)
            window.execute_command("/time set midnight")
            assert window.world_renderer.time_of_day == 0.75

            window.execute_command("/difficulty peaceful")
            assert window.settings.gameplay.difficulty == "peaceful"
            assert hostile not in window.entities.world.alive

            window.execute_command("/help")
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
            assert len(window.item_icon_images) == len(window.item_registry)
            assert len(window.heart_sprites) == 10
            window.on_key_press(None, 0)
        finally:
            window.close()
