# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from voxel_sandbox.engine.chunks import ChunkCoord, SectionCoord
from voxel_sandbox.render.world_scene import DemoWorldRenderer


class _EastFacingView:
    def intersects(
        self,
        minimum: tuple[float, float, float],
        _maximum: tuple[float, float, float],
    ) -> bool:
        return minimum[0] >= 0.0


def test_world_scene_remesh_queue_prefers_visible_section_at_equal_distance() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    offscreen = SectionCoord(-1, 0, 0)
    visible = SectionCoord(1, 0, 0)
    renderer._stream_remesh_queue = {offscreen: None, visible: None}
    renderer._streaming_frustum = cast(Any, _EastFacingView())
    renderer.mesh_uploads_per_frame = 1
    scheduled: list[SectionCoord] = []
    renderer._schedule_section = scheduled.append  # type: ignore[method-assign]

    renderer._flush_stream_remesh_queue(ChunkCoord(0, 0))

    assert scheduled == [visible]
    assert tuple(renderer._stream_remesh_queue) == (offscreen,)


def test_world_scene_remesh_queue_prefers_collision_section_over_visibility() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    critical_offscreen = SectionCoord(-1, 0, 0)
    visible = SectionCoord(1, 0, 0)
    renderer._stream_remesh_queue = {visible: None, critical_offscreen: None}
    renderer._streaming_frustum = cast(Any, _EastFacingView())
    renderer.mesh_uploads_per_frame = 1
    scheduled: list[SectionCoord] = []
    renderer._schedule_section = scheduled.append  # type: ignore[method-assign]

    renderer._flush_stream_remesh_queue(
        ChunkCoord(0, 0),
        collision_chunks=frozenset({critical_offscreen.chunk}),
    )

    assert scheduled == [critical_offscreen]
    assert tuple(renderer._stream_remesh_queue) == (visible,)


def test_world_scene_perf_queues_exposes_pending_relight_work() -> None:
    renderer = object.__new__(DemoWorldRenderer)
    renderer._streamer = SimpleNamespace(loaded_count=7, pending_count=2)
    renderer.mesh_worker = SimpleNamespace(pending_count=3)
    renderer._stream_relight_queue = {ChunkCoord(0, 0): None, ChunkCoord(1, 0): None}
    renderer._stream_remesh_queue = {SectionCoord(0, 0, 0): None}
    renderer.visible_sections = 9

    queues = renderer.perf_queues()

    assert queues.loaded_chunks == 7
    assert queues.pending_chunks == 2
    assert queues.pending_meshes == 3
    assert queues.pending_stream_relights == 2
    assert queues.pending_stream_remeshes == 1
    assert queues.visible_sections == 9
