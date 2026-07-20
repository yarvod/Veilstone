# pyright: reportPrivateUsage=false

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import Chunk, ChunkCoord
from voxel_sandbox.engine.lighting import effective_light_level, relight_chunk, relight_chunks
from voxel_sandbox.engine.lighting.propagation import _propagate_light
from voxel_sandbox.engine.perf.light_propagation import (
    NATIVE_LIGHT_PROPAGATION,
    propagate_light,
    python_propagate_light,
)


def _reference_propagate_light(
    sources: NDArray[np.uint8],
    opaque: NDArray[np.bool_],
) -> NDArray[np.uint8]:
    light = sources.copy()
    blocked = opaque & (sources == 0)
    for _ in range(15):
        attenuated = np.where(light > 0, light - 1, 0).astype(np.uint8)
        neighbors = np.zeros_like(light)
        neighbors[1:, :, :] = np.maximum(neighbors[1:, :, :], attenuated[:-1, :, :])
        neighbors[:-1, :, :] = np.maximum(neighbors[:-1, :, :], attenuated[1:, :, :])
        neighbors[:, 1:, :] = np.maximum(neighbors[:, 1:, :], attenuated[:, :-1, :])
        neighbors[:, :-1, :] = np.maximum(neighbors[:, :-1, :], attenuated[:, 1:, :])
        neighbors[:, :, 1:] = np.maximum(neighbors[:, :, 1:], attenuated[:, :, :-1])
        neighbors[:, :, :-1] = np.maximum(neighbors[:, :, :-1], attenuated[:, :, 1:])
        updated = np.maximum(sources, neighbors)
        updated[blocked] = 0
        if np.array_equal(updated, light):
            break
        light = updated
    return light


def test_skylight_blocks_opaque_roof_and_spreads_below_it() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    for x in range(2, 7):
        for z in range(2, 7):
            chunk.set_block(x, 20, z, 1)

    relight_chunk(chunk, create_core_block_registry())

    assert chunk.sections[2].sky_light[4, 15, 4] == 15
    assert chunk.sections[1].sky_light[4, 4, 4] == 0
    center_below = chunk.sections[1].sky_light[4, 3, 4]
    edge_below = chunk.sections[1].sky_light[2, 3, 4]
    assert 0 < center_below < edge_below < 15
    assert chunk.sections[0].sky_light[10, 10, 10] == 15


def test_cutout_leaf_roof_does_not_block_skylight() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    for x in range(2, 7):
        for z in range(2, 7):
            chunk.set_block(x, 20, z, 5)

    relight_chunk(chunk, create_core_block_registry())

    assert chunk.sections[1].sky_light[4, 3, 4] == 15


def test_lantern_light_propagates_and_is_blocked_by_stone() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    chunk.set_block(8, 8, 8, 7)
    chunk.set_block(9, 8, 8, 1)

    relight_chunk(chunk, create_core_block_registry())

    section = chunk.sections[0]
    assert section.block_light[8, 8, 8] == 14
    assert section.block_light[7, 8, 8] == 13
    assert section.block_light[9, 8, 8] == 0
    assert section.block_light[8, 8, 10] == 12


def test_removing_lantern_clears_stale_light() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    chunk.set_block(8, 8, 8, 7)
    registry = create_core_block_registry()
    relight_chunk(chunk, registry)
    chunk.set_block(8, 8, 8, 0)

    relight_chunk(chunk, registry)

    assert chunk.sections[0].block_light.max() == 0


def test_relighting_unchanged_chunk_does_not_report_mesh_work() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    registry = create_core_block_registry()

    assert relight_chunks((chunk,), registry) == (chunk,)
    assert relight_chunks((chunk,), registry) == ()


def test_block_light_propagates_across_loaded_chunk_boundary() -> None:
    left = Chunk(ChunkCoord(0, 0))
    right = Chunk(ChunkCoord(1, 0))
    left.set_block(15, 8, 8, 7)

    relight_chunks((left, right), create_core_block_registry())

    assert left.sections[0].block_light[15, 8, 8] == 14
    assert right.sections[0].block_light[0, 8, 8] == 13
    assert right.sections[0].block_light[1, 8, 8] == 12

    left.set_block(15, 8, 8, 0)
    relight_chunks((left, right), create_core_block_registry())

    assert left.sections[0].block_light.max() == 0
    assert right.sections[0].block_light.max() == 0


def test_effective_spawn_light_tracks_daylight_and_block_sources() -> None:
    assert effective_light_level(15, 0, 1.0) == 15
    assert effective_light_level(15, 0, 0.12) == 2
    assert effective_light_level(0, 10, 0.0) == 10


def test_light_propagation_empty_volume_matches_reference_without_mutating_inputs() -> None:
    sources = np.zeros((5, 7, 4), dtype=np.uint8)
    opaque = np.zeros_like(sources, dtype=np.bool_)
    opaque[1:4, 2:5, 1:3] = True
    source_before = sources.copy()
    opaque_before = opaque.copy()

    actual = _propagate_light(sources, opaque)

    np.testing.assert_array_equal(actual, _reference_propagate_light(sources, opaque))
    assert actual.dtype == np.uint8
    assert actual is not sources
    np.testing.assert_array_equal(sources, source_before)
    np.testing.assert_array_equal(opaque, opaque_before)
    actual[0, 0, 0] = 9
    assert sources[0, 0, 0] == 0


def test_light_propagation_randomized_volumes_match_reference() -> None:
    random = np.random.default_rng(20260711)
    for _ in range(12):
        sources = np.zeros((7, 9, 6), dtype=np.uint8)
        source_mask = random.random(sources.shape) < 0.04
        sources[source_mask] = random.integers(1, 16, size=np.count_nonzero(source_mask))
        opaque = random.random(sources.shape) < 0.22

        actual = _propagate_light(sources, opaque)
        expected = _reference_propagate_light(sources, opaque)

        np.testing.assert_array_equal(actual, expected)


def test_selected_light_propagation_matches_python_for_dense_sources() -> None:
    sources = np.full((6, 8, 5), 15, dtype=np.uint8)
    opaque = np.zeros_like(sources, dtype=np.bool_)
    opaque[2:4, 2:6, 1:4] = True

    np.testing.assert_array_equal(
        propagate_light(sources, opaque),
        python_propagate_light(sources, opaque),
    )


def test_light_backend_state_keeps_optional_native_fallback() -> None:
    assert isinstance(NATIVE_LIGHT_PROPAGATION, bool)
