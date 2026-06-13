from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkSection
from voxel_sandbox.render.meshes import build_visible_face_mesh
from voxel_sandbox.tools.benchmark_mesher import UVS


def lit_section() -> ChunkSection:
    section = ChunkSection()
    section.sky_light.fill(15)
    return section


def test_single_block_has_six_visible_faces() -> None:
    section = lit_section()
    section.set_block(1, 1, 1, 1)

    mesh = build_visible_face_mesh(section, create_core_block_registry(), UVS)

    assert mesh.vertices.shape == (24, 10)
    assert mesh.face_count == 6
    assert mesh.triangle_count == 12


def test_adjacent_blocks_hide_shared_faces() -> None:
    section = lit_section()
    section.set_block(1, 1, 1, 1)
    section.set_block(2, 1, 1, 1)

    mesh = build_visible_face_mesh(section, create_core_block_registry(), UVS)

    assert mesh.face_count == 10
    assert mesh.triangle_count == 20


def test_empty_section_produces_empty_arrays() -> None:
    mesh = build_visible_face_mesh(lit_section(), create_core_block_registry(), UVS)

    assert mesh.vertices.shape == (0, 10)
    assert mesh.indices.size == 0


def test_vertex_light_and_ao_can_be_toggled() -> None:
    section = lit_section()
    section.sky_light[3:, :, :] = 0
    section.set_block(1, 1, 1, 1)
    section.set_block(2, 2, 1, 1)

    smooth = build_visible_face_mesh(
        section,
        create_core_block_registry(),
        UVS,
        smooth_lighting=True,
        ambient_occlusion=True,
    )
    flat = build_visible_face_mesh(
        section,
        create_core_block_registry(),
        UVS,
        smooth_lighting=False,
        ambient_occlusion=False,
    )

    assert smooth.vertices[:, 8].min() < smooth.vertices[:, 8].max()
    assert smooth.vertices[:, 9].min() < 1.0
    assert flat.vertices[:, 9].min() == 1.0
