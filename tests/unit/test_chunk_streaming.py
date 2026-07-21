# pyright: reportPrivateUsage=false

from __future__ import annotations

import threading
import time
from pathlib import Path

from voxel_sandbox.engine.chunks import Chunk, ChunkCoord, DirtyFlag
from voxel_sandbox.engine.generation import ChunkStreamer, TerrainGenerator, WorldSeed
from voxel_sandbox.infrastructure.storage import WorldStorage


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


def test_streamer_reconfigures_render_distance() -> None:
    streamer = ChunkStreamer(
        TerrainGenerator(WorldSeed.parse("distance-reconfigure")),
        render_distance=0,
        workers=1,
    )
    center = ChunkCoord(0, 0)
    try:
        streamer.prime(center)
        assert streamer.loaded_count == 1

        assert streamer.set_render_distance(1) is True
        deadline = time.monotonic() + 3.0
        while streamer.loaded_count < 9 and time.monotonic() < deadline:
            streamer.update(center, max_completed=9)
            time.sleep(0.005)
        assert streamer.loaded_count == 9

        assert streamer.set_render_distance(0) is True
        batch = streamer.update(center, max_completed=9)
        assert len(batch.unloaded) == 8
        assert streamer.loaded_count == 1
        assert streamer.set_render_distance(0) is False
    finally:
        streamer.close()


def test_streamer_reuses_desired_coords_until_center_or_distance_changes() -> None:
    streamer = ChunkStreamer(
        TerrainGenerator(WorldSeed.parse("desired-cache")),
        render_distance=1,
        workers=1,
    )
    center = ChunkCoord(0, 0)
    try:
        streamer.update(center, max_completed=0, max_submitted=0)
        first = streamer._desired
        assert streamer.expects_chunk(ChunkCoord(1, 1)) is True
        assert streamer.expects_chunk(ChunkCoord(2, 0)) is False

        streamer.update(center, max_completed=0, max_submitted=0)

        assert streamer._desired is first
        streamer.update(ChunkCoord(1, 0), max_completed=0, max_submitted=0)
        assert streamer._desired is not first
        second = streamer._desired
        assert streamer.set_render_distance(2) is True
        streamer.update(ChunkCoord(1, 0), max_completed=0, max_submitted=0)
        assert streamer._desired is not second
        assert len(streamer._desired) == 25
    finally:
        streamer.close()


def test_streamer_bounds_new_chunk_submissions_per_update() -> None:
    generator = RecordingGenerator()
    streamer = ChunkStreamer(generator, render_distance=2, workers=1)
    center = ChunkCoord(0, 0)

    try:
        streamer.prime(center)

        batch = streamer.update(center, max_completed=25, max_submitted=2)

        assert batch.loaded == ()
        assert streamer.loaded_count == 1
        assert streamer.pending_count == 2

        deadline = time.monotonic() + 3.0
        while streamer.loaded_count < 3 and time.monotonic() < deadline:
            streamer.update(center, max_completed=25, max_submitted=0)
            time.sleep(0.005)

        assert streamer.loaded_count == 3
        assert streamer.pending_count == 0

        streamer.update(center, max_completed=25, max_submitted=2)
        assert streamer.pending_count == 2
    finally:
        streamer.close()


def test_streamer_exposes_loaded_world_blocks_and_mutation() -> None:
    streamer = ChunkStreamer(
        TerrainGenerator(WorldSeed.parse("mutation-test")),
        render_distance=0,
        workers=1,
    )
    try:
        streamer.prime(ChunkCoord(0, 0))
        original = streamer.get_block(8, 1, 8)
        assert original != 0
        assert streamer.set_block(8, 1, 8, 0)
        assert streamer.get_block(8, 1, 8) == 0
        assert streamer.dirty_chunk_count == 1
        for section in streamer.get_chunk(ChunkCoord(0, 0)).sections:  # type: ignore[union-attr]
            section.clear_dirty(DirtyFlag.SAVE)
        assert streamer.dirty_chunk_count == 0
        assert not streamer.set_block(32, 1, 32, 1)

        streamer.update(ChunkCoord(4, 0), max_completed=0)
        assert streamer.get_chunk(ChunkCoord(0, 0)) is None
        reloaded = streamer.prime(ChunkCoord(0, 0))
        assert reloaded.get_block(8, 1, 8) == 0
    finally:
        streamer.close()


def test_region_snapshot_copies_blocks_and_light_across_chunk_boundary() -> None:
    streamer = ChunkStreamer(
        TerrainGenerator(WorldSeed.parse("snapshot-test")),
        render_distance=1,
        workers=1,
    )
    try:
        left = streamer.prime(ChunkCoord(-1, 0))
        right = streamer.prime(ChunkCoord(0, 0))
        left.set_block(15, 10, 2, 6)
        right.set_block(0, 10, 2, 7)
        right.set_metadata(0, 10, 2, 6)
        left.sections[0].sky_light[15, 10, 2] = 11
        right.sections[0].block_light[0, 10, 2] = 14

        blocks, sky, block, metadata = streamer.snapshot_region((-1, 9, 1), (3, 3, 3))

        assert blocks[0, 1, 1] == 6
        assert blocks[1, 1, 1] == 7
        assert sky[0, 1, 1] == 11
        assert block[1, 1, 1] == 14
        assert metadata[1, 1, 1] == 6
    finally:
        streamer.close()


def test_streamer_preserves_fluid_level_across_reload() -> None:
    streamer = ChunkStreamer(
        TerrainGenerator(WorldSeed.parse("fluid-override")),
        render_distance=0,
        workers=1,
    )
    try:
        streamer.prime(ChunkCoord(0, 0))
        assert streamer.set_fluid(8, 40, 8, 8, 5)
        assert streamer.get_metadata(8, 40, 8) == 5

        streamer.update(ChunkCoord(4, 0), max_completed=0)
        streamer.prime(ChunkCoord(0, 0))

        assert streamer.get_block(8, 40, 8) == 8
        assert streamer.get_metadata(8, 40, 8) == 5
    finally:
        streamer.close()


def test_streamer_limits_deferred_unload_saves_per_update(tmp_path: Path) -> None:
    storage = WorldStorage(tmp_path / "deferred-save-world")
    storage.ensure_world(name="Deferred", seed="deferred-save")
    streamer = ChunkStreamer(
        TerrainGenerator(WorldSeed.parse("deferred-save")),
        render_distance=1,
        workers=1,
        storage=storage,
    )
    try:
        for x in range(-1, 2):
            for z in range(-1, 2):
                streamer.prime(ChunkCoord(x, z))

        streamer.update(ChunkCoord(10, 0), max_completed=0, max_submitted=0)

        assert streamer.loaded_count == 0
        assert streamer.pending_save_count == 8
        assert len(tuple(storage.regions.glob("*.vchk"))) == 1

        streamer.update(ChunkCoord(10, 0), max_completed=0, max_submitted=0)

        assert streamer.pending_save_count == 7
        assert len(tuple(storage.regions.glob("*.vchk"))) == 2

        restored = streamer.update(ChunkCoord(0, 0), max_completed=1, max_submitted=0)

        assert len(restored.loaded) == 1
        assert restored.loaded[0].coord in {
            ChunkCoord(x, z) for x in range(-1, 2) for z in range(-1, 2)
        }
        assert streamer.loaded_count == 1
        assert streamer.pending_count == 0
    finally:
        streamer.close()
