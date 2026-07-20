from __future__ import annotations

import time

import numpy as np

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkCoord, SectionCoord
from voxel_sandbox.engine.perf.greedy_rectangles import NATIVE_GREEDY_RECTANGLES
from voxel_sandbox.render.meshes import build_greedy_mesh
from voxel_sandbox.render.meshes.neighborhood import MeshingNeighborhood
from voxel_sandbox.render.meshes.worker import SectionMeshWorker

UVS = {
    "stone": (0.0, 0.0, 0.5, 0.5),
    "dirt": (0.5, 0.0, 1.0, 0.5),
    "grass_top": (0.0, 0.5, 0.5, 1.0),
    "grass_side": (0.5, 0.5, 1.0, 1.0),
}


def create_benchmark_neighborhood() -> MeshingNeighborhood:
    blocks = np.zeros((20, 20, 20), dtype=np.uint16)
    blocks[2:18, 2:10, 2:18] = 1
    sky_light = np.zeros((20, 20, 20), dtype=np.uint8)
    sky_light[2:18, 10:18, 2:18] = 15
    block_light = np.zeros((20, 20, 20), dtype=np.uint8)
    metadata = np.zeros((20, 20, 20), dtype=np.uint8)
    return MeshingNeighborhood(blocks, sky_light, block_light, metadata)


def run_benchmark(iterations: int = 250) -> int:
    registry = create_core_block_registry()
    neighborhood = create_benchmark_neighborhood()

    # 1. Single Section Mesh Time
    start = time.perf_counter()
    mesh = build_greedy_mesh(
        neighborhood, registry, UVS, smooth_lighting=False, ambient_occlusion=False
    )
    single_mesh_time = (time.perf_counter() - start) * 1000.0
    print(f"greedy scanner backend: {'cython' if NATIVE_GREEDY_RECTANGLES else 'python'}")
    print(
        f"greedy 16^3 single section: {single_mesh_time:.3f} ms. "
        f"Mesh bytes: {mesh.vertices.nbytes + mesh.indices.nbytes}"
    )

    # 2. Worker comparison
    for backend in ["thread", "process"]:
        worker = SectionMeshWorker(registry, UVS, workers=4, backend=backend)  # type: ignore

        # Test individual sections (current)
        start = time.perf_counter()
        for i in range(iterations):
            key = SectionCoord(i % 10, i % 16, i // 16)
            worker.submit(
                key, neighborhood, greedy=True, smooth_lighting=False, ambient_occlusion=False
            )

        completed = 0
        while completed < iterations:
            results = worker.poll(100)
            completed += len(results)
            time.sleep(0.001)
        duration = time.perf_counter() - start
        print(
            f"{backend} backend, 1 section/future: "
            f"{iterations / duration:.1f} sections/sec ({duration:.3f}s total)"
        )

        # Test chunk batching
        start = time.perf_counter()
        chunks = iterations // 16
        for i in range(chunks):
            coord = ChunkCoord(i % 10, i // 10)
            tasks = {SectionCoord(coord.x, y, coord.z): neighborhood for y in range(16)}
            worker.submit_chunk(
                coord, tasks, greedy=True, smooth_lighting=False, ambient_occlusion=False
            )

        completed = 0
        while completed < chunks * 16:
            results = worker.poll(100)
            completed += len(results)
            time.sleep(0.001)
        duration = time.perf_counter() - start
        print(
            f"{backend} backend, 16 sections/future: "
            f"{(chunks * 16) / duration:.1f} sections/sec ({duration:.3f}s total)"
        )

        worker.close()

    return 0
