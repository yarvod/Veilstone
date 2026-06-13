from __future__ import annotations

from statistics import mean
from time import perf_counter

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkSection
from voxel_sandbox.render.meshes import build_visible_face_mesh

UVS = {
    "stone": (0.0, 0.0, 0.5, 0.5),
    "dirt": (0.5, 0.0, 1.0, 0.5),
    "grass_top": (0.0, 0.5, 0.5, 1.0),
    "grass_side": (0.5, 0.5, 1.0, 1.0),
}


def create_benchmark_section() -> ChunkSection:
    section = ChunkSection()
    section.blocks[:, :8, :] = 1
    return section


def run_benchmark(iterations: int = 25) -> int:
    section = create_benchmark_section()
    registry = create_core_block_registry()
    timings: list[float] = []
    mesh = build_visible_face_mesh(section, registry, UVS)
    for _ in range(iterations):
        start = perf_counter()
        mesh = build_visible_face_mesh(section, registry, UVS)
        timings.append((perf_counter() - start) * 1000.0)
    print(
        f"visible-face 16^3: avg={mean(timings):.3f} ms "
        f"min={min(timings):.3f} ms faces={mesh.face_count} triangles={mesh.triangle_count}"
    )
    return 0
