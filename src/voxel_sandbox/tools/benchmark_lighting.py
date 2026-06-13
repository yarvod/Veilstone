from __future__ import annotations

from statistics import mean
from time import perf_counter

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import Chunk, ChunkCoord
from voxel_sandbox.engine.lighting import relight_chunk


def create_benchmark_chunk() -> Chunk:
    chunk = Chunk(ChunkCoord(0, 0))
    for x in range(16):
        for z in range(16):
            height = 7 + (x + z) % 5
            for y in range(height):
                chunk.set_block(x, y, z, 1)
    for x, y, z in ((3, 14, 3), (12, 16, 4), (8, 12, 12), (5, 18, 9)):
        chunk.set_block(x, y, z, 7)
    return chunk


def run_benchmark(iterations: int = 25) -> int:
    chunk = create_benchmark_chunk()
    registry = create_core_block_registry()
    timings: list[float] = []
    for _ in range(iterations):
        start = perf_counter()
        relight_chunk(chunk, registry)
        timings.append((perf_counter() - start) * 1000.0)
    print(f"lighting 16x64x16: avg={mean(timings):.3f} ms min={min(timings):.3f} ms sources=4")
    return 0
