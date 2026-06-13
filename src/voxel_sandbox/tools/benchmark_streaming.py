from __future__ import annotations

import time
from time import perf_counter

import numpy as np

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkCoord, SectionCoord
from voxel_sandbox.engine.generation import ChunkStreamer, TerrainGenerator, WorldSeed
from voxel_sandbox.engine.lighting import relight_chunk
from voxel_sandbox.render.meshes import MeshingNeighborhood
from voxel_sandbox.render.meshes.neighborhood import HALO_RADIUS, HALO_SIZE
from voxel_sandbox.render.meshes.worker import SectionMeshWorker
from voxel_sandbox.render.texture_atlas import create_block_atlas


def run_benchmark() -> int:
    registry = create_core_block_registry()
    streamer = ChunkStreamer(
        TerrainGenerator(WorldSeed.parse("streaming-benchmark")),
        render_distance=1,
        workers=2,
        postprocess=lambda chunk: relight_chunk(chunk, registry),
    )
    worker = SectionMeshWorker(
        registry,
        create_block_atlas().uvs,
        workers=2,
        backend="process",
    )
    try:
        for chunk_x in range(-1, 2):
            for chunk_z in range(-1, 2):
                streamer.prime(ChunkCoord(chunk_x, chunk_z))

        submit_start = perf_counter()
        submitted = 0
        for section_y in range(3):
            key = SectionCoord(0, section_y, 0)
            origin = (
                -HALO_RADIUS,
                section_y * SECTION_SIZE - HALO_RADIUS,
                -HALO_RADIUS,
            )
            arrays = streamer.snapshot_region(origin, (HALO_SIZE, HALO_SIZE, HALO_SIZE))
            if not np.any(arrays[0][2:18, 2:18, 2:18]):
                continue
            worker.submit(
                key,
                MeshingNeighborhood(*arrays),
                greedy=True,
                smooth_lighting=True,
                ambient_occlusion=True,
            )
            submitted += 1
        submit_ms = (perf_counter() - submit_start) * 1000.0

        completed = 0
        background_start = perf_counter()
        while completed < submitted:
            completed += len(worker.poll(submitted))
            if completed < submitted:
                time.sleep(0.0005)
        background_ms = (perf_counter() - background_start) * 1000.0
        print(
            f"stream integration: sections={submitted} main-submit={submit_ms:.3f} ms "
            f"background-mesh={background_ms:.3f} ms "
            f"avg={background_ms / max(submitted, 1):.3f} ms/section"
        )
        return 0
    finally:
        worker.close()
        streamer.close()
