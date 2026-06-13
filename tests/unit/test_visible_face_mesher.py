from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkSection
from voxel_sandbox.render.meshes import build_visible_face_mesh
from voxel_sandbox.tools.benchmark_mesher import UVS


def test_single_block_has_six_visible_faces() -> None:
    section = ChunkSection()
    section.set_block(1, 1, 1, 1)

    mesh = build_visible_face_mesh(section, create_core_block_registry(), UVS)

    assert mesh.vertices.shape == (24, 8)
    assert mesh.face_count == 6
    assert mesh.triangle_count == 12


def test_adjacent_blocks_hide_shared_faces() -> None:
    section = ChunkSection()
    section.set_block(1, 1, 1, 1)
    section.set_block(2, 1, 1, 1)

    mesh = build_visible_face_mesh(section, create_core_block_registry(), UVS)

    assert mesh.face_count == 10
    assert mesh.triangle_count == 20


def test_empty_section_produces_empty_arrays() -> None:
    mesh = build_visible_face_mesh(ChunkSection(), create_core_block_registry(), UVS)

    assert mesh.vertices.shape == (0, 8)
    assert mesh.indices.size == 0
