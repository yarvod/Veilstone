from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.tools.gameplay_smoke_screenshot import (
    build_smoke_metadata,
    write_smoke_metadata,
)


def test_gameplay_smoke_metadata_records_runtime_summary(tmp_path: Path) -> None:
    settings = AppSettings()
    settings = replace(
        settings,
        world=replace(settings.world, seed="smoke-seed", render_distance=4),
        graphics=replace(settings.graphics, resource_pack_path="/packs/Faithful.zip"),
    )
    screenshot = tmp_path / "smoke.png"

    metadata = build_smoke_metadata(
        screenshot=screenshot,
        settings=settings,
        frames=12,
        start_position=(8.5, 88.0, 8.5),
        end_position=(8.5, 88.0, 7.5),
        queue_summary={"visible_sections": 8, "loaded_chunks": 9},
    )

    assert metadata.screenshot == str(screenshot)
    assert metadata.seed == "smoke-seed"
    assert metadata.render_distance == 4
    assert metadata.resource_pack == "Faithful"
    assert metadata.frames == 12
    assert metadata.moved_distance == 1.0
    assert metadata.queue_summary == {"loaded_chunks": 9, "visible_sections": 8}


def test_gameplay_smoke_metadata_writes_json(tmp_path: Path) -> None:
    metadata = build_smoke_metadata(
        screenshot=tmp_path / "smoke.png",
        settings=AppSettings(),
        frames=1,
        start_position=(0.0, 0.0, 0.0),
        end_position=(0.0, 0.0, 0.0),
        queue_summary={},
    )
    metadata_path = tmp_path / "smoke.json"

    write_smoke_metadata(metadata_path, metadata)

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["resource_pack"] == "Default"
    assert payload["debug_overlay_enabled"] is True
    assert payload["display_status"] == "available"
