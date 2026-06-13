from __future__ import annotations

from time import perf_counter

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.generation import TerrainGenerator, WorldSeed


def run_benchmark(chunk_count: int = 100) -> int:
    generator = TerrainGenerator(WorldSeed.parse("benchmark-world"))
    start = perf_counter()
    for index in range(chunk_count):
        generator.generate_chunk(ChunkCoord(index % 10, index // 10))
    elapsed = perf_counter() - start
    print(
        f"worldgen {chunk_count} chunks: total={elapsed * 1000.0:.2f} ms "
        f"avg={elapsed * 1000.0 / chunk_count:.3f} ms/chunk"
    )
    return 0
