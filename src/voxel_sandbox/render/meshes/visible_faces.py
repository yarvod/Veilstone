from __future__ import annotations

from typing import Final

import numpy as np
from numpy.typing import NDArray

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
    blocks = section.blocks
    max_block_id = max((definition.id for definition in registry), default=0)
    opaque_lookup = np.zeros(max_block_id + 1, dtype=np.bool_)
    texture_lookups = {
        face: np.zeros((max_block_id + 1, 4), dtype=np.float32)
        for face in ("top", "side", "bottom")
    }
    for definition in registry:
        opaque_lookup[definition.id] = definition.is_opaque
        for face in texture_lookups:
            texture = getattr(definition, f"texture_{face}")
            if texture in texture_uvs:
                texture_lookups[face][definition.id] = texture_uvs[texture]

    opaque = opaque_lookup[blocks]
    padded = np.pad(opaque, 1, constant_values=False)
    vertex_batches: list[NDArray[np.float32]] = []
    index_batches: list[NDArray[np.uint32]] = []
    vertex_offset = 0

    for (dx, dy, dz), corners, normal, texture_face in FACES:
        neighbor = padded[
            1 + dx : 1 + dx + SECTION_SIZE,
            1 + dy : 1 + dy + SECTION_SIZE,
            1 + dz : 1 + dz + SECTION_SIZE,
        ]
        coordinates = np.argwhere((blocks != 0) & ~neighbor)
        face_count = coordinates.shape[0]
        if face_count == 0:
            continue

        corners_array = np.asarray(corners, dtype=np.float32)
        positions = coordinates[:, None, :].astype(np.float32) + corners_array[None, :, :]
        block_ids = blocks[coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]]
        rectangles = texture_lookups[texture_face][block_ids]
        local_uvs = np.asarray(UVS, dtype=np.float32)
        uvs = np.empty((face_count, 4, 2), dtype=np.float32)
        uvs[:, :, 0] = (
            rectangles[:, 0, None]
            + (rectangles[:, 2, None] - rectangles[:, 0, None]) * local_uvs[None, :, 0]
        )
        uvs[:, :, 1] = (
            rectangles[:, 1, None]
            + (rectangles[:, 3, None] - rectangles[:, 1, None]) * local_uvs[None, :, 1]
        )

        vertices = np.empty((face_count, 4, 8), dtype=np.float32)
        vertices[:, :, :3] = positions
        vertices[:, :, 3:5] = uvs
        vertices[:, :, 5:] = np.asarray(normal, dtype=np.float32)
        vertex_batches.append(vertices.reshape((-1, 8)))

        bases = np.arange(face_count, dtype=np.uint32) * 4 + vertex_offset
        pattern = np.asarray((0, 1, 2, 0, 2, 3), dtype=np.uint32)
        index_batches.append((bases[:, None] + pattern[None, :]).reshape(-1))
        vertex_offset += face_count * 4

    if not vertex_batches:
        return MeshData(
            np.empty((0, 8), dtype=np.float32),
            np.empty(0, dtype=np.uint32),
        )
    return MeshData(np.concatenate(vertex_batches), np.concatenate(index_batches))
