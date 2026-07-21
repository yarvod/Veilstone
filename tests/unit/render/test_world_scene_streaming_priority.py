# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false

from __future__ import annotations

from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any, cast

import moderngl
import pytest

from voxel_sandbox.engine.chunks import (
    CHUNK_HEIGHT,
    SECTION_SIZE,
    Chunk,
    ChunkCoord,
    SectionCoord,
)
from voxel_sandbox.engine.fluids import WATER_BLOCK_ID, FluidUpdate
from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.texture_atlas import GeneratedAtlas
from voxel_sandbox.render.world_scene import (
    DemoWorldRenderer,
    _atlas_tile_margin,
    _configure_block_texture,
    _outside_fog_range,
)


class _FakeTexture:
    def __init__(self) -> None:
        self.filter: tuple[int, int] | None = None
        self.repeat_x = True
        self.repeat_y = True
        self.mipmap_levels: list[int] = []

    def build_mipmaps(self, *, max_level: int) -> None:
        self.mipmap_levels.append(max_level)


class _MeshWorkerSpy:
    def __init__(self) -> None:
        self.invalidated: list[tuple[int, int]] = []

    def invalidate_chunk(self, x: int, z: int) -> None:
        self.invalidated.append((x, z))


class _MeshCacheSpy:
    def __init__(self) -> None:
        self.removals: list[tuple[SectionCoord, ...]] = []

    def remove_many(self, keys: Iterable[SectionCoord]) -> None:
        self.removals.append(tuple(keys))


def test_world_texture_smooths_minification_but_keeps_nearest_magnification() -> None:
    texture = _FakeTexture()

    _configure_block_texture(cast(Any, texture))

    assert texture.filter == (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.NEAREST)
    assert texture.mipmap_levels == [1]
    assert texture.repeat_x is False
    assert texture.repeat_y is False


def test_world_texture_keeps_nearest_sampling_for_low_end_profile() -> None:
    texture = _FakeTexture()

    _configure_block_texture(cast(Any, texture), linear_minification=False)

    assert texture.filter == (moderngl.NEAREST, moderngl.NEAREST)
    assert texture.mipmap_levels == []
    assert texture.repeat_x is False
    assert texture.repeat_y is False


def test_world_scene_applies_texture_minification_to_color_and_material_maps() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    renderer.texture = cast(Any, _FakeTexture())
    material_texture = _FakeTexture()
    renderer.material_atlas_textures = {
        MaterialMapRole.NORMAL: cast(Any, SimpleNamespace(texture=material_texture))
    }

    renderer.apply_texture_minification(False)

    assert renderer.linear_texture_minification is False
    assert renderer.texture.filter == (moderngl.NEAREST, moderngl.NEAREST)
    assert material_texture.filter == (moderngl.NEAREST, moderngl.NEAREST)
    assert renderer.texture.mipmap_levels == []
    assert material_texture.mipmap_levels == []


def test_world_scene_terrain_height_uses_floored_world_coordinates() -> None:
    def height_at(x: int, z: int) -> int:
        return x * 100 + z

    renderer = object.__new__(DemoWorldRenderer)
    renderer._generator = cast(
        Any,
        SimpleNamespace(height_at=height_at),
    )

    assert renderer.terrain_height_at(8.9, -2.1) == 797.0


def test_fluid_neighborhood_activates_only_loaded_water_chunks() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    center = Chunk(ChunkCoord(0, 0))
    east = Chunk(ChunkCoord(1, 0))
    center.set_block(8, 1, 8, WATER_BLOCK_ID)
    east.set_block(8, 1, 8, WATER_BLOCK_ID)
    chunks = {center.coord: center, east.coord: east}
    renderer._streamer = cast(Any, SimpleNamespace(get_chunk=chunks.get))
    renderer._fluid_active_chunks = set()

    renderer._activate_fluid_neighborhood((center.coord,))

    assert renderer._fluid_active_chunks == {center.coord, east.coord}


def test_fluid_neighborhood_skips_loaded_dry_chunks() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    center = Chunk(ChunkCoord(0, 0))
    renderer._streamer = cast(Any, SimpleNamespace(get_chunk={center.coord: center}.get))
    renderer._fluid_active_chunks = set()

    renderer._activate_fluid_neighborhood((center.coord,))

    assert renderer._fluid_active_chunks == set()


def test_stream_work_horizon_keeps_rd12_loaded_but_queues_only_fog_range() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    relight_edge = Chunk(ChunkCoord(1, 0))
    visible_edge = Chunk(ChunkCoord(4, 0))
    fogged_corner = Chunk(ChunkCoord(4, 4))
    prefetched = Chunk(ChunkCoord(5, 0))
    chunks = {
        chunk.coord: chunk for chunk in (relight_edge, visible_edge, fogged_corner, prefetched)
    }
    renderer._streamer = cast(
        Any,
        SimpleNamespace(render_distance=12, get_chunk=chunks.get),
    )
    renderer.fog_enabled = True
    renderer.fog_end = 56.0
    renderer._stream_mesh_active = set()
    renderer._stream_relight_active = set()
    renderer._stream_relight_queue = {}
    renderer._stream_remesh_queue = {}

    renderer._refresh_stream_work_horizon(ChunkCoord(0, 0))

    assert visible_edge.coord in renderer._stream_mesh_active
    assert fogged_corner.coord not in renderer._stream_mesh_active
    assert prefetched.coord not in renderer._stream_mesh_active
    assert renderer._stream_relight_queue == {relight_edge.coord: None}
    assert renderer._stream_remesh_queue == {
        relight_edge.coord: None,
        visible_edge.coord: None,
    }


def test_stream_work_horizon_queues_prefetched_chunk_when_player_approaches() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    entering = Chunk(ChunkCoord(5, 0))
    renderer._streamer = cast(
        Any,
        SimpleNamespace(render_distance=12, get_chunk={entering.coord: entering}.get),
    )
    renderer.fog_enabled = True
    renderer.fog_end = 56.0
    renderer._stream_mesh_active = {
        ChunkCoord(dx, dz) for dx in range(-4, 5) for dz in range(-4, 5)
    }
    renderer._stream_relight_active = {
        ChunkCoord(dx, dz) for dx in range(-1, 2) for dz in range(-1, 2)
    }
    leaving = ChunkCoord(-4, 0)
    renderer._stream_relight_queue = {leaving: None}
    renderer._stream_remesh_queue = {leaving: None}

    renderer._refresh_stream_work_horizon(ChunkCoord(1, 0))

    assert leaving not in renderer._stream_mesh_active
    assert leaving not in renderer._stream_remesh_queue
    assert entering.coord not in renderer._stream_relight_queue
    assert entering.coord in renderer._stream_remesh_queue


def test_stream_remesh_queue_ignores_prefetched_chunks_outside_fog_horizon() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    active = Chunk(ChunkCoord(4, 0))
    prefetched = Chunk(ChunkCoord(5, 0))
    renderer._stream_mesh_active = {active.coord}
    renderer._stream_remesh_queue = {}

    renderer._queue_stream_remesh((active, prefetched))

    assert renderer._stream_remesh_queue == {active.coord: None}


def test_chunk_removal_coalesces_cache_updates_for_streaming_batch() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    first = ChunkCoord(0, 0)
    second = ChunkCoord(1, 0)
    renderer._fluid_active_chunks = {first, second}
    renderer._stream_relight_queue = {first: None, second: None}
    renderer._stream_remesh_queue = {first: None, second: None}
    worker = _MeshWorkerSpy()
    opaque_cache = _MeshCacheSpy()
    water_cache = _MeshCacheSpy()
    renderer.mesh_worker = cast(Any, worker)
    renderer.mesh_cache = cast(Any, opaque_cache)
    renderer.water_mesh_cache = cast(Any, water_cache)

    renderer._remove_chunks((first, second))

    expected_key_count = 2 * CHUNK_HEIGHT // SECTION_SIZE
    assert worker.invalidated == [(0, 0), (1, 0)]
    assert renderer._fluid_active_chunks == set()
    assert renderer._stream_relight_queue == {}
    assert renderer._stream_remesh_queue == {}
    assert len(opaque_cache.removals) == 1
    assert len(water_cache.removals) == 1
    assert len(opaque_cache.removals[0]) == expected_key_count
    assert opaque_cache.removals == water_cache.removals


def test_fluid_update_scans_only_active_chunks_and_retires_stable_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renderer = object.__new__(DemoWorldRenderer)
    active = Chunk(ChunkCoord(0, 0))
    idle = Chunk(ChunkCoord(1, 0))
    renderer.day_cycle_seconds = 0.0
    renderer.animation_time = 0.0
    renderer._fluid_accumulator = 0.0
    renderer._fluid_active_chunks = {active.coord}
    renderer._streamer = cast(
        Any,
        SimpleNamespace(loaded_chunks=lambda: (active, idle)),
    )
    scanned: list[ChunkCoord] = []

    def stable_step(chunk: Chunk, _neighbors: object) -> FluidUpdate:
        scanned.append(chunk.coord)
        return FluidUpdate(0)

    monkeypatch.setattr(
        "voxel_sandbox.render.world_scene.simulate_water_step",
        stable_step,
    )

    renderer.update(0.2)

    assert scanned == [active.coord]
    assert renderer._fluid_active_chunks == set()


def test_gutter_atlas_keeps_full_tile_uv_range() -> None:
    atlas = GeneratedAtlas(
        width=18,
        height=18,
        pixels=b"",
        uvs={},
        tile_size=16,
        edge_inset_pixels=0.5,
        gutter_pixels=1,
    )

    assert _atlas_tile_margin(atlas) == 0.0


def test_fog_range_culls_only_batches_entirely_beyond_fog_end() -> None:
    camera = (0.0, 8.0, 0.0)

    assert not _outside_fog_range(camera, (48.0, 0.0, 0.0), (64.0, 16.0, 16.0), 56.0)
    assert _outside_fog_range(camera, (64.0, 0.0, 0.0), (80.0, 16.0, 16.0), 56.0)
    assert not _outside_fog_range(camera, (-8.0, 0.0, -8.0), (8.0, 16.0, 8.0), 0.0)


class _EastFacingView:
    def intersects(
        self,
        minimum: tuple[float, float, float],
        _maximum: tuple[float, float, float],
    ) -> bool:
        return minimum[0] >= 0.0


def test_world_scene_remesh_queue_prefers_visible_chunk_at_equal_distance() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    offscreen = ChunkCoord(-1, 0)
    visible = ChunkCoord(1, 0)
    renderer._stream_remesh_queue = {offscreen: None, visible: None}
    renderer._streaming_frustum = cast(Any, _EastFacingView())
    renderer.mesh_uploads_per_frame = 1
    chunks = {offscreen: Chunk(offscreen), visible: Chunk(visible)}
    renderer._streamer = cast(
        Any,
        SimpleNamespace(get_chunk=chunks.get, expects_chunk=lambda _coord: False),
    )
    renderer.mesh_worker = cast(
        Any,
        SimpleNamespace(
            pending_count=0,
            max_pending_count=2,
            is_chunk_pending=lambda _coord: False,
        ),
    )
    scheduled: list[ChunkCoord] = []
    renderer._schedule_chunk = lambda chunk: scheduled.append(chunk.coord)  # type: ignore[method-assign]

    renderer._flush_stream_remesh_queue(ChunkCoord(0, 0))

    assert scheduled == [visible]
    assert tuple(renderer._stream_remesh_queue) == (offscreen,)


def test_world_scene_remesh_queue_prefers_collision_chunk_over_visibility() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    critical_offscreen = ChunkCoord(-1, 0)
    visible = ChunkCoord(1, 0)
    renderer._stream_remesh_queue = {visible: None, critical_offscreen: None}
    renderer._streaming_frustum = cast(Any, _EastFacingView())
    renderer.mesh_uploads_per_frame = 1
    chunks = {critical_offscreen: Chunk(critical_offscreen), visible: Chunk(visible)}
    renderer._streamer = cast(
        Any,
        SimpleNamespace(get_chunk=chunks.get, expects_chunk=lambda _coord: False),
    )
    renderer.mesh_worker = cast(
        Any,
        SimpleNamespace(
            pending_count=0,
            max_pending_count=2,
            is_chunk_pending=lambda _coord: False,
        ),
    )
    scheduled: list[ChunkCoord] = []
    renderer._schedule_chunk = lambda chunk: scheduled.append(chunk.coord)  # type: ignore[method-assign]

    renderer._flush_stream_remesh_queue(
        ChunkCoord(0, 0),
        collision_chunks=frozenset({critical_offscreen}),
    )

    assert scheduled == [critical_offscreen]
    assert tuple(renderer._stream_remesh_queue) == (visible,)


def test_world_scene_remesh_queue_honors_shared_frame_limit() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    first = ChunkCoord(0, 0)
    second = ChunkCoord(1, 0)
    renderer._stream_remesh_queue = {first: None, second: None}
    renderer._streaming_frustum = None
    renderer.mesh_uploads_per_frame = 2
    chunks = {first: Chunk(first), second: Chunk(second)}
    renderer._streamer = cast(
        Any,
        SimpleNamespace(get_chunk=chunks.get, expects_chunk=lambda _coord: False),
    )
    renderer.mesh_worker = cast(
        Any,
        SimpleNamespace(
            pending_count=0,
            max_pending_count=2,
            is_chunk_pending=lambda _coord: False,
        ),
    )
    scheduled: list[ChunkCoord] = []
    renderer._schedule_chunk = lambda chunk: scheduled.append(chunk.coord)  # type: ignore[method-assign]

    renderer._flush_stream_remesh_queue(ChunkCoord(0, 0), limit=1)

    assert len(scheduled) == 1
    assert len(renderer._stream_remesh_queue) == 1


def test_world_scene_remesh_queue_waits_for_expected_neighbors_and_worker_capacity() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    center = ChunkCoord(0, 0)
    expected_neighbor = ChunkCoord(1, 0)
    chunks = {center: Chunk(center)}
    renderer._stream_remesh_queue = {center: None}
    renderer._streaming_frustum = None
    renderer.mesh_uploads_per_frame = 2
    renderer._streamer = cast(
        Any,
        SimpleNamespace(
            get_chunk=chunks.get,
            expects_chunk=lambda coord: coord == expected_neighbor,
        ),
    )
    renderer.mesh_worker = cast(
        Any,
        SimpleNamespace(
            pending_count=0,
            max_pending_count=2,
            is_chunk_pending=lambda _coord: False,
        ),
    )
    scheduled: list[ChunkCoord] = []
    renderer._schedule_chunk = lambda chunk: scheduled.append(chunk.coord)  # type: ignore[method-assign]

    renderer._flush_stream_remesh_queue(center)

    assert scheduled == []
    assert renderer._stream_remesh_queue == {center: None}

    chunks[expected_neighbor] = Chunk(expected_neighbor)
    renderer.mesh_worker.pending_count = 2
    renderer._flush_stream_remesh_queue(center)

    assert scheduled == []

    renderer.mesh_worker.pending_count = 1
    renderer._flush_stream_remesh_queue(center)

    assert scheduled == [center]
    assert renderer._stream_remesh_queue == {}


def test_world_scene_perf_queues_exposes_chunk_pipeline_work() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    renderer._streamer = SimpleNamespace(
        loaded_count=7,
        pending_count=2,
        pending_save_count=4,
        dirty_chunk_count=5,
    )
    renderer.mesh_worker = SimpleNamespace(pending_count=3)
    renderer._stream_relight_queue = {ChunkCoord(0, 0): None, ChunkCoord(1, 0): None}
    renderer._stream_remesh_queue = {ChunkCoord(0, 0): None}
    renderer.visible_sections = 9
    renderer._completed_gpu_uploads = 11
    renderer._dirty_chunk_sample = 1
    renderer._next_pipeline_diagnostic_sample = 0.0

    queues = renderer.perf_queues()

    assert queues.loaded_chunks == 7
    assert queues.pending_chunks == 2
    assert queues.generation_jobs == 2
    assert queues.pending_meshes == 3
    assert queues.pending_stream_relights == 2
    assert queues.pending_stream_remeshes == 1
    assert queues.visible_sections == 9
    assert queues.completed_gpu_uploads == 11
    assert queues.dirty_chunks == 5
    assert queues.pending_saves == 4


def test_world_scene_perf_queues_bounds_dirty_chunk_sampling() -> None:
    class DiagnosticStreamer:
        loaded_count = 7
        pending_count = 2
        pending_save_count = 4
        dirty_reads = 0

        @property
        def dirty_chunk_count(self) -> int:
            self.dirty_reads += 1
            return 5

    renderer = object.__new__(DemoWorldRenderer)
    streamer = DiagnosticStreamer()
    renderer._streamer = cast(Any, streamer)
    renderer.mesh_worker = SimpleNamespace(pending_count=3)
    renderer._stream_relight_queue = {}
    renderer._stream_remesh_queue = {}
    renderer.visible_sections = 9
    renderer._completed_gpu_uploads = 11
    renderer._dirty_chunk_sample = 1
    renderer._next_pipeline_diagnostic_sample = float("inf")

    assert renderer.perf_queues().dirty_chunks == 1
    assert streamer.dirty_reads == 0

    renderer._next_pipeline_diagnostic_sample = 0.0
    assert renderer.perf_queues().dirty_chunks == 5
    assert streamer.dirty_reads == 1
