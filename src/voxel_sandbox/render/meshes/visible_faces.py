from __future__ import annotations

from typing import Final

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkSection
from voxel_sandbox.render.meshes.data import MeshData
from voxel_sandbox.render.meshes.neighborhood import (
    HALO_RADIUS,
    MeshingNeighborhood,
    as_neighborhood,
)

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
    section: ChunkSection | MeshingNeighborhood,
    registry: BlockRegistry,
    texture_uvs: dict[str, tuple[float, float, float, float]],
    *,
    smooth_lighting: bool = True,
    ambient_occlusion: bool = True,
) -> MeshData:
    neighborhood = as_neighborhood(section)
    blocks = neighborhood.center_blocks
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

    padded_opaque = opaque_lookup[neighborhood.blocks]
    padded_sky_light = neighborhood.sky_light.astype(np.float32) / 15.0
    padded_block_light = neighborhood.block_light.astype(np.float32) / 15.0
    vertex_batches: list[NDArray[np.float32]] = []
    index_batches: list[NDArray[np.uint32]] = []
    vertex_offset = 0

    for (dx, dy, dz), corners, normal, texture_face in FACES:
        neighbor = padded_opaque[
            HALO_RADIUS + dx : HALO_RADIUS + dx + SECTION_SIZE,
            HALO_RADIUS + dy : HALO_RADIUS + dy + SECTION_SIZE,
            HALO_RADIUS + dz : HALO_RADIUS + dz + SECTION_SIZE,
        ]
        coordinates = np.argwhere((blocks != 0) & ~neighbor)
        face_count = coordinates.shape[0]
        if face_count == 0:
            continue

        corners_array = np.asarray(corners, dtype=np.float32)
        positions = coordinates[:, None, :].astype(np.float32) + corners_array[None, :, :]
        block_ids = blocks[coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]]
        rectangles = texture_lookups[texture_face][block_ids]
        sky_lights, block_lights, ao = sample_vertex_lighting(
            coordinates,
            (dx, dy, dz),
            corners,
            padded_sky_light,
            padded_block_light,
            padded_opaque,
            smooth_lighting=smooth_lighting,
            ambient_occlusion=ambient_occlusion,
        )
        vertices = np.empty((face_count, 4, 15), dtype=np.float32)
        vertices[:, :, :3] = positions
        vertices[:, :, 3:5] = np.asarray(UVS, dtype=np.float32)
        vertices[:, :, 5:8] = np.asarray(normal, dtype=np.float32)
        vertices[:, :, 8] = sky_lights
        vertices[:, :, 9] = block_lights
        vertices[:, :, 10] = ao
        vertices[:, :, 11:15] = rectangles[:, None, :]
        vertex_batches.append(vertices.reshape((-1, 15)))

        index_batches.append(build_quad_indices(sky_lights, block_lights, ao, vertex_offset))
        vertex_offset += face_count * 4

    if not vertex_batches:
        return MeshData(
            np.empty((0, 15), dtype=np.float32),
            np.empty(0, dtype=np.uint32),
        )
    return MeshData(np.concatenate(vertex_batches), np.concatenate(index_batches))


def build_quad_indices(
    sky_lights: NDArray[np.float32],
    block_lights: NDArray[np.float32],
    ao: NDArray[np.float32],
    vertex_offset: int,
) -> NDArray[np.uint32]:
    face_count = sky_lights.shape[0]
    bases = np.arange(face_count, dtype=np.uint32) * 4 + vertex_offset
    indices = np.empty((face_count, 6), dtype=np.uint32)
    default_pattern = np.asarray((0, 1, 2, 0, 2, 3), dtype=np.uint32)
    flipped_pattern = np.asarray((0, 1, 3, 1, 2, 3), dtype=np.uint32)
    brightness = np.maximum(sky_lights, block_lights) * ao
    flip = brightness[:, 0] + brightness[:, 2] > brightness[:, 1] + brightness[:, 3]
    indices[:] = bases[:, None] + default_pattern[None, :]
    indices[flip] = bases[flip, None] + flipped_pattern[None, :]
    return indices.reshape(-1)


def sample_vertex_lighting(
    coordinates: NDArray[np.int64],
    direction: tuple[int, int, int],
    corners: tuple[tuple[int, int, int], ...],
    padded_sky_light: NDArray[np.float32],
    padded_block_light: NDArray[np.float32],
    padded_opaque: NDArray[np.bool_],
    *,
    smooth_lighting: bool,
    ambient_occlusion: bool,
) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.float32]]:
    face_count = coordinates.shape[0]
    sky_lights = np.empty((face_count, 4), dtype=np.float32)
    block_lights = np.empty((face_count, 4), dtype=np.float32)
    ao = np.ones((face_count, 4), dtype=np.float32)
    normal_axis = next(axis for axis, value in enumerate(direction) if value != 0)
    tangent_axes = tuple(axis for axis in range(3) if axis != normal_axis)
    base = coordinates + np.asarray(direction, dtype=np.int64)

    for vertex_index, corner in enumerate(corners):
        offsets: list[NDArray[np.int64]] = [np.zeros(3, dtype=np.int64)]
        side_offsets: list[NDArray[np.int64]] = []
        for axis in tangent_axes:
            offset = np.zeros(3, dtype=np.int64)
            offset[axis] = -1 if corner[axis] == 0 else 1
            side_offsets.append(offset)
        corner_offset = side_offsets[0] + side_offsets[1]
        if smooth_lighting:
            offsets.extend((*side_offsets, corner_offset))
        sky_samples = [_sample_float(padded_sky_light, base + offset) for offset in offsets]
        block_samples = [_sample_float(padded_block_light, base + offset) for offset in offsets]
        sky_lights[:, vertex_index] = np.mean(np.stack(sky_samples), axis=0)
        block_lights[:, vertex_index] = np.mean(np.stack(block_samples), axis=0)

        if ambient_occlusion:
            side_one = _sample_bool(padded_opaque, base + side_offsets[0]).astype(np.float32)
            side_two = _sample_bool(padded_opaque, base + side_offsets[1]).astype(np.float32)
            corner_block = _sample_bool(padded_opaque, base + corner_offset).astype(np.float32)
            occlusion = np.where(
                (side_one > 0.0) & (side_two > 0.0),
                3.0,
                side_one + side_two + corner_block,
            )
            ao[:, vertex_index] = 1.0 - occlusion * 0.18
    return sky_lights, block_lights, ao


def _sample_float(
    array: NDArray[np.float32], coordinates: NDArray[np.int64]
) -> NDArray[np.float32]:
    indices = coordinates + HALO_RADIUS
    return array[indices[:, 0], indices[:, 1], indices[:, 2]]


def _sample_bool(array: NDArray[np.bool_], coordinates: NDArray[np.int64]) -> NDArray[np.bool_]:
    indices = coordinates + HALO_RADIUS
    return array[indices[:, 0], indices[:, 1], indices[:, 2]]
