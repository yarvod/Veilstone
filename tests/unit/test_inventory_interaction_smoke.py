from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.tools.inventory_interaction_smoke import (
    InventorySmokeResult,
    InventorySmokeScenario,
    build_inventory_smoke_metadata,
    validate_inventory_smoke_metadata,
    write_inventory_smoke_metadata,
)


@pytest.mark.parametrize(
    ("scenario", "result"),
    [
        (
            InventorySmokeScenario.ICONS,
            InventorySmokeResult(
                source_count=1,
                target_counts=(),
                cursor_count=0,
                crafting_input_count=0,
                crafting_result_count=0,
                observed_item_id=3,
                inventory_item_count=1,
                icon_count=12,
                refreshed_icon_count=1,
                action_status="Applied resource pack: contrast_pack",
            ),
        ),
        (
            InventorySmokeScenario.CRAFTING_RESULT,
            InventorySmokeResult(
                0, (), 0, 0, 0, 9, 12, action_status="Crafted Oak Planks x12 into inventory."
            ),
        ),
        (
            InventorySmokeScenario.CRAFTING_INPUT,
            InventorySmokeResult(
                0, (), 0, 0, 0, 4, 5, action_status="Moved Oak Log x5 to inventory."
            ),
        ),
        (
            InventorySmokeScenario.RIGHT_DRAG,
            InventorySmokeResult(3, (1, 1, 1), 0, 0, 0, 1, 6),
        ),
        (
            InventorySmokeScenario.LEFT_DRAG,
            InventorySmokeResult(
                0,
                (64, 5, 3),
                3,
                3,
                0,
                1,
                67,
                action_status="Distributed Stone x7 across 3 slots.",
            ),
        ),
        (
            InventorySmokeScenario.RIGHT_CLICK_SPLIT,
            InventorySmokeResult(2, (), 3, 0, 0, 1, 2),
        ),
    ],
)
def test_inventory_smoke_scenario_metadata_validates(
    scenario: InventorySmokeScenario,
    result: InventorySmokeResult,
) -> None:
    metadata = build_inventory_smoke_metadata(
        scenario=scenario,
        screenshot=Path("screenshots/inventory.png"),
        result=result,
    )

    validated = validate_inventory_smoke_metadata(metadata)

    assert validated.scenario == scenario.value
    assert validated.invariants_passed


def test_inventory_smoke_validation_rejects_count_drift() -> None:
    metadata = build_inventory_smoke_metadata(
        scenario=InventorySmokeScenario.RIGHT_CLICK_SPLIT,
        screenshot=Path("screenshots/inventory.png"),
        result=InventorySmokeResult(2, (), 3, 0, 0, 1, 2),
    )

    with pytest.raises(ValueError, match="invariant mismatch"):
        validate_inventory_smoke_metadata(replace(metadata, cursor_count=2))


def test_inventory_smoke_metadata_writer_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"
    metadata = validate_inventory_smoke_metadata(
        build_inventory_smoke_metadata(
            scenario=InventorySmokeScenario.RIGHT_CLICK_SPLIT,
            screenshot=Path("screenshots/inventory.png"),
            result=InventorySmokeResult(2, (), 3, 0, 0, 1, 2),
        )
    )

    write_inventory_smoke_metadata(path, metadata)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["source_count"] == 2
    assert payload["cursor_count"] == 3
    assert payload["target_counts"] == []
    assert payload["invariants_passed"] is True
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_inventory_smoke_skips_successfully_without_display(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import pyglet

    from voxel_sandbox.tools.inventory_interaction_smoke import run_inventory_interaction_smoke

    def no_screens() -> list[object]:
        return []

    monkeypatch.setattr(
        pyglet.display,
        "get_display",
        lambda: SimpleNamespace(get_screens=no_screens),
    )

    assert run_inventory_interaction_smoke(AppSettings()) == 0
    assert capsys.readouterr().out == ("inventory-interaction-smoke: skipped (no active display)\n")
