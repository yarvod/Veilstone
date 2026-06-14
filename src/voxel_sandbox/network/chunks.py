from __future__ import annotations

import zlib

import numpy as np

from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, SECTION_SIZE, Chunk, ChunkCoord


def encode_chunk_blocks(chunk: Chunk) -> bytes:
    blocks = np.concatenate([section.blocks for section in chunk.sections], axis=1)
    return zlib.compress(blocks.astype("<u2", copy=False).tobytes(), level=3)


def decode_chunk_blocks(coord: ChunkCoord, payload: bytes) -> Chunk:
    raw = zlib.decompress(payload)
    expected = SECTION_SIZE * CHUNK_HEIGHT * SECTION_SIZE * 2
    if len(raw) != expected:
        raise ValueError(f"Invalid network chunk size: {len(raw)} != {expected}")
    blocks = np.frombuffer(raw, "<u2").reshape((SECTION_SIZE, CHUNK_HEIGHT, SECTION_SIZE))
    chunk = Chunk(coord)
    for section_index, section in enumerate(chunk.sections):
        start = section_index * SECTION_SIZE
        section.blocks[:] = blocks[:, start : start + SECTION_SIZE, :]
        section.revision = 1
    return chunk
