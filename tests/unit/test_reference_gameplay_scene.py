from __future__ import annotations

import json
from pathlib import Path

import pytest

from voxel_sandbox.__main__ import main
from voxel_sandbox.tools.reference_gameplay_scene import (
    build_capture_metadata,
    build_reference_gameplay_scene,
    summarize_reference_gameplay_scene,
    write_capture_metadata,
)


def test_reference_gameplay_scene_covers_core_visual_features() -> None:
    scene = build_reference_gameplay_scene(seed=42)
    block_keys = {block.block_key for block in scene.blocks}

    assert scene.seed == 42
    assert "water" in block_keys
    assert "oak_leaves" in block_keys
    assert "gloam_lantern" in block_keys
    assert len(scene.mobs) == 2
    assert len(scene.inventory_icons) == 5
    assert scene.first_person_interaction.interaction == "place"
    assert set(scene.features) == {
        "water",
        "foliage",
        "lighting",
        "mob_movement",
        "inventory_icons",
        "first_person_interaction",
    }


def test_reference_gameplay_scene_summary_is_numeric_and_deterministic() -> None:
    scene = build_reference_gameplay_scene()

    summary = summarize_reference_gameplay_scene(scene)

    assert summary.block_count == len(scene.blocks)
    assert summary.block_counts["grass"] == 99
    assert summary.block_counts["water"] == 12
    assert summary.block_counts["oak_leaves"] == 25
    assert summary.mob_count == 2
    assert summary.inventory_icon_count == 5


def test_reference_capture_metadata_writes_sidecar(tmp_path: Path) -> None:
    scene = build_reference_gameplay_scene(seed=7)
    metadata = build_capture_metadata(
        scene,
        resource_pack="default",
        render_distance=4,
        settings_profile="ci-reference",
    )
    path = tmp_path / "reference_scene.json"

    write_capture_metadata(path, metadata)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["scene_key"] == "reference_gameplay_snapshot"
    assert payload["seed"] == 7
    assert payload["resource_pack"] == "default"
    assert payload["render_distance"] == 4
    assert payload["settings_profile"] == "ci-reference"
    assert payload["camera_mode"] == "isometric"
    assert payload["summary"]["block_counts"]["crafting_table"] == 1


def test_reference_gameplay_scene_cli_writes_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = tmp_path / "capture.json"

    assert (
        main(
            [
                "reference-gameplay-scene",
                "--metadata",
                str(metadata),
                "--seed",
                "99",
                "--resource-pack",
                "faithful",
                "--render-distance",
                "2",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    assert "scene=reference_gameplay_snapshot seed=99" in output
    assert (
        "features=water,foliage,lighting,mob_movement,inventory_icons,first_person_interaction"
        in output
    )
    assert payload["seed"] == 99
    assert payload["resource_pack"] == "faithful"
    assert payload["render_distance"] == 2
