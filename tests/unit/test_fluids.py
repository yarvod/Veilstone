from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import Chunk, ChunkCoord, ChunkSection, DirtyFlag
from voxel_sandbox.engine.fluids import FLUID_MAX_LEVEL, WATER_BLOCK_ID, simulate_water_step
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


def _chunk_with_stone_floor(coord: ChunkCoord) -> Chunk:
    chunk = Chunk(coord)
    for x in range(16):
        for z in range(16):
            chunk.set_block(x, 0, z, 1)  # stone floor
    return chunk


def _fluid_level(chunk: Chunk, x: int, y: int, z: int) -> int:
    section, local_y = divmod(y, 16)
    return int(chunk.sections[section].metadata[x, local_y, z])


def _clear_dirty(chunk: Chunk) -> None:
    for section in chunk.sections:
        section.clear_dirty()


def test_water_flows_across_chunk_boundary() -> None:
    """Water at the right edge of one chunk flows into the neighboring chunk."""
    left = _chunk_with_stone_floor(ChunkCoord(0, 0))
    right = _chunk_with_stone_floor(ChunkCoord(1, 0))

    # Source water at x=15 (right edge of left chunk)
    left.set_block(15, 1, 8, WATER_BLOCK_ID)
    left.set_metadata(15, 1, 8, FLUID_MAX_LEVEL)

    simulate_water_step(left, {(1, 0): right})

    # Water should have entered the neighboring chunk at x=0
    assert right.get_block(0, 1, 8) == WATER_BLOCK_ID


def test_cross_chunk_flow_reports_neighbor_change() -> None:
    left = _chunk_with_stone_floor(ChunkCoord(0, 0))
    right = _chunk_with_stone_floor(ChunkCoord(1, 0))

    left.set_block(15, 1, 8, WATER_BLOCK_ID)
    left.set_metadata(15, 1, 8, FLUID_MAX_LEVEL)

    result = simulate_water_step(left, {(1, 0): right})
    assert (1, 0) in result.neighbor_keys


def test_cross_chunk_flow_marks_dirty_sections_and_preserves_levels() -> None:
    left = _chunk_with_stone_floor(ChunkCoord(0, 0))
    right = _chunk_with_stone_floor(ChunkCoord(1, 0))
    left.set_block(15, 1, 8, WATER_BLOCK_ID)
    left.set_metadata(15, 1, 8, FLUID_MAX_LEVEL)
    _clear_dirty(left)
    _clear_dirty(right)

    result = simulate_water_step(left, {(1, 0): right})

    assert result.changed
    assert result.neighbor_keys == frozenset({(1, 0)})
    assert _fluid_level(left, 15, 1, 8) == FLUID_MAX_LEVEL
    assert _fluid_level(right, 0, 1, 8) == FLUID_MAX_LEVEL - 1
    assert left.sections[0].dirty & DirtyFlag.MESH
    assert left.sections[0].dirty & DirtyFlag.SAVE
    assert right.sections[0].dirty & DirtyFlag.MESH
    assert right.sections[0].dirty & DirtyFlag.LIGHTING
    assert right.sections[0].dirty & DirtyFlag.SAVE


def test_source_creation_level_update_marks_mesh_dirty() -> None:
    chunk = _chunk_with_stone_floor(ChunkCoord(0, 0))
    for x, z in (
        (4, 8),
        (5, 7),
        (5, 9),
        (6, 7),
        (6, 9),
        (7, 7),
        (7, 9),
        (8, 8),
    ):
        chunk.set_block(x, 1, z, 1)
    chunk.set_block(5, 1, 8, WATER_BLOCK_ID)
    chunk.set_metadata(5, 1, 8, FLUID_MAX_LEVEL)
    chunk.set_block(7, 1, 8, WATER_BLOCK_ID)
    chunk.set_metadata(7, 1, 8, FLUID_MAX_LEVEL)

    simulate_water_step(chunk)
    assert _fluid_level(chunk, 6, 1, 8) == FLUID_MAX_LEVEL - 1
    _clear_dirty(chunk)

    result = simulate_water_step(chunk)

    assert result.changed_blocks == 1
    assert _fluid_level(chunk, 6, 1, 8) == FLUID_MAX_LEVEL
    assert chunk.sections[0].dirty & DirtyFlag.MESH
    assert chunk.sections[0].dirty & DirtyFlag.SAVE


def test_water_source_created_from_two_adjacent_sources() -> None:
    """A gap between two source blocks fills and becomes a source."""
    chunk = _chunk_with_stone_floor(ChunkCoord(0, 0))

    # Two source blocks with a gap: (5,1,8) - gap at (6,1,8) - (7,1,8)
    chunk.set_block(5, 1, 8, WATER_BLOCK_ID)
    chunk.set_metadata(5, 1, 8, FLUID_MAX_LEVEL)
    chunk.set_block(7, 1, 8, WATER_BLOCK_ID)
    chunk.set_metadata(7, 1, 8, FLUID_MAX_LEVEL)

    # First step: both sources spread toward the gap
    simulate_water_step(chunk)
    # Gap now has flowing water
    assert chunk.get_block(6, 1, 8) == WATER_BLOCK_ID

    # Second step: the gap block is adjacent to 2 sources → becomes a source
    simulate_water_step(chunk)
    sec, local_y = divmod(1, 16)
    assert chunk.sections[sec].metadata[6, local_y, 8] == FLUID_MAX_LEVEL


def test_no_cross_chunk_flow_without_neighbor() -> None:
    """With no neighbor provided, water stops at the chunk boundary."""
    left = _chunk_with_stone_floor(ChunkCoord(0, 0))
    left.set_block(15, 1, 8, WATER_BLOCK_ID)
    left.set_metadata(15, 1, 8, FLUID_MAX_LEVEL)

    result = simulate_water_step(left, neighbors=None)
    assert not result.neighbor_keys
