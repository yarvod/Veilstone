from __future__ import annotations

import numpy as np

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkSection
from voxel_sandbox.render.meshes import (
    MeshingNeighborhood,
    build_greedy_mesh,
    build_visible_face_mesh,
)
from voxel_sandbox.render.meshes.neighborhood import HALO_RADIUS, HALO_SIZE
from voxel_sandbox.render.meshes.visible_faces import build_quad_indices
from voxel_sandbox.tools.benchmark_mesher import UVS


def lit_section() -> ChunkSection:
    section = ChunkSection()
    section.sky_light.fill(15)
    return section


def test_single_block_has_six_visible_faces() -> None:
    section = lit_section()
    section.set_block(1, 1, 1, 1)

    mesh = build_visible_face_mesh(section, create_core_block_registry(), UVS)

    assert mesh.vertices.shape == (24, 15)
    assert mesh.face_count == 6
    assert mesh.triangle_count == 12


def test_adjacent_blocks_hide_shared_faces() -> None:
    section = lit_section()
    section.set_block(1, 1, 1, 1)
    section.set_block(2, 1, 1, 1)

    mesh = build_visible_face_mesh(section, create_core_block_registry(), UVS)

    assert mesh.face_count == 10
    assert mesh.triangle_count == 20


def test_cutout_leaf_does_not_cull_neighbor_stone_face() -> None:
    section = lit_section()
    section.set_block(1, 1, 1, 1)
    section.set_block(2, 1, 1, 5)
    registry = create_core_block_registry()

    visible = build_visible_face_mesh(section, registry, UVS)
    greedy = build_greedy_mesh(section, registry, UVS)

    assert visible.face_count == 11
    assert visible.triangle_count == 22
    assert greedy.face_count == 11
    assert greedy.triangle_count == 22


def test_short_grass_uses_cross_quads_instead_of_cube_faces() -> None:
    section = lit_section()
    section.set_block(1, 1, 1, 13)
    registry = create_core_block_registry()

    visible = build_visible_face_mesh(section, registry, UVS)
    greedy = build_greedy_mesh(section, registry, UVS)

    assert visible.face_count == 4
    assert visible.triangle_count == 8
    assert greedy.face_count == 4
    assert greedy.triangle_count == 8
    assert round(float(visible.vertices[:, 0].min()), 2) == 1.12
    assert round(float(visible.vertices[:, 0].max()), 2) == 1.88
    assert round(float(visible.vertices[:, 1].min()), 2) == 1.0
    assert round(float(visible.vertices[:, 1].max()), 2) == 1.82
    assert np.allclose(visible.vertices[:, 5:8], (0.0, 1.0, 0.0))


def test_short_grass_samples_light_from_air_above() -> None:
    section = lit_section()
    section.sky_light.fill(0)
    section.sky_light[1, 2, 1] = 15
    section.set_block(1, 1, 1, 13)
    registry = create_core_block_registry()

    visible = build_visible_face_mesh(section, registry, UVS)
    greedy = build_greedy_mesh(section, registry, UVS)

    assert visible.face_count == 4
    assert greedy.face_count == 4
    assert visible.vertices[:, 8].min() == 1.0
    assert greedy.vertices[:, 8].min() == 1.0


def test_empty_section_produces_empty_arrays() -> None:
    mesh = build_visible_face_mesh(lit_section(), create_core_block_registry(), UVS)

    assert mesh.vertices.shape == (0, 15)
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
    assert smooth.vertices[:, 10].min() < 1.0
    assert flat.vertices[:, 10].min() == 1.0


def test_quad_diagonal_follows_vertex_brightness() -> None:
    import numpy as np

    sky = np.asarray(((1.0, 0.2, 1.0, 0.2),), dtype=np.float32)
    block = np.zeros((1, 4), dtype=np.float32)
    ao = np.ones((1, 4), dtype=np.float32)

    indices = build_quad_indices(sky, block, ao, vertex_offset=8)

    assert indices.tolist() == [8, 9, 11, 9, 10, 11]


def test_neighbor_halo_hides_boundary_face_and_supplies_light() -> None:
    import numpy as np

    blocks = np.zeros((HALO_SIZE, HALO_SIZE, HALO_SIZE), dtype=np.uint16)
    sky = np.full((HALO_SIZE, HALO_SIZE, HALO_SIZE), 15, dtype=np.uint8)
    block_light = np.zeros_like(sky)
    blocks[HALO_RADIUS + 15, HALO_RADIUS + 1, HALO_RADIUS + 1] = 1
    blocks[HALO_RADIUS + 16, HALO_RADIUS + 1, HALO_RADIUS + 1] = 1
    neighborhood = MeshingNeighborhood(blocks, sky, block_light)

    mesh = build_visible_face_mesh(neighborhood, create_core_block_registry(), UVS)

    assert mesh.face_count == 5
    assert mesh.vertices[:, 8].min() == 1.0


def test_greedy_meshing_reduces_flat_section_to_six_quads() -> None:
    import numpy as np

    blocks = np.zeros((HALO_SIZE, HALO_SIZE, HALO_SIZE), dtype=np.uint16)
    sky = np.full((HALO_SIZE, HALO_SIZE, HALO_SIZE), 15, dtype=np.uint8)
    block_light = np.zeros_like(sky)
    blocks[
        HALO_RADIUS : HALO_RADIUS + 16,
        HALO_RADIUS : HALO_RADIUS + 8,
        HALO_RADIUS : HALO_RADIUS + 16,
    ] = 1
    neighborhood = MeshingNeighborhood(blocks, sky, block_light)

    visible = build_visible_face_mesh(neighborhood, create_core_block_registry(), UVS)
    greedy = build_greedy_mesh(neighborhood, create_core_block_registry(), UVS)

    assert visible.triangle_count == 2048
    assert greedy.face_count == 6
    assert greedy.triangle_count == 12
    assert greedy.vertices[:, 3:5].max() == 16.0
