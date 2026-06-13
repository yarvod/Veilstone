from __future__ import annotations

from typing import Final

import numpy as np

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkSection
from voxel_sandbox.render.meshes.data import MeshData

Face = tuple[
    tuple[int, int, int],
    tuple[tuple[int, int, int], ...],
    tuple[float, float, float],
    str,
]

FACES: Final[tuple[Face, ...]] = (
    ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)), (1.0, 0.0, 0.0), "side"),
    ((-1, 0, 0), ((0, 0, 1), (0, 1, 1), (0, 1, 0), (0, 0, 0)), (-1.0, 0.0, 0.0), "side"),
    ((0, 1, 0), ((0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)), (0.0, 1.0, 0.0), "top"),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)), (0.0, -1.0, 0.0), "bottom"),
    ((0, 0, 1), ((1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1)), (0.0, 0.0, 1.0), "side"),
    ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)), (0.0, 0.0, -1.0), "side"),
)
UVS: Final = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))


def build_visible_face_mesh(
    section: ChunkSection,
    registry: BlockRegistry,
    texture_uvs: dict[str, tuple[float, float, float, float]],
) -> MeshData:
    vertices: list[float] = []
    indices: list[int] = []

    for x, y, z in np.argwhere(section.blocks != 0):
        block = registry.by_id(int(section.blocks[x, y, z]))
        for (dx, dy, dz), corners, normal, texture_face in FACES:
            nx, ny, nz = int(x) + dx, int(y) + dy, int(z) + dz
            if _is_opaque(section, registry, nx, ny, nz):
                continue
            texture = getattr(block, f"texture_{texture_face}")
            u0, v0, u1, v1 = texture_uvs[texture]
            base = len(vertices) // 8
            for corner, (local_u, local_v) in zip(corners, UVS, strict=True):
                u = u0 + (u1 - u0) * local_u
                v = v0 + (v1 - v0) * local_v
                vertices.extend(
                    (
                        float(int(x) + corner[0]),
                        float(int(y) + corner[1]),
                        float(int(z) + corner[2]),
                        u,
                        v,
                        *normal,
                    )
                )
            indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))

    return MeshData(
        np.asarray(vertices, dtype=np.float32).reshape((-1, 8)),
        np.asarray(indices, dtype=np.uint32),
    )


def _is_opaque(
    section: ChunkSection,
    registry: BlockRegistry,
    x: int,
    y: int,
    z: int,
) -> bool:
    if not (0 <= x < SECTION_SIZE and 0 <= y < SECTION_SIZE and 0 <= z < SECTION_SIZE):
        return False
    return registry.by_id(int(section.blocks[x, y, z])).is_opaque
