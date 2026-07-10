from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.tools.reference_gameplay_scene import (
    ReferenceGameplayScene,
    build_reference_gameplay_scene,
)
from voxel_sandbox.tools.reference_gameplay_screenshot import (
    RenderedReferenceMetadata,
    apply_reference_render_layout,
    build_reference_render_layout,
    camera_angles,
    reference_capture_settings,
    reference_scene_chunks,
    validate_rendered_reference_metadata,
    write_rendered_reference_metadata,
)


def _valid_metadata() -> tuple[RenderedReferenceMetadata, ReferenceGameplayScene]:
    scene = build_reference_gameplay_scene(seed=42)
    layout = build_reference_render_layout(scene, base_y=96)
    metadata = RenderedReferenceMetadata(
        scene_key=scene.key,
        seed=scene.seed,
        screenshot="screenshots/reference.png",
        display_status="available",
        resource_pack="default",
        render_distance=2,
        camera_mode="isometric",
        base_y=layout.base_y,
        camera_position=layout.camera_position,
        look_at=layout.look_at,
        block_count=len(scene.blocks),
        block_counts={
            "crafting_table": 1,
            "gloam_lantern": 1,
            "grass": 99,
            "oak_leaves": 25,
            "oak_log": 4,
            "short_grass": 1,
            "stone": 16,
            "water": 12,
            "wildflower": 1,
        },
        placed_block_count=len(scene.blocks),
        expected_chunks=1,
        rebuilt_chunks=1,
        visible_sections=3,
        water_mesh_sections=1,
        water_mesh_triangles=24,
    )
    return metadata, scene


def test_reference_render_layout_offsets_fixture_without_mutating_it() -> None:
    scene = build_reference_gameplay_scene()
    original = scene.blocks[0]

    layout = build_reference_render_layout(scene, base_y=96)

    assert original.position[1] == 3
    assert layout.blocks[0].position[1] == 96
    assert len(layout.blocks) == len(scene.blocks)
    assert layout.camera_position != layout.look_at
    assert len(reference_scene_chunks(layout)) == 1


def test_reference_render_layout_applies_every_block() -> None:
    scene = build_reference_gameplay_scene()
    layout = build_reference_render_layout(scene, base_y=96)
    placed: list[tuple[tuple[int, int, int], int]] = []

    changed = apply_reference_render_layout(
        layout,
        set_block=lambda position, block_id: placed.append((position, block_id)) or True,
        registry=create_core_block_registry(),
    )

    assert changed == len(scene.blocks)
    assert len(placed) == len(scene.blocks)


def test_reference_camera_angles_target_scene_center() -> None:
    yaw, pitch = camera_angles((1.0, 107.0, 0.5), (9.0, 98.0, 8.0))

    assert math.isclose(yaw, 43.15, abs_tol=0.01)
    assert math.isclose(pitch, -39.38, abs_tol=0.01)


def test_reference_capture_settings_are_deterministic() -> None:
    settings = reference_capture_settings(
        AppSettings(),
        seed=42,
        render_distance=3,
        resource_pack="default",
    )

    assert settings.world.seed == "42"
    assert settings.world.render_distance == 3
    assert settings.world.generation_backend == "thread"
    assert settings.graphics.day_cycle_seconds == 0.0
    assert settings.graphics.resource_pack_path is None
    assert settings.graphics.clouds is False


def test_rendered_reference_metadata_validates_and_writes(tmp_path: Path) -> None:
    metadata, scene = _valid_metadata()

    validated = validate_rendered_reference_metadata(metadata, scene)
    path = tmp_path / "reference.json"
    write_rendered_reference_metadata(path, validated)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["block_count"] == 160
    assert payload["placed_block_count"] == 160
    assert payload["water_mesh_triangles"] == 24
    assert payload["invariants_passed"] is True


def test_rendered_reference_metadata_rejects_missing_blocks() -> None:
    metadata, scene = _valid_metadata()

    with pytest.raises(ValueError, match="place every fixture block"):
        validate_rendered_reference_metadata(
            replace(metadata, placed_block_count=159),
            scene,
        )


def test_reference_screenshot_skips_successfully_without_display(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import pyglet

    from voxel_sandbox.tools.reference_gameplay_screenshot import (
        run_reference_gameplay_screenshot,
    )

    def no_screens() -> list[object]:
        return []

    monkeypatch.setattr(
        pyglet.display,
        "get_display",
        lambda: SimpleNamespace(get_screens=no_screens),
    )

    assert run_reference_gameplay_screenshot(AppSettings()) == 0
    assert capsys.readouterr().out == (
        "reference-gameplay-screenshot: skipped (no active display)\n"
    )
