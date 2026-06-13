from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import Chunk, ChunkCoord, ChunkSection
from voxel_sandbox.engine.fluids import simulate_water_step
from voxel_sandbox.render.meshes import build_greedy_mesh, build_visible_face_mesh, build_water_mesh
from voxel_sandbox.tools.benchmark_mesher import UVS


def test_water_is_excluded_from_opaque_meshes() -> None:
    section = ChunkSection()
    section.set_block(1, 1, 1, 8)
    section.set_metadata(1, 1, 1, 8)
    registry = create_core_block_registry()

    assert build_visible_face_mesh(section, registry, UVS).indices.size == 0
    assert build_greedy_mesh(section, registry, UVS).indices.size == 0


def test_water_mesh_hides_shared_face_and_uses_fluid_level() -> None:
    section = ChunkSection()
    section.sky_light.fill(15)
    section.set_block(1, 1, 1, 8)
    section.set_metadata(1, 1, 1, 4)
    section.set_block(2, 1, 1, 8)
    section.set_metadata(2, 1, 1, 4)

    mesh = build_water_mesh(section, create_core_block_registry(), UVS)

    assert mesh.face_count == 10
    assert abs(float(mesh.vertices[:, 1].max()) - 1.5) < 0.001


def test_water_mesh_exposes_only_height_step_between_different_levels() -> None:
    section = ChunkSection()
    section.set_block(1, 1, 1, 8)
    section.set_metadata(1, 1, 1, 8)
    section.set_block(2, 1, 1, 8)
    section.set_metadata(2, 1, 1, 4)

    mesh = build_water_mesh(section, create_core_block_registry(), UVS)

    assert mesh.face_count == 11
    step_vertices = mesh.vertices[(mesh.vertices[:, 0] == 2.0) & (mesh.vertices[:, 5] == 1.0)]
    assert float(step_vertices[:, 1].min()) == 1.5
    assert float(step_vertices[:, 1].max()) == 2.0


def test_water_falls_then_spreads_horizontally_without_same_tick_cascade() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    chunk.set_block(8, 10, 8, 8)
    chunk.set_metadata(8, 10, 8, 8)

    first = simulate_water_step(chunk)

    assert first.changed
    assert chunk.get_block(8, 9, 8) == 8
    assert chunk.get_block(8, 8, 8) == 0

    chunk.set_block(8, 8, 8, 1)
    second = simulate_water_step(chunk)

    assert second.changed
    assert chunk.get_block(9, 9, 8) == 8
    section, local_y = divmod(9, 16)
    assert chunk.sections[section].metadata[9, local_y, 8] == 7
