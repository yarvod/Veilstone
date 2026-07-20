from __future__ import annotations

import numpy as np

from voxel_sandbox.engine.chunks import SectionCoord
from voxel_sandbox.render.meshes.data import MeshData
from voxel_sandbox.render.meshes.gpu_cache import combine_section_meshes


def _mesh(x: float) -> MeshData:
    vertices = np.zeros((2, 16), dtype=np.float32)
    vertices[:, 0] = (x, x + 1.0)
    return MeshData(vertices, np.array([0, 1], dtype=np.uint32))


def test_combined_mesh_offsets_vertices_indices_and_bounds() -> None:
    first = SectionCoord(0, 1, 0)
    second = SectionCoord(1, 2, 0)

    combined, origin, minimum, maximum = combine_section_meshes(
        SectionCoord(0, 0, 0),
        {second: _mesh(2.0), first: _mesh(0.0)},
    )

    assert origin == (0, 0, 0)
    assert minimum == (0.0, 16.0, 0.0)
    assert maximum == (32.0, 48.0, 16.0)
    np.testing.assert_array_equal(combined.indices, np.array([0, 1, 2, 3], dtype=np.uint32))
    np.testing.assert_array_equal(combined.vertices[:, 0], np.array([0, 1, 18, 19]))
    np.testing.assert_array_equal(combined.vertices[:, 1], np.array([16, 16, 32, 32]))
