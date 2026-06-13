from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkSection

HALO_RADIUS = 2
HALO_SIZE = SECTION_SIZE + HALO_RADIUS * 2
CENTER = slice(HALO_RADIUS, HALO_RADIUS + SECTION_SIZE)


@dataclass(frozen=True, slots=True)
class MeshingNeighborhood:
    blocks: NDArray[np.uint16]
    sky_light: NDArray[np.uint8]
    block_light: NDArray[np.uint8]

    @classmethod
    def from_section(cls, section: ChunkSection) -> MeshingNeighborhood:
        padding = ((HALO_RADIUS, HALO_RADIUS),) * 3
        return cls(
            np.pad(section.blocks, padding),
            np.pad(section.sky_light, padding),
            np.pad(section.block_light, padding),
        )

    @property
    def center_blocks(self) -> NDArray[np.uint16]:
        return self.blocks[CENTER, CENTER, CENTER]


def as_neighborhood(source: ChunkSection | MeshingNeighborhood) -> MeshingNeighborhood:
    if isinstance(source, MeshingNeighborhood):
        return source
    return MeshingNeighborhood.from_section(source)
