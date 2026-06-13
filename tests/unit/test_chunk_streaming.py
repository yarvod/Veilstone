from __future__ import annotations

import threading
import time

from voxel_sandbox.engine.chunks import Chunk, ChunkCoord
from voxel_sandbox.engine.generation import ChunkStreamer, TerrainGenerator, WorldSeed


class RecordingGenerator(TerrainGenerator):
    def __init__(self) -> None:
        super().__init__(WorldSeed.parse("stream-test"))
        self.thread_ids: set[int] = set()

    def generate_chunk(self, coord: ChunkCoord) -> Chunk:
        self.thread_ids.add(threading.get_ident())
        time.sleep(0.005)
        return super().generate_chunk(coord)


def test_streamer_generates_surrounding_chunks_off_thread_and_unloads() -> None:
    generator = RecordingGenerator()
    streamer = ChunkStreamer(generator, render_distance=1, workers=2)
    main_thread = threading.get_ident()
    try:
        center = ChunkCoord(0, 0)
        streamer.prime(center)
        assert streamer.loaded_count == 1

        deadline = time.monotonic() + 3.0
        while streamer.loaded_count < 9 and time.monotonic() < deadline:
            streamer.update(center, max_completed=9)
            time.sleep(0.005)

        assert streamer.loaded_count == 9
        assert any(thread_id != main_thread for thread_id in generator.thread_ids)

        batch = streamer.update(ChunkCoord(4, 0), max_completed=9)
        assert center in batch.unloaded
        assert streamer.loaded_count == 0
        assert streamer.pending_count > 0
    finally:
        streamer.close()
