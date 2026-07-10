from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.domain.items import ItemStack


class InventorySmokeScenario(StrEnum):
    ICONS = "icons"
    CRAFTING_RESULT = "crafting-result"
    CRAFTING_INPUT = "crafting-input"
    RIGHT_DRAG = "right-drag"
    LEFT_DRAG = "left-drag"
    RIGHT_CLICK_SPLIT = "right-click-split"


@dataclass(frozen=True, slots=True)
class InventorySmokeResult:
    source_count: int
    target_counts: tuple[int, ...]
    cursor_count: int
    crafting_input_count: int
    crafting_result_count: int
    observed_item_id: int
    inventory_item_count: int
    icon_count: int = 0
    refreshed_icon_count: int = 0
    inventory_identity_preserved: bool = True
    controller_identity_preserved: bool = True
    action_status: str = ""


@dataclass(frozen=True, slots=True)
class InventorySmokeMetadata:
    scenario: str
    display_status: str
    screenshot: str
    source_count: int
    target_counts: tuple[int, ...]
    cursor_count: int
    crafting_input_count: int
    crafting_result_count: int
    observed_item_id: int
    inventory_item_count: int
    icon_count: int
    refreshed_icon_count: int
    inventory_identity_preserved: bool
    controller_identity_preserved: bool
    action_status: str
    invariants_passed: bool = False


@dataclass(frozen=True, slots=True)
class _ExpectedResult:
    source_count: int
    target_counts: tuple[int, ...]
    cursor_count: int
    crafting_input_count: int
    crafting_result_count: int
    observed_item_id: int
    inventory_item_count: int
    action_status: str


_EXPECTED_RESULTS: dict[InventorySmokeScenario, _ExpectedResult] = {
    InventorySmokeScenario.CRAFTING_RESULT: _ExpectedResult(
        source_count=0,
        target_counts=(),
        cursor_count=0,
        crafting_input_count=0,
        crafting_result_count=0,
        observed_item_id=9,
        inventory_item_count=12,
        action_status="Crafted Oak Planks x12 into inventory.",
    ),
    InventorySmokeScenario.CRAFTING_INPUT: _ExpectedResult(
        source_count=0,
        target_counts=(),
        cursor_count=0,
        crafting_input_count=0,
        crafting_result_count=0,
        observed_item_id=4,
        inventory_item_count=5,
        action_status="Moved Oak Log x5 to inventory.",
    ),
    InventorySmokeScenario.RIGHT_DRAG: _ExpectedResult(
        source_count=3,
        target_counts=(1, 1, 1),
        cursor_count=0,
        crafting_input_count=0,
        crafting_result_count=0,
        observed_item_id=1,
        inventory_item_count=6,
        action_status="",
    ),
    InventorySmokeScenario.LEFT_DRAG: _ExpectedResult(
        source_count=0,
        target_counts=(64, 5, 3),
        cursor_count=3,
        crafting_input_count=3,
        crafting_result_count=0,
        observed_item_id=1,
        inventory_item_count=67,
        action_status="Distributed Stone x7 across 3 slots.",
    ),
    InventorySmokeScenario.RIGHT_CLICK_SPLIT: _ExpectedResult(
        source_count=2,
        target_counts=(),
        cursor_count=3,
        crafting_input_count=0,
        crafting_result_count=0,
        observed_item_id=1,
        inventory_item_count=2,
        action_status="",
    ),
}


def build_inventory_smoke_metadata(
    *,
    scenario: InventorySmokeScenario | str,
    screenshot: Path,
    result: InventorySmokeResult,
    display_status: str = "available",
) -> InventorySmokeMetadata:
    scenario = InventorySmokeScenario(scenario)
    return InventorySmokeMetadata(
        scenario=scenario.value,
        display_status=display_status,
        screenshot=str(screenshot),
        **asdict(result),
    )


def validate_inventory_smoke_metadata(
    metadata: InventorySmokeMetadata,
) -> InventorySmokeMetadata:
    scenario = InventorySmokeScenario(metadata.scenario)
    if metadata.display_status != "available":
        raise ValueError("Inventory smoke metadata requires an available display")
    if not metadata.screenshot:
        raise ValueError("Inventory smoke metadata requires a screenshot path")
    if not metadata.inventory_identity_preserved:
        raise ValueError("Inventory identity changed during smoke scenario")
    if not metadata.controller_identity_preserved:
        raise ValueError("Inventory controller identity changed during smoke scenario")

    if scenario is InventorySmokeScenario.ICONS:
        if metadata.source_count != 1 or metadata.observed_item_id <= 0:
            raise ValueError("Icon scenario did not retain its visible inventory item")
        if metadata.inventory_item_count != 1 or metadata.target_counts:
            raise ValueError("Icon scenario inventory counts are invalid")
        if metadata.cursor_count or metadata.crafting_input_count or metadata.crafting_result_count:
            raise ValueError("Icon scenario unexpectedly changed carried or crafting items")
        if metadata.icon_count <= 0 or metadata.refreshed_icon_count != 1:
            raise ValueError("Resource-pack icon refresh was not observed")
        if not metadata.action_status:
            raise ValueError("Resource-pack icon scenario has no action status")
    else:
        expected = _EXPECTED_RESULTS[scenario]
        actual = (
            metadata.source_count,
            metadata.target_counts,
            metadata.cursor_count,
            metadata.crafting_input_count,
            metadata.crafting_result_count,
            metadata.observed_item_id,
            metadata.inventory_item_count,
            metadata.action_status,
        )
        wanted = (
            expected.source_count,
            expected.target_counts,
            expected.cursor_count,
            expected.crafting_input_count,
            expected.crafting_result_count,
            expected.observed_item_id,
            expected.inventory_item_count,
            expected.action_status,
        )
        if actual != wanted:
            raise ValueError(f"Inventory smoke invariant mismatch for {scenario.value}")
        if metadata.icon_count or metadata.refreshed_icon_count:
            raise ValueError("Non-icon scenario unexpectedly reported icon refreshes")
    return replace(metadata, invariants_passed=True)


def write_inventory_smoke_metadata(path: Path, metadata: InventorySmokeMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_inventory_interaction_smoke(
    settings: AppSettings,
    *,
    scenario: InventorySmokeScenario | str = InventorySmokeScenario.ICONS,
    output_dir: Path | None = None,
) -> int:
    import pyglet

    scenario = InventorySmokeScenario(scenario)
    if not pyglet.display.get_display().get_screens():
        print("inventory-interaction-smoke: skipped (no active display)")
        return 0

    from voxel_sandbox.app.composition import UserSettingsStore, build_app_runtime
    from voxel_sandbox.render.ui.menu import Screen
    from voxel_sandbox.render.window import GameWindow

    root = output_dir or Path("saves/inventory_interaction_smoke") / scenario.value
    root.mkdir(parents=True, exist_ok=True)
    run_settings = replace(
        settings,
        world=replace(
            settings.world,
            generation_backend="thread",
            meshing_backend="thread",
        ),
    )
    app_runtime = build_app_runtime(
        run_settings,
        data_root=root,
        settings_store=UserSettingsStore(root / "settings.toml"),
    )
    with tempfile.TemporaryDirectory(
        prefix="veilstone-inventory-smoke-world-",
        dir=root,
    ) as world_directory:
        window = GameWindow(
            run_settings,
            visible=False,
            save_root=Path(world_directory),
            app_runtime=app_runtime,
        )
        try:
            window.switch_to()
            window.menu.screen = Screen.GAME
            result = _run_scenario(window, scenario, root)
            window.on_draw()
            window.mgl_context.finish()
            screenshot = window.save_screenshot()
            metadata = validate_inventory_smoke_metadata(
                build_inventory_smoke_metadata(
                    scenario=scenario,
                    screenshot=screenshot,
                    result=result,
                )
            )
            metadata_path = root / "inventory_interaction_smoke.json"
            write_inventory_smoke_metadata(metadata_path, metadata)
            print(f"scenario={scenario.value}")
            print(f"screenshot={screenshot}")
            print(f"metadata={metadata_path}")
        finally:
            window.close()
    return 0


def _run_scenario(
    window: Any, scenario: InventorySmokeScenario, root: Path
) -> InventorySmokeResult:
    from pyglet.window import key

    inventory = window.inventory
    controller = window._inv_ctrl
    window.on_key_press(key.E, 0)
    if not window.inventory_open:
        raise RuntimeError("Inventory smoke could not open the inventory through input routing")

    if scenario is InventorySmokeScenario.ICONS:
        result = _run_icon_scenario(window, root)
    elif scenario is InventorySmokeScenario.CRAFTING_RESULT:
        result = _run_crafting_result_scenario(window)
    elif scenario is InventorySmokeScenario.CRAFTING_INPUT:
        result = _run_crafting_input_scenario(window)
    elif scenario is InventorySmokeScenario.RIGHT_DRAG:
        result = _run_right_drag_scenario(window)
    elif scenario is InventorySmokeScenario.LEFT_DRAG:
        result = _run_left_drag_scenario(window)
    else:
        result = _run_right_click_split_scenario(window)
    return replace(
        result,
        inventory_identity_preserved=window.inventory is inventory,
        controller_identity_preserved=window._inv_ctrl is controller,
    )


def _run_icon_scenario(window: Any, root: Path) -> InventorySmokeResult:
    from PIL import Image

    grass_id = window.item_registry.by_key("grass_block").id
    window.inventory.set(9, ItemStack(grass_id, 1), window.item_registry)
    old_icon = window._inv_ctrl.item_icon_images[grass_id]
    pack = root / "contrast_pack"
    texture_root = pack / "assets" / "minecraft" / "textures" / "block"
    texture_root.mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        '{"pack":{"pack_format":18,"description":"Inventory smoke"}}\n',
        encoding="utf-8",
    )
    Image.new("RGBA", (16, 16), (240, 40, 30, 255)).save(texture_root / "grass_block_top.png")
    Image.new("RGBA", (16, 16), (20, 220, 70, 255)).save(texture_root / "grass_block_side.png")
    window._gameplay.execute_command(f"/resourcepack {pack}")
    refreshed = window._inv_ctrl.item_icon_images[grass_id] is not old_icon
    return InventorySmokeResult(
        source_count=_stack_count(window.inventory[9]),
        target_counts=(),
        cursor_count=_stack_count(window.cursor_stack),
        crafting_input_count=_stack_count(window.crafting_grid[0]),
        crafting_result_count=_stack_count(window._inv_ctrl.crafting_result_stack()),
        observed_item_id=grass_id,
        inventory_item_count=window.inventory.count(grass_id),
        icon_count=len(window._inv_ctrl.item_icon_images),
        refreshed_icon_count=int(refreshed),
        action_status=window.inventory_status,
    )


def _run_crafting_result_scenario(window: Any) -> InventorySmokeResult:
    from pyglet.window import key, mouse

    window.crafting_grid.set_index(0, ItemStack(4, 3))
    x, y = _slot_center(window._inv_ctrl._crafting_result_position(), 28)
    window.on_mouse_press(x, y, mouse.LEFT, key.MOD_SHIFT)
    return _interaction_result(window, item_id=9, source=window.crafting_grid[0])


def _run_crafting_input_scenario(window: Any) -> InventorySmokeResult:
    from pyglet.window import key, mouse

    window.crafting_grid.set_index(0, ItemStack(4, 5))
    x, y = _slot_center(window._inv_ctrl._crafting_slot_position(0))
    window.on_mouse_press(x, y, mouse.LEFT, key.MOD_SHIFT)
    return _interaction_result(window, item_id=4, source=window.crafting_grid[0])


def _run_right_drag_scenario(window: Any) -> InventorySmokeResult:
    from pyglet.window import mouse

    window.inventory.set(9, ItemStack(1, 6), window.item_registry)
    source = _slot_center(window._inv_ctrl._inventory_slot_position(0))
    targets = tuple(
        _slot_center(window._inv_ctrl._inventory_slot_position(index)) for index in (1, 2, 3)
    )
    _drag(window, source, targets, mouse.RIGHT)
    return _interaction_result(
        window,
        item_id=1,
        source=window.inventory[9],
        targets=tuple(window.inventory[index] for index in (10, 11, 12)),
    )


def _run_left_drag_scenario(window: Any) -> InventorySmokeResult:
    from pyglet.window import mouse

    window.inventory.set(9, ItemStack(1, 10), window.item_registry)
    window.inventory.set(10, ItemStack(1, 63), window.item_registry)
    window.inventory.set(11, ItemStack(2, 5), window.item_registry)
    source = _slot_center(window._inv_ctrl._inventory_slot_position(0))
    inventory_targets = tuple(
        _slot_center(window._inv_ctrl._inventory_slot_position(index)) for index in (1, 2, 3)
    )
    crafting_target = _slot_center(window._inv_ctrl._crafting_slot_position(0))
    _drag(
        window,
        source,
        (
            inventory_targets[0],
            inventory_targets[1],
            crafting_target,
            inventory_targets[2],
            crafting_target,
        ),
        mouse.LEFT,
    )
    return _interaction_result(
        window,
        item_id=1,
        source=window.inventory[9],
        targets=tuple(window.inventory[index] for index in (10, 11, 12)),
    )


def _run_right_click_split_scenario(window: Any) -> InventorySmokeResult:
    from pyglet.window import mouse

    window.inventory.set(9, ItemStack(1, 5), window.item_registry)
    x, y = _slot_center(window._inv_ctrl._inventory_slot_position(0))
    window.on_mouse_press(x, y, mouse.RIGHT, 0)
    return _interaction_result(window, item_id=1, source=window.inventory[9])


def _interaction_result(
    window: Any,
    *,
    item_id: int,
    source: ItemStack | None,
    targets: tuple[ItemStack | None, ...] = (),
) -> InventorySmokeResult:
    return InventorySmokeResult(
        source_count=_stack_count(source),
        target_counts=tuple(_stack_count(stack) for stack in targets),
        cursor_count=_stack_count(window.cursor_stack),
        crafting_input_count=_stack_count(window.crafting_grid[0]),
        crafting_result_count=_stack_count(window._inv_ctrl.crafting_result_stack()),
        observed_item_id=item_id,
        inventory_item_count=window.inventory.count(item_id),
        action_status=window.inventory_status,
    )


def _drag(
    window: Any, source: tuple[int, int], targets: tuple[tuple[int, int], ...], button: int
) -> None:
    window.on_mouse_press(*source, button, 0)
    previous_x, previous_y = source
    for x, y in targets:
        window.on_mouse_drag(x, y, x - previous_x, y - previous_y, button, 0)
        previous_x, previous_y = x, y
    window.on_mouse_release(previous_x, previous_y, button, 0)


def _slot_center(position: tuple[int, int], offset: int = 24) -> tuple[int, int]:
    return position[0] + offset, position[1] + offset


def _stack_count(stack: ItemStack | None) -> int:
    return stack.count if stack is not None else 0
