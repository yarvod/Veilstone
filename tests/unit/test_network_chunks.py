from __future__ import annotations

import numpy as np

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.generation import TerrainGenerator, WorldSeed
from voxel_sandbox.network import decode_chunk_blocks, encode_chunk_blocks


def test_network_chunk_codec_roundtrip() -> None:
    chunk = TerrainGenerator(WorldSeed.parse("network-chunk")).generate_chunk(ChunkCoord(-1, 2))

    decoded = decode_chunk_blocks(chunk.coord, encode_chunk_blocks(chunk))

    for original, restored in zip(chunk.sections, decoded.sections, strict=True):
        assert np.array_equal(original.blocks, restored.blocks)
