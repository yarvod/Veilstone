from __future__ import annotations

import numpy as np

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkSection
from voxel_sandbox.render.meshes import build_water_mesh
from voxel_sandbox.tools.benchmark_mesher import UVS


def lit_section() -> ChunkSection:
    section = ChunkSection()
    section.sky_light.fill(15)
    return section


def test_water_top_surface_smooths_shared_edge_between_flow_levels() -> None:
    section = lit_section()
    section.set_block(1, 1, 1, 8)
    section.set_block(2, 1, 1, 8)
    section.set_metadata(2, 1, 1, 4)

    mesh = build_water_mesh(section, create_core_block_registry(), UVS)

    faces = mesh.vertices.reshape((-1, 4, 15))
    top_faces = faces[np.isclose(faces[:, 0, 6], 1.0)]
    low_flow_face = next(face for face in top_faces if np.isclose(face[:, 0].min(), 2.0))

    assert [round(float(y), 2) for y in sorted(low_flow_face[:, 1])] == [
        1.5,
        1.5,
        2.0,
        2.0,
    ]
