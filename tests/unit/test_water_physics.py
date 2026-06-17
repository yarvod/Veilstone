"""Tests for water physics: swimming, raycast through water, fluid simulation."""

from __future__ import annotations

import math

from voxel_sandbox.engine.chunks import Chunk, ChunkCoord
from voxel_sandbox.engine.fluids import FLUID_MAX_LEVEL, WATER_BLOCK_ID, simulate_water_step
from voxel_sandbox.engine.physics.player import PlayerController, PlayerInput
from voxel_sandbox.engine.physics.raycast import RaycastHit, voxel_raycast


STONE = 1
AIR = 0
WATER = WATER_BLOCK_ID


def _flat_world(water_y: int | None = None):
    def get_block(x: int, y: int, z: int) -> int:
        if y < 0 or y > 127:
            return 0
        if y < 30:
            return STONE
        if water_y is not None and 30 <= y <= water_y:
            return WATER
        return AIR
    return get_block


def _is_solid(x: int, y: int, z: int) -> bool:
    block = _flat_world()(x, y, z)
    return block != 0 and block != WATER


def _is_solid_with_water(water_y: int):
    get = _flat_world(water_y)
    def check(x: int, y: int, z: int) -> bool:
        block = get(x, y, z)
        return block != 0 and block != WATER
    return check


def _is_fluid(water_y: int):
    get = _flat_world(water_y)
    def check(x: int, y: int, z: int) -> bool:
        return get(x, y, z) == WATER
    return check


class TestPlayerSwimming:
    def test_player_enters_water_without_getting_stuck(self):
        player = PlayerController(x=5.0, y=32.0, z=5.0)
        solid = _is_solid_with_water(34)
        fluid = _is_fluid(34)
        get_block = _flat_world(34)
        inp = PlayerInput()
        for _ in range(20):
            player.update(inp, 0.0, 1 / 60, get_block, is_solid=solid, is_fluid=fluid)
        assert player.in_water

    def test_player_swims_up_with_jump(self):
        player = PlayerController(x=5.0, y=31.0, z=5.0)
        solid = _is_solid_with_water(35)
        fluid = _is_fluid(35)
        get_block = _flat_world(35)
        inp = PlayerInput(jump=True)
        initial_y = player.y
        for _ in range(30):
            player.update(inp, 0.0, 1 / 60, get_block, is_solid=solid, is_fluid=fluid)
        assert player.y > initial_y

    def test_player_sinks_without_jump(self):
        player = PlayerController(x=5.0, y=33.0, z=5.0)
        solid = _is_solid_with_water(38)
        fluid = _is_fluid(38)
        get_block = _flat_world(38)
        inp = PlayerInput()
        initial_y = player.y
        for _ in range(60):
            player.update(inp, 0.0, 1 / 60, get_block, is_solid=solid, is_fluid=fluid)
        assert player.y <= initial_y

    def test_swim_speed_slower_than_walk(self):
        player = PlayerController()
        assert player.swim_speed < player.walk_speed

    def test_in_water_flag_set_correctly(self):
        player = PlayerController(x=5.0, y=31.0, z=5.0)
        solid = _is_solid_with_water(35)
        fluid = _is_fluid(35)
        get_block = _flat_world(35)
        player.update(PlayerInput(), 0.0, 1 / 60, get_block, is_solid=solid, is_fluid=fluid)
        assert player.in_water

    def test_not_in_water_on_land(self):
        player = PlayerController(x=5.0, y=30.0, z=5.0)
        solid = _is_solid_with_water(28)
        fluid = _is_fluid(28)
        get_block = _flat_world(28)
        player.update(PlayerInput(), 0.0, 1 / 60, get_block, is_solid=solid, is_fluid=fluid)
        assert not player.in_water


class TestRaycastThroughWater:
    def test_raycast_passes_through_water(self):
        def get_block(x: int, y: int, z: int) -> int:
            if y == 30:
                return WATER
            if y == 29:
                return STONE
            return AIR

        hit = voxel_raycast(
            get_block,
            (0.5, 32.5, 0.5),
            (0.0, -1.0, 0.0),
            10.0,
            skip_block=lambda bid: bid == WATER,
        )
        assert hit is not None
        assert hit.block == (0, 29, 0)
        assert hit.block_id == STONE

    def test_raycast_stops_at_water_without_skip(self):
        def get_block(x: int, y: int, z: int) -> int:
            if y == 30:
                return WATER
            if y == 29:
                return STONE
            return AIR

        hit = voxel_raycast(
            get_block,
            (0.5, 32.5, 0.5),
            (0.0, -1.0, 0.0),
            10.0,
        )
        assert hit is not None
        assert hit.block_id == WATER

    def test_raycast_skip_block_none_hits_water(self):
        def get_block(x: int, y: int, z: int) -> int:
            if y == 30:
                return WATER
            return AIR

        hit = voxel_raycast(get_block, (0.5, 32.5, 0.5), (0.0, -1.0, 0.0), 5.0)
        assert hit is not None
        assert hit.block_id == WATER


class TestWaterSimulation:
    def _make_chunk_with_water(self, positions: list[tuple[int, int, int]], level: int = FLUID_MAX_LEVEL) -> Chunk:
        chunk = Chunk(ChunkCoord(0, 0))
        for x in range(16):
            for z in range(16):
                chunk.set_block(x, 0, z, STONE)
        for x, y, z in positions:
            chunk.set_block(x, y, z, WATER)
            chunk.set_metadata(x, y, z, level)
        return chunk

    def test_water_flows_down(self):
        chunk = self._make_chunk_with_water([(5, 5, 5)])
        result = simulate_water_step(chunk)
        assert result.changed
        assert chunk.get_block(5, 4, 5) == WATER

    def test_water_spreads_horizontally(self):
        chunk = self._make_chunk_with_water([(5, 1, 5)])
        result = simulate_water_step(chunk)
        assert result.changed
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            assert chunk.get_block(5 + dx, 1, 5 + dz) == WATER

    def test_water_level_decays_horizontally(self):
        chunk = self._make_chunk_with_water([(5, 1, 5)])
        simulate_water_step(chunk)
        section = chunk.sections[0]
        neighbor_level = int(section.metadata[6, 1, 5])
        source_level = int(section.metadata[5, 1, 5]) or FLUID_MAX_LEVEL
        assert neighbor_level < source_level

    def test_flowing_water_drains_without_source(self):
        chunk = self._make_chunk_with_water([(5, 1, 5)], level=3)
        result = simulate_water_step(chunk)
        assert chunk.get_block(5, 1, 5) == AIR

    def test_source_water_does_not_drain(self):
        chunk = self._make_chunk_with_water([(5, 1, 5)], level=FLUID_MAX_LEVEL)
        simulate_water_step(chunk)
        assert chunk.get_block(5, 1, 5) == WATER

    def test_water_does_not_spread_past_level_1(self):
        chunk = self._make_chunk_with_water([(5, 1, 5)], level=1)
        simulate_water_step(chunk)
        assert chunk.get_block(6, 1, 5) == AIR
