from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from voxel_sandbox.engine.chunks import Chunk, ChunkCoord


@runtime_checkable
class HeightProvider(Protocol):
    def height_at(self, world_x: int, world_z: int) -> int: ...
    def biome_key_at(self, world_x: int, world_z: int) -> str: ...


@runtime_checkable
class SurfacePlacer(Protocol):
    def fill_column(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        local_x: int,
        local_z: int,
        height: int,
        water_level: int,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None: ...


@runtime_checkable
class FeatureDecorator(Protocol):
    def decorate(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class DimensionDef:
    water_level: int
    height_provider: HeightProvider
    surface_placer: SurfacePlacer
    feature_decorators: tuple[FeatureDecorator, ...]
