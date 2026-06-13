from __future__ import annotations

from collections.abc import Callable
from statistics import mean
from time import perf_counter

from voxel_sandbox.domain.blocks import BlockRegistry, create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkSection
from voxel_sandbox.render.meshes import MeshData, build_greedy_mesh, build_visible_face_mesh

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
    visible_time, visible_mesh = _measure(build_visible_face_mesh, section, registry, iterations)
    greedy_time, greedy_mesh = _measure(build_greedy_mesh, section, registry, iterations)
    reduction = 1.0 - greedy_mesh.triangle_count / max(visible_mesh.triangle_count, 1)
    print(
        f"visible-face 16^3: avg={visible_time:.3f} ms "
        f"faces={visible_mesh.face_count} triangles={visible_mesh.triangle_count}"
    )
    print(
        f"greedy 16^3: avg={greedy_time:.3f} ms "
        f"quads={greedy_mesh.face_count} triangles={greedy_mesh.triangle_count} "
        f"reduction={reduction:.1%}"
    )
    return 0


def _measure(
    builder: Callable[..., MeshData],
    section: ChunkSection,
    registry: BlockRegistry,
    iterations: int,
) -> tuple[float, MeshData]:
    timings: list[float] = []
    mesh = builder(section, registry, UVS)
    for _ in range(iterations):
        start = perf_counter()
        mesh = builder(section, registry, UVS)
        timings.append((perf_counter() - start) * 1000.0)
    return mean(timings), mesh
