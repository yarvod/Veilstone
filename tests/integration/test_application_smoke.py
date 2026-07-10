# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false

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


def test_debug_overlay_shows_minecraft_like_diagnostics(monkeypatch) -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")

    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-debug-hud-") as directory:
        memory_reads: list[int] = []

        def fake_memory_label() -> str:
            memory_reads.append(1)
            return "123 MB"

        monkeypatch.setattr(
            "voxel_sandbox.render.hud_controller._process_memory_label",
            fake_memory_label,
        )

        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.debug_overlay_visible = True
            window.on_draw()
            window.mgl_context.finish()

            text = window._hud.debug_label.text
            assert "FPS " in text
            assert "Frame " in text
            assert "Block " in text
            assert "Chunk " in text
            assert "Facing " in text
            assert "Biome " in text
            assert "Memory " in text
            assert "Render distance " in text
            assert "Mesh uploads/frame " in text
            assert "Resource pack Default" in text
            assert "Network singleplayer" in text
            assert "Remote players 0" in text
            assert "Runtime Python " in text
            assert "Device " in text
            assert "Memory 123 MB" in text
            assert "Frame " in text
            window._hud._last_update_time = 0.0
            window.on_draw()
            assert len(memory_reads) == 1
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


def test_texture_pack_apply_preserves_shadow_depth_cache() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.render.texture_packs.importer import load_active_block_atlas
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    settings = AppSettings()
    settings = replace(
        settings,
        graphics=replace(settings.graphics, shadow_quality="low"),
    )
    with tempfile.TemporaryDirectory(prefix="veilstone-pack-shadow-smoke-") as directory:
        save_root = Path(directory)
        window = GameWindow(settings, visible=False, save_root=save_root)
        try:
            window.menu.screen = Screen.GAME
            atlas = load_active_block_atlas(
                None,
                registry=window.world_runtime.block_registry,
                cache_root=save_root / "texture_cache",
            )
            window.world_renderer.apply_texture_pack(atlas)
            window.switch_to()
            window.on_draw()
            window.mgl_context.finish()

            assert window.world_renderer.shadow_map is not None
            assert window.world_renderer.mesh_cache.depth_program is not None
        finally:
            window.close()


def test_third_person_local_player_participates_in_shadow_pass() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from voxel_sandbox.application.player_camera import PerspectiveMode
    from voxel_sandbox.engine.ecs import EntityWorld
    from voxel_sandbox.render.entity_renderer import EntityRenderer
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    class SpyEntityRenderer:
        def __init__(self) -> None:
            self.render_worlds: list[EntityWorld] = []
            self.shadow_worlds: list[EntityWorld] = []

        def render(self, world: EntityWorld, *args: object, **kwargs: object) -> int:
            self.render_worlds.append(world)
            return 0

        def render_shadow(self, world: EntityWorld, *args: object, **kwargs: object) -> None:
            self.shadow_worlds.append(world)

        def release(self) -> None:
            return None

    settings = AppSettings()
    settings = replace(
        settings,
        graphics=replace(settings.graphics, shadow_quality="low"),
    )
    with tempfile.TemporaryDirectory(prefix="veilstone-player-shadow-smoke-") as directory:
        window = GameWindow(settings, visible=False, save_root=Path(directory))
        original_renderer = window.entity_renderer
        spy = SpyEntityRenderer()
        window.entity_renderer = cast(EntityRenderer, spy)
        try:
            window.menu.screen = Screen.GAME
            window.perspective_mode = PerspectiveMode.THIRD_PERSON_BACK
            window.switch_to()
            window.on_draw()
            window.mgl_context.finish()

            assert spy.shadow_worlds[0] is window.entities.world
            assert len(spy.shadow_worlds) == 2
            assert spy.shadow_worlds[1] is not window.entities.world
            assert spy.render_worlds == spy.shadow_worlds
        finally:
            window.entity_renderer = original_renderer
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


def test_transparent_foliage_scene_renders() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")

    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow
    from voxel_sandbox.tools.foliage_smoke_scene import apply_foliage_smoke_scene

    with tempfile.TemporaryDirectory(prefix="veilstone-foliage-smoke-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            scene = apply_foliage_smoke_scene(
                window.world_renderer.set_block,
                window.world_runtime.block_registry,
            )
            window.camera.position = scene.spawn_position

            registry = window.world_runtime.block_registry
            assert registry.by_key("veilwood_leaves").render_layer == "cutout"
            assert window.world_renderer.get_block(6, 4, 7) == registry.by_key("veilwood_leaves").id
            assert window.world_renderer.get_block(6, 4, 8) == registry.by_key("stone").id

            window.menu.screen = Screen.GAME
            window.switch_to()
            window.on_draw()
            window.mgl_context.finish()
        finally:
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
    from pyglet.window import key, mouse

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
            target_x, target_y = window._inv_ctrl._inventory_slot_position(1)
            window.on_mouse_press(slot_x + 24, slot_y + 24, mouse.LEFT, 0)
            window.on_mouse_drag(
                target_x + 24,
                target_y + 24,
                target_x - slot_x,
                target_y - slot_y,
                mouse.LEFT,
                0,
            )
            window.on_mouse_release(target_x + 24, target_y + 24, mouse.LEFT, 0)
            assert window.inventory[9] is None
            assert window.inventory[10] == ItemStack(3, 5)
            assert window.cursor_stack is None
            window.on_key_press(None, 0)
        finally:
            window.close()


def test_active_resource_pack_refreshes_existing_inventory_icon_sprites() -> None:
    import pyglet
    from PIL import Image

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from pyglet.window import key

    from voxel_sandbox.render.resource_pack_presentation import ResourcePackPresentationAdapter
    from voxel_sandbox.render.texture_packs.importer import load_active_block_atlas
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-inventory-pack-") as directory:
        root = Path(directory)
        pack = root / "contrast_pack"
        texture_root = pack / "assets" / "minecraft" / "textures" / "block"
        texture_root.mkdir(parents=True)
        (pack / "pack.mcmeta").write_text(
            '{"pack":{"pack_format":18,"description":"Inventory smoke"}}',
            encoding="utf-8",
        )
        Image.new("RGBA", (16, 16), (240, 40, 30, 255)).save(texture_root / "grass_block_top.png")
        Image.new("RGBA", (16, 16), (20, 220, 70, 255)).save(texture_root / "grass_block_side.png")
        window = GameWindow(AppSettings(), visible=False, save_root=root / "save")
        try:
            controller = window._inv_ctrl
            inventory = window.inventory
            grass_id = window.item_registry.by_key("grass_block").id
            old_icon = controller.item_icon_images[grass_id]
            old_hotbar_texture = controller.hotbar_icons[0].image
            atlas = load_active_block_atlas(
                pack,
                registry=window.world_runtime.block_registry,
                cache_root=root / "texture_cache",
            )

            ResourcePackPresentationAdapter(window.world_renderer, controller).apply_texture_pack(
                atlas
            )

            assert window._inv_ctrl is controller
            assert window.inventory is inventory
            assert controller.item_icon_images[grass_id] is not old_icon
            assert controller.hotbar_icons[0].image is not old_hotbar_texture
            window.menu.screen = Screen.GAME
            window.on_key_press(key.E, 0)
            window.on_draw()
            window.mgl_context.finish()
        finally:
            window.close()


def test_shift_click_crafting_result_quick_moves_all_valid_outputs() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from pyglet.window import key, mouse

    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-crafting-quick-move-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.on_key_press(key.E, 0)
            window.crafting_grid.set_index(0, ItemStack(4, 3))
            controller = vars(window)["_inv_ctrl"]
            result_x, result_y = controller._crafting_result_position()

            window.on_mouse_press(
                result_x + 28,
                result_y + 28,
                mouse.LEFT,
                key.MOD_SHIFT,
            )
            window.on_draw()
            window.mgl_context.finish()

            assert window.crafting_grid[0] is None
            assert window.inventory.count(9) == 12
            assert window.cursor_stack is None
            assert window.inventory_status == "Crafted Oak Planks x12 into inventory."
        finally:
            window.close()


def test_shift_click_crafting_input_preserves_partial_remainder() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from pyglet.window import key, mouse

    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-crafting-input-move-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.on_key_press(key.E, 0)
            window.inventory.set(0, ItemStack(4, 62), window.item_registry)
            for index in range(1, len(window.inventory)):
                window.inventory.set(index, ItemStack(1, 64), window.item_registry)
            window.crafting_grid.set_index(0, ItemStack(4, 5))
            controller = vars(window)["_inv_ctrl"]
            slot_x, slot_y = controller._crafting_slot_position(0)

            window.on_mouse_press(
                slot_x + 24,
                slot_y + 24,
                mouse.LEFT,
                key.MOD_SHIFT,
            )
            window.on_draw()
            window.mgl_context.finish()

            assert window.inventory[0] == ItemStack(4, 64)
            assert window.crafting_grid[0] == ItemStack(4, 3)
            assert window.cursor_stack is None
            assert window.inventory_status == "Moved Oak Log x2 to inventory."
        finally:
            window.close()


def test_right_drag_distributes_cursor_stack_across_distinct_inventory_slots() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from pyglet.window import key, mouse

    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-right-drag-distribution-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.on_key_press(key.E, 0)
            window.inventory.set(9, ItemStack(1, 6), window.item_registry)
            controller = vars(window)["_inv_ctrl"]
            source_x, source_y = controller._inventory_slot_position(0)
            targets = [controller._inventory_slot_position(index) for index in (1, 2, 1, 3)]

            window.on_mouse_press(source_x + 24, source_y + 24, mouse.RIGHT, 0)
            previous_x, previous_y = source_x + 24, source_y + 24
            for target_x, target_y in targets:
                x, y = target_x + 24, target_y + 24
                window.on_mouse_drag(
                    x,
                    y,
                    x - previous_x,
                    y - previous_y,
                    mouse.RIGHT,
                    0,
                )
                previous_x, previous_y = x, y
            window.on_mouse_release(previous_x, previous_y, mouse.RIGHT, 0)
            window.on_draw()
            window.mgl_context.finish()

            assert window.inventory[9] == ItemStack(1, 3)
            assert window.inventory[10] == ItemStack(1, 1)
            assert window.inventory[11] == ItemStack(1, 1)
            assert window.inventory[12] == ItemStack(1, 1)
            assert window.cursor_stack is None
        finally:
            window.close()


def test_left_drag_even_distribution_respects_mixed_target_capacity() -> None:
    import pyglet

    if not pyglet.display.get_display().get_screens():
        pytest.skip("OpenGL smoke requires an active display")
    from pyglet.window import key, mouse

    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    with tempfile.TemporaryDirectory(prefix="veilstone-left-drag-distribution-") as directory:
        window = GameWindow(AppSettings(), visible=False, save_root=Path(directory))
        try:
            window.menu.screen = Screen.GAME
            window.on_key_press(key.E, 0)
            window.inventory.set(9, ItemStack(1, 10), window.item_registry)
            window.inventory.set(10, ItemStack(1, 63), window.item_registry)
            window.inventory.set(11, ItemStack(2, 5), window.item_registry)
            controller = vars(window)["_inv_ctrl"]
            source = controller._inventory_slot_position(0)
            inventory_targets = {
                index: controller._inventory_slot_position(index) for index in (1, 2, 3)
            }
            crafting_target = controller._crafting_slot_position(0)
            targets = (
                inventory_targets[1],
                inventory_targets[2],
                crafting_target,
                inventory_targets[3],
                crafting_target,
            )

            previous_x, previous_y = source[0] + 24, source[1] + 24
            window.on_mouse_press(previous_x, previous_y, mouse.LEFT, 0)
            for target_x, target_y in targets:
                x, y = target_x + 24, target_y + 24
                window.on_mouse_drag(
                    x,
                    y,
                    x - previous_x,
                    y - previous_y,
                    mouse.LEFT,
                    0,
                )
                previous_x, previous_y = x, y
            window.on_mouse_release(previous_x, previous_y, mouse.LEFT, 0)
            window.on_draw()
            window.mgl_context.finish()

            assert window.inventory[9] is None
            assert window.inventory[10] == ItemStack(1, 64)
            assert window.inventory[11] == ItemStack(2, 5)
            assert window.inventory[12] == ItemStack(1, 3)
            assert window.crafting_grid[0] == ItemStack(1, 3)
            assert window.cursor_stack == ItemStack(1, 3)
            assert window.inventory_status == "Distributed Stone x7 across 3 slots."
        finally:
            window.close()
