from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.generation import (
    ChunkStreamer,
    TerrainGenerator,
    WorldSeed,
    find_safe_spawn,
)
from voxel_sandbox.engine.physics import PlayerController, PlayerInput


def test_player_settles_on_generated_terrain() -> None:
    generator = TerrainGenerator(WorldSeed.parse("player-integration"))
    streamer = ChunkStreamer(generator, render_distance=0, workers=1)
    registry = create_core_block_registry()
    try:
        streamer.prime(ChunkCoord(0, 0))
        expected_ground = generator.height_at(8, 8)
        player = PlayerController(x=8.5, y=float(expected_ground + 4), z=8.5)

        for _ in range(180):
            player.update(
                PlayerInput(),
                -90.0,
                1.0 / 60.0,
                lambda x, y, z: registry.by_id(streamer.get_block(x, y, z)).is_solid,
            )

        assert abs(player.y - expected_ground) < 0.01
        assert player.on_ground
    finally:
        streamer.close()


def test_safe_spawn_is_clear_in_featured_generated_chunk() -> None:
    generator = TerrainGenerator(WorldSeed.parse("veilstone-dev"))
    streamer = ChunkStreamer(generator, render_distance=0, workers=1)
    registry = create_core_block_registry()
    try:
        streamer.prime(ChunkCoord(0, 0))
        spawn = find_safe_spawn(
            streamer.get_block,
            generator.height_at,
            lambda block_id: registry.by_id(block_id).is_solid,
        )
        x, y, z = int(spawn[0]), int(spawn[1]), int(spawn[2])

        assert registry.by_id(streamer.get_block(x, y - 1, z)).is_solid
        assert not registry.by_id(streamer.get_block(x, y, z)).is_solid
        assert not registry.by_id(streamer.get_block(x, y + 1, z)).is_solid
    finally:
        streamer.close()
