# pyright: reportPrivateUsage=false

from __future__ import annotations

import time
from threading import Event
from typing import Literal

import pytest

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkCoord, ChunkSection, SectionCoord
from voxel_sandbox.render.meshes import MeshingNeighborhood
from voxel_sandbox.render.meshes.worker import CompletedMesh, MeshTask, SectionMeshWorker
from voxel_sandbox.render.texture_atlas import create_block_atlas


class _BlockingMeshWorker(SectionMeshWorker):
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.build_calls = 0
        super().__init__(
            create_core_block_registry(),
            create_block_atlas(tile_size=8).uvs,
            workers=1,
        )

    def _build_chunk(
        self,
        tasks: tuple[MeshTask, ...],
        greedy: bool,
        smooth_lighting: bool,
        ambient_occlusion: bool,
    ) -> tuple[CompletedMesh, ...]:
        del tasks, greedy, smooth_lighting, ambient_occlusion
        self.build_calls += 1
        if self.build_calls == 1:
            self.started.set()
            assert self.release.wait(timeout=2.0)
        return ()


@pytest.mark.parametrize("backend", ["thread", "process"])
def test_mesh_worker_builds_section_off_thread(
    backend: Literal["thread", "process"],
) -> None:
    section = ChunkSection()
    section.blocks[:, :8, :] = 1
    section.sky_light.fill(15)
    worker = SectionMeshWorker(
        create_core_block_registry(),
        create_block_atlas(tile_size=8).uvs,
        workers=1,
        backend=backend,
    )
    try:
        key = SectionCoord(0, 0, 0)
        worker.submit(
            key,
            MeshingNeighborhood.from_section(section),
            greedy=True,
            smooth_lighting=True,
            ambient_occlusion=True,
        )
        deadline = time.monotonic() + 2.0
        completed = ()
        while not completed and time.monotonic() < deadline:
            completed = worker.poll(1)
            time.sleep(0.001)

        assert len(completed) == 1
        assert completed[0].key == key
        assert completed[0].mesh.triangle_count < 2048
        assert completed[0].transparent_mesh.indices.size == 0
    finally:
        worker.close()


def test_mesh_worker_coalesces_chunk_replacements_while_running() -> None:
    worker = _BlockingMeshWorker()
    coord = ChunkCoord(0, 0)
    try:
        worker.submit_chunk(
            coord,
            {},
            greedy=True,
            smooth_lighting=False,
            ambient_occlusion=False,
        )
        assert worker.started.wait(timeout=2.0)

        for _ in range(3):
            worker.submit_chunk(
                coord,
                {},
                greedy=True,
                smooth_lighting=False,
                ambient_occlusion=False,
            )

        assert worker.pending_count == 2
        worker.release.set()
        deadline = time.monotonic() + 2.0
        while worker.pending_count and time.monotonic() < deadline:
            worker.poll(1)
            time.sleep(0.001)

        assert worker.pending_count == 0
        assert worker.build_calls == 2
    finally:
        worker.release.set()
        worker.close()


def test_mesh_worker_invalidates_only_indexed_chunk_revisions() -> None:
    worker = SectionMeshWorker(
        create_core_block_registry(),
        create_block_atlas(tile_size=8).uvs,
        workers=1,
    )
    try:
        first = SectionCoord(0, 0, 0)
        second = SectionCoord(1, 0, 0)
        section = ChunkSection()
        neighborhood = MeshingNeighborhood.from_section(section)
        worker.submit(
            first,
            neighborhood,
            greedy=True,
            smooth_lighting=False,
            ambient_occlusion=False,
        )
        worker.submit(
            second,
            neighborhood,
            greedy=True,
            smooth_lighting=False,
            ambient_occlusion=False,
        )

        worker.invalidate_chunk(0, 0)

        assert first not in worker._revisions
        assert second in worker._revisions
        assert (0, 0) not in worker._chunk_revision_keys
        assert worker._chunk_revision_keys[(1, 0)] == {second}
    finally:
        worker.close()
