from __future__ import annotations

import time
from typing import Literal

import pytest

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkSection, SectionCoord
from voxel_sandbox.render.meshes import MeshingNeighborhood
from voxel_sandbox.render.meshes.worker import SectionMeshWorker
from voxel_sandbox.render.texture_atlas import create_block_atlas


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
    finally:
        worker.close()
