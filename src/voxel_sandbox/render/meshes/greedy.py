from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkSection
from voxel_sandbox.render.meshes.block_visuals import build_block_mesh_visual_lookups
from voxel_sandbox.render.meshes.data import MeshData
from voxel_sandbox.render.meshes.neighborhood import (
    HALO_RADIUS,
    MeshingNeighborhood,
    as_neighborhood,
)
from voxel_sandbox.render.meshes.visible_faces import (
    FACES,
    UVS,
    VERTEX_COMPONENTS,
    append_cross_quads,
    build_quad_indices,
    sample_vertex_lighting,
)


def build_greedy_mesh(
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
    fluid_lookup = np.zeros(max_block_id + 1, dtype=np.bool_)
    for definition in registry:
        opaque_lookup[definition.id] = definition.is_opaque
        fluid_lookup[definition.id] = definition.is_fluid
    visuals = build_block_mesh_visual_lookups(registry, texture_uvs)

    padded_opaque = opaque_lookup[neighborhood.blocks]
    padded_sky = neighborhood.sky_light.astype(np.float32) / 15.0
    padded_block = neighborhood.block_light.astype(np.float32) / 15.0
    vertex_batches: list[NDArray[np.float32]] = []
    index_batches: list[NDArray[np.uint32]] = []
    vertex_offset = 0

    for (dx, dy, dz), corners, normal, texture_face in FACES:
        direction = (dx, dy, dz)
        neighbor = padded_opaque[
            HALO_RADIUS + dx : HALO_RADIUS + dx + SECTION_SIZE,
            HALO_RADIUS + dy : HALO_RADIUS + dy + SECTION_SIZE,
            HALO_RADIUS + dz : HALO_RADIUS + dz + SECTION_SIZE,
        ]
        coordinates = np.argwhere(
            (blocks != 0) & ~fluid_lookup[blocks] & ~visuals.cross_lookup[blocks] & ~neighbor
        )
        if coordinates.size == 0:
            continue
        sky, block_light, ao = sample_vertex_lighting(
            coordinates,
            direction,
            corners,
            padded_sky,
            padded_block,
            padded_opaque,
            smooth_lighting=smooth_lighting,
            ambient_occlusion=ambient_occlusion,
        )
        block_ids = blocks[coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]]
        rectangles = visuals.texture_rects[texture_face][block_ids]
        normal_axis = next(axis for axis, value in enumerate(direction) if value != 0)
        u_axis = next(axis for axis in range(3) if corners[3][axis] != corners[0][axis])
        v_axis = next(axis for axis in range(3) if corners[1][axis] != corners[0][axis])
        signature_values = np.column_stack(
            (
                block_ids,
                np.rint(sky * 60.0).astype(np.uint16),
                np.rint(block_light * 60.0).astype(np.uint16),
                np.rint(ao * 100.0).astype(np.uint16),
            )
        )
        _, signatures = np.unique(signature_values, axis=0, return_inverse=True)

        for slice_index in range(SECTION_SIZE):
            selected = np.flatnonzero(coordinates[:, normal_axis] == slice_index)
            if selected.size == 0:
                continue
            signature_mask = np.full((SECTION_SIZE, SECTION_SIZE), -1, dtype=np.int32)
            face_mask = np.full((SECTION_SIZE, SECTION_SIZE), -1, dtype=np.int32)
            u_values = coordinates[selected, u_axis]
            v_values = coordinates[selected, v_axis]
            signature_mask[v_values, u_values] = signatures[selected]
            face_mask[v_values, u_values] = selected

            for u, v, width, height, face_index in _greedy_rectangles(signature_mask, face_mask):
                coordinate = np.zeros(3, dtype=np.float32)
                coordinate[normal_axis] = slice_index
                coordinate[u_axis] = u
                coordinate[v_axis] = v
                scaled_corners = np.asarray(corners, dtype=np.float32)
                scaled_corners[:, u_axis] *= width
                scaled_corners[:, v_axis] *= height
                vertices = np.empty((4, VERTEX_COMPONENTS), dtype=np.float32)
                vertices[:, :3] = coordinate[None, :] + scaled_corners
                tile_uvs = np.asarray(UVS, dtype=np.float32)
                tile_uvs[:, 0] *= width
                tile_uvs[:, 1] *= height
                vertices[:, 3:5] = tile_uvs
                vertices[:, 5:8] = np.asarray(normal, dtype=np.float32)
                face_sky = sky[face_index : face_index + 1]
                face_block = block_light[face_index : face_index + 1]
                face_ao = ao[face_index : face_index + 1]
                vertices[:, 8] = face_sky[0]
                vertices[:, 9] = face_block[0]
                vertices[:, 10] = face_ao[0]
                vertices[:, 11:15] = rectangles[face_index]
                vertices[:, 15] = visuals.wind_lookup[block_ids[face_index]]
                vertex_batches.append(vertices)
                index_batches.append(
                    build_quad_indices(face_sky, face_block, face_ao, vertex_offset)
                )
                vertex_offset += 4

    vertex_offset = append_cross_quads(
        blocks,
        visuals.cross_lookup,
        visuals.texture_rects["side"],
        visuals.wind_lookup,
        padded_sky,
        padded_block,
        vertex_batches,
        index_batches,
        vertex_offset,
    )

    if not vertex_batches:
        return MeshData(
            np.empty((0, VERTEX_COMPONENTS), dtype=np.float32),
            np.empty(0, dtype=np.uint32),
        )
    return MeshData(np.concatenate(vertex_batches), np.concatenate(index_batches))


def _greedy_rectangles(
    signatures: NDArray[np.int32],
    faces: NDArray[np.int32],
) -> list[tuple[int, int, int, int, int]]:
    rectangles: list[tuple[int, int, int, int, int]] = []
    for v in range(SECTION_SIZE):
        u = 0
        while u < SECTION_SIZE:
            signature = int(signatures[v, u])
            if signature < 0:
                u += 1
                continue
            width = 1
            while u + width < SECTION_SIZE and int(signatures[v, u + width]) == signature:
                width += 1
            height = 1
            while v + height < SECTION_SIZE and np.all(
                signatures[v + height, u : u + width] == signature
            ):
                height += 1
            face_index = int(faces[v, u])
            signatures[v : v + height, u : u + width] = -1
            rectangles.append((u, v, width, height, face_index))
            u += width
    return rectangles
