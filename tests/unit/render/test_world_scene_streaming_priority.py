# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false

from __future__ import annotations

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
