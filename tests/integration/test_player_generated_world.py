from __future__ import annotations

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.generation import ChunkStreamer, TerrainGenerator, WorldSeed
from voxel_sandbox.engine.physics import PlayerController, PlayerInput


def test_player_settles_on_generated_terrain() -> None:
    generator = TerrainGenerator(WorldSeed.parse("player-integration"))
    streamer = ChunkStreamer(generator, render_distance=0, workers=1)
    try:
        streamer.prime(ChunkCoord(0, 0))
        expected_ground = generator.height_at(8, 8)
        player = PlayerController(x=8.5, y=float(expected_ground + 4), z=8.5)

        for _ in range(180):
            player.update(PlayerInput(), -90.0, 1.0 / 60.0, streamer.get_block)

        assert abs(player.y - expected_ground) < 0.01
        assert player.on_ground
    finally:
        streamer.close()
