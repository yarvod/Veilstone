from __future__ import annotations

import pytest

from voxel_sandbox.__main__ import main
from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.tools.foliage_smoke_scene import (
    apply_foliage_smoke_scene,
    build_foliage_smoke_scene,
    run_preview,
)


def test_foliage_smoke_scene_places_cutout_leaves_before_opaque_backdrop() -> None:
    registry = create_core_block_registry()
    scene = build_foliage_smoke_scene(registry)
    occupied = {block.position: block.block_key for block in scene.blocks}

    leaves = registry.by_key("veilwood_leaves")
    assert leaves.render_layer == "cutout"
    assert not leaves.is_opaque

    leaf_positions = {position for position, key in occupied.items() if key == "veilwood_leaves"}
    assert len(leaf_positions) == 25
    for x, y, z in leaf_positions:
        backdrop = registry.by_key(occupied[(x, y, z + 1)])
        assert backdrop.is_opaque
        assert backdrop.render_layer == "opaque"


def test_foliage_smoke_scene_applies_registry_ids() -> None:
    registry = create_core_block_registry()
    placed: dict[tuple[int, int, int], int] = {}

    scene = apply_foliage_smoke_scene(placed.__setitem__, registry)

    assert scene.key == "foliage_cutout_smoke"
    assert placed[(8, 8, 6)] == registry.by_key("gloam_lantern").id
    assert placed[(6, 4, 7)] == registry.by_key("veilwood_leaves").id
    assert placed[(6, 4, 8)] == registry.by_key("stone").id


def test_foliage_smoke_scene_preview_prints_manual_scene(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_preview() == 0

    output = capsys.readouterr().out
    assert "foliage_cutout_smoke spawn=" in output
    assert "look_at=" in output
    assert "layer y=8" in output
    assert "leaf holes reveal the stone backdrop" in output


def test_foliage_smoke_scene_cli_command_is_registered(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["foliage-smoke-scene"]) == 0
    assert "foliage_cutout_smoke" in capsys.readouterr().out
