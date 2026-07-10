from __future__ import annotations

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
from voxel_sandbox.render.meshes.visible_faces import (
    FACES,
    UVS,
    build_quad_indices,
    sample_vertex_lighting,
)

FLUID_MAX_LEVEL = 8


def _fluid_render_heights(levels: NDArray[np.uint8]) -> NDArray[np.float32]:
    heights = np.where(levels > 0, levels, FLUID_MAX_LEVEL).astype(np.float32)
    heights /= FLUID_MAX_LEVEL
    return heights


def _smooth_top_vertex_heights(
    coordinates: NDArray[np.intp],
    corners: NDArray[np.float32],
    padded_fluid: NDArray[np.bool_],
    padded_heights: NDArray[np.float32],
) -> NDArray[np.float32]:
    heights = np.zeros((coordinates.shape[0], corners.shape[0]), dtype=np.float32)
    padded_y = coordinates[:, 1] + HALO_RADIUS

    for vertex_index, corner in enumerate(corners):
        if corner[1] != 1.0:
            continue
        x_offsets = (-1, 0) if corner[0] == 0.0 else (0, 1)
        z_offsets = (-1, 0) if corner[2] == 0.0 else (0, 1)
        best = np.zeros(coordinates.shape[0], dtype=np.float32)
        for x_offset in x_offsets:
            for z_offset in z_offsets:
                padded_x = coordinates[:, 0] + HALO_RADIUS + x_offset
                padded_z = coordinates[:, 2] + HALO_RADIUS + z_offset
                sample_fluid = padded_fluid[padded_x, padded_y, padded_z]
                sample_heights = padded_heights[padded_x, padded_y, padded_z]
                best = np.maximum(best, np.where(sample_fluid, sample_heights, 0.0))
        heights[:, vertex_index] = best
    return heights


def _top_shore_factors(
    coordinates: NDArray[np.intp],
    corners: NDArray[np.float32],
    padded_opaque: NDArray[np.bool_],
) -> NDArray[np.float32]:
    factors = np.zeros((coordinates.shape[0], corners.shape[0]), dtype=np.float32)
    padded_y = coordinates[:, 1] + HALO_RADIUS

    for vertex_index, corner in enumerate(corners):
        if corner[1] != 1.0:
            continue
        x_offset = -1 if corner[0] == 0.0 else 1
        z_offset = -1 if corner[2] == 0.0 else 1
        x_indices = coordinates[:, 0] + HALO_RADIUS + x_offset
        z_indices = coordinates[:, 2] + HALO_RADIUS + z_offset
        center_x = coordinates[:, 0] + HALO_RADIUS
        center_z = coordinates[:, 2] + HALO_RADIUS
        touches_x = padded_opaque[x_indices, padded_y, center_z]
        touches_z = padded_opaque[center_x, padded_y, z_indices]
        touches_diagonal = padded_opaque[x_indices, padded_y, z_indices]
        factors[:, vertex_index] = np.maximum(
            np.maximum(touches_x, touches_z).astype(np.float32),
            touches_diagonal.astype(np.float32) * 0.65,
        )
    return factors


def build_water_mesh(
    section: ChunkSection | MeshingNeighborhood,
    registry: BlockRegistry,
    texture_uvs: dict[str, tuple[float, float, float, float]],
) -> MeshData:
    neighborhood = as_neighborhood(section)
    blocks = neighborhood.center_blocks
    metadata = neighborhood.center_metadata
    max_block_id = max((definition.id for definition in registry), default=0)
    fluid_lookup = np.zeros(max_block_id + 1, dtype=np.bool_)
    opaque_lookup = np.zeros(max_block_id + 1, dtype=np.bool_)
    texture_lookup = np.zeros((max_block_id + 1, 4), dtype=np.float32)
    for definition in registry:
        fluid_lookup[definition.id] = definition.is_fluid
        opaque_lookup[definition.id] = definition.is_opaque
        texture = definition.texture_top
        if texture in texture_uvs:
            texture_lookup[definition.id] = texture_uvs[texture]

    padded_blocks = neighborhood.blocks
    padded_metadata = (
        neighborhood.metadata
        if neighborhood.metadata is not None
        else np.zeros_like(padded_blocks, dtype=np.uint8)
    )
    padded_fluid = fluid_lookup[padded_blocks]
    padded_opaque = opaque_lookup[padded_blocks]
    padded_render_heights = _fluid_render_heights(padded_metadata)
    padded_sky = neighborhood.sky_light.astype(np.float32) / 15.0
    padded_block = neighborhood.block_light.astype(np.float32) / 15.0
    vertex_batches: list[NDArray[np.float32]] = []
    index_batches: list[NDArray[np.uint32]] = []
    vertex_offset = 0

    for (dx, dy, dz), corners, normal, _texture_face in FACES:
        neighbor_fluid = padded_fluid[
            HALO_RADIUS + dx : HALO_RADIUS + dx + SECTION_SIZE,
            HALO_RADIUS + dy : HALO_RADIUS + dy + SECTION_SIZE,
            HALO_RADIUS + dz : HALO_RADIUS + dz + SECTION_SIZE,
        ]
        neighbor_opaque = padded_opaque[
            HALO_RADIUS + dx : HALO_RADIUS + dx + SECTION_SIZE,
            HALO_RADIUS + dy : HALO_RADIUS + dy + SECTION_SIZE,
            HALO_RADIUS + dz : HALO_RADIUS + dz + SECTION_SIZE,
        ]
        neighbor_levels = padded_metadata[
            HALO_RADIUS + dx : HALO_RADIUS + dx + SECTION_SIZE,
            HALO_RADIUS + dy : HALO_RADIUS + dy + SECTION_SIZE,
            HALO_RADIUS + dz : HALO_RADIUS + dz + SECTION_SIZE,
        ]
        current_heights = np.where(metadata > 0, metadata, FLUID_MAX_LEVEL)
        neighbor_heights = np.where(neighbor_levels > 0, neighbor_levels, FLUID_MAX_LEVEL)
        exposed_fluid_step = dy == 0 and (current_heights > neighbor_heights)
        visible = fluid_lookup[blocks] & ~neighbor_opaque & (~neighbor_fluid | exposed_fluid_step)
        coordinates = np.argwhere(visible)
        face_count = coordinates.shape[0]
        if face_count == 0:
            continue
        block_ids = blocks[coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]]
        corners_array = np.asarray(corners, dtype=np.float32)
        positions = coordinates[:, None, :].astype(np.float32) + corners_array[None, :, :]
        top_vertices = corners_array[:, 1] == 1.0
        smooth_heights = _smooth_top_vertex_heights(
            coordinates,
            corners_array,
            padded_fluid,
            padded_render_heights,
        )
        positions[:, top_vertices, 1] = coordinates[:, None, 1] + smooth_heights[:, top_vertices]
        shore_factors = (
            _top_shore_factors(coordinates, corners_array, padded_opaque)
            if dy == 1
            else np.zeros((face_count, 4), dtype=np.float32)
        )
        if dy == 0:
            adjacent_fluid = neighbor_fluid[coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]]
            adjacent_levels = neighbor_heights[
                coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]
            ].astype(np.float32)
            adjacent_heights = np.where(adjacent_fluid, adjacent_levels, 0.0)
            adjacent_heights /= FLUID_MAX_LEVEL
            bottom_vertices = corners_array[:, 1] == 0.0
            positions[:, bottom_vertices, 1] = coordinates[:, None, 1] + adjacent_heights[:, None]
        sky, block_light, ao = sample_vertex_lighting(
            coordinates,
            (dx, dy, dz),
            corners,
            padded_sky,
            padded_block,
            padded_opaque,
            smooth_lighting=True,
            ambient_occlusion=False,
        )
        vertices = np.empty((face_count, 4, 15), dtype=np.float32)
        vertices[:, :, :3] = positions
        vertices[:, :, 3:5] = np.asarray(UVS, dtype=np.float32)
        vertices[:, :, 5:8] = np.asarray(normal, dtype=np.float32)
        vertices[:, :, 8] = sky
        vertices[:, :, 9] = block_light
        vertices[:, :, 10] = shore_factors
        vertices[:, :, 11:15] = texture_lookup[block_ids, None, :]
        vertex_batches.append(vertices.reshape((-1, 15)))
        index_batches.append(build_quad_indices(sky, block_light, ao, vertex_offset))
        vertex_offset += face_count * 4

    if not vertex_batches:
        return MeshData(
            np.empty((0, 15), dtype=np.float32),
            np.empty(0, dtype=np.uint32),
        )
    return MeshData(np.concatenate(vertex_batches), np.concatenate(index_batches))
