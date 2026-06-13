from __future__ import annotations

from pathlib import Path

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.generation import ChunkStreamer, TerrainGenerator, WorldSeed
from voxel_sandbox.infrastructure.storage import WorldStorage


def test_modified_chunk_persists_across_streamer_restart(tmp_path: Path) -> None:
    storage = WorldStorage(tmp_path / "persistent-world")
    storage.ensure_world(name="Persistent", seed="restart-seed")
    generator = TerrainGenerator(WorldSeed.parse("restart-seed"))
    first = ChunkStreamer(generator, render_distance=0, workers=1, storage=storage)
    try:
        first.prime(ChunkCoord(0, 0))
        assert first.set_block(8, 40, 8, 10)
        assert first.save_dirty() == 1
    finally:
        first.close()

    second = ChunkStreamer(generator, render_distance=0, workers=1, storage=storage)
    try:
        second.prime(ChunkCoord(0, 0))
        assert second.get_block(8, 40, 8) == 10
    finally:
        second.close()
